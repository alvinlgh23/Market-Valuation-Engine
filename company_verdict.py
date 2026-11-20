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
def macro_axis(archetype: str, environment: dict[str, Any]) -> dict[str, Any]:
    from exposure_map import LIQUIDITY_SENSITIVE, exposures_for
    from company_economics_registry import Archetype

    factors = environment.get("factors") or {}
    rows, tail, head, missing = [], 0, 0, []
    for exposure in exposures_for(archetype):
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
        weight = "confirmed" if exposure["validation"] == "CONFIRMED" else "unconfirmed"
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
    if switch:
        evidence.insert(0, switch)
    return axis(state, confidence=confidence, evidence=evidence, missing=missing, families=["macro_data", "price"],
                detail={"exposures": rows, "confirmed_tailwinds": tail, "confirmed_headwinds": head, "carry_switch": switch})


def flow_axis(ticker: str, etf: str | None, mapping_note: str, store: SignalStore, company_vs_sector_3m: float | None) -> dict[str, Any]:
    if not etf:
        return axis("No sector mapping", missing=["sector ETF for this company"], families=["price"])
    signal = f"sector.{etf}.rel_3m"
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
    evidence = [f"{etf} 3M relative strength vs SPY {_pct(latest)} on {latest_day}, {percentile:.0%} percentile of its stored history; same bucket {held} of last 10 observations."]
    if company_vs_sector_3m is not None:
        evidence.append(f"{ticker} {'leads' if company_vs_sector_3m > 0 else 'lags'} {etf} by {_size(company_vs_sector_3m)} over three months.")
    return axis(state, direction=direction, confidence="MODERATE" if held >= 8 else "LOW", evidence=evidence, families=["price"],
                missing=["sector breadth", "ETF share creation/redemption", "dollar volume"],
                detail={"sector_etf": etf, "mapping": mapping_note, "rel_3m": latest, "percentile": percentile, "persistence_of_10": held,
                        "company_vs_sector_3m": company_vs_sector_3m, "rel_3m_21_obs_ago": prior})


def valuation_axis(report: dict[str, Any] | None, observed_growth: float | None, consensus_growth: float | None,
                   implied_erp: float | None, erp_sensitivity: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return axis("Valuation unavailable", missing=["valuation report"], families=["valuation"])
    price = _num((report.get("company") or {}).get("current_market_price"))
    reverse = report.get("reverse_dcf") or {}
    scenarios = report.get("scenarios") or {}
    fair = {name: _num((scenarios.get(name) or {}).get("fair_value_per_share")) for name in ("bear", "base", "bull")}
    rates = report.get("discount_rate") or {}
    notes = ["Five-year explicit forecast with a capped first-year growth rate and 2.5% terminal growth; for fast growers this structure understates value (checklist 7.6)."]
    detail = {"price": price, "fair_value": fair, "reverse_dcf_status": reverse.get("status"), "observed_growth": observed_growth,
              "consensus_next_year_growth": consensus_growth, "fixed_erp": _num(rates.get("equity_risk_premium")), "implied_erp": implied_erp,
              "erp_sensitivity": erp_sensitivity, "wacc": _num(rates.get("wacc")), "notes": notes}
    status = reverse.get("status")
    evidence: list[str] = []
    if reverse.get("converged"):
        implied = _num(reverse.get("required_5y_revenue_cagr"))
        detail["implied_5y_revenue_cagr"] = implied
        reference = consensus_growth if consensus_growth is not None else observed_growth
        if implied is None or reference is None:
            state = "Priced growth known; no comparison growth"
        elif implied > reference + 0.05:
            state = "Price implies more growth than observed/consensus"
        elif implied < reference - 0.05:
            state = "Price implies less growth than observed/consensus"
        else:
            state = "Price roughly matches observed/consensus growth"
        evidence.append(f"Price {price} implies {_pct(implied)} five-year revenue CAGR; observed {_pct(observed_growth)}, consensus next year {_pct(consensus_growth)}.")
        confidence = "MODERATE"
    elif status == "NO_ECONOMIC_SOLUTION":
        high, low = _num(reverse.get("high_case_value")), _num(reverse.get("low_case_value"))
        if high is not None and price is not None and high < price:
            state = "Price implies growth above what the model can reach"
            evidence.append(f"Even 50% first-year growth values the share at {high:.2f} vs price {price:.2f}; consensus next-year growth {_pct(consensus_growth)}.")
        elif low is not None and price is not None and low > price:
            state = "Price implies contraction beyond the model's floor"
            evidence.append(f"Even -20% first-year growth values the share at {low:.2f} vs price {price:.2f}.")
        else:
            state = "Reverse DCF has no solution"
        confidence = "LOW"
    else:
        reason = (report.get("data_quality") or {}).get("reason") or reverse.get("reason") or (report.get("final_interpretation") or {}).get("text")
        return axis("Fair value withheld", missing=[reason or "valuation inputs"], families=["valuation"], detail=detail)
    if all(value is not None for value in fair.values()) and price is not None:
        evidence.append(f"Model range {fair['bear']:.2f} / {fair['base']:.2f} / {fair['bull']:.2f} (bear/base/bull) against price {price:.2f}; secondary to the priced-growth read.")
    return axis(state, confidence=confidence, evidence=evidence, families=["valuation", "fundamentals"], detail=detail,
                missing=["valuation multiple history (percentile in own history)"])


def crowding_axis(heat: dict[str, Any] | None) -> dict[str, Any]:
    if not heat:
        return axis("Crowding unavailable", missing=["price and valuation heat"], families=["price"])
    import Valuation_model as vm
    label = vm.chase_risk_label(heat)
    evidence = [f"Heat {heat.get('heat'):.0f}/100 (valuation {heat.get('valuation_heat'):.0f}, momentum {heat.get('momentum_heat'):.0f}); "
                f"{_pct(heat.get('dist_200'))} from the 200-day average; RSI {heat.get('rsi'):.0f}." if heat.get('rsi') is not None else
                f"Heat {heat.get('heat'):.0f}/100."]
    return axis(label, confidence="LOW", evidence=evidence, families=["price", "valuation"],
                missing=["positioning data (short interest, options, fund ownership)"],
                detail={key: heat.get(key) for key in ("heat", "valuation_heat", "momentum_heat", "rsi", "dist_50", "dist_200", "six_month", "forward_pe", "ev_sales")})


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
    evidence = [f"Next-year EPS estimate {_pct(change)} over 90 days; last 30 days {up} up / {down} down revisions."]
    if expectations.get("revenue_growth_next_year") is not None:
        evidence.append(f"Consensus revenue growth next fiscal year {_pct(expectations['revenue_growth_next_year'])} ({expectations.get('analysts_next_year')} analysts).")
    return axis(state, direction=None if change is None else "up" if change > 0 else "down", confidence="MODERATE" if change is not None else "LOW",
                evidence=evidence, families=["fundamentals"], detail=expectations)


def fundamentals_axis(economics: dict[str, Any] | None) -> dict[str, Any]:
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
    return axis(state, confidence="MODERATE" if unknown == 0 else "LOW", evidence=evidence, families=["fundamentals"],
                missing=[f"{key.replace('_', ' ')}" for key, value in states.items() if value in (None, "INSUFFICIENT_EVIDENCE")],
                detail={"financial_translation": states, "current_revenue_growth": growth, "archetype": (economics.get("classification") or {}).get("primary_archetype")})


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


def changes_since_last(ticker: str, axes: dict[str, dict[str, Any]], store: SignalStore, today: str) -> list[dict[str, str]]:
    output = []
    for key, value in axes.items():
        prior = [row for row in store.rows(f"verdict.{ticker}.{key}") if row["observation_date"] < today and row["label"]]
        if prior and prior[-1]["label"] != value["state"]:
            output.append({"axis": key, "from": prior[-1]["label"], "to": value["state"], "since": prior[-1]["observation_date"]})
    return output


def record_verdict(ticker: str, axes: dict[str, dict[str, Any]], store: SignalStore, today: str) -> int:
    return store.append([observation(f"verdict.{ticker}.{key}", today, label=value["state"], source="company_verdict", source_state="LIVE") for key, value in axes.items()])


# ---- data collection (network) ---------------------------------------------------------------
def collect_expectations(ticker: str) -> dict[str, Any]:
    import yfinance as yf
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            handle = yf.Ticker(ticker)
            trend, revisions, revenue, calendar = handle.eps_trend, handle.eps_revisions, handle.revenue_estimate, handle.calendar
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    def row(frame, period):
        try:
            return {key: (value.item() if hasattr(value, "item") else value) for key, value in frame.loc[period].to_dict().items()}
        except Exception:  # noqa: BLE001
            return {}
    next_year_revenue = row(revenue, "+1y")
    rev = row(revisions, "+1y")
    earnings_dates = (calendar or {}).get("Earnings Date") or []
    return {
        "eps_trend_next_year": row(trend, "+1y"),
        "revisions_up_30d": rev.get("upLast30days"), "revisions_down_30d": rev.get("downLast30days"),
        "revenue_growth_next_year": _num(next_year_revenue.get("growth")), "analysts_next_year": next_year_revenue.get("numberOfAnalysts"),
        "next_earnings_date": str(earnings_dates[0]) if earnings_dates else None,
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
    info = data.get("info") or {}
    etf, mapping = sector_etf_for(ticker, info.get("sector"))
    company_vs_sector = None
    if etf:
        company_vs_sector = vm.relative_change_from_histories(vm.fetch_history(ticker, "1y"), vm.fetch_history(etf, "1y"), 63)
    with contextlib.redirect_stdout(io.StringIO()):
        heat = (vm.heat_rows([ticker]) or [None])[0]
    expectations = collect_expectations(ticker)
    erp_sensitivity = None
    rates = (report or {}).get("discount_rate") or {}
    if report and report.get("scenarios") and _num(rates.get("wacc")) and _num(rates.get("beta")) and _num(rates.get("equity_weight")):
        lower = rates["wacc"] - rates["beta"] * rates["equity_weight"] * 0.01
        try:
            alt = build_valuation_report(ticker, overrides={"wacc": lower}, data=data)
            erp_sensitivity = {"erp_change_pp": -1.0, "wacc": lower, "base_fair_value": _num(((alt.get("scenarios") or {}).get("base") or {}).get("fair_value_per_share"))}
        except Exception as exc:  # noqa: BLE001
            erp_sensitivity = {"error": f"{type(exc).__name__}: {exc}"}
    observed_growth = _num(info.get("revenueGrowth"))
    axes = {
        "macro": macro_axis(archetype, environment),
        "flow": flow_axis(ticker, etf, mapping, store, company_vs_sector),
        "valuation": valuation_axis(report, observed_growth, expectations.get("revenue_growth_next_year"), _num((core.get("macro") or {}).get("erp")), erp_sensitivity),
        "crowding": crowding_axis(heat),
        "expectations": expectations_axis(expectations),
        "fundamentals": fundamentals_axis(economics),
    }
    risk = environment.get("risk_regime") or {}
    tactical_env = f"Risk regime: {risk.get('regime') or 'unavailable'}"
    from exposure_map import exposures_for
    exposed = {item["factor"] for item in exposures_for(archetype)}
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
        "home_currency": home_currency_view(home_currency) if home_currency else None,
        "errors": errors,
        "disclaimer": "Research map, not a recommendation. Axes are shown separately and never combined into a score.",
    }
    if record:
        card["recorded"] = record_verdict(ticker, axes, store, today.isoformat())
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX company judgment card")
    parser.add_argument("tickers", nargs="*")
    parser.add_argument("--watchlist", action="store_true", help=f"Run every ticker in {WATCHLIST_PATH.relative_to(ROOT)}.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--home-currency", help="Show USD returns translated into this currency, e.g. SGD.")
    args = parser.parse_args(argv)
    tickers = [item.upper() for item in args.tickers]
    if args.watchlist:
        tickers += json.loads(WATCHLIST_PATH.read_text()).get("tickers", [])
    if not tickers:
        parser.error("give at least one ticker or --watchlist")
    return run_watchlist(list(dict.fromkeys(tickers)), home_currency=args.home_currency, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
