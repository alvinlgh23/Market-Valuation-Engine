"""Does the shadow S$NEER behave like a safe-haven currency? (checklist 3.3)

The owner's design intent: S$NEER moves reflect Singapore's FX policy, and because SGD is
now treated as a safe haven, basket moves can be read back as a global risk signal.

Pass criteria, fixed before running the data:
  1. Weekly change in the NEER deviation from its estimated centre correlates positively
     with the weekly VIX change, |t| >= 2.
  2. It correlates negatively with the weekly SPY return, |t| >= 2.
  3. Its mean change in weeks when SPY falls more than 2% exceeds its mean in other weeks,
     Welch t >= 2.
All three must hold. If they do, NEER can enter the environment layer as a risk-appetite
reading; if not, it stays a regional policy tool. Gold, yen and Swiss franc are reported
alongside as reference safe havens, and a one-week lead/lag shows whether NEER leads VIX.

Run:  python neer_safe_haven.py   (reads .cache/research/neer.json, downloads 5y weekly data)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "data" / "neer_safe_haven.json"
REFERENCE = {"VIX": "^VIX", "SPY": "SPY", "GOLD": "GLD", "USDJPY": "JPY=X", "USDCHF": "CHF=X", "DXY": "DX-Y.NYB"}


def _corr_t(x, y):
    n = len(x)
    if n < 20:
        return None, None, n
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if not sxx or not syy:
        return None, None, n
    r = sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else math.inf
    return r, t, n


def _welch(a, b):
    if len(a) < 5 or len(b) < 5:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else None


def weekly_frame(neer_history: list[dict[str, Any]], histories: dict[str, Any]):
    import pandas as pd

    neer = pd.DataFrame(neer_history)
    neer.index = pd.to_datetime(neer["date"])
    frame = pd.DataFrame({
        "neer_deviation_change": neer["deviation_pct"].astype(float).resample("W-FRI").last().diff(),
        "neer_index_return": neer["index"].astype(float).resample("W-FRI").last().pct_change(),
    })
    for name, ticker in REFERENCE.items():
        if ticker in histories:
            weekly = histories[ticker]["Close"].resample("W-FRI").last()
            frame[name] = weekly.diff() if name == "VIX" else weekly.pct_change()
    return frame


def analyse(neer_history: list[dict[str, Any]], histories: dict[str, Any]) -> dict[str, Any]:
    frame = weekly_frame(neer_history, histories)
    target = "neer_deviation_change"

    def corr(column, lag=0):
        if column not in frame:
            return {"r": None, "t": None, "weeks": 0}
        pair = frame[[target, column]].copy()
        if lag:
            pair[column] = pair[column].shift(-lag)  # NEER at t against the reference at t+lag
        pair = pair.dropna()
        r, t, n = _corr_t(pair[target].tolist(), pair[column].tolist())
        return {"r": r, "t": t, "weeks": n}

    correlations = {name: corr(name) for name in REFERENCE}
    correlations["SGD_STRENGTH_vs_JPY_STRENGTH"] = None
    if "USDJPY" in frame:
        pair = frame[[target, "USDJPY"]].dropna()
        r, t, n = _corr_t(pair[target].tolist(), (-pair["USDJPY"]).tolist())
        correlations["SGD_STRENGTH_vs_JPY_STRENGTH"] = {"r": r, "t": t, "weeks": n}
    down_weeks = up_weeks = []
    if "SPY" in frame:
        pair = frame[[target, "SPY"]].dropna()
        down_weeks = pair.loc[pair["SPY"] < -0.02, target].tolist()
        up_weeks = pair.loc[pair["SPY"] >= -0.02, target].tolist()
    stress_t = _welch(down_weeks, up_weeks)
    vix, spy = correlations["VIX"], correlations["SPY"]
    criteria = {
        "positive_with_vix": bool(vix["r"] is not None and vix["r"] > 0 and abs(vix["t"]) >= 2),
        "negative_with_spy": bool(spy["r"] is not None and spy["r"] < 0 and abs(spy["t"]) >= 2),
        "rises_in_spy_down_weeks": bool(stress_t is not None and stress_t >= 2),
    }
    passed = all(criteria.values())
    return {
        "schema_version": "1.0",
        "question": "Does the shadow S$NEER deviation behave like a safe-haven currency?",
        "pass_rule": "All three: positive with weekly VIX change (|t|>=2), negative with weekly SPY return (|t|>=2), higher mean change in weeks SPY falls >2% (Welch t>=2).",
        "first_week": str(frame.dropna(subset=[target]).index[0].date()) if frame[target].notna().any() else None,
        "last_week": str(frame.dropna(subset=[target]).index[-1].date()) if frame[target].notna().any() else None,
        "correlations": correlations,
        "lead_lag": {"neer_t_vs_vix_t_plus_1": corr("VIX", lag=1), "neer_t_vs_spy_t_plus_1": corr("SPY", lag=1)},
        "stress_weeks": {
            "spy_down_more_than_2pct": len(down_weeks),
            "other_weeks": len(up_weeks),
            "mean_change_in_down_weeks": sum(down_weeks) / len(down_weeks) if down_weeks else None,
            "mean_change_in_other_weeks": sum(up_weeks) / len(up_weeks) if up_weeks else None,
            "welch_t": stress_t,
        },
        "criteria": criteria,
        "passed": passed,
        "decision": "ENTER_ENVIRONMENT_LAYER" if passed else "KEEP_AS_REGIONAL_TOOL",
        "limitations": [
            "The shadow basket, weights, centre and band are estimates; the centre fit R^2 is about 0.34.",
            "About 250 weekly observations since 2022; one tightening cycle dominates the sample.",
            "USD is 17% of the basket, so part of any co-movement is the dollar itself (see DXY).",
        ],
    }


def main() -> int:
    from signal_history import fetch_long_histories

    neer = json.loads((ROOT / ".cache" / "research" / "neer.json").read_text())
    histories, failures = fetch_long_histories(REFERENCE.values(), period="5y")
    result = analyse(neer["history"], histories)
    result["neer_as_of"] = neer.get("as_of")
    result["unavailable_tickers"] = failures
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("criteria", "passed", "decision", "stress_weeks")}, indent=2))
    for name, value in result["correlations"].items():
        if value:
            print(f"{name:30} r={value['r'] if value['r'] is None else round(value['r'], 3)} t={value['t'] if value['t'] is None else round(value['t'], 2)} n={value['weeks']}")
    print("lead/lag", {key: (None if value['r'] is None else round(value['r'], 3), None if value['t'] is None else round(value['t'], 2)) for key, value in result["lead_lag"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
