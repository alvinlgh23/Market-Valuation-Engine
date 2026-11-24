"""Company judgment card (checklist P4).

One card per company that joins the macro environment, sector money flow, valuation and
crowding, read on three horizons. The card never prints buy/sell and never adds the axes
into one score: a total would mix back in the noise the separate axes filter out.

Axes (each: state, direction of change, confidence, up to two dated evidence lines,
missing inputs, and the independent information families it rests on)
    macro         environment factors the archetype is exposed to (exposure_map); downgraded
                  exposures are ignored; yen carry acts as a switch, not a vote
    flow          the company's sector ETF: 3M relative strength percentile in its own
                  history, held for >= 6 of the last 10 observations, and the company's 3M
                  return against that ETF
    valuation     what the price implies (reverse DCF) against observed and consensus growth;
                  the fair-value range is secondary
    crowding      existing heat / chase-risk engine
    expectations  consensus EPS trend and revision counts (Yahoo)
    fundamentals  company economics financial translation (revenue, margin, capital, FCF)

Horizons
    tactical  (1-3 months): risk regime, flow, crowding
    cyclical  (6-12 months): macro, expectations, fundamentals
    structural (3-5 years): valuation

Usage
    python company_verdict.py NVDA [MSFT ...] [--json] [--home-currency SGD]
    python company_verdict.py --watchlist            (data/watchlist.json)
    python model.py verdict NVDA
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from signal_history import SignalStore, observation

ROOT = Path(__file__).resolve().parent
WATCHLIST_PATH = ROOT / "data" / "watchlist.json"
ATTRIBUTION_CACHE = ROOT / ".cache" / "attribution"   # one file per company, refreshed daily (checklist 10.3)
FAMILIES = ("price", "fundamentals", "macro_data", "valuation")
YAHOO_SECTOR_ETF = {
    "technology": "XLK", "healthcare": "XLV", "financial services": "XLF", "consumer cyclical": "XLY", "consumer defensive": "XLP",
    "energy": "XLE", "industrials": "XLI", "basic materials": "XLB", "real estate": "XLRE", "utilities": "XLU", "communication services": "XLC",
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) else None


def _pct(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value * 100:+.{digits}f}%"


def _versus(p: float, noun: str, period: str) -> str:
    """A place in history in plain words, not a percentile (owner request 2026-11-24)."""
    n = round(p * 100)
    return f"higher than {n} of every 100 {noun} {period}" if n >= 50 else f"lower than {100 - n} of every 100 {noun} {period}"


def _size(value: float | None, digits: int = 1) -> str:
    """Unsigned magnitude, for sentences that already say lead/lag or up/down."""
    return "n/a" if value is None else f"{abs(value) * 100:.{digits}f}%"


def axis(state: str, *, direction: str | None = None, confidence: str = "LOW", evidence: list[str] | None = None,
         missing: list[str] | None = None, families: list[str] | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"state": state, "direction": direction, "confidence": confidence, "evidence": (evidence or [])[:2],
            "missing": missing or [], "families": sorted(set(families or [])), "detail": detail or {}}


# ---- sector mapping ------------------------------------------------------------------------
def sector_etf_for(ticker: str, yahoo_sector: str | None) -> tuple[str | None, str]:
    import Valuation_model as vm
    for etf, members in vm.SECTOR_CANDIDATES.items():
        if ticker.upper() in members and etf != ticker.upper():
            return etf, "listed constituent in the sector engine's candidate list"
    etf = YAHOO_SECTOR_ETF.get(str(yahoo_sector or "").strip().lower())
    return (etf, f"proxy from Yahoo sector '{yahoo_sector}'") if etf else (None, "no sector mapping")


# ---- axes ----------------------------------------------------------------------------------
def macro_axis(archetype: str, environment: dict[str, Any], sector_etf: str | None = None) -> dict[str, Any]:
    from exposure_map import LIQUIDITY_SENSITIVE, exposures_for
    from company_economics_registry import Archetype

    factors = environment.get("factors") or {}
    # Checklist 10.5: factors whose scorecard sign was reversed (high VIX preceded *better* returns) describe
    # what already moved prices; they are shown but not counted as a forward tailwind or headwind.
    reversed_ids = {"volatility"} if "vix_score" in reversed_signals() else set()
    rows, tail, head, missing = [], 0, 0, []
    for exposure in exposures_for(archetype, sector_etf=sector_etf):
        if exposure["factor"] == "yen_carry":
            continue  # a switch, handled below
        if exposure["validation"] == "DOWNGRADED":
            continue
        factor = factors.get(exposure["factor"]) or {}
        direction = factor.get("direction")
        if direction is None:
            missing.append(f"{exposure['factor_label']} current state")
            continue
        effect = direction * exposure["direction"]
        weight = "context" if exposure["factor"] in reversed_ids else "confirmed" if exposure["validation"] == "CONFIRMED" else "unconfirmed"
        rows.append({"factor": exposure["factor"], "label": exposure["factor_label"], "factor_state": factor.get("state"),
                     "effect": effect, "validation": exposure["validation"], "mechanism": exposure["mechanism"], "weight": weight})
        if weight == "confirmed":
            tail += effect > 0
            head += effect < 0
    confirmed = [row for row in rows if row["weight"] == "confirmed"]
    if not confirmed:
        state, confidence = "No confirmed exposure has a current reading", "LOW"
    elif tail > head:
        state, confidence = "Tailwind", "MODERATE" if tail - head >= 2 else "LOW"
    elif head > tail:
        state, confidence = "Headwind", "MODERATE" if head - tail >= 2 else "LOW"
    else:
        state, confidence = "Mixed", "LOW"
    carry = (factors.get("yen_carry") or {}).get("readings", {}).get("carry_state")
    switch = None
    try:
        sensitive = Archetype(archetype) in LIQUIDITY_SENSITIVE
    except ValueError:
        sensitive = False
    if carry == "UNWIND_RISK" and sensitive:
        switch = "Yen-carry unwind risk is on and this business is liquidity-sensitive."
    evidence = [f"{row['label']}: {row['factor_state']} → {'tailwind' if row['effect'] > 0 else 'headwind' if row['effect'] < 0 else 'neutral'} ({row['validation'].lower()})"
                for row in sorted(confirmed, key=lambda item: -abs(item["effect"]))]
    context_note = [f"{row['label']}: {row['factor_state']}. Moves prices at the time, but high readings preceded better, not worse, returns in the scorecard, so it is not counted as a headwind."
                    for row in rows if row["weight"] == "context"]
    if switch:
        evidence.insert(0, switch)
    return axis(state, confidence=confidence, evidence=evidence, missing=missing, families=["macro_data", "price"],
                detail={"exposures": rows, "confirmed_tailwinds": tail, "confirmed_headwinds": head, "carry_switch": switch, "context_only": context_note})


def reversed_signals() -> set[str]:
    """Signals whose forward sign was the opposite of the hypothesis in the scorecard (checklist 6.1)."""
    path = ROOT / "data" / "signal_validation.json"
    try:
        return set(json.loads(path.read_text()).get("reversed", []))
    except (OSError, json.JSONDecodeError):
        return set()


def card_removals() -> set[str]:
    """Signals the scorecard found to carry no information (checklist 6.2); empty if it has not been run."""
    path = ROOT / "data" / "signal_validation.json"
    try:
        return set(json.loads(path.read_text()).get("card_removals", []))
    except (OSError, json.JSONDecodeError):
        return set()


FLOW_BASIS = (("rel_1m", "1M"), ("rel_3m", "3M"), ("rel_6m", "6M"))


def flow_axis(ticker: str, etf: str | None, mapping_note: str, store: SignalStore, company_vs_sector_3m: float | None,
              sector_flow: dict[str, Any] | None = None, removed: set[str] | None = None) -> dict[str, Any]:
    if not etf:
        return axis("No sector mapping", missing=["sector ETF for this company"], families=["price"])
    removed = card_removals() if removed is None else removed
    basis = next(((metric, label) for metric, label in FLOW_BASIS if metric not in removed), None)
    if basis is None:
        return axis("No informative flow signal", missing=["a relative-strength horizon that passed the scorecard"], families=["price"])
    metric, horizon = basis
    signal = f"sector.{etf}.{metric}"
    points = store.series(signal)
    if len(points) < 60:
        return axis("Insufficient sector history", missing=[f"{signal} history"], families=["price"], detail={"sector_etf": etf})
    buckets = []
    for index in range(max(0, len(points) - 10), len(points)):
        day, value = points[index]
        percentile = store.percentile(signal, value=value, as_of=day)
        buckets.append(None if percentile is None else 1 if percentile >= 0.67 else -1 if percentile <= 0.33 else 0)
    latest_day, latest = points[-1]
    percentile = store.percentile(signal, value=latest, as_of=latest_day)
    current = buckets[-1]
    held = sum(bucket == current for bucket in buckets if bucket is not None)
    names = {1: "Money flowing in", -1: "Money flowing out", 0: "Neutral"}
    state = names.get(current, "Unavailable") if held >= 6 else "Mixed (not persistent)"
    prior = store.value_observations_ago(signal, 21)
    direction = None if prior is None else "strengthening" if latest > prior[1] else "weakening" if latest < prior[1] else "unchanged"
    evidence = [f"{etf} against the S&P 500 over {({'1M': 'one month', '3M': 'three months', '6M': 'six months'}).get(horizon, horizon)}: {_pct(latest)} on {latest_day}, {_versus(percentile, 'readings', 'in its stored record')}; the same reading on {held} of the last 10 days."]
    flow = sector_flow or {}
    volume_parts = []
    if flow.get("dollar_volume_percentile") is not None:
        volume_parts.append(f"trading value {_versus(flow['dollar_volume_percentile'], 'days', 'in its record')}")
    if flow.get("updown_volume_20d") is not None:
        volume_parts.append(f"up/down volume {flow['updown_volume_20d']:.2f}")
    if flow.get("breadth_50") is not None and "breadth_50" not in removed:
        volume_parts.insert(0, f"{flow['breadth_50']:.0%} of {etf}'s top holdings above their 50-day average")
    if volume_parts:
        evidence.append(f"{etf}: " + ", ".join(volume_parts) + ".")
    elif company_vs_sector_3m is not None:
        evidence.append(f"{ticker} {'leads' if company_vs_sector_3m > 0 else 'lags'} {etf} by {_size(company_vs_sector_3m)} over three months.")
    missing = [] if volume_parts else ["sector volume"]
    if not flow.get("shares_outstanding_change"):
        missing.append("ETF share creation/redemption (history starts with the first snapshot)")
    confidence = "MODERATE" if held >= 8 else "LOW"
    if flow.get("breadth_50") is not None and "breadth_50" not in removed and current in (1, -1):
        confirms = (current == 1 and flow["breadth_50"] >= 0.5) or (current == -1 and flow["breadth_50"] < 0.5)
        if not confirms:
            confidence = "LOW"
            evidence.append("Breadth does not confirm the relative-strength reading.")
    return axis(state, direction=direction, confidence=confidence, evidence=evidence, families=["price"], missing=missing,
                detail={"sector_etf": etf, "mapping": mapping_note, "basis": metric, "relative_strength": latest, "percentile": percentile,
                        "persistence_of_10": held, "company_vs_sector_3m": company_vs_sector_3m, "relative_strength_21_obs_ago": prior,
                        "sector_flow": flow, "removed_by_scorecard": sorted(removed)})


def plain_withheld_reason(report: dict[str, Any]) -> str | None:
    """Checklist 11.5: why fair value is withheld, in words an investor can act on (the model's text stays in detail)."""
    quality = report.get("data_quality") or {}
    status, missing = quality.get("status"), quality.get("missing") or []
    if report.get("company_type") == "Financial Institution":
        return "Banks and lenders are valued on book value and return on equity, not cash flow. That model is not built yet, so no fair value is shown."
    if status == "SECURITY_UNIT_AMBIGUITY":
        return "The accounts are in a different currency from the share price (an ADR). The share-ratio and FX conversion is not built yet."
    if status == "FAILED_FCFF_RECONCILIATION" and missing:
        return f"The filings we read do not report {', '.join(missing)}, so cash flow cannot be checked. Nothing is filled in with zero."
    if status == "FAILED_FCFF_RECONCILIATION":
        return "Two independent measures of last year's cash flow disagree by more than the allowed gap, so the model will not value the company until the difference is explained."
    return None


LOWER_CONFIDENCE = {"HIGH": "MODERATE", "MODERATE": "LOW", "LOW": "LOW"}
BASE_LABEL = {"operating_profit": "operating-profit base", "cash_flow_statement": "cash-flow-statement base"}


def _range_text(low: float | None, high: float | None, fmt) -> str:
    if low is None or high is None:
        return "n/a"
    low, high = sorted((low, high))
    return fmt(low) if abs(high - low) < 1e-9 else f"{fmt(low)} to {fmt(high)}"


ROE_BAND = 0.02   # implied vs latest ROE within two points reads as "roughly matches"
QUOTE_UNIT_KEYS = {"current_market_price", "fair_value_per_share", "high_case_value", "low_case_value", "bear", "base", "bull"}


def _scale(node: Any, factor: float) -> Any:
    if isinstance(node, dict):
        return {key: (value * factor if key in QUOTE_UNIT_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool) else _scale(value, factor))
                for key, value in node.items()}
    return node


def in_quote_units(report: dict[str, Any]) -> dict[str, Any]:
    """Checklist 12.3: per-share figures of a company-level (ADR) valuation, converted to the quoted share price."""
    bridge = report.get("unit_bridge") or {}
    factor = _num(bridge.get("quote_per_model_share"))
    if not factor:
        return report
    converted = dict(report)
    for key in ("company", "scenarios", "fair_value", "reverse_dcf", "cash_flow_bases"):
        if key in report:
            converted[key] = _scale(report[key], factor)
    return converted


def bank_axis(bank: dict[str, Any], price: float | None = None, observed_growth: float | None = None,
              consensus_growth: float | None = None) -> dict[str, Any]:
    """Checklist 12.2: what the price assumes about a bank's return on equity."""
    implied, latest = _num(bank.get("implied_roe")), _num(bank.get("latest_roe"))
    if implied > latest + ROE_BAND:
        state = "Price implies higher ROE than the bank earns"
    elif implied < latest - ROE_BAND:
        state = "Price implies lower ROE than the bank earns"
    else:
        state = "Price roughly matches the bank's ROE"
    evidence = [f"Price-to-book {bank['price_to_book']:.2f} with a {bank['cost_of_equity']:.1%} cost of equity (beta {bank.get('beta', 0):.2f}) implies a sustained ROE of {implied:.1%}; latest annual ROE {latest:.1%}.",
                "Banks are not valued on cash flow; single-stage justified price-to-book with 2.5% long-run growth."]
    return axis(state, confidence="LOW", evidence=evidence, families=["valuation", "fundamentals"],
                detail={"bank_implied_roe": bank, "fair_value": {}, "notes": [bank.get("method")], "price": price,
                        "observed_growth": observed_growth, "consensus_next_year_growth": consensus_growth},
                missing=["regulatory capital and payout history", "ROE history (one year used)"])


def valuation_axis(report: dict[str, Any] | None, observed_growth: float | None, consensus_growth: float | None,
                   implied_erp: float | None, erp_sensitivity: dict[str, Any] | None, band: dict[str, Any] | None = None) -> dict[str, Any]:
    """Checklist 12.1: when the two cash-flow measures differ, read both and publish only what holds on both.
    12.2: banks read the ROE the price implies. 12.3: ADR figures are converted to the quoted share first."""
    bank = (report or {}).get("bank_implied_roe") or {}
    if bank.get("status") == "AVAILABLE":
        return bank_axis(bank, _num((report.get("company") or {}).get("current_market_price")), observed_growth, consensus_growth)
    if report and report.get("unit_bridge"):
        report = in_quote_units(report)
    bases = (report or {}).get("cash_flow_bases") or {}
    if not bases or (report.get("data_quality") or {}).get("status") != "CASH_FLOW_MEASURES_DIFFER":
        return _single_valuation_axis(report, observed_growth, consensus_growth, implied_erp, erp_sensitivity, band)
    alt_source = bases.get("alternate") or {}
    alternate_report = {**report, "reverse_dcf": alt_source.get("reverse_dcf") or {}, "fair_value": alt_source.get("fair_value") or {},
                        "scenarios": {name: {"fair_value_per_share": value} for name, value in (alt_source.get("scenarios") or {}).items()}}
    shown = _single_valuation_axis(report, observed_growth, consensus_growth, implied_erp, erp_sensitivity, band)
    other = _single_valuation_axis(alternate_report, observed_growth, consensus_growth, implied_erp, erp_sensitivity, band)
    gap = _num(bases.get("gap_pct"))
    rev_a, rev_b = _reverse_of(report), _reverse_of(alternate_report)
    implied = [_num(rev.get("required_5y_revenue_cagr")) if rev.get("converged") else None for rev in (rev_a, rev_b)]
    reach = [_num(rev.get("high_case_value")) for rev in (rev_a, rev_b)]
    detail = {**shown["detail"], "cash_flow_bases": {
        "gap_pct": gap, "operating_profit_base": bases.get("operating_profit_base"), "cash_flow_statement_base": bases.get("cash_flow_statement_base"),
        "readings": {"operating_profit": shown["state"], "cash_flow_statement": other["state"]},
        "implied_5y_revenue_cagr": {"operating_profit": implied[0], "cash_flow_statement": implied[1]},
        "fair_value": {"operating_profit": shown["detail"].get("fair_value"), "cash_flow_statement": other["detail"].get("fair_value")}}}
    if None not in implied:
        span = f"Price implies {_range_text(implied[0], implied[1], _pct)} five-year revenue CAGR"
    elif None not in reach and shown["state"] == other["state"] and "above what the model can reach" in shown["state"]:
        span = f"Even 50% first-year growth values the share at {_range_text(reach[0], reach[1], lambda v: f'{v:.2f}')}"
        stretches = [value for value in (shown["detail"].get("price_to_max_case"), other["detail"].get("price_to_max_case")) if value is not None]
        if stretches:
            detail["price_to_max_case"] = min(stretches)      # the more generous base: the smaller stretch
            span = f"The price is {_range_text(min(stretches), max(stretches), lambda v: f'{v:.1f}x')} what even 50% first-year growth justifies"
    else:
        span = None
    measures = f"the two measures of last year's free cash flow differ by {gap:.0%}" if gap is not None else "the two measures of last year's free cash flow differ"
    if shown["state"] == other["state"] and shown["state"] != "Fair value withheld":
        evidence = [f"{span} on the two cash-flow bases; {reference_text(observed_growth, consensus_growth, band)}." if span else shown["evidence"][0] if shown["evidence"] else "",
                    f"The reading holds on both bases, though {measures}."]
        return axis(shown["state"], direction=shown["direction"], confidence=LOWER_CONFIDENCE.get(shown["confidence"], "LOW"),
                    evidence=[item for item in evidence if item], missing=shown["missing"], families=shown["families"], detail=detail)
    detail["fair_value"] = {}
    evidence = [f"{span} depending on the base; {reference_text(observed_growth, consensus_growth, band)}." if span
                else f"Operating-profit base: {shown['state']}; cash-flow-statement base: {other['state']}."]
    return axis("Depends on which cash-flow measure", confidence="LOW", evidence=evidence, families=["valuation"], detail=detail,
                missing=[f"No single fair value: {measures}, and the answer changes with the measure "
                         f"({shown['state'].lower()} on the operating-profit base, {other['state'].lower()} on the cash-flow-statement base)."])


def _reverse_of(report: dict[str, Any]) -> dict[str, Any]:
    """The reverse DCF the card reads: the phased headline's when it has one (checklist 7.6), else the five-year one."""
    headline = report.get("fair_value") or {}
    return (headline.get("reverse_dcf") if headline.get("fair_value") else None) or report.get("reverse_dcf") or {}


# Checklist 15.6 (owner-approved 2026-11-24): the five-year growth the price assumes is compared with
# two references of similar length, analysts' two-year yearly growth and the last three years' actual
# yearly growth, instead of one year of forecasts. More than 5 points above both: priced high; more than
# 5 points below both: priced low; otherwise it roughly matches.
BAND_MARGIN = 0.05


def growth_band_from(expectations: dict[str, Any] | None) -> dict[str, Any] | None:
    band = {"consensus_2y": _num((expectations or {}).get("revenue_cagr_2y_consensus")), "history_3y": _num((expectations or {}).get("revenue_cagr_3y_history"))}
    return band if any(value is not None for value in band.values()) else None


def band_reading(implied: float, band: dict[str, Any]) -> str:
    references = [value for value in (band.get("consensus_2y"), band.get("history_3y")) if value is not None]
    if implied > max(references) + BAND_MARGIN:
        return "Price implies more growth than observed/consensus"
    if implied < min(references) - BAND_MARGIN:
        return "Price implies less growth than observed/consensus"
    return "Price roughly matches observed/consensus growth"


def reference_text(observed: float | None, consensus: float | None, band: dict[str, Any] | None) -> str:
    if band:
        parts = []
        if band.get("consensus_2y") is not None:
            parts.append(f"analysts expect {_pct(band['consensus_2y'])} a year over the next two years")
        if band.get("history_3y") is not None:
            parts.append(f"the last three years grew {_pct(band['history_3y'])} a year")
        return " and ".join(parts)
    return f"observed {_pct(observed)}, consensus next year {_pct(consensus)}"


def _single_valuation_axis(report: dict[str, Any] | None, observed_growth: float | None, consensus_growth: float | None,
                           implied_erp: float | None, erp_sensitivity: dict[str, Any] | None, band: dict[str, Any] | None = None) -> dict[str, Any]:
    if not report:
        return axis("Valuation unavailable", missing=["valuation report"], families=["valuation"])
    price = _num((report.get("company") or {}).get("current_market_price"))
    headline = report.get("fair_value") or {}
    if headline.get("fair_value"):
        # Checklist 7.6 (owner decision): the ten-year model is phased in above the type's growth cap.
        reverse = _reverse_of(report)
        fair = {name: _num(headline["fair_value"].get(name)) for name in ("bear", "base", "bull")}
    else:
        reverse = report.get("reverse_dcf") or {}
        scenarios = report.get("scenarios") or {}
        fair = {name: _num((scenarios.get(name) or {}).get("fair_value_per_share")) for name in ("bear", "base", "bull")}
    rates = report.get("discount_rate") or {}
    weight = _num(headline.get("extended_weight"))
    if headline.get("method") == "PHASED" and weight is not None:
        notes = [f"Blends the five-year ({1 - weight:.0%}) and ten-year ({weight:.0%}) models: observed growth {_pct(headline.get('observed_growth'))} is above the {_pct(headline.get('type_cap'))} cap; full ten-year weight at cap + {_pct(headline.get('phase_in_band'))}."]
    elif report.get("company_type") == "Cyclical Company" or "Cyclical company" in str(headline.get("reason")):
        notes = ["Cyclical company: five-year model on normalized mid-cycle economics; the ten-year model is not blended in (owner decision 2026-11-22)."]
    else:
        notes = ["Five-year explicit forecast with a capped first-year growth rate and 2.5% terminal growth; growth is within the type's cap, so the ten-year model is not blended in."]
    detail = {"price": price, "fair_value": fair, "valuation_method": headline.get("method"), "ten_year_weight": weight,
              "growth_basis": headline.get("growth_basis"), "latest_quarter_yoy": ((headline.get("growth_inputs") or {}).get("latest_quarter_yoy")),
              "reverse_dcf_status": reverse.get("status"), "observed_growth": observed_growth,
              "consensus_next_year_growth": consensus_growth, "fixed_erp": _num(rates.get("equity_risk_premium")), "implied_erp": implied_erp,
              "erp_sensitivity": erp_sensitivity, "wacc": _num(rates.get("wacc")), "notes": notes}
    status = reverse.get("status")
    evidence: list[str] = []
    if reverse.get("converged"):
        implied = _num(reverse.get("required_5y_revenue_cagr"))
        detail["implied_5y_revenue_cagr"] = implied
        reference = consensus_growth if consensus_growth is not None else observed_growth
        detail["growth_band"] = band
        if implied is not None and band:
            state = band_reading(implied, band)
        elif implied is None or reference is None:
            state = "Priced growth known; no comparison growth"
        elif implied > reference + 0.05:
            state = "Price implies more growth than observed/consensus"
        elif implied < reference - 0.05:
            state = "Price implies less growth than observed/consensus"
        else:
            state = "Price roughly matches observed/consensus growth"
        evidence.append(f"The price {price} assumes sales grow {_pct(implied)} a year for five years; {reference_text(observed_growth, consensus_growth, band)}.")
        confidence = "MODERATE"
    elif status == "NO_ECONOMIC_SOLUTION":
        high, low = _num(reverse.get("high_case_value")), _num(reverse.get("low_case_value"))
        if high is not None and price is not None and high < price:
            state = "Price implies growth above what the model can reach"
            # Checklist 18.16: how far beyond, so companies above the ceiling can still be compared.
            if high > 0:
                detail["price_to_max_case"] = price / high
            stretch = f"The price is {price / high:.1f}x what even 50% first-year growth justifies ({high:.2f} vs {price:.2f})" if high > 0 else \
                f"Even 50% first-year growth values the share at {high:.2f} vs price {price:.2f}"
            evidence.append(f"{stretch}; {reference_text(observed_growth, consensus_growth, band)}.")
        elif low is not None and price is not None and low > price:
            state = "Price implies contraction beyond the model's floor"
            evidence.append(f"Even -20% first-year growth values the share at {low:.2f} vs price {price:.2f}.")
        else:
            state = "Reverse DCF has no solution"
        confidence = "LOW"
    else:
        reason = (report.get("data_quality") or {}).get("reason") or reverse.get("reason") or (report.get("final_interpretation") or {}).get("text")
        detail["model_reason"] = reason
        return axis("Fair value withheld", missing=[plain_withheld_reason(report) or reason or "valuation inputs"], families=["valuation"], detail=detail)
    if all(value is not None for value in fair.values()) and price is not None:
        evidence.append(f"Model range {fair['bear']:.2f} / {fair['base']:.2f} / {fair['bull']:.2f} (bear/base/bull) against price {price:.2f}; secondary to the priced-growth read.")
    return axis(state, confidence=confidence, evidence=evidence, families=["valuation", "fundamentals"], detail=detail,
                missing=["valuation multiple history (percentile in own history)"])


def crowding_axis(heat: dict[str, Any] | None, sector_flow: dict[str, Any] | None = None, relative: dict[str, Any] | None = None) -> dict[str, Any]:
    if not heat:
        return axis("Crowding unavailable", missing=["price and valuation heat"], families=["price"])
    import Valuation_model as vm
    label = vm.chase_risk_label(heat)
    sector_crowding = (sector_flow or {}).get("crowding")
    valuation = (relative or {}).get("valuation") or {}
    technicals = f"{_pct(heat.get('dist_200'))} from the 200-day average" + (f", RSI {heat.get('rsi'):.0f}" if heat.get("rsi") is not None else "")
    missing = ["positioning data (short interest, options, fund ownership)"]
    # Checklist 7.3 step 2: the valuation part is read against the company's own history first.
    if valuation.get("state") == "AVAILABLE":
        evidence = [f"Price-to-sales {valuation['current']:.1f}, {_versus(valuation['percentile'], 'days', 'since ' + valuation['first'][:4])}; {technicals}."]
    else:
        evidence = [f"Heat {heat.get('heat'):.0f}/100 on the absolute scale (valuation {heat.get('valuation_heat'):.0f}, momentum {heat.get('momentum_heat'):.0f}); {technicals}."]
        missing.append(f"valuation in own history ({valuation.get('reason') or valuation.get('state') or 'not computed'})")
    if sector_crowding and sector_crowding != "Unavailable":
        evidence.append(f"Sector positioning: {sector_crowding} (breadth, dollar volume and relative strength against their own history).")
    return axis(label, confidence="LOW", evidence=evidence, families=["price", "valuation"], missing=missing,
                detail={**{key: heat.get(key) for key in ("heat", "valuation_heat", "momentum_heat", "rsi", "dist_50", "dist_200", "six_month", "forward_pe", "ev_sales")},
                        "valuation_in_own_history": valuation})


def _fiscal_year_text(year_end: str | None) -> str:
    try:
        return f" (fiscal year ending {dt.date.fromisoformat(year_end):%b %Y})" if year_end else ""
    except ValueError:
        return ""


def expectations_axis(expectations: dict[str, Any] | None) -> dict[str, Any]:
    if not expectations or expectations.get("error"):
        return axis("Consensus data unavailable", missing=[(expectations or {}).get("error") or "consensus estimates"], families=["fundamentals"])
    trend = expectations.get("eps_trend_next_year") or {}
    current, ago = _num(trend.get("current")), _num(trend.get("90daysAgo"))
    change = None if current is None or not ago else current / ago - 1
    up, down = expectations.get("revisions_up_30d"), expectations.get("revisions_down_30d")
    if change is None:
        state = "Revisions unavailable"
    elif change > 0.02 and (up or 0) > (down or 0):
        state = "Estimates rising"
    elif change < -0.02 and (down or 0) > (up or 0):
        state = "Estimates falling"
    else:
        state = "Estimates stable or mixed"
    year = _fiscal_year_text(expectations.get("forward_fiscal_year_end"))
    evidence = [f"Next-year EPS estimate{year} {_pct(change)} over 90 days; last 30 days {up} up / {down} down revisions."]
    if expectations.get("revenue_growth_next_year") is not None:
        evidence.append(f"Consensus revenue growth next fiscal year{year} {_pct(expectations['revenue_growth_next_year'])} ({expectations.get('analysts_next_year')} analysts).")
    return axis(state, direction=None if change is None else "up" if change > 0 else "down", confidence="MODERATE" if change is not None else "LOW",
                evidence=evidence, families=["fundamentals"], detail=expectations)


QUARTER_STATES = {"IMPROVING": "Improving", "DETERIORATING": "Deteriorating", "MIXED": "Mixed", "NO_CHANGE": "No change"}


def fundamentals_axis(economics: dict[str, Any] | None, relative: dict[str, Any] | None = None, quarterly: dict[str, Any] | None = None) -> dict[str, Any]:
    """Checklist 15.5: the latest quarterly report decides whether the business changed; the stored
    economics profile is the fallback when the quarter cannot be read."""
    if quarterly and quarterly.get("status") == "AVAILABLE":
        shift = quarterly.get("change") or {}
        finances = quarterly.get("health") or {}
        if shift.get("state") in QUARTER_STATES:
            evidence = [quarterly["summary"]]
            if shift.get("reasons"):
                evidence.append(f"{QUARTER_STATES[shift['state']]}: {'; '.join(shift['reasons'])}.")
            if finances.get("state") == "NOT_APPLICABLE":
                evidence.append(f"Finances: {finances['reason']}")
            return axis(QUARTER_STATES[shift["state"]], confidence="MODERATE", evidence=evidence, families=["fundamentals"],
                        detail={"quarterly": quarterly, "basis": "latest quarterly report",
                                "archetype": ((economics or {}).get("classification") or {}).get("primary_archetype")})
    if not economics:
        return axis("Company economics unavailable", missing=["company economics"], families=["fundamentals"])
    translation = economics.get("financial_translation") or {}
    states = {key: (value or {}).get("state") for key, value in translation.items() if isinstance(value, dict)}
    positive = sum(state == "POSITIVE" for state in states.values())
    negative = sum(state == "NEGATIVE" for state in states.values())
    unknown = sum(state in (None, "INSUFFICIENT_EVIDENCE") for state in states.values())
    if unknown == len(states) or not states:
        state = "Trajectory not established"
    elif positive > negative:
        state = "Improving"
    elif negative > positive:
        state = "Deteriorating"
    else:
        state = "Mixed"
    growth = (economics.get("growth_sustainability") or {}).get("current_revenue_growth")
    evidence = [", ".join(f"{key.replace('_', ' ')} {str(value).lower().replace('_', ' ')}" for key, value in states.items())]
    if growth is not None:
        evidence.append(f"Current revenue growth {_pct(growth)}.")
    quality = (relative or {}).get("quality") or {}
    if quality.get("quality_percentile") is not None:
        evidence.append(f"Business quality better than {quality['quality_percentile']:.0%} of its {quality['peers']} sector peers (score {quality['metrics']['score']['value']:.0f} of 100).")
    return axis(state, confidence="MODERATE" if unknown == 0 else "LOW", evidence=evidence, families=["fundamentals"],
                missing=[f"{key.replace('_', ' ')}" for key, value in states.items() if value in (None, "INSUFFICIENT_EVIDENCE")],
                detail={"peer_quality": quality, "financial_translation": states, "current_revenue_growth": growth, "archetype": (economics.get("classification") or {}).get("primary_archetype")})


# ---- cross-axis reading ----------------------------------------------------------------------
def contradictions(axes: dict[str, dict[str, Any]], environment: dict[str, Any], exposed_factors: set[str]) -> list[str]:
    output = []
    flow, valuation, macro, crowding, expectations = (axes[key] for key in ("flow", "valuation", "macro", "crowding", "expectations"))
    gap = flow["detail"].get("company_vs_sector_3m")
    if flow["state"] == "Money flowing in" and gap is not None and gap < -0.05:
        output.append(f"Money is flowing into the sector but the company lags it by {_size(gap)} over three months.")
    if flow["state"] == "Money flowing out" and gap is not None and gap > 0.05:
        output.append(f"The company leads its sector by {_size(gap)} while money flows out of the sector.")
    if macro["state"] == "Headwind" and valuation["state"].startswith(("Price implies growth above", "Price implies more growth")):
        output.append("The macro environment is a headwind for this business while the price assumes strong growth.")
    if crowding["state"].lower().startswith(("high", "extreme", "elevated")) and flow["direction"] == "weakening":
        output.append("Positioning looks crowded while sector relative strength is weakening.")
    if expectations["state"] == "Estimates rising" and flow["state"] == "Money flowing out":
        output.append("Analysts are raising estimates while money leaves the sector.")
    for item in environment.get("contradictions") or []:
        if set(item.get("factors") or []) & exposed_factors:
            output.append(item["text"])
    return output


def next_catalysts(earnings_date: str | None, fomc: dict[str, Any] | None, today: dt.date) -> dict[str, Any]:
    """Only future dates count as next catalysts; a past earnings date is reported as last reported."""
    output: dict[str, Any] = {"earnings": None, "last_earnings": None, "fomc": (fomc or {}).get("date")}
    if earnings_date:
        try:
            day = dt.date.fromisoformat(str(earnings_date)[:10])
        except ValueError:
            day = None
        if day and day >= today:
            output["earnings"] = day.isoformat()
        elif day:
            output["last_earnings"] = day.isoformat()
    return output


def falsification(economics: dict[str, Any] | None) -> list[str]:
    return [item.get("condition") for item in (economics or {}).get("falsification_conditions") or [] if item.get("condition")][:4]


# Checklist 18.13: every recorded card carries the version of the rules that produced it. Raise this
# whenever a card rule changes, so a reading that moved because the rules moved is not shown as news.
VERDICT_RULES_VERSION = "2026-11-24"
VERDICT_SOURCE = f"company_verdict@{VERDICT_RULES_VERSION}"


def change_origin(before_source: str | None, after_source: str | None) -> str:
    """COMPANY: both readings came from the same rules, so the company or its data changed.
    RULES: the rules changed between them. UNKNOWN: recorded before versions existed (21-24 Nov 2026,
    while the rules were being revised), so a rule change cannot be ruled out."""
    if not before_source or "@" not in before_source or not after_source or "@" not in after_source:
        return "UNKNOWN"
    return "COMPANY" if before_source == after_source else "RULES"


def changes_since_last(ticker: str, axes: dict[str, dict[str, Any]], store: SignalStore, today: str) -> list[dict[str, str]]:
    output = []
    for key, value in axes.items():
        prior = [row for row in store.rows(f"verdict.{ticker}.{key}") if row["observation_date"] < today and row["label"]]
        if prior and prior[-1]["label"] != value["state"]:
            output.append({"axis": key, "from": prior[-1]["label"], "to": value["state"], "since": prior[-1]["observation_date"],
                           "origin": change_origin(prior[-1].get("source"), VERDICT_SOURCE)})
    return output


def record_verdict(ticker: str, axes: dict[str, dict[str, Any]], store: SignalStore, today: str) -> int:
    # Checklist 18.16: the valuation row also stores how far above the model's ceiling the price is.
    def value_of(key: str, axis_value: dict[str, Any]) -> float | None:
        return _num((axis_value.get("detail") or {}).get("price_to_max_case")) if key == "valuation" else None
    return store.append([observation(f"verdict.{ticker}.{key}", today, value=value_of(key, value), label=value["state"], source=VERDICT_SOURCE, source_state="LIVE")
                         for key, value in axes.items()])


# ---- data collection (network) ---------------------------------------------------------------
def forward_fiscal_year(current_fiscal_year_end: dt.date | None, today: dt.date) -> tuple[str, dt.date | None]:
    """The fiscal year the card calls "next year" (owner decision 2026-11-24).

    Yahoo labels the fiscal year in progress "0y" and the one after it "+1y". While at least half of the
    current fiscal year is still ahead, it is the next year to be reported ("0y"); in its second half the
    following year ("+1y") is. Without the year-end date the old choice ("+1y") is kept.
    """
    if current_fiscal_year_end is None:
        return "+1y", None
    if (current_fiscal_year_end - today).days >= 365 / 2:
        return "0y", current_fiscal_year_end
    try:
        following = current_fiscal_year_end.replace(year=current_fiscal_year_end.year + 1)
    except ValueError:  # 29 February
        following = current_fiscal_year_end + dt.timedelta(days=365)
    return "+1y", following


def consensus_two_year_cagr(this_year: dict[str, Any], next_year: dict[str, Any]) -> float | None:
    """Yearly sales growth analysts expect from the last reported fiscal year to two years after it."""
    base, target = _num(this_year.get("yearAgoRevenue")), _num(next_year.get("avg"))
    return (target / base) ** 0.5 - 1 if base and target and base > 0 and target > 0 else None


def history_cagr(annual) -> float | None:
    """Actual yearly sales growth over the last three reported fiscal years (four annual figures)."""
    try:
        values = [float(value) for value in annual.loc["Total Revenue"].dropna().tolist()]   # newest first
    except Exception:  # noqa: BLE001
        return None
    if len(values) < 4 or values[3] <= 0 or values[0] <= 0:
        return None
    return (values[0] / values[3]) ** (1 / 3) - 1


def collect_expectations(ticker: str, today: dt.date | None = None) -> dict[str, Any]:
    import yfinance as yf
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            handle = yf.Ticker(ticker)
            trend, revisions, revenue, calendar = handle.eps_trend, handle.eps_revisions, handle.revenue_estimate, handle.calendar
            year_end_stamp = (handle.info or {}).get("nextFiscalYearEnd")
            annual = handle.income_stmt
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    def row(frame, period):
        try:
            return {key: (value.item() if hasattr(value, "item") else value) for key, value in frame.loc[period].to_dict().items()}
        except Exception:  # noqa: BLE001
            return {}
    try:
        current_year_end = dt.datetime.fromtimestamp(int(year_end_stamp), dt.timezone.utc).date() if year_end_stamp else None
    except (TypeError, ValueError, OverflowError, OSError):
        current_year_end = None
    period, year_end = forward_fiscal_year(current_year_end, today or dt.date.today())
    next_year_revenue = row(revenue, period)
    rev = row(revisions, period)
    earnings_dates = (calendar or {}).get("Earnings Date") or []
    cagr_2y, cagr_3y = consensus_two_year_cagr(row(revenue, "0y"), row(revenue, "+1y")), history_cagr(annual)
    return {
        "eps_trend_next_year": row(trend, period),
        "revisions_up_30d": rev.get("upLast30days"), "revisions_down_30d": rev.get("downLast30days"),
        "revenue_growth_next_year": _num(next_year_revenue.get("growth")), "analysts_next_year": next_year_revenue.get("numberOfAnalysts"),
        "forward_period": period, "forward_fiscal_year_end": year_end.isoformat() if year_end else None,
        "next_earnings_date": str(earnings_dates[0]) if earnings_dates else None,
        "revenue_cagr_2y_consensus": cagr_2y, "revenue_cagr_3y_history": cagr_3y,
        "source": "Yahoo Finance analyst estimates via yfinance",
    }


def next_fomc(today: dt.date, timeout: int = 20) -> dict[str, Any]:
    """Next FOMC decision date parsed from the Federal Reserve's calendar page."""
    from urllib.request import Request, urlopen
    try:
        with urlopen(Request("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", headers={"User-Agent": "chainstox-research"}), timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {"date": None, "error": f"{type(exc).__name__}: {exc}"}
    return parse_fomc(html, today)


def parse_fomc(html: str, today: dt.date) -> dict[str, Any]:
    months = {name: index for index, name in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
    headings = [(match.start(), int(match.group(1))) for match in re.finditer(r"(\d{4}) FOMC Meetings", html)]
    dates = []
    for position, (start, year) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(html)
        for month, days in re.findall(r"fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<", html[start:end], re.S):
            month = month.split("/")[-1].strip()
            last_day = re.findall(r"\d+", days)
            if month in months and last_day:
                try:
                    dates.append(dt.date(year, months[month], int(last_day[-1])))
                except ValueError:
                    continue
    upcoming = sorted(day for day in dates if day >= today)
    return {"date": upcoming[0].isoformat() if upcoming else None, "source": "federalreserve.gov FOMC calendar", "error": None if upcoming else "No upcoming meeting parsed."}


def home_currency_view(home: str) -> dict[str, Any]:
    """USD-asset returns seen from another currency (checklist 4.7)."""
    import Valuation_model as vm
    symbol = f"{home.upper()}=X"
    history = vm.fetch_history(symbol, "1y")
    change = vm.price_change(history, 63)
    if change is None:
        return {"currency": home.upper(), "error": f"{symbol} history unavailable"}
    return {"currency": home.upper(), "usd_per_home_3m_change": -change, "home_per_usd_3m_change": change,
            "note": f"Over three months the US dollar {'gained' if change > 0 else 'lost'} {abs(change):.1%} against {home.upper()}; a USD asset's return in {home.upper()} is roughly its USD return {'plus' if change > 0 else 'minus'} that."}


def build_card(ticker: str, environment: dict[str, Any], core: dict[str, Any], store: SignalStore, *, today: dt.date | None = None,
               home_currency: str | None = None, fomc: dict[str, Any] | None = None, record: bool = True) -> dict[str, Any]:
    import Valuation_model as vm
    from company_economics import build_company_economics, snapshot_from_valuation_data
    from intrinsic_valuation import build_valuation_report, collect_valuation_data

    ticker = ticker.upper()
    today = today or dt.date.today()
    errors: dict[str, str] = {}
    with contextlib.redirect_stdout(io.StringIO()):
        data = collect_valuation_data(ticker)
    report = None
    try:
        report = build_valuation_report(ticker, data=data)
    except Exception as exc:  # noqa: BLE001
        errors["valuation"] = f"{type(exc).__name__}: {exc}"
    economics = build_company_economics(snapshot_from_valuation_data(data), report).to_dict()["company_economics"]
    archetype = (economics.get("classification") or {}).get("primary_archetype") or "GENERIC_OPERATING_COMPANY"
    # Checklist 15.5: the latest quarterly report, read with fixed rules.
    try:
        import quarterly_read
        quarterly = quarterly_read.collect(ticker, is_bank=archetype == "BANK")
    except Exception as exc:  # noqa: BLE001
        quarterly = {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    info = data.get("info") or {}
    etf, mapping = sector_etf_for(ticker, info.get("sector"))
    company_vs_sector = None
    if etf:
        company_vs_sector = vm.relative_change_from_histories(vm.fetch_history(ticker, "1y"), vm.fetch_history(etf, "1y"), 63)
    with contextlib.redirect_stdout(io.StringIO()):
        heat = (vm.heat_rows([ticker]) or [None])[0]
    expectations = collect_expectations(ticker, today)
    # Checklist 10.1: what moved the price (macro / market / sector / company).
    from price_attribution import build_attribution, price_reading
    try:
        attribution = build_attribution(ticker, archetype, etf)
    except Exception as exc:  # noqa: BLE001
        attribution = {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    from sector_flow import latest_sector_flow
    sector_flow = latest_sector_flow(store, etf) if etf else None
    from relative_scales import relative_readings
    try:
        relative = relative_readings(ticker, [name for name in vm.SECTOR_CANDIDATES.get(etf or "", []) if name != ticker])
    except Exception as exc:  # noqa: BLE001
        relative, errors["relative_scales"] = None, f"{type(exc).__name__}: {exc}"
    erp_sensitivity = None
    rates = (report or {}).get("discount_rate") or {}
    if report and report.get("scenarios") and _num(rates.get("wacc")) and _num(rates.get("beta")) and _num(rates.get("equity_weight")):
        lower = rates["wacc"] - rates["beta"] * rates["equity_weight"] * 0.01
        try:
            alt = build_valuation_report(ticker, overrides={"wacc": lower}, data=data)
            erp_sensitivity = {"erp_change_pp": -1.0, "wacc": lower, "base_fair_value": _num(((alt.get("scenarios") or {}).get("base") or {}).get("fair_value_per_share"))}
        except Exception as exc:  # noqa: BLE001
            erp_sensitivity = {"error": f"{type(exc).__name__}: {exc}"}
    # Checklist 9.2: the twelve-month growth the valuation used, falling back to Yahoo's one-quarter figure.
    headline = (report or {}).get("fair_value") or {}
    observed_growth = _num(headline.get("observed_growth")) if _num(headline.get("observed_growth")) is not None else _num(info.get("revenueGrowth"))
    axes = {
        "macro": macro_axis(archetype, environment, etf),
        "flow": flow_axis(ticker, etf, mapping, store, company_vs_sector, sector_flow),
        "valuation": valuation_axis(report, observed_growth, expectations.get("revenue_growth_next_year"), _num((core.get("macro") or {}).get("erp")), erp_sensitivity,
                                    growth_band_from(expectations)),
        "crowding": crowding_axis(heat, sector_flow, relative),
        "expectations": expectations_axis(expectations),
        "fundamentals": fundamentals_axis(economics, relative, quarterly),
    }
    risk = environment.get("risk_regime") or {}
    tactical_env = f"Market regime (context only, not predictive): {risk.get('regime') or 'unavailable'}"
    from exposure_map import exposures_for
    exposed = {item["factor"] for item in exposures_for(archetype, sector_etf=etf)}
    card = {
        "schema_version": "1.0",
        "ticker": ticker,
        "name": data.get("company"),
        "archetype": archetype,
        "sector_etf": etf,
        "generated_on": today.isoformat(),
        "environment_as_of": environment.get("as_of"),
        "axes": axes,
        "horizons": {
            "tactical": {"window": "1-3 months", "context": tactical_env, "axes": ["flow", "crowding"]},
            "cyclical": {"window": "6-12 months", "axes": ["macro", "expectations", "fundamentals"]},
            "structural": {"window": "3-5 years", "axes": ["valuation"]},
        },
        "contradictions": contradictions(axes, environment, exposed),
        "changes": changes_since_last(ticker, axes, store, today.isoformat()),
        "falsification": falsification(economics),
        "next_catalysts": next_catalysts(expectations.get("next_earnings_date"), fomc, today),
        "families": {family: sorted(key for key, value in axes.items() if family in value["families"]) for family in FAMILIES},
        "attribution": attribution,
        "price_reading": price_reading(attribution, axes["expectations"]["state"],
                                       next((item for item in changes_since_last(ticker, axes, store, today.isoformat()) if item["axis"] == "fundamentals"), None)),
        "home_currency": home_currency_view(home_currency) if home_currency else None,
        "errors": errors,
        "disclaimer": "Research map, not a recommendation. Axes are shown separately and never combined into a score.",
    }
    save_attribution(ticker, {"date": today.isoformat(), "archetype": archetype, "sector_etf": etf, "archetype_source": "judgment card",
                              "attribution": attribution, "reading": card["price_reading"]})
    if record:
        card["recorded"] = record_verdict(ticker, axes, store, today.isoformat())
        reading = card["price_reading"]
        card["recorded"] += store.append([observation(f"attribution.{ticker}.3m", today.isoformat(), reading.get("company_z"), reading["kind"],
                                                      source="price_attribution", source_state="LIVE")])
    return card


def load_environment() -> tuple[dict[str, Any], dict[str, Any]]:
    import research_system
    with contextlib.redirect_stdout(io.StringIO()):
        system = research_system.build_research_system(refresh=False)
    return system["environment"], (system["modules"]["core_market"]["payload"] or {})


def render(card: dict[str, Any]) -> str:
    lines = [f"{card['ticker']} · {card['name']} · {card['archetype'].replace('_', ' ').title()} · sector {card['sector_etf'] or 'n/a'} · {card['generated_on']}"]
    for horizon, spec in card["horizons"].items():
        lines.append(f"\n{horizon.upper()} ({spec['window']})" + (f" — {spec['context']}" if spec.get("context") else ""))
        for key in spec["axes"]:
            item = card["axes"][key]
            lines.append(f"  {key:<12} {item['state']}  [{item['confidence'].lower()}{', ' + item['direction'] if item['direction'] else ''}]")
            for line in item["evidence"]:
                lines.append(f"               · {line}")
            if key == "valuation" and item["detail"].get("fixed_erp") is not None:
                detail = item["detail"]
                sensitivity = detail.get("erp_sensitivity") or {}
                alt = sensitivity.get("base_fair_value")
                lines.append(f"               · Discount rate: fixed ERP {detail['fixed_erp']:.1%} (model policy); market-implied ERP "
                             f"{'n/a' if detail.get('implied_erp') is None else format(detail['implied_erp'], '.1%')} (SPY earnings yield minus 10Y)"
                             f"{'' if alt is None else f'; base value with ERP 1pp lower: {alt:.2f}'}.")
            if item["missing"]:
                lines.append(f"               missing: {', '.join(item['missing'])}")
    if card["contradictions"]:
        lines.append("\nCONTRADICTIONS")
        lines.extend(f"  · {item}" for item in card["contradictions"])
    if card["changes"]:
        lines.append("\nCHANGED SINCE LAST RUN")
        lines.extend(f"  · {item['axis']}: {item['from']} → {item['to']} (since {item['since']})" for item in card["changes"])
    if card["falsification"]:
        lines.append("\nWHAT WOULD CHANGE THE VIEW")
        lines.extend(f"  · {item}" for item in card["falsification"])
    catalysts = card["next_catalysts"]
    earnings = catalysts["earnings"] or (f"not yet published (last reported {catalysts['last_earnings']})" if catalysts.get("last_earnings") else "unavailable")
    lines.append(f"\nNEXT CATALYSTS  earnings {earnings} · FOMC {catalysts['fomc'] or 'unavailable'}")
    if card.get("home_currency"):
        lines.append(f"HOME CURRENCY  {card['home_currency'].get('note') or card['home_currency'].get('error')}")
    lines.append(f"\n{card['disclaimer']}")
    return "\n".join(lines)


def run_watchlist(tickers: list[str], *, home_currency: str | None = None, as_json: bool = False) -> int:
    environment, core = load_environment()
    store = SignalStore()
    fomc = next_fomc(dt.date.today())
    cards = []
    for ticker in tickers:
        try:
            cards.append(build_card(ticker, environment, core, store, home_currency=home_currency, fomc=fomc))
        except Exception as exc:  # noqa: BLE001 - one company must not stop the list
            cards.append({"ticker": ticker.upper(), "error": f"{type(exc).__name__}: {exc}", "changes": []})
    cards.sort(key=lambda card: (-len(card.get("changes") or []), card["ticker"]))
    if as_json:
        print(json.dumps(cards, indent=2, default=str))
        return 0
    for card in cards:
        print("=" * 72)
        print(f"{card['ticker']}: {card['error']}" if card.get("error") else render(card))
    return 0


def watchlist_summary(store: SignalStore | None = None) -> list[dict[str, Any]]:
    """Last recorded card states per watchlist company, read from history only (no network)."""
    store = store or SignalStore()
    tickers = json.loads(WATCHLIST_PATH.read_text()).get("tickers", []) if WATCHLIST_PATH.exists() else []
    output, stretch = [], {}
    for ticker in tickers:
        axes, last_date, changed = {}, None, []
        for key in ("macro", "flow", "valuation", "crowding", "expectations", "fundamentals"):
            rows = [row for row in store.rows(f"verdict.{ticker}.{key}") if row["label"]]
            if not rows:
                continue
            axes[key] = rows[-1]["label"]
            if key == "valuation" and rows[-1].get("value") is not None:
                stretch[ticker] = rows[-1]["value"]
            last_date = max(last_date or rows[-1]["observation_date"], rows[-1]["observation_date"])
            if len(rows) >= 2 and rows[-2]["label"] != rows[-1]["label"]:
                changed.append({"axis": key, "from": rows[-2]["label"], "to": rows[-1]["label"], "on": rows[-1]["observation_date"],
                                "origin": change_origin(rows[-2].get("source"), rows[-1].get("source"))})
        output.append({"ticker": ticker, "last_card": last_date, "axes": axes, "changed": changed, "price_to_max_case": stretch.get(ticker)})
    output.sort(key=lambda item: (-len(item["changed"]), item["last_card"] is None, item["ticker"]))
    return output


EVENTS_CACHE = ROOT / ".cache" / "events"   # one file per day (checklist 18.14)


def _earnings_date(ticker: str) -> str | None:
    import yfinance as yf
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            calendar = yf.Ticker(ticker).calendar or {}
        dates = calendar.get("Earnings Date") or []
        return str(dates[0]) if dates else None
    except Exception:  # noqa: BLE001
        return None


def watchlist_events(today: dt.date | None = None) -> dict[str, Any]:
    """Scheduled events for the watchlist: each company's next earnings date and the next FOMC decision.
    Cached for the day; the list follows the current watchlist."""
    today = today or dt.date.today()
    tickers = json.loads(WATCHLIST_PATH.read_text()).get("tickers", []) if WATCHLIST_PATH.exists() else []
    path = EVENTS_CACHE / f"{today.isoformat()}.json"
    cached = {}
    try:
        cached = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        cached = {}
    earnings = dict(cached.get("earnings") or {})
    for ticker in tickers:
        if ticker not in earnings:
            earnings[ticker] = _earnings_date(ticker)
    fomc = cached.get("fomc") or next_fomc(today)
    payload = {"date": today.isoformat(), "earnings": earnings, "fomc": fomc}
    try:
        EVENTS_CACHE.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload))
        temporary.replace(path)
    except OSError:
        pass
    return {"date": today.isoformat(), "earnings": [{"ticker": ticker, "date": earnings.get(ticker)} for ticker in tickers],
            "fomc": fomc, "source": "Yahoo Finance earnings calendar; federalreserve.gov FOMC calendar"}


def save_attribution(ticker: str, payload: dict[str, Any]) -> None:
    try:
        ATTRIBUTION_CACHE.mkdir(parents=True, exist_ok=True)
        target = ATTRIBUTION_CACHE / f"{ticker.upper()}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, default=str))
        temporary.replace(target)
    except OSError:
        pass


def load_attribution(ticker: str) -> dict[str, Any] | None:
    try:
        return json.loads((ATTRIBUTION_CACHE / f"{ticker.upper()}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _stored_archetype(ticker: str) -> tuple[str | None, str | None]:
    """Archetype from the last judgment card, else from the stored company-economics profile."""
    cached = load_attribution(ticker)
    if cached and cached.get("archetype"):
        return cached["archetype"], cached.get("archetype_source") or "judgment card"
    try:
        profile = json.loads((ROOT / ".cache" / "company_economics" / f"{ticker.upper()}.json").read_text())
        return profile["company_economics"]["classification"]["primary_archetype"], "stored company profile"
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        pass
    try:   # last resort: classify from Yahoo's industry and description only
        import yfinance as yf
        from company_economics import BusinessModelClassifier, snapshot_from_resolved_security
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = yf.Ticker(ticker).info or {}
        archetype = BusinessModelClassifier().classify(snapshot_from_resolved_security({"info": info})).primary_archetype
        return getattr(archetype, "value", str(archetype)), "Yahoo industry"
    except Exception:  # noqa: BLE001
        return None, None


def watchlist_drivers(store: SignalStore | None = None, today: dt.date | None = None) -> list[dict[str, Any]]:
    """What moved each watchlist company's price (checklist 10.3). Reuses today's cached attribution;
    otherwise fetches prices (no valuation run, no card is recorded)."""
    from price_attribution import build_attribution, price_reading
    store = store or SignalStore()
    today = today or dt.date.today()
    tickers = json.loads(WATCHLIST_PATH.read_text()).get("tickers", []) if WATCHLIST_PATH.exists() else []
    output = []
    for ticker in tickers:
        cached = load_attribution(ticker)
        expectations = next((row["label"] for row in reversed(store.rows(f"verdict.{ticker}.expectations")) if row["label"]), None)
        fresh_format = (((cached or {}).get("attribution") or {}).get("windows") or {}).get("3M", {}).get("parts_basis") == "simple"
        if cached and cached.get("date") == today.isoformat() and cached.get("attribution") and fresh_format:
            payload = cached
        else:
            archetype, source = _stored_archetype(ticker)
            etf = (cached or {}).get("sector_etf") or sector_etf_for(ticker, None)[0]
            try:
                attribution = build_attribution(ticker, archetype or "GENERIC_OPERATING_COMPANY", etf) if archetype else \
                    {"status": "UNAVAILABLE", "reason": "No archetype on record yet; open the company card once."}
            except Exception as exc:  # noqa: BLE001
                attribution = {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
            payload = {"date": today.isoformat(), "archetype": archetype, "archetype_source": source, "sector_etf": etf, "attribution": attribution}
            if attribution.get("status") == "AVAILABLE":
                save_attribution(ticker, payload)
        payload["reading"] = price_reading(payload["attribution"], expectations)
        attribution = payload["attribution"] or {}
        output.append({"ticker": ticker, "archetype": payload.get("archetype"), "archetype_source": payload.get("archetype_source"),
                       "expectations": expectations, "reading": payload["reading"],
                       "attribution": {key: attribution.get(key) for key in ("status", "reason", "as_of", "fit", "factor_labels", "windows", "betas")}})
    return output


HOME_CURRENCIES = ("EUR", "GBP", "JPY", "CHF", "CNY", "HKD", "SGD", "AUD", "CAD", "KRW", "INR", "TWD")


def fx_moves(currencies: tuple[str, ...] = HOME_CURRENCIES) -> dict[str, Any]:
    """Three-month change in units of each home currency per US dollar (checklist 10.9).
    A USD asset's return in that currency is (1 + USD return) x (1 + change) - 1."""
    output = {}
    for currency in currencies:
        view = home_currency_view(currency)
        output[currency] = None if view.get("error") else view.get("home_per_usd_3m_change")
    return {"window": "3M", "home_per_usd_change": output, "as_of": dt.date.today().isoformat(), "source": "Yahoo Finance currency pairs (CUR=X)"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX company judgment card")
    parser.add_argument("tickers", nargs="*")
    parser.add_argument("--watchlist", action="store_true", help=f"Run every ticker in {WATCHLIST_PATH.relative_to(ROOT)}.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--home-currency", help="Show USD returns translated into this currency, e.g. SGD.")
    parser.add_argument("--summary", action="store_true", help="Print the last recorded card states for the watchlist as JSON (no network).")
    parser.add_argument("--drivers", action="store_true", help="Print what moved each watchlist price (macro / market / sector / company) as JSON.")
    parser.add_argument("--fx", action="store_true", help="Print three-month USD moves against common home currencies as JSON.")
    parser.add_argument("--events", action="store_true", help="Print the watchlist's next earnings dates and the next FOMC decision as JSON.")
    args = parser.parse_args(argv)
    if args.fx:
        print(json.dumps(fx_moves()))
        return 0
    if args.drivers:
        print(json.dumps(watchlist_drivers(), default=str))
        return 0
    if args.events:
        print(json.dumps(watchlist_events(), default=str))
        return 0
    if args.summary:
        print(json.dumps(watchlist_summary(), indent=2))
        return 0
    tickers = [item.upper() for item in args.tickers]
    if args.watchlist:
        tickers += json.loads(WATCHLIST_PATH.read_text()).get("tickers", [])
    if not tickers:
        parser.error("give at least one ticker or --watchlist")
    return run_watchlist(list(dict.fromkeys(tickers)), home_currency=args.home_currency, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
