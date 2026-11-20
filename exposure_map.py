"""Archetype -> macro factor exposure map (checklist 3.1, 3.2).

This is the channel through which the macro engines (Central Bank Compass, yen carry,
KOSPI, inflation, risk regime) reach a single company. A company only sees the macro
signals its archetype is exposed to; everything else is noise for that company.

Every entry starts as a STRUCTURAL_HYPOTHESIS: a direction and a one-line mechanism,
written before looking at data. `python exposure_map.py validate` then regresses each
archetype's proxy ETF (weekly return minus SPY) on each factor's weekly change over five
years and stores the result in data/exposure_validation.json:

    CONFIRMED      hypothesised sign, |t| >= 2 and the sign holds in >= 60% of rolling years
    WEAK           hypothesised sign but not significant or not stable
    DOWNGRADED     opposite sign with |t| >= 2 (the hypothesis is contradicted; do not use)
    UNTESTED       no market proxy for the factor or the archetype

Weekly (Friday) closes are used so Korean and US sessions line up. Factor proxies are
market series, not the engines' own readings; the engines supply the *current state*,
the regression only checks the *direction* of the exposure.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from company_economics_registry import Archetype

ROOT = Path(__file__).resolve().parent
VALIDATION_PATH = ROOT / "data" / "exposure_validation.json"


@dataclass(frozen=True)
class Factor:
    id: str
    label: str
    rising_means: str
    environment_signals: tuple[str, ...]
    proxy: str | None            # how the regression measures a weekly change; None = untested
    tickers: tuple[str, ...] = ()


FACTORS: dict[str, Factor] = {item.id: item for item in [
    Factor("long_rates", "US long-term yields", "10Y yield rises", ("macro.tnx_level", "macro.tnx_3m"), "weekly change in ^TNX (yield points)", ("^TNX",)),
    Factor("fed_path", "Fed policy path", "path turns more hawkish", ("compass.US.probabilities_3m.tightening", "compass.US.probabilities_3m.easing", "macro.front_rate_3m"), "weekly change in 2Y Treasury yield futures (2YY=F)", ("2YY=F",)),
    Factor("usd", "US dollar", "dollar strengthens", ("macro.dxy_level", "macro.dxy_3m"), "weekly return of DX-Y.NYB", ("DX-Y.NYB",)),
    Factor("credit", "Credit risk appetite", "high yield outperforms Treasuries", ("macro.hyg_ief",), "weekly return of HYG minus IEF", ("HYG", "IEF")),
    Factor("volatility", "Equity volatility", "VIX rises", ("macro.vix_level",), "weekly change in ^VIX", ("^VIX",)),
    Factor("oil", "Crude oil", "oil price rises", ("inflation.metric.wti",), "weekly return of CL=F", ("CL=F",)),
    Factor("inflation", "Inflation expectations", "breakeven inflation rises", ("inflation.near_term", "inflation.medium_term"), "weekly return of TIP minus IEF (breakeven proxy)", ("TIP", "IEF")),
    Factor("growth", "Global growth", "growth improves", ("fragility.ism_pmi",), "weekly return of HG=F copper (growth proxy)", ("HG=F",)),
    Factor("semis_cycle", "Semiconductor cycle", "memory and foundry demand improves", ("kospi.factor.tech.corr",), "weekly return of SK Hynix + Samsung Electronics (the KOSPI engine's tech proxy)", ("000660.KS", "005930.KS")),
    Factor("yen_carry", "Yen carry", "USD/JPY rises (carry builds); a fall is unwinding", ("macro.usdjpy_level", "macro.usdjpy_3m"), "weekly return of JPY=X (USD/JPY)", ("JPY=X",)),
    Factor("liquidity", "Policy liquidity", "liquidity loosens", ("compass.US.liquidity_score", "macro.liquidity_score"), None),
]}


@dataclass(frozen=True)
class Exposure:
    factor: str
    direction: int          # +1: archetype tends to outperform when the factor rises; -1: underperform
    mechanism: str


E = Exposure
EXPOSURES: dict[Archetype, tuple[Exposure, ...]] = {
    Archetype.ENTERPRISE_AI_SOFTWARE: (
        E("long_rates", -1, "Most value sits in distant cash flows, so higher discount rates cut it most."),
        E("fed_path", -1, "A more hawkish path raises the discount rate and tightens funding for long-duration equity."),
        E("credit", +1, "Moves with risk appetite; wider credit spreads usually hit high-multiple software."),
        E("volatility", -1, "High-multiple, crowded names fall hardest when volatility spikes."),
        E("yen_carry", +1, "Liquidity-sensitive; a carry unwind (USD/JPY falling) forces de-risking of crowded growth."),
        E("liquidity", +1, "Multiple expansion depends on loose financial conditions."),
    ),
    Archetype.TRADITIONAL_SAAS: (
        E("long_rates", -1, "Long-duration recurring cash flows are rate sensitive."),
        E("credit", +1, "Moves with risk appetite."),
        E("volatility", -1, "Growth multiples compress in volatility spikes."),
        E("yen_carry", +1, "Liquidity-sensitive growth is de-risked in carry unwinds."),
    ),
    Archetype.FABLESS_SEMICONDUCTOR: (
        E("semis_cycle", +1, "Revenue follows the chip demand cycle that Korean memory and foundry exports lead."),
        E("long_rates", -1, "High-multiple growth is discount-rate sensitive."),
        E("usd", -1, "Most revenue is earned abroad; a stronger dollar reduces translated demand."),
        E("volatility", -1, "High-beta and crowded; sells off in volatility spikes."),
        E("yen_carry", +1, "Among the most crowded liquidity trades; carry unwinds hit it early."),
    ),
    Archetype.SEMICONDUCTOR_FOUNDRY: (
        E("semis_cycle", +1, "Utilisation and pricing follow the chip demand cycle."),
        E("usd", -1, "Global customer base and non-US cost base."),
        E("volatility", -1, "Cyclical high-beta equity."),
    ),
    Archetype.HYPERSCALER_CLOUD_PLATFORM: (
        E("long_rates", -1, "Long-duration platform cash flows."),
        E("usd", -1, "Large share of revenue earned outside the US."),
    ),
    Archetype.CONSUMER_PLATFORM: (
        E("long_rates", -1, "Growth multiple is discount-rate sensitive."),
        E("credit", +1, "Advertising and consumer spend follow risk appetite."),
        E("volatility", -1, "Sells off with growth equities in volatility spikes."),
        E("yen_carry", +1, "Liquidity-sensitive growth."),
    ),
    Archetype.RETAIL_PHYSICAL_NETWORK: (
        E("oil", -1, "Fuel and freight costs squeeze margins and household budgets."),
        E("volatility", +1, "Staple-like demand makes it relatively defensive in stress."),
    ),
    Archetype.BANK: (
        E("long_rates", +1, "Higher long yields widen net interest margins."),
        E("credit", +1, "Loan losses and capital markets income follow credit conditions."),
        E("volatility", -1, "Financial stress raises funding and credit costs."),
    ),
    Archetype.INDUSTRIAL: (
        E("growth", +1, "Orders follow the industrial cycle."),
        E("credit", +1, "Capex is financed in credit markets."),
        E("usd", -1, "Exporters lose competitiveness when the dollar strengthens."),
    ),
    Archetype.PHARMA_BIOTECH: (
        E("volatility", +1, "Earnings do not depend on the cycle, so it is relatively defensive in stress."),
        E("credit", -1, "Tends to lag when risk appetite is strong."),
    ),
    Archetype.COMMODITY_PRODUCER: (
        E("oil", +1, "Revenue is the commodity price."),
        E("inflation", +1, "Real assets benefit when inflation expectations rise."),
        E("usd", -1, "Commodities are priced in dollars; a stronger dollar lowers them."),
    ),
    Archetype.PAYMENT_NETWORK: (
        E("inflation", +1, "Fees are a share of nominal spending."),
        E("credit", +1, "Volumes follow consumer confidence and credit availability."),
        E("usd", -1, "Cross-border volumes fall when the dollar is strong."),
    ),
    Archetype.MARKETPLACE_PLATFORM: (
        E("credit", +1, "Transaction volume follows consumer risk appetite."),
        E("volatility", -1, "Higher-beta growth equity."),
        E("long_rates", -1, "Growth multiple is discount-rate sensitive."),
        E("yen_carry", +1, "Liquidity-sensitive growth."),
    ),
    Archetype.UTILITY_INFRASTRUCTURE: (
        E("long_rates", -1, "Trades as a bond proxy; higher yields lower it."),
        E("volatility", +1, "Regulated earnings make it defensive in stress."),
    ),
    Archetype.GENERIC_OPERATING_COMPANY: (),
}

# Proxy ETF whose return minus SPY stands in for the archetype in the regression.
PROXY_ETF: dict[Archetype, str | None] = {
    Archetype.ENTERPRISE_AI_SOFTWARE: "IGV",
    Archetype.TRADITIONAL_SAAS: "IGV",
    Archetype.FABLESS_SEMICONDUCTOR: "SMH",
    Archetype.SEMICONDUCTOR_FOUNDRY: "SMH",
    Archetype.HYPERSCALER_CLOUD_PLATFORM: "XLK",
    Archetype.CONSUMER_PLATFORM: "XLC",
    Archetype.RETAIL_PHYSICAL_NETWORK: "XRT",
    Archetype.BANK: "KBE",
    Archetype.INDUSTRIAL: "XLI",
    Archetype.PHARMA_BIOTECH: "XLV",
    Archetype.COMMODITY_PRODUCER: "XLE",
    Archetype.PAYMENT_NETWORK: "IPAY",
    Archetype.MARKETPLACE_PLATFORM: "XLY",
    Archetype.UTILITY_INFRASTRUCTURE: "XLU",
    Archetype.GENERIC_OPERATING_COMPANY: None,
}

LIQUIDITY_SENSITIVE = frozenset(archetype for archetype, entries in EXPOSURES.items() if any(item.factor == "yen_carry" for item in entries))


def load_validation(path: Path = VALIDATION_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def exposures_for(archetype: str | Archetype, validation: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Exposure entries for an archetype with their validation status attached."""
    key = Archetype(archetype) if not isinstance(archetype, Archetype) else archetype
    results = (validation if validation is not None else load_validation()).get("results", {})
    output = []
    for item in EXPOSURES.get(key, ()):
        factor = FACTORS[item.factor]
        tested = results.get(key.value, {}).get(item.factor)
        output.append({
            **asdict(item),
            "factor_label": factor.label,
            "rising_means": factor.rising_means,
            "environment_signals": list(factor.environment_signals),
            "claim_type": "STRUCTURAL_HYPOTHESIS",
            "validation": tested["status"] if tested else "UNTESTED",
            "evidence": tested,
        })
    return output


# ---- validation (checklist 3.2) ---------------------------------------------------------
def _weekly(frame):
    return frame["Close"].resample("W-FRI").last().dropna()


def factor_series(factor_id: str, histories: dict[str, Any]):
    """Weekly change series for a factor's market proxy, or None if unavailable."""
    factor = FACTORS[factor_id]
    if not factor.proxy or any(ticker not in histories for ticker in factor.tickers):
        return None
    weekly = {ticker: _weekly(histories[ticker]) for ticker in factor.tickers}
    if factor_id in {"long_rates", "fed_path", "volatility"}:
        return weekly[factor.tickers[0]].diff()
    returns = {ticker: series.pct_change() for ticker, series in weekly.items()}
    if factor_id in {"credit", "inflation"}:
        return returns[factor.tickers[0]] - returns[factor.tickers[1]]
    if factor_id == "semis_cycle":
        import pandas as pd
        return pd.concat(returns.values(), axis=1).mean(axis=1, skipna=False)
    return returns[factor.tickers[0]]


def _ols(x, y):
    """Slope and t-statistic of y on x with an intercept."""
    n = len(x)
    if n < 20:
        return None, None
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None, None
    beta = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    alpha = my - beta * mx
    residual = sum((b - alpha - beta * a) ** 2 for a, b in zip(x, y)) / (n - 2)
    se = math.sqrt(residual / sxx) if residual > 0 else 0.0
    return beta, (beta / se if se else None)


def classify(direction: int, beta: float | None, t_stat: float | None, agreement: float | None) -> str:
    if beta is None or t_stat is None:
        return "UNTESTED"
    same = (beta > 0) == (direction > 0)
    if same and abs(t_stat) >= 2 and (agreement or 0) >= 0.6:
        return "CONFIRMED"
    if not same and abs(t_stat) >= 2:
        return "DOWNGRADED"
    return "WEAK"


def validate(histories: dict[str, Any], window_weeks: int = 52, step_weeks: int = 4) -> dict[str, Any]:
    import pandas as pd

    spy = _weekly(histories["SPY"]).pct_change()
    results: dict[str, dict[str, Any]] = {}
    for archetype, entries in EXPOSURES.items():
        proxy = PROXY_ETF.get(archetype)
        results[archetype.value] = {}
        for item in entries:
            factor = factor_series(item.factor, histories)
            if not proxy or proxy not in histories or factor is None:
                results[archetype.value][item.factor] = {"status": "UNTESTED", "reason": "no proxy ETF" if not proxy or proxy not in histories else "no market proxy for this factor", "direction": item.direction}
                continue
            excess = _weekly(histories[proxy]).pct_change() - spy
            frame = pd.concat({"x": factor, "y": excess}, axis=1).dropna()
            beta, t_stat = _ols(frame["x"].tolist(), frame["y"].tolist())
            signs = []
            for start in range(0, max(0, len(frame) - window_weeks + 1), step_weeks):
                window = frame.iloc[start:start + window_weeks]
                window_beta, _ = _ols(window["x"].tolist(), window["y"].tolist())
                if window_beta is not None:
                    signs.append((window_beta > 0) == (item.direction > 0))
            agreement = sum(signs) / len(signs) if signs else None
            results[archetype.value][item.factor] = {
                "status": classify(item.direction, beta, t_stat, agreement),
                "direction": item.direction,
                "proxy_etf": proxy,
                "beta": beta,
                "t_stat": t_stat,
                "rolling_sign_agreement": agreement,
                "rolling_windows": len(signs),
                "weeks": len(frame),
                "first_week": str(frame.index[0].date()) if len(frame) else None,
                "last_week": str(frame.index[-1].date()) if len(frame) else None,
            }
    return {
        "schema_version": "1.0",
        "method": f"Weekly (W-FRI) proxy ETF return minus SPY regressed on each factor's weekly change; OLS with intercept; rolling {window_weeks}-week windows every {step_weeks} weeks.",
        "thresholds": {"confirmed": "same sign, |t| >= 2, rolling agreement >= 0.6", "downgraded": "opposite sign, |t| >= 2"},
        "factor_proxies": {key: factor.proxy for key, factor in FACTORS.items()},
        "results": results,
    }


def summary(validation: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for factors in validation.get("results", {}).values():
        for entry in factors.values():
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX archetype exposure map")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("validate", help="Download five years of weekly data and test every exposure.")
    run.add_argument("--period", default="5y")
    show = sub.add_parser("show", help="Print an archetype's exposures with validation status.")
    show.add_argument("archetype", choices=[item.value for item in Archetype])
    args = parser.parse_args(argv)
    if args.command == "validate":
        from signal_history import fetch_long_histories
        tickers = {"SPY", *(proxy for proxy in PROXY_ETF.values() if proxy), *(ticker for factor in FACTORS.values() for ticker in factor.tickers)}
        histories, failures = fetch_long_histories(tickers, period=args.period)
        if "SPY" not in histories:
            print("SPY unavailable; cannot validate.")
            return 1
        result = validate(histories)
        result["unavailable_tickers"] = failures
        VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        VALIDATION_PATH.write_text(json.dumps(result, indent=2) + "\n")
        print(summary(result))
        for ticker, reason in sorted(failures.items()):
            print(f"  unavailable: {ticker}: {reason}")
        return 0
    for entry in exposures_for(args.archetype):
        evidence = entry["evidence"] or {}
        t_stat = evidence.get("t_stat")
        print(f"{entry['factor']:12} {entry['direction']:+d}  {entry['validation']:10} t={t_stat if t_stat is None else round(t_stat, 2)}  {entry['mechanism']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
