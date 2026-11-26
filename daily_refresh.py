"""P20 item 6: one background refresh a day, so pages read precomputed results instead of computing on open.

`--start` starts the refresh in the background if today's has not run (or is not running) and prints the status.
`--status` only prints the status. `--run` does the work in this process:

1. builds the judgment card for every watchlist company (this records card history and the card cache, the same
   as opening each company page);
2. precomputes what moved each price, the next events and FX moves, each stamped with its data date;
3. scores the valuation track record (track_record.py).

The status file says how far it has got, so the pages can show "updating 4 of 12" and one data date.
Nothing here calls the research refresh (`refresh=1` / `--refresh`); macro inputs are read cache-first.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
DAILY = ROOT / ".cache" / "daily"
STATUS = DAILY / "status.json"
LOG = DAILY / "refresh.log"
PRECOMPUTED = ("drivers", "events", "fx")
STALE_RUN_SECONDS = 60 * 60          # a RUNNING status older than this with a dead process is treated as failed


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str))
    temporary.replace(path)


def read_status(directory: Path = DAILY) -> dict[str, Any]:
    try:
        return json.loads((directory / STATUS.name).read_text())
    except (OSError, ValueError):
        return {"state": "NEVER_RUN"}


def _alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def current_status(today: dt.date | None = None, directory: Path = DAILY) -> dict[str, Any]:
    """The stored status, with a crashed run reported as FAILED and `fresh` saying whether it is today's."""
    today = today or dt.date.today()
    status = read_status(directory)
    if status.get("state") == "RUNNING" and not _alive(status.get("pid")):
        status = {**status, "state": "FAILED", "error": "the refresh process stopped before finishing"}
    status["fresh"] = status.get("data_date") == today.isoformat() and status.get("state") in ("DONE", "RUNNING")
    return status


def precomputed(name: str, today: dt.date | None = None, directory: Path = DAILY, tickers: list[str] | None = None) -> Any | None:
    """Today's precomputed result, or None (the caller then computes it live). With `tickers`, also None when the
    watchlist has changed since it was computed."""
    today = today or dt.date.today()
    try:
        payload = json.loads((directory / f"{name}.json").read_text())
    except (OSError, ValueError):
        return None
    if payload.get("data_date") != today.isoformat():
        return None
    if tickers is not None and sorted(payload.get("tickers") or []) != sorted(tickers):
        return None
    return payload.get("data")


def run(today: dt.date | None = None, *, directory: Path = DAILY, tickers: list[str] | None = None,
        build: Callable[[str], dict[str, Any]] | None = None, steps: dict[str, Callable[[], Any]] | None = None,
        score: Callable[[], Any] | None = None) -> dict[str, Any]:
    """Do the refresh. The callables are injectable for tests; by default they are the real engines."""
    today = today or dt.date.today()
    import company_verdict as cv
    if tickers is None:
        tickers = json.loads(cv.WATCHLIST_PATH.read_text()).get("tickers", [])
    if build is None:
        environment, core = cv.load_environment()
        store = cv.SignalStore()
        fomc = cv.next_fomc(today)
        build = lambda ticker: cv.build_card(ticker, environment, core, store, fomc=fomc)   # noqa: E731
    if steps is None:
        steps = {"drivers": cv.watchlist_drivers, "events": cv.watchlist_events, "fx": cv.fx_moves}
    if score is None:
        import track_record
        score = track_record.run
    status: dict[str, Any] = {"state": "RUNNING", "pid": os.getpid(), "data_date": today.isoformat(), "started_at": _now(),
                              "total": len(tickers) + len(steps) + 1, "done": 0, "current": None, "companies": len(tickers),
                              "cards_done": [], "errors": []}

    def advance(label: str, action: Callable[[], Any]) -> Any:
        status["current"] = label
        _write(directory / STATUS.name, status)
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the rest
            status["errors"].append({"step": label, "error": f"{type(exc).__name__}: {exc}"})
            return None
        finally:
            status["done"] += 1

    for ticker in tickers:
        card = advance(ticker, lambda t=ticker: build(t))
        if card is not None:
            status["cards_done"].append(ticker)
    for name, action in steps.items():
        data = advance(name, action)
        if data is not None:
            _write(directory / f"{name}.json", {"data_date": today.isoformat(), "computed_at": _now(), "tickers": tickers, "data": data})
    advance("track record", score)
    status.update(state="DONE", current=None, finished_at=_now())
    _write(directory / STATUS.name, status)
    return status


def start(today: dt.date | None = None, directory: Path = DAILY) -> dict[str, Any]:
    """Start today's refresh in the background unless it is done or running. Returns the status."""
    status = current_status(today, directory)
    if status["fresh"]:
        return status
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / LOG.name).open("a") as log:
        log.write(f"\n--- {_now()} start\n")
        log.flush()
        process = subprocess.Popen([sys.executable, "-B", str(ROOT / "daily_refresh.py"), "--run"], cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    queued = {"state": "RUNNING", "pid": process.pid, "data_date": (today or dt.date.today()).isoformat(), "started_at": _now(),
              "total": None, "done": 0, "current": "starting", "errors": []}
    _write(directory / STATUS.name, queued)
    return {**queued, "fresh": True, "started": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX daily background refresh")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="print the refresh status as JSON")
    group.add_argument("--start", action="store_true", help="start today's refresh in the background if needed")
    group.add_argument("--run", action="store_true", help="run the refresh in this process")
    args = parser.parse_args(argv)
    if args.status:
        print(json.dumps(current_status()))
    elif args.start:
        print(json.dumps(start()))
    else:
        began = time.time()
        try:
            status = run()
            print(f"done in {time.time() - began:.0f}s; errors: {status['errors']}")
        except Exception:  # noqa: BLE001
            failed = {**read_status(), "state": "FAILED", "error": traceback.format_exc(limit=3), "finished_at": _now()}
            _write(STATUS, failed)
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
