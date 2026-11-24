"""When did the yen-carry switch show UNWIND_RISK around sharp equity drops? (checklist 3.6)

Carry state per day comes from the signal history (macro.usdjpy_3m, macro.vix_level)
through environment.yen_carry_state, the single definition. Sharp drops are defined
before looking: SPY's 10-trading-day return at or below -5%; a new event starts only after
20 trading days without one. For each event we report whether UNWIND_RISK appeared in the
10 trading days before it started, on the start day, and within the event window. The
base rate of UNWIND_RISK days says how often the switch is on anyway.

Run:  python carry_events.py   (downloads SPY history; writes data/yen_carry_events.json)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from environment import yen_carry_state
from signal_history import SignalStore

ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "data" / "yen_carry_events.json"
DROP, WINDOW, GAP, LOOKBACK = -0.05, 10, 20, 10


def carry_states(store: SignalStore) -> dict[str, str]:
    usdjpy = dict(store.series("macro.usdjpy_3m"))
    vix = dict(store.series("macro.vix_level"))
    return {day: yen_carry_state(usdjpy.get(day), vix.get(day)) for day in sorted(set(usdjpy) | set(vix))}


def drop_events(spy) -> list[dict[str, Any]]:
    closes = spy["Close"]
    returns = closes / closes.shift(WINDOW) - 1
    events, last = [], None
    for position, (day, value) in enumerate(returns.items()):
        if value is None or value != value or value > DROP:
            continue
        if last is not None and position - last < GAP:
            last = position
            continue
        start = max(0, position - WINDOW)
        events.append({"start": str(closes.index[start].date()), "trigger": str(day.date()), "return_10d": float(value), "position": position})
        last = position
    return events


def analyse(states: dict[str, str], spy) -> dict[str, Any]:
    days = [str(day.date()) for day in spy.index]
    covered = [day for day in days if day in states]
    if not covered:
        return {"events": [], "base_rate_unwind": None, "error": "No overlap between SPY dates and stored carry states."}
    first, last = covered[0], covered[-1]
    events = [event for event in drop_events(spy) if first <= event["start"] <= last]
    index = {day: position for position, day in enumerate(days)}
    report = []
    for event in events:
        start = index[event["start"]]
        before = [states.get(day) for day in days[max(0, start - LOOKBACK):start]]
        during = [states.get(day) for day in days[start:event["position"] + 1]]
        report.append({
            "start": event["start"], "trigger": event["trigger"], "spy_return_10d": event["return_10d"],
            "unwind_in_prior_10d": "UNWIND_RISK" in before,
            "unwind_on_start_day": states.get(event["start"]) == "UNWIND_RISK",
            "unwind_during_event": "UNWIND_RISK" in during,
            "state_on_start_day": states.get(event["start"]),
        })
    window_states = [states[day] for day in covered]
    base = sum(state == "UNWIND_RISK" for state in window_states) / len(window_states)
    return {
        "schema_version": "1.0",
        "rule": f"Sharp drop: SPY 10-day return <= {DROP:.0%}; events separated by {GAP} trading days. Lookback {LOOKBACK} days before the event start.",
        "period": {"first": first, "last": last, "trading_days": len(covered)},
        "base_rate_unwind": base,
        "events": report,
        "summary": {
            "events": len(report),
            "unwind_before": sum(item["unwind_in_prior_10d"] for item in report),
            "unwind_on_start": sum(item["unwind_on_start_day"] for item in report),
            "unwind_during": sum(item["unwind_during_event"] for item in report),
        },
        "limitations": [
            "USD/JPY and VIX only; the rate spread, BOJ probabilities and CFTC positioning have no stored history yet.",
            "VIX above 24 also triggers UNWIND_RISK, so the switch partly restates equity stress itself.",
            "Three years of history; a handful of events.",
        ],
    }


def main() -> int:
    from signal_history import fetch_long_histories

    histories, failures = fetch_long_histories(["SPY"], period="5y")
    if "SPY" not in histories:
        print("SPY unavailable", failures)
        return 1
    result = analyse(carry_states(SignalStore()), histories["SPY"])
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("period", "base_rate_unwind", "summary")}, indent=2))
    for item in result["events"]:
        print(f"{item['start']} -> {item['trigger']}  SPY {item['spy_return_10d']:+.1%}  start={item['state_on_start_day']}  before={item['unwind_in_prior_10d']}  during={item['unwind_during_event']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
