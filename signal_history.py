"""Append-only signal history for CHAINSTOX (checklist P2).

Every refresh used to overwrite the previous snapshot, so the system could not say what
changed, where a reading sits in its own history, or how a signal performed. This module
keeps one row per (signal_id, observation_date):

    data/history/<family>.csv   family = text before the first "." in signal_id

Rules
- Append only. A key that already exists is never rewritten, so a later refresh cannot
  change history. Re-running a backfill is a no-op for dates already stored.
- Only LIVE refreshes and BACKFILL rows are written. CACHED and STALE payloads are
  re-readings of something already recorded.
- Missing values are not stored as zero. A row needs a finite value or a label.
- BACKFILL rows are recomputed from Yahoo daily closes with the same pure functions the
  live engine calls (Valuation_model.sector_row_from_histories, macro_scores and the
  risk_regime collector). They use only the Yahoo leg of compute_macro's provider
  fallbacks and a trailing 365-calendar-day window to mirror the live "1y" fetch.

CLI
    python signal_history.py backfill --years 2
    python signal_history.py show sector.XLV.rel_6m
    python signal_history.py ids [prefix]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_HISTORY_DIR = ROOT / "data" / "history"
FIELDS = ["signal_id", "observation_date", "value", "label", "source", "source_state", "recorded_at"]
RECORDED_STATES = {"LIVE", "BACKFILL"}
BACKFILL_SOURCE = "Yahoo daily closes (backfill)"  # recomputed with the live engine functions


def history_dir() -> Path:
    return Path(os.environ.get("CHAINSTOX_HISTORY_DIR") or DEFAULT_HISTORY_DIR)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        return None
    return text


@dataclass(frozen=True)
class Observation:
    signal_id: str
    observation_date: str
    value: float | None
    label: str | None
    source: str
    source_state: str

    @property
    def key(self) -> tuple[str, str]:
        return self.signal_id, self.observation_date


def observation(signal_id: str, date: Any, value: Any = None, label: Any = None, *, source: str, source_state: str) -> Observation | None:
    """Build a storable observation, or None when it has no date or no content."""
    day = _date(date)
    number = _finite(value)
    text = None if label is None or str(label).strip() == "" else str(label)
    if day is None or (number is None and text is None):
        return None
    return Observation(signal_id, day, number, text, source, source_state)


class SignalStore:
    """CSV-backed append-only store with a small read API (checklist 2.3)."""

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory) if directory else history_dir()
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    @staticmethod
    def family(signal_id: str) -> str:
        return signal_id.split(".", 1)[0]

    def _path(self, family: str) -> Path:
        return self.directory / f"{family}.csv"

    def _rows(self, family: str) -> list[dict[str, Any]]:
        path = self._path(family)
        if not path.exists():
            return []
        mtime = path.stat().st_mtime
        cached = self._cache.get(family)
        if cached and cached[0] == mtime:
            return cached[1]
        rows = []
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row["value"] = float(row["value"]) if row["value"] not in ("", None) else None
                row["label"] = row["label"] or None
                rows.append(row)
        rows.sort(key=lambda item: (item["signal_id"], item["observation_date"]))
        self._cache[family] = (mtime, rows)
        return rows

    def append(self, observations: Iterable[Observation | None]) -> int:
        """Write observations whose (signal_id, observation_date) is not stored yet."""
        by_family: dict[str, list[Observation]] = {}
        for item in observations:
            if item is None:
                continue
            if item.source_state not in RECORDED_STATES:
                raise ValueError(f"Only {sorted(RECORDED_STATES)} observations are recorded, got {item.source_state}.")
            by_family.setdefault(self.family(item.signal_id), []).append(item)
        written = 0
        recorded_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        for family, items in by_family.items():
            existing = {(row["signal_id"], row["observation_date"]) for row in self._rows(family)}
            fresh: dict[tuple[str, str], Observation] = {}
            for item in items:
                if item.key not in existing and item.key not in fresh:
                    fresh[item.key] = item
            if not fresh:
                continue
            path = self._path(family)
            path.parent.mkdir(parents=True, exist_ok=True)
            new_file = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                if new_file:
                    writer.writeheader()
                for item in sorted(fresh.values(), key=lambda obs: obs.key):
                    writer.writerow({
                        "signal_id": item.signal_id,
                        "observation_date": item.observation_date,
                        "value": "" if item.value is None else repr(item.value),
                        "label": item.label or "",
                        "source": item.source,
                        "source_state": item.source_state,
                        "recorded_at": recorded_at,
                    })
            self._cache.pop(family, None)
            written += len(fresh)
        return written

    # ---- read API -------------------------------------------------------------------
    def rows(self, signal_id: str, as_of: str | None = None) -> list[dict[str, Any]]:
        limit = _date(as_of) if as_of else None
        return [row for row in self._rows(self.family(signal_id)) if row["signal_id"] == signal_id and (limit is None or row["observation_date"] <= limit)]

    def series(self, signal_id: str, as_of: str | None = None) -> list[tuple[str, float]]:
        """(date, value) pairs in date order; label-only rows are skipped."""
        return [(row["observation_date"], row["value"]) for row in self.rows(signal_id, as_of) if row["value"] is not None]

    def labels(self, signal_id: str, as_of: str | None = None) -> list[tuple[str, str]]:
        return [(row["observation_date"], row["label"]) for row in self.rows(signal_id, as_of) if row["label"]]

    def latest(self, signal_id: str, as_of: str | None = None) -> dict[str, Any] | None:
        rows = self.rows(signal_id, as_of)
        return rows[-1] if rows else None

    def value_days_ago(self, signal_id: str, days: int, as_of: str | None = None) -> tuple[str, float] | None:
        """The last stored value on or before (as_of - days calendar days)."""
        anchor = _date(as_of) or (self.series(signal_id) or [(None, None)])[-1][0]
        if anchor is None:
            return None
        target = (dt.date.fromisoformat(anchor) - dt.timedelta(days=days)).isoformat()
        points = self.series(signal_id, target)
        return points[-1] if points else None

    def value_observations_ago(self, signal_id: str, count: int, as_of: str | None = None) -> tuple[str, float] | None:
        """The value `count` stored observations before the latest one on or before as_of."""
        points = self.series(signal_id, as_of)
        return points[-1 - count] if len(points) > count else None

    def percentile(self, signal_id: str, value: float | None = None, as_of: str | None = None, min_observations: int = 60) -> float | None:
        """Share (0-1) of stored values on or before as_of that are <= value.

        value defaults to the latest stored value. Returns None with fewer than
        min_observations points, rather than a percentile from a thin sample.
        """
        points = [number for _, number in self.series(signal_id, as_of)]
        if len(points) < min_observations:
            return None
        current = _finite(value) if value is not None else points[-1]
        if current is None:
            return None
        return sum(number <= current for number in points) / len(points)

    def signal_ids(self, prefix: str | None = None) -> list[str]:
        families = [path.stem for path in sorted(self.directory.glob("*.csv"))] if self.directory.exists() else []
        ids = sorted({row["signal_id"] for family in families for row in self._rows(family)})
        return [item for item in ids if not prefix or item.startswith(prefix)]


# ---- extractors: engine payload -> observations ---------------------------------------
MACRO_VALUE_KEYS = (
    "tnx_level", "tnx_3m", "tyx_level", "tyx_3m", "front_rate_level", "front_rate_3m", "yield_curve",
    "dxy_level", "dxy_3m", "usdjpy_level", "usdjpy_3m", "vix_level", "m2_6m", "hyg_ief",
    "forward_pe", "earning_yield", "erp", "liquidity_score", "risk_score", "macro_score",
)
CATALYST_VALUE_KEYS = ("cpi_yoy", "core_cpi_yoy", "ppi_yoy", "nfp_change", "unemployment", "wages_yoy", "claims", "fed_future_rate", "fed_future_trend")
CATALYST_LABEL_KEYS = ("inflation_state", "labor_state", "fed_sensitivity")


def _latest_sector_date(payload: dict[str, Any]) -> str | None:
    dates = [_date(row.get("as_of")) for row in payload.get("sectors") or []]
    dates = [item for item in dates if item]
    return max(dates) if dates else None


def observations_from_core_market(payload: dict[str, Any], source_state: str, source: str = "Python core market engine") -> list[Observation]:
    output: list[Observation | None] = []
    market_date = _latest_sector_date(payload)
    for row in payload.get("sectors") or []:
        ticker, day = row.get("ticker"), row.get("as_of")
        for key in ("rel_1m", "rel_3m", "rel_6m", "breakout", "score"):
            output.append(observation(f"sector.{ticker}.{key}", day, row.get(key), source=source, source_state=source_state))
    macro = payload.get("macro") or {}
    macro_date = macro.get("tnx_observed_at") or market_date
    for key in MACRO_VALUE_KEYS:
        output.append(observation(f"macro.{key}", macro_date, macro.get(key), source=source, source_state=source_state))
    risk = payload.get("risk") or {}
    output.append(observation("risk.regime", market_date, label=risk.get("regime"), source=source, source_state=source_state))
    output.append(observation("risk.published_regime", market_date, label=risk.get("published_regime"), source=source, source_state=source_state))
    for key in ("coverage", "supporting_evidence", "conflicting_evidence"):
        output.append(observation(f"risk.{key}", market_date, risk.get(key), source=source, source_state=source_state))
    fragility = payload.get("fragility") or {}
    output.append(observation("fragility.label", market_date, label=fragility.get("label"), source=source, source_state=source_state))
    for key in ("consumer_sentiment", "ism_pmi", "breadth_proxy"):
        output.append(observation(f"fragility.{key}", market_date, fragility.get(key), source=source, source_state=source_state))
    catalysts = payload.get("catalysts") or {}
    for key in CATALYST_VALUE_KEYS:
        output.append(observation(f"catalyst.{key}", market_date, catalysts.get(key), source=source, source_state=source_state))
    for key in CATALYST_LABEL_KEYS:
        output.append(observation(f"catalyst.{key}", market_date, label=catalysts.get(key), source=source, source_state=source_state))
    return [item for item in output if item]


def observations_from_inflation(payload: dict[str, Any], source_state: str) -> list[Observation]:
    day = payload.get("latest_source") or payload.get("generated")
    source = "US Inflation Pressure Engine"
    output = [
        observation("inflation.near_term", day, label=payload.get("near_term"), source=source, source_state=source_state),
        observation("inflation.medium_term", day, label=payload.get("medium_term"), source=source, source_state=source_state),
        observation("inflation.fed_sensitivity", day, label=payload.get("fed_sensitivity"), source=source, source_state=source_state),
        observation("inflation.available_metrics", day, payload.get("available"), source=source, source_state=source_state),
    ]
    for key, metric in (payload.get("metrics") or {}).items():
        if isinstance(metric, dict):
            output.append(observation(f"inflation.metric.{key}", day, metric.get("current"), source=source, source_state=source_state))
    return [item for item in output if item]


def observations_from_neer(payload: dict[str, Any], source_state: str) -> list[Observation]:
    current = payload.get("current") or {}
    day, source = payload.get("as_of"), "Shadow S$NEER proxy"
    output = [observation(f"neer.{key}", day, current.get(key), source=source, source_state=source_state)
              for key in ("index", "estimated_center", "deviation_pct", "volatility_21d_ann_pct", "usd_per_sgd")]
    output.append(observation("neer.band_state", day, label=current.get("band_state"), source=source, source_state=source_state))
    return [item for item in output if item]


def observations_from_kospi(payload: dict[str, Any], source_state: str) -> list[Observation]:
    sweep = payload.get("sweep") or {}
    day, source = sweep.get("timestamp"), "KOSPI Multi-Factor Signal Monitor"
    output: list[Observation | None] = []
    for factor in sweep.get("results") or []:
        key = factor.get("key")
        observed = int((factor.get("detail") or {}).get("obs") or 0) > 0
        if not key or not observed:
            continue  # a factor with no observations has no data, not a zero correlation
        output.append(observation(f"kospi.factor.{key}.corr", day, factor.get("corr"), source=source, source_state=source_state))
        output.append(observation(f"kospi.factor.{key}.pval", day, factor.get("pval"), source=source, source_state=source_state))
        output.append(observation(f"kospi.factor.{key}.strength", day, label=factor.get("strength"), source=source, source_state=source_state))
    volatility = sweep.get("volatility") or {}
    output.append(observation("kospi.volatility.current", day, volatility.get("current_vol"), source=source, source_state=source_state))
    output.append(observation("kospi.volatility.regime", day, label=volatility.get("regime"), source=source, source_state=source_state))
    output.append(observation("kospi.regime", day, label=(sweep.get("interpretation") or {}).get("regime", {}).get("name"), source=source, source_state=source_state))
    return [item for item in output if item]


def observations_from_world(world: dict[str, Any], source_state: str) -> list[Observation]:
    output: list[Observation | None] = []
    for region_id, region in (world.get("regions") or {}).items():
        compass = (region.get("engine_specific") or {}).get("central_bank_compass") or {}
        day = compass.get("latest")
        if not compass.get("available") or not day:
            continue
        source = "Central Bank Compass"
        prefix = f"compass.{region_id}"
        output.append(observation(f"{prefix}.policy_score", day, compass.get("policy_score"), source=source, source_state=source_state))
        output.append(observation(f"{prefix}.signal", day, label=compass.get("signal"), source=source, source_state=source_state))
        output.append(observation(f"{prefix}.bias", day, label=compass.get("bias"), source=source, source_state=source_state))
        liquidity = compass.get("liquidity") or {}
        output.append(observation(f"{prefix}.liquidity_score", day, liquidity.get("score"), source=source, source_state=source_state))
        output.append(observation(f"{prefix}.liquidity_state", day, label=liquidity.get("classification"), source=source, source_state=source_state))
        for block, score in (compass.get("block_scores") or {}).items():
            output.append(observation(f"{prefix}.block.{block}", day, score, source=source, source_state=source_state))
        special = compass.get("special") or {}
        for horizon in ("probabilities_3m", "probabilities_6m"):
            for outcome, probability in (special.get(horizon) or {}).items():
                output.append(observation(f"{prefix}.{horizon}.{outcome}".lower(), day, probability, source=source, source_state=source_state))
        for outcome, probability in (special.get("probabilities") or {}).items():
            output.append(observation(f"{prefix}.probability.{outcome}".lower(), day, probability, source=source, source_state=source_state))
    return [item for item in output if item]


def observations_from_cftc(payload: dict[str, Any], source_state: str) -> list[Observation]:
    day = payload.get("as_of")
    source = payload.get("source") or "CFTC"
    output = [observation(f"cftc.jpy.{key}", day, payload.get(key), source=source, source_state=source_state)
              for key in ("leveraged_net", "leveraged_long", "leveraged_short", "open_interest")]
    return [item for item in output if item]


EXTRACTORS: dict[str, Callable[[dict[str, Any], str], list[Observation]]] = {
    "cftc": observations_from_cftc,
    "core-market": observations_from_core_market,
    "inflation": observations_from_inflation,
    "neer": observations_from_neer,
    "kospi": observations_from_kospi,
    "world": observations_from_world,
}


def record_module(name: str, payload: dict[str, Any] | None, source_state: str, store: SignalStore | None = None) -> dict[str, Any]:
    """Record a module payload. Never raises: history must not break a research refresh."""
    if os.environ.get("CHAINSTOX_RECORD_HISTORY", "1") == "0":
        return {"state": "DISABLED", "written": 0, "error": None}
    if source_state not in RECORDED_STATES or not payload or name not in EXTRACTORS:
        return {"state": "SKIPPED", "written": 0, "error": None}
    try:
        written = (store or SignalStore()).append(EXTRACTORS[name](payload, source_state))
        return {"state": "RECORDED", "written": written, "error": None}
    except Exception as exc:  # noqa: BLE001 - reported to the caller instead of raised
        return {"state": "FAILED", "written": 0, "error": f"{type(exc).__name__}: {exc}"}


# ---- backfill -------------------------------------------------------------------------
FRONT_RATE_TICKERS = ["2YY=F", "^IRX", "^FVX"]
MACRO_TICKERS = ["^TNX", "^TYX", "DX-Y.NYB", "JPY=X", "HYG", "IEF", "^VIX", *FRONT_RATE_TICKERS]


def trailing_window(frame, cutoff, days: int = 365):
    """Rows in (cutoff - days, cutoff], mirroring the live engine's '1y' fetch at that date."""
    if frame is None:
        return None
    import pandas as pd
    end = pd.Timestamp(cutoff)
    window = frame[(frame.index > end - pd.Timedelta(days=days)) & (frame.index <= end)]
    return window if len(window) else None


def macro_inputs_at(windows: dict[str, Any]) -> dict[str, Any]:
    """Yahoo-leg compute_macro inputs from date-truncated windows."""
    import Valuation_model as vm

    def level(frame):
        return float(frame["Close"].iloc[-1]) if frame is not None else None

    front_ticker = next((ticker for ticker in FRONT_RATE_TICKERS if windows.get(ticker) is not None), FRONT_RATE_TICKERS[0])
    front = windows.get(front_ticker)
    tnx_level, front_level = level(windows.get("^TNX")), level(front)
    yield_curve = None
    if vm.is_number(tnx_level) and vm.is_number(front_level) and front_ticker != "^IRX":
        yield_curve = (tnx_level - front_level) / 100
    return {
        "tnx_level": tnx_level,
        "tnx_3m": vm.price_change(windows.get("^TNX"), 63),
        "tyx_level": level(windows.get("^TYX")),
        "tyx_3m": vm.price_change(windows.get("^TYX"), 63),
        "front_rate_ticker": front_ticker,
        "front_rate_level": front_level,
        "front_rate_3m": vm.price_change(front, 63),
        "yield_curve": yield_curve,
        "dxy_level": level(windows.get("DX-Y.NYB")),
        "dxy_3m": vm.price_change(windows.get("DX-Y.NYB"), 63),
        "usdjpy_level": level(windows.get("JPY=X")),
        "usdjpy_3m": vm.price_change(windows.get("JPY=X"), 63),
        "vix_level": level(windows.get("^VIX")),
        "hyg_ief": vm.relative_change_from_histories(windows.get("HYG"), windows.get("IEF"), 63),
    }


def backfill_observations_at(cutoff, histories: dict[str, Any]) -> list[Observation]:
    """All price-derived signals for one historical cutoff date."""
    import Valuation_model as vm
    from risk_regime import analyze_risk_regime, collect_risk_regime_data

    day = str(cutoff)[:10]
    state, source = "BACKFILL", BACKFILL_SOURCE
    windows = {ticker: trailing_window(frame, cutoff) for ticker, frame in histories.items()}
    output: list[Observation | None] = []
    spy = windows.get("SPY")
    for ticker, name in vm.SECTOR_ETFS.items():
        window = windows.get(ticker)
        if window is None or spy is None:
            continue
        row = vm.sector_row_from_histories(ticker, name, window, spy)
        for key in ("rel_1m", "rel_3m", "rel_6m", "breakout", "score"):
            output.append(observation(f"sector.{ticker}.{key}", row["as_of"], row[key], source=source, source_state=state))
    inputs = macro_inputs_at(windows)
    scores = vm.macro_scores(inputs["tnx_3m"], inputs["front_rate_3m"], inputs["dxy_3m"], inputs["yield_curve"], inputs["hyg_ief"], inputs["vix_level"])
    for key, value in {**inputs, **scores}.items():
        if key != "front_rate_ticker":
            output.append(observation(f"macro.{key}", day, value, source=source, source_state=state))
    risk = analyze_risk_regime(collect_risk_regime_data(lambda ticker, period="1y": windows.get(ticker)))
    output.append(observation("risk.regime", day, label=risk.get("regime"), source=source, source_state=state))
    output.append(observation("risk.published_regime", day, label=risk.get("published_regime"), source=source, source_state=state))
    for key in ("coverage", "supporting_evidence", "conflicting_evidence"):
        output.append(observation(f"risk.{key}", day, risk.get(key), source=source, source_state=state))
    return [item for item in output if item]


def fetch_long_histories(tickers: Iterable[str], period: str = "5y") -> tuple[dict[str, Any], dict[str, str]]:
    import pandas as pd
    from data_sources.market_history import fetch_yahoo_history

    histories, failures = {}, {}
    for ticker in sorted(set(tickers)):
        try:
            result = fetch_yahoo_history(ticker, period=period)
        except Exception as exc:  # noqa: BLE001 - reported per ticker
            failures[ticker] = f"{type(exc).__name__}: {exc}"
            continue
        if not result.observations:
            failures[ticker] = result.error or result.limitation or "no observations"
            continue
        histories[ticker] = pd.DataFrame(
            {"Close": [item.value for item in result.observations]},
            index=pd.to_datetime([item.date for item in result.observations]),
        )
    return histories, failures


def backfill(years: float = 2.0, store: SignalStore | None = None, histories: dict[str, Any] | None = None, period: str = "5y") -> dict[str, Any]:
    import Valuation_model as vm
    from risk_regime import ALL_TICKERS

    failures: dict[str, str] = {}
    if histories is None:
        histories, failures = fetch_long_histories(["SPY", *vm.SECTOR_ETFS, *MACRO_TICKERS, *ALL_TICKERS], period=period)
    spy = histories.get("SPY")
    if spy is None:
        return {"state": "FAILED", "written": 0, "cutoffs": 0, "failures": failures, "error": "SPY history unavailable; no trading calendar."}
    start = spy.index[-1] - dt.timedelta(days=int(365 * years))
    cutoffs = [day for day in spy.index if day >= start]
    store = store or SignalStore()
    written = 0
    for cutoff in cutoffs:
        written += store.append(backfill_observations_at(cutoff, histories))
    return {
        "state": "COMPLETED", "written": written, "cutoffs": len(cutoffs),
        "first_cutoff": str(cutoffs[0])[:10] if cutoffs else None, "last_cutoff": str(cutoffs[-1])[:10] if cutoffs else None,
        "tickers": len(histories), "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX signal history")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("backfill", help="Recompute price-derived signals from Yahoo history and append them.")
    run.add_argument("--years", type=float, default=2.0)
    run.add_argument("--period", default="5y", help="Yahoo range to download (must cover years + one year of lookback).")
    show = sub.add_parser("show", help="Print one signal's series.")
    show.add_argument("signal_id")
    show.add_argument("--tail", type=int, default=10)
    ids = sub.add_parser("ids", help="List stored signal ids.")
    ids.add_argument("prefix", nargs="?")
    args = parser.parse_args(argv)
    store = SignalStore()
    if args.command == "backfill":
        result = backfill(args.years, store, period=args.period)
        print({key: value for key, value in result.items() if key != "failures"})
        for ticker, reason in sorted(result.get("failures", {}).items()):
            print(f"  unavailable: {ticker}: {reason}")
        return 0 if result["state"] == "COMPLETED" else 1
    if args.command == "show":
        rows = store.rows(args.signal_id)
        for row in rows[-args.tail:]:
            print(row["observation_date"], row["value"] if row["value"] is not None else "", row["label"] or "", row["source_state"])
        latest = store.latest(args.signal_id)
        if latest and latest["value"] is not None:
            print(f"percentile in own history: {store.percentile(args.signal_id)}")
            print(f"value 30 days earlier: {store.value_days_ago(args.signal_id, 30)}")
        return 0
    for item in store.signal_ids(args.prefix):
        print(item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
