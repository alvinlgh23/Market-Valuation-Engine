"""The scenario gate (checklist 17): a "likely" call reaches the page only if it beat chance out of sample.

Each method is replayed month by month since 2005 using only what was known at the time
(macro data lagged one month; analogs drawn from months whose 3-month outcome had already
finished). It passes only if it beats a simple baseline with t >= 2.

Methods tested
- analog_sectors: the 3 sectors that did best after past months with the same conditions
  (Fed hiking, CPI above 3%, VIX in the top third of its history) against the average sector.
- analog_market: S&P 500 up or down 3 months later by majority of analog months, against
  always saying "up".
- sector_strength_{1,3,6}m: the 3 sectors with the strongest recent move (where money has
  been going) against the average sector, 1 and 3 months ahead.

It also stores what happened after each set of conditions (context, not a forecast) and the
link test "tight liquidity -> bigger swings next month" from the stored daily history.

Writes data/scenario_validation.json. Run: python scenario_validation.py
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import math
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data" / "scenario_validation.json"
SECTORS = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU"]   # SPDR sectors with history since 1998
CONDITIONS = ["hiking", "hot", "fear"]
PASS_T = 2.0
HIKING_PP, HOT_CPI = 0.10, 0.03


# ---- pure helpers ----------------------------------------------------------------------------
def episodes(flags) -> int:
    """Separate runs of consecutive True months."""
    count, previous = 0, False
    for flag in flags:
        if flag and not previous:
            count += 1
        previous = bool(flag)
    return count


def t_stat(values: list[float]) -> float | None:
    n = len(values)
    if n < 3:
        return None
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return mean / sd * math.sqrt(n) if sd > 0 else None


def verdict(t: float | None, beat_share: float | None, baseline_share: float | None = None) -> str:
    if t is None:
        return "INSUFFICIENT_SAMPLE"
    if baseline_share is not None:
        return "PASSED" if beat_share is not None and beat_share > baseline_share and t >= PASS_T else "FAILED"
    return "PASSED" if t >= PASS_T else "FAILED"


def link_test(signal: list[float], outcome: list[float]) -> dict[str, Any]:
    """Correlation of a signal with a later outcome on non-overlapping samples."""
    pairs = [(a, b) for a, b in zip(signal, outcome) if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
    n = len(pairs)
    if n < 8:
        return {"samples": n, "corr": None, "t_stat": None, "verdict": "INSUFFICIENT_SAMPLE"}
    xs, ys = zip(*pairs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sxx, syy = sum((x - mx) ** 2 for x in xs), sum((y - my) ** 2 for y in ys)
    r = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else None
    return {"samples": n, "corr": r, "t_stat": t, "verdict": "LINKED" if t is not None and abs(t) >= PASS_T else "NO_LINK"}


# ---- data and replay (network) ------------------------------------------------------------------
def monthly_frame():
    import pandas as pd
    import yfinance as yf
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        closes = yf.download(SECTORS + ["SPY", "^VIX"], start="1998-12-01", auto_adjust=True, progress=False)["Close"]
    px = closes.resample("ME").last()
    fred = ROOT / ".cache" / "compass_fred"
    ff = pd.read_csv(fred / "FEDFUNDS.csv", index_col=0, parse_dates=True).iloc[:, 0].astype(float).resample("ME").last()
    cpi = pd.read_csv(fred / "CPIAUCSL.csv", index_col=0, parse_dates=True).iloc[:, 0].astype(float).resample("ME").last()
    frame = pd.DataFrame(index=px.index)
    frame["ff_chg3"] = ff.reindex(px.index).ffill().diff(3).shift(1)               # known with a one-month lag
    frame["cpi_yoy"] = cpi.reindex(px.index).pct_change(12, fill_method=None).shift(1)
    frame["vix"] = px["^VIX"]
    frame["hiking"] = frame.ff_chg3 > HIKING_PP
    frame["hot"] = frame.cpi_yoy > HOT_CPI
    frame["fear"] = frame.vix > frame.vix.expanding(36).quantile(0.67)
    forward3 = px[SECTORS + ["SPY"]].pct_change(3).shift(-3)
    frame["spy_fwd3"] = forward3["SPY"]
    for sector in SECTORS:
        frame[f"{sector}_ex3"] = forward3[sector] - forward3["SPY"]
    return frame, px


def replay(frame, px) -> dict[str, Any]:
    import pandas as pd
    start = pd.Timestamp("2004-12-31")
    ex_cols = [f"{s}_ex3" for s in SECTORS]
    picks, market_hits = [], []
    for day, row in frame.iterrows():
        if day < start or row[ex_cols].isna().any():
            continue
        known = frame[frame.index <= day - pd.offsets.MonthEnd(3)].dropna(subset=ex_cols)
        analog = known[(known[CONDITIONS] == row[CONDITIONS]).all(axis=1)]
        if len(analog) < 6:
            continue
        top = analog[ex_cols].median().sort_values(ascending=False).index[:3]
        picks.append(float(row[top].mean() - row[ex_cols].mean()))
        market_hits.append(((analog.spy_fwd3 > 0).mean() > 0.5) == (row.spy_fwd3 > 0))
    every_third = picks[::3]
    base_up = float((frame.loc[start:].spy_fwd3.dropna() > 0).mean())
    results = {
        "analog_sectors": {"what": "Pick the 3 sectors that did best after similar past months",
                           "periods": len(every_third), "beat_share": sum(p > 0 for p in picks) / len(picks) if picks else None,
                           "edge_per_3m": sum(picks) / len(picks) if picks else None, "t_stat": t_stat(every_third)},
        "analog_market": {"what": "Call the S&P 500 up or down 3 months ahead from similar past months",
                          "periods": len(market_hits), "beat_share": sum(market_hits) / len(market_hits) if market_hits else None,
                          "baseline_share": base_up, "baseline": "always saying up", "t_stat": None},
    }
    results["analog_sectors"]["verdict"] = verdict(results["analog_sectors"]["t_stat"], None)
    hit, base = results["analog_market"]["beat_share"], base_up
    results["analog_market"]["verdict"] = "PASSED" if hit is not None and hit > base + 0.05 else "FAILED"
    for months in (1, 3, 6):
        strength = px[SECTORS].pct_change(months)
        for horizon in (1, 3):
            forward = px[SECTORS].pct_change(horizon).shift(-horizon)
            edges = []
            for day in strength.index:
                if day < pd.Timestamp("2000-06-30"):
                    continue
                s, f = strength.loc[day], forward.loc[day]
                if s.isna().any() or f.isna().any():
                    continue
                top = s.sort_values(ascending=False).index[:3]
                edges.append(float(f[top].mean() - f.mean()))
            sample = edges[::horizon]
            results[f"sector_strength_{months}m_{horizon}m"] = {
                "what": f"Back the 3 sectors money moved into most over {months} month{'s' if months > 1 else ''}, held {horizon} month{'s' if horizon > 1 else ''}",
                "periods": len(sample), "beat_share": sum(e > 0 for e in edges) / len(edges) if edges else None,
                "edge": sum(edges) / len(edges) if edges else None, "t_stat": t_stat(sample)}
            results[f"sector_strength_{months}m_{horizon}m"]["verdict"] = verdict(t_stat(sample), None)
    return results


def condition_context(frame) -> dict[str, Any]:
    """What happened after each combination of conditions: context, not a forecast."""
    ex_cols = [f"{s}_ex3" for s in SECTORS]
    known = frame.dropna(subset=["spy_fwd3", "hiking", "hot", "fear", "cpi_yoy", "ff_chg3"])
    all_up = float((known.spy_fwd3 > 0).mean())
    output = {}
    for combo in product([True, False], repeat=3):
        mask = (known[CONDITIONS] == list(combo)).all(axis=1)
        months = known[mask]
        key = ",".join(f"{name}={'yes' if flag else 'no'}" for name, flag in zip(CONDITIONS, combo))
        full_mask = (frame[CONDITIONS] == list(combo)).all(axis=1)
        output[key] = {
            "months": int(len(months)), "episodes": episodes(full_mask.tolist()),
            "spy_up_share": float((months.spy_fwd3 > 0).mean()) if len(months) else None,
            "spy_median": float(months.spy_fwd3.median()) if len(months) else None,
            "all_months_up_share": all_up,
            "sectors": {col[:-4]: {"beat_share": float((months[col] > 0).mean()), "median_excess": float(months[col].median())} for col in ex_cols} if len(months) else {},
            "examples": [day.strftime("%Y-%m") for day in months.index[:: max(1, len(months) // 8)]][:8],
        }
    return output


def liquidity_volatility_link() -> dict[str, Any]:
    """Does tight market liquidity come before bigger S&P 500 swings? Stored daily history, monthly samples."""
    import numpy as np
    import pandas as pd
    import yfinance as yf
    history = pd.read_csv(ROOT / "data" / "history" / "macro.csv")
    liquidity = history[history.signal_id == "macro.liquidity_score"].set_index("observation_date")["value"].astype(float)
    liquidity.index = pd.to_datetime(liquidity.index)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        closes = yf.Ticker("^GSPC").history(start=str(liquidity.index.min().date()))["Close"]
    closes.index = closes.index.tz_localize(None).normalize()
    returns = np.log(closes).diff()
    next_vol = returns[::-1].rolling(21).std()[::-1].shift(-1) * math.sqrt(252)
    joined = pd.DataFrame({"liquidity": liquidity, "next_vol": next_vol}).dropna().iloc[::21]
    result = link_test(joined.liquidity.tolist(), joined.next_vol.tolist())
    tight = joined[joined.liquidity < 40].next_vol
    loose = joined[joined.liquidity >= 40].next_vol
    return {**result, "claim": "Tight market liquidity is followed by bigger S&P 500 swings the next month",
            "tight_months": int(len(tight)), "tight_next_vol": float(tight.mean()) if len(tight) else None,
            "other_next_vol": float(loose.mean()) if len(loose) else None,
            "first": str(joined.index.min().date()), "last": str(joined.index.max().date())}


def main() -> int:
    frame, px = monthly_frame()
    payload = {
        "schema_version": "1.0", "generated_on": dt.date.today().isoformat(),
        "method": __doc__.split("Writes")[0].strip(), "pass_rule": f"Beats the baseline with t >= {PASS_T} (market call: beats always-up by 5 points).",
        "methods": replay(frame, px), "conditions": condition_context(frame),
        "condition_rules": {"hiking": f"Fed funds rate up more than {HIKING_PP} points over 3 months", "hot": f"CPI above {HOT_CPI:.0%} a year earlier",
                            "fear": "VIX in the top third of its own history"},
        "links": {"liquidity_to_volatility": liquidity_volatility_link()},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, default=float) + "\n")
    for name, item in payload["methods"].items():
        print(f"{name:28} {item['verdict']:8} beat {item['beat_share']:.0%}  t={item['t_stat'] if item['t_stat'] is None else round(item['t_stat'], 1)}")
    print("liquidity -> volatility:", payload["links"]["liquidity_to_volatility"]["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
