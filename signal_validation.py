"""Signal scorecard: does each stored signal say anything about what happens next? (checklist P6)

Sector signals (cross-section of 34 sector/theme ETFs)
    Forward return = the ETF's relative return against SPY over the next 20 trading days
    (1M) or 62 trading days (3M). It is read from the stored rel_1m / rel_3m series shifted
    back by the same number of observations, so the window starts after the signal date and
    uses the engine's own arithmetic.
    On each sample date the signal and the forward return are ranked across ETFs and their
    Spearman correlation (the information coefficient, IC) is taken. Sample dates are
    spaced by the horizon, so windows do not overlap.
    Reported: mean IC, its t-statistic over sample dates, the number of sample dates and of
    (date, ETF) pairs, and the hit rate: the share of pairs where the cross-sectionally
    demeaned signal and forward return have the same sign.

Macro signals (time series)
    Forward return = SPY's return over the next 21 or 63 trading days, non-overlapping
    samples. Reported: Pearson correlation, its t-statistic, sample size and hit rate
    (sign of the demeaned signal against sign of the demeaned forward return).
    The risk regime label is reported as the mean forward return per regime.

Decision rule for the card (fixed before running, checklist 6.2)
    A signal has NO INFORMATION when, at both horizons, |t| < 1 and the hit rate is within
    0.47-0.53. Such signals are removed from the judgment card; the engines keep them.
    A signal is REVERSED when the mean IC is negative with t <= -2 at either horizon: it
    stays on the card but must not be read as "more is better".

Run:  python signal_validation.py      (downloads SPY history; writes data/signal_validation.json)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "data" / "history"
RESULT_PATH = ROOT / "data" / "signal_validation.json"
HORIZONS = {"1M": ("rel_1m", 20), "3M": ("rel_3m", 62)}
CROWDING_ORDINAL = {"UNLOVED": -1.0, "NEUTRAL": 0.0, "EXTENDED": 1.0, "CROWDED": 2.0}


def _panel(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = frame[frame["metric"] == metric]
    return rows.pivot_table(index="observation_date", columns="etf", values="value", aggfunc="last").sort_index()


def load_panels() -> dict[str, pd.DataFrame]:
    sector = pd.read_csv(HISTORY / "sector.csv", usecols=["signal_id", "observation_date", "value"])
    flow = pd.read_csv(HISTORY / "flow.csv", usecols=["signal_id", "observation_date", "value"])
    panels = {}
    for frame in (sector, flow):
        parts = frame["signal_id"].str.split(".", expand=True)
        frame["etf"], frame["metric"] = parts[1], parts[2]
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        for metric in frame["metric"].unique():
            if metric != "shares_outstanding":
                panels[metric] = _panel(frame, metric)
    rel_3m = panels["rel_3m"]
    panels["rs_persistence_63"] = (rel_3m > 0).astype(float).where(rel_3m.notna()).rolling(63, min_periods=63).mean()
    dollar = np.log(panels["dollar_volume_20d"])
    panels["dollar_volume_z"] = (dollar - dollar.rolling(252, min_periods=120).mean()) / dollar.rolling(252, min_periods=120).std()
    panels["crowding_state"] = crowding_panel(panels)
    return panels


def crowding_panel(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Crowding state per date from expanding percentiles (no look-ahead), as an ordinal."""
    from sector_flow import crowding_state

    breadth = panels["breadth_50"]
    dollar_pct = panels["dollar_volume_20d"].expanding(min_periods=60).rank(pct=True)
    rs_pct = panels["rel_3m"].expanding(min_periods=60).rank(pct=True)
    index = breadth.index.intersection(dollar_pct.index).intersection(rs_pct.index)
    output = pd.DataFrame(index=index, columns=breadth.columns, dtype=float)
    for etf in breadth.columns:
        for day in index:
            state = crowding_state(_value(breadth, day, etf), _value(dollar_pct, day, etf), _value(rs_pct, day, etf))
            output.loc[day, etf] = CROWDING_ORDINAL.get(state, np.nan)
    return output


def _value(panel, day, etf):
    try:
        value = panel.at[day, etf]
    except KeyError:
        return None
    return None if value is None or value != value else float(value)


def _t(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    mean, sd = float(np.mean(values)), float(np.std(values, ddof=1))
    return mean / (sd / math.sqrt(len(values))) if sd else None


def cross_sectional(signal: pd.DataFrame, forward: pd.DataFrame, step: int, min_names: int = 10) -> dict[str, Any]:
    dates = signal.index.intersection(forward.dropna(how="all").index)
    sampled = dates[::step]
    ics, hits, pairs = [], 0, 0
    for day in sampled:
        pair = pd.concat({"s": signal.loc[day], "f": forward.loc[day]}, axis=1).dropna()
        if len(pair) < min_names or pair["s"].nunique() < 3:
            continue
        ic = pair["s"].rank().corr(pair["f"].rank())
        if ic == ic:
            ics.append(float(ic))
        demeaned = pair - pair.mean()
        hits += int(((demeaned["s"] > 0) == (demeaned["f"] > 0)).sum())
        pairs += len(pair)
    return {"mean_ic": float(np.mean(ics)) if ics else None, "t_stat": _t(ics), "sample_dates": len(ics), "pairs": pairs,
            "hit_rate": hits / pairs if pairs else None, "first": str(sampled[0].date()) if len(sampled) else None,
            "last": str(sampled[-1].date()) if len(sampled) else None}


def time_series(signal: pd.Series, forward: pd.Series, step: int) -> dict[str, Any]:
    pair = pd.concat({"s": signal, "f": forward}, axis=1).dropna().iloc[::step]
    if len(pair) < 6:
        return {"corr": None, "t_stat": None, "samples": len(pair), "hit_rate": None}
    r = float(pair["s"].corr(pair["f"]))
    n = len(pair)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else None
    demeaned = pair - pair.mean()
    hit = float(((demeaned["s"] > 0) == (demeaned["f"] > 0)).mean())
    return {"corr": r, "t_stat": t, "samples": n, "hit_rate": hit, "first": str(pair.index[0].date()), "last": str(pair.index[-1].date())}


def verdict(results: dict[str, dict[str, Any]], t_key: str = "t_stat") -> str:
    t_values = [item.get(t_key) for item in results.values()]
    hits = [item.get("hit_rate") for item in results.values()]
    if any(value is None for value in t_values + hits):
        return "INSUFFICIENT_SAMPLE"
    if any((item.get("mean_ic", item.get("corr")) or 0) < 0 and item[t_key] <= -2 for item in results.values()):
        return "REVERSED"
    if all(abs(value) < 1 for value in t_values) and all(0.47 <= hit <= 0.53 for hit in hits):
        return "NO_INFORMATION"
    if any(abs(value) >= 2 for value in t_values):
        return "INFORMATIVE"
    return "WEAK"


SECTOR_SIGNALS = ["rel_1m", "rel_3m", "rel_6m", "breakout", "score", "breadth_50", "breadth_200", "dollar_volume_z", "updown_volume_20d", "rs_persistence_63", "crowding_state"]
MACRO_SIGNALS = ["liquidity_score", "risk_score", "macro_score", "rate_score", "front_rate_score", "usd_score", "curve_score", "vix_score", "credit_score",
                 "tnx_3m", "dxy_3m", "hyg_ief", "vix_level", "usdjpy_3m"]


def run(spy: pd.DataFrame) -> dict[str, Any]:
    panels = load_panels()
    forwards = {name: panels[metric].shift(-offset) for name, (metric, offset) in HORIZONS.items()}
    sector = {}
    for name in SECTOR_SIGNALS:
        results = {horizon: cross_sectional(panels[name], forwards[horizon], step=offset + 1) for horizon, (_, offset) in HORIZONS.items()}
        sector[name] = {"horizons": results, "verdict": verdict(results)}
    macro_frame = pd.read_csv(HISTORY / "macro.csv", usecols=["signal_id", "observation_date", "value"])
    macro_frame["observation_date"] = pd.to_datetime(macro_frame["observation_date"])
    close = spy["Close"]
    spy_forward = {"1M": close.shift(-21) / close - 1, "3M": close.shift(-63) / close - 1}
    macro = {}
    for name in MACRO_SIGNALS:
        series = macro_frame[macro_frame["signal_id"] == f"macro.{name}"].set_index("observation_date")["value"].sort_index()
        series = series[~series.index.duplicated(keep="last")]
        results = {horizon: time_series(series, spy_forward[horizon].reindex(series.index), step={"1M": 21, "3M": 63}[horizon]) for horizon in spy_forward}
        macro[name] = {"horizons": results, "verdict": verdict(results)}
    risk = pd.read_csv(HISTORY / "risk.csv")
    regimes = risk[risk["signal_id"] == "risk.regime"].assign(observation_date=lambda frame: pd.to_datetime(frame["observation_date"])).set_index("observation_date")["label"]
    regime_table = {}
    for horizon, forward in spy_forward.items():
        joined = pd.concat({"regime": regimes, "f": forward.reindex(regimes.index)}, axis=1).dropna()
        regime_table[horizon] = {label: {"mean_forward_return": float(group["f"].mean()), "days": int(len(group)),
                                         "non_overlapping_samples": int(len(group.iloc[::21 if horizon == "1M" else 63]))}
                                 for label, group in joined.groupby("regime")}
    return {
        "schema_version": "1.0",
        "method": __doc__.split("Run:")[0].strip(),
        "sector": sector,
        "macro": macro,
        "risk_regime_forward_spy": regime_table,
        "card_removals": sorted(name for name, item in sector.items() if item["verdict"] == "NO_INFORMATION"),
        "reversed": sorted(name for name, item in {**sector, **macro}.items() if item["verdict"] == "REVERSED"),
    }


def main() -> int:
    from signal_history import fetch_long_histories
    histories, failures = fetch_long_histories(["SPY"], period="5y")
    if "SPY" not in histories:
        print("SPY unavailable", failures)
        return 1
    result = run(histories["SPY"])
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    fmt = lambda value, digits=3: "  n/a" if value is None else f"{value:+.{digits}f}"
    print("SECTOR (cross-sectional IC vs forward relative return)")
    for name, item in result["sector"].items():
        h1, h3 = item["horizons"]["1M"], item["horizons"]["3M"]
        print(f"  {name:20} 1M ic={fmt(h1['mean_ic'])} t={fmt(h1['t_stat'], 2)} hit={fmt(h1['hit_rate'], 2)} n={h1['sample_dates']:>2} | "
              f"3M ic={fmt(h3['mean_ic'])} t={fmt(h3['t_stat'], 2)} hit={fmt(h3['hit_rate'], 2)} n={h3['sample_dates']:>2}  {item['verdict']}")
    print("MACRO (correlation with forward SPY return)")
    for name, item in result["macro"].items():
        h1, h3 = item["horizons"]["1M"], item["horizons"]["3M"]
        print(f"  {name:20} 1M r={fmt(h1['corr'])} t={fmt(h1['t_stat'], 2)} n={h1['samples']:>2} | 3M r={fmt(h3['corr'])} t={fmt(h3['t_stat'], 2)} n={h3['samples']:>2}  {item['verdict']}")
    print("RISK REGIME → mean forward SPY return")
    for horizon, table in result["risk_regime_forward_spy"].items():
        print(f"  {horizon}: " + "; ".join(f"{label} {value['mean_forward_return']:+.2%} ({value['days']}d)" for label, value in table.items()))
    print("card removals:", result["card_removals"], "| reversed:", result["reversed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
