"""Refresh the Central Bank Compass FRED observations into this repo's cache.

Owner approval: 2026-11-22 ("批准刷新").

- Writes only to .cache/compass_fred/. The nested Compass repo (and its data/cache/fred) is never written.
- First run seeds .cache/compass_fred/ by copying the Compass cache; existing files there are kept.
- The FRED key is read from the Compass .env and never printed.
- Prints, per series, the latest observation date before and after.

Usage: python3 scripts/refresh_compass_data.py [--seed-only]
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from macro_world import COMPASS_CACHE_DIR, COMPASS_DIR, CentralBankCompassAdapter  # noqa: E402

NESTED_CACHE = COMPASS_DIR / "data" / "cache" / "fred"


def latest_date(path: Path) -> str | None:
    try:
        lines = [line for line in path.read_text().splitlines()[1:] if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        date, _, value = line.partition(",")
        if value.strip():
            return date[:10]
    return None


def seed() -> int:
    COMPASS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sorted(NESTED_CACHE.glob("*.csv")):
        target = COMPASS_CACHE_DIR / source.name
        if not target.exists():
            shutil.copy2(source, target)
            copied += 1
    return copied


def main() -> int:
    copied = seed()
    print(f"Seeded {copied} files into {COMPASS_CACHE_DIR.relative_to(ROOT)} (existing files kept).")
    if "--seed-only" in sys.argv:
        return 0
    from dotenv import dotenv_values
    key = (dotenv_values(COMPASS_DIR / ".env").get("FRED_API_KEY") or os.getenv("FRED_API_KEY") or "").strip()
    if not key:
        print("No FRED_API_KEY found; nothing refreshed.")
        return 1
    before = {path.stem: latest_date(path) for path in COMPASS_CACHE_DIR.glob("*.csv")}
    os.environ["FRED_API_KEY"] = key
    os.environ["CBC_FRED_OFFLINE"] = "0"
    adapter = CentralBankCompassAdapter()
    modules = adapter._modules()
    fred = modules["fred"]
    assert Path(fred.CACHE_DIR).resolve() == COMPASS_CACHE_DIR.resolve(), "refusing to write outside .cache/compass_fred"
    config = modules["config"].load_config(COMPASS_DIR / "config.yaml")
    for series_id in sorted(fred.configured_series_ids(config)):
        fred.fetch_series(series_id, config)
    for region in ("US", "JP", "SG", "EURO_AREA"):   # also caches series the models fetch directly
        adapter.load(region)
    after = {path.stem: latest_date(path) for path in COMPASS_CACHE_DIR.glob("*.csv")}
    changed = 0
    for series_id in sorted(after):
        old, new = before.get(series_id), after[series_id]
        mark = "" if old == new else "  <- updated" if old else "  <- new"
        changed += bool(mark)
        print(f"{series_id:28s} {old or '—':>10s} -> {new or '—':>10s}{mark}")
    failed = [sid for sid, diag in getattr(fred, "_FETCH_DIAGNOSTICS", {}).items() if diag.get("data_source") != "FRED_LIVE"]
    print(f"{changed} series updated or added; {len(failed)} fetches fell back to cache: {', '.join(sorted(failed)) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
