"""P20 item 5: a track record for the card's valuation reading.

The card says whether the price assumes more or less growth than the business has shown. Whether that reading
was followed by worse or better returns is an empirical question, so this module keeps score instead of
asserting it:

* Each run of one reading for one company (a "spell": consecutive days with the same label) counts once, on
  its first day. Daily repeats of the same reading are not independent and are not counted again.
* Once 1, 3, 6 or 12 months of trading days have passed, the spell's return is compared with the S&P 500 (SPY)
  over the same window.
* A reading group is called "tested" only when at least MIN_SPELLS spells from MIN_TICKERS companies have
  matured at that horizon. Until then it is "not tested yet", with the date of the first check.

There is no historical backfill: Yahoo has no point-in-time analyst estimates, so earlier readings cannot be
rebuilt without hindsight. The record starts with the first stored card (2026-11-21).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from typing import Any, Callable

import numpy as np

from signal_history import SignalStore, history_dir

HORIZONS = (("1m", 21), ("3m", 63), ("6m", 126), ("12m", 252))   # trading days
MIN_SPELLS = 20
MIN_TICKERS = 10
RESULTS_FILE = "track_record.json"

# Which way each reading would point if it carried information. "Matches" points nowhere.
GROUPS = {
    "Price implies growth above what the model can reach": "RICH",
    "Price implies more growth than observed/consensus": "RICH",
    "Price implies higher ROE than the bank earns": "RICH",
    "Price roughly matches observed/consensus growth": "MATCHES",
    "Price roughly matches the bank's ROE": "MATCHES",
    "Price implies less growth than observed/consensus": "CHEAP",
    "Price implies lower ROE than the bank earns": "CHEAP",
    "Price implies contraction beyond the model's floor": "CHEAP",
}
GROUP_WORDS = {"RICH": "price assumes more than the business has shown",
               "MATCHES": "price roughly matches the business",
               "CHEAP": "price assumes less than the business has shown"}
EXPECTED_SIGN = {"RICH": -1, "CHEAP": 1, "MATCHES": 0}


def group_of(label: str | None) -> str | None:
    return GROUPS.get(label or "")


def spells(store: SignalStore) -> list[dict[str, Any]]:
    """First day of each run of one reading per company, for card readings only."""
    out: list[dict[str, Any]] = []
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in store._rows("verdict"):   # all card rows; keep valuation readings only
        if not row["signal_id"].endswith(".valuation") or not str(row.get("source", "")).startswith("company_verdict"):
            continue
        by_ticker.setdefault(row["signal_id"].split(".")[1], []).append(row)
    for ticker, rows in sorted(by_ticker.items()):
        rows.sort(key=lambda row: row["observation_date"])
        last = None
        for row in rows:
            group = group_of(row["label"])
            if row["label"] != last and group:
                out.append({"ticker": ticker, "date": row["observation_date"], "label": row["label"], "group": group,
                            "rules": row.get("source")})
            last = row["label"]
    return out


def due_date(start: str, trading_days: int) -> str:
    return str(np.busday_offset(np.datetime64(start), trading_days, roll="forward"))


def _close_on_or_after(frame, day: str, offset: int = 0):
    """(date, close) of the first session on/after `day`, moved forward `offset` sessions; None if not there yet."""
    closes = frame["Close"].dropna()
    index = [str(stamp.date()) for stamp in closes.index]
    start = next((i for i, value in enumerate(index) if value >= day), None)
    if start is None or start + offset >= len(index):
        return None
    return index[start + offset], float(closes.iloc[start + offset])


def forward_excess(spell: dict[str, Any], stock, spy, trading_days: int) -> float | None:
    """Stock return minus SPY return over `trading_days` sessions from the spell's first day; None until matured."""
    begin, end = _close_on_or_after(stock, spell["date"]), _close_on_or_after(stock, spell["date"], trading_days)
    spy_begin, spy_end = _close_on_or_after(spy, spell["date"]), _close_on_or_after(spy, spell["date"], trading_days)
    if not (begin and end and spy_begin and spy_end) or begin[1] <= 0 or spy_begin[1] <= 0:
        return None
    return (end[1] / begin[1] - 1.0) - (spy_end[1] / spy_begin[1] - 1.0)


def score(all_spells: list[dict[str, Any]], fetch: Callable[[str, str], Any] | None, today: dt.date) -> dict[str, Any]:
    """Results per reading group and horizon. Prices are fetched only for spells that have matured."""
    matured_any = [s for s in all_spells if due_date(s["date"], HORIZONS[0][1]) <= today.isoformat()]
    histories: dict[str, Any] = {}
    if matured_any and fetch is not None:
        for symbol in sorted({s["ticker"] for s in matured_any} | {"SPY"}):
            frame = fetch(symbol, "2y")
            if frame is not None and not getattr(frame, "empty", True):
                histories[symbol] = frame
    groups: dict[str, Any] = {}
    for group in ("RICH", "MATCHES", "CHEAP"):
        members = [s for s in all_spells if s["group"] == group]
        horizons = {}
        for name, days in HORIZONS:
            values = []
            for s in members:
                if due_date(s["date"], days) > today.isoformat() or s["ticker"] not in histories or "SPY" not in histories:
                    continue
                value = forward_excess(s, histories[s["ticker"]], histories["SPY"], days)
                if value is not None:
                    values.append((s["ticker"], value))
            tickers = {t for t, _ in values}
            tested = len(values) >= MIN_SPELLS and len(tickers) >= MIN_TICKERS
            pending = [due_date(s["date"], days) for s in members if due_date(s["date"], days) > today.isoformat()]
            result: dict[str, Any] = {"matured": len(values), "companies": len(tickers), "tested": tested,
                                      "next_check": min(pending) if pending else None}
            if values:
                excess = [v for _, v in values]
                result["median_excess"] = float(np.median(excess))
                sign = EXPECTED_SIGN[group]
                result["share_as_expected"] = (float(np.mean([np.sign(v) == sign for v in excess])) if sign
                                               else float(np.mean([abs(v) < 0.05 for v in excess])))
            horizons[name] = result
        groups[group] = {"spells": len(members), "companies": len({s["ticker"] for s in members}),
                         "since": min((s["date"] for s in members), default=None), "horizons": horizons}
    return {"as_of": today.isoformat(), "min_spells": MIN_SPELLS, "min_tickers": MIN_TICKERS,
            "benchmark": "SPY", "groups": groups,
            "method": "Each run of one reading per company counts once, on its first day; return minus the S&P 500 "
                      "over the next 1, 3, 6 and 12 months of trading days. Tested only with at least "
                      f"{MIN_SPELLS} matured runs from {MIN_TICKERS} companies. No historical backfill."}


def load_results(directory=None) -> dict[str, Any] | None:
    path = (directory or history_dir()) / RESULTS_FILE
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def for_label(label: str | None, results: dict[str, Any] | None) -> dict[str, Any] | None:
    """What the card shows next to its valuation reading."""
    group = group_of(label)
    if not group or not results:
        return None
    entry = results["groups"].get(group) or {}
    horizons = entry.get("horizons") or {}
    tested = [(name, horizons[name]) for name, _ in HORIZONS if horizons.get(name, {}).get("tested")]
    if tested:
        name, best = tested[-1]
        text = (f"Tested at {name}: after readings like this, the median return was "
                f"{best['median_excess'] * 100:+.1f} points vs the S&P 500 ({best['matured']} cases, {best['companies']} companies).")
        status = "TESTED"
    else:
        first = horizons.get("1m", {})
        due = first.get("next_check")
        text = (f"Not tested yet. {entry.get('spells', 0)} readings like this since {entry.get('since') or 'the first card'}"
                + (f"; the first 1-month check is due around {due}." if due and not first.get("matured") else ".")
                + f" A result is shown once {results['min_spells']} cases from {results['min_tickers']} companies have run their course.")
        status = "NOT_TESTED"
    return {"status": status, "group": group, "meaning": GROUP_WORDS[group], "text": text, "as_of": results.get("as_of")}


def run(today: dt.date | None = None, fetch: Callable[[str, str], Any] | None = None, store: SignalStore | None = None,
        write: bool = True) -> dict[str, Any]:
    today = today or dt.date.today()
    store = store or SignalStore()
    if fetch is None:
        import Valuation_model as vm
        fetch = vm.fetch_history
    results = score(spells(store), fetch, today)
    if write:
        path = store.directory / RESULTS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Score stored valuation readings against later returns.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="do not write data/history/track_record.json")
    args = parser.parse_args()
    results = run(write=not args.dry_run)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for group, entry in results["groups"].items():
            first = entry["horizons"]["1m"]
            print(f"{group:8} {entry['spells']:3} runs, {entry['companies']:2} companies; 1m matured {first['matured']}, next check {first['next_check']}")


if __name__ == "__main__":
    main()
