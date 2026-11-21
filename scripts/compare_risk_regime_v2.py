"""Checklist 7.1: label counts per day under the legacy and v2 risk regime over the last three years."""
import collections
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from risk_regime import ALL_TICKERS, analyze_risk_regime, collect_risk_regime_data  # noqa: E402
from signal_history import fetch_long_histories, trailing_window  # noqa: E402

histories, failures = fetch_long_histories(set(ALL_TICKERS) | {"SPY"}, period="5y")
spy = histories["SPY"]
start = spy.index[-1] - dt.timedelta(days=365 * 3)
legacy, new, transitions = collections.Counter(), collections.Counter(), collections.Counter()
for day in [item for item in spy.index if item >= start]:
    windows = {ticker: trailing_window(frame, day) for ticker, frame in histories.items()}
    report = analyze_risk_regime(collect_risk_regime_data(lambda ticker, period="1y": windows.get(ticker)))
    legacy[report["regime"]] += 1
    new[report["regime_v2"]] += 1
    if report["regime"] != report["regime_v2"]:
        transitions[f"{report['regime']} -> {report['regime_v2']}"] += 1
result = {"first": str(start.date()), "last": str(spy.index[-1].date()), "days": sum(legacy.values()),
          "legacy_counts": dict(legacy), "v2_counts": dict(new), "relabelled": dict(transitions), "unavailable_tickers": failures}
Path("data/risk_regime_v2_comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
