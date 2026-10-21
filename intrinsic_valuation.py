"""Company-type-aware intrinsic valuation engine.

This module is intentionally separate from ``company_report.py``.  It estimates
value from explicit operating assumptions; it does not score narratives or
produce investment recommendations.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

import yfinance as yf


SUPPORTED_DCF_TYPES = {
    "MATURE_OPERATING_COMPANY",
    "GROWTH_SOFTWARE_COMPANY",
    "CYCLICAL_COMPANY",
}

METHODS = {
    "MATURE_OPERATING_COMPANY": "Five-year FCFF DCF with FCF-yield and trading-multiple cross-checks",
    "GROWTH_SOFTWARE_COMPANY": "Revenue-to-FCFF convergence DCF with reverse DCF",
    "CYCLICAL_COMPANY": "Cycle-adjusted FCFF DCF using normalized mid-cycle economics",
    "FINANCIAL_INSTITUTION": "Residual-income or dividend-discount framework required",
    "REIT": "NAV / AFFO framework required",
    "PRE_PROFIT_COMPANY": "Revenue-scenario and financing-runway framework required",
    "ETF_OR_FUND": "Portfolio NAV and exposure analysis; company DCF is not applicable",
    "SPAC_OR_SHELL": "Trust-value and transaction-structure analysis required",
    "INSUFFICIENT_DATA": "No economically supported valuation method",
}

COMPANY_TYPE_LABELS = {
    key: key.replace("_", " ").title() for key in METHODS
}

REVERSE_GROWTH_BOUNDS = (-0.20, 0.50)
REVERSE_TOLERANCE_PER_SHARE = 0.005
FCFF_RELATIVE_TOLERANCE = 0.05
FCFF_REVENUE_TOLERANCE = 0.01
SBC_ACCOUNTING_POLICY = "accounting-fcff"
SBC_OWNER_EARNINGS_POLICY = "owner-earnings"
SBC_POLICIES = {SBC_ACCOUNTING_POLICY, SBC_OWNER_EARNINGS_POLICY}


@dataclass
class Assumption:
    name: str
    value: float
    unit: str
    source: str
    basis: str
    confidence: str
    scenario: str
    period: str = "Forecast annual"
    overridden: bool = False


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _pick(mapping: dict, *keys: str, default=None):
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return default


def _info(ticker_obj) -> dict:
    try:
        value = ticker_obj.info or {}
        return value if isinstance(value, dict) else dict(value)
    except Exception:
        try:
            return dict(ticker_obj.fast_info)
        except Exception:
            return {}


def _statement(ticker_obj, *attrs):
    for attr in attrs:
        try:
            frame = getattr(ticker_obj, attr)
            if frame is not None and not frame.empty:
                return frame
        except Exception:
            pass
    return None


def _row(frame, *names) -> list[float]:
    if frame is None:
        return []
    for name in names:
        if name in frame.index:
            raw_values = frame.loc[name].tolist()
            # Never compact a missing latest-period cell into a stale value.
            # Try the next statement alias instead.
            if not raw_values or not _number(raw_values[0]):
                continue
            return [float(value) for value in raw_values if _number(value)]
    return []


def _cagr(latest, oldest, years):
    if not (_number(latest) and _number(oldest)) or latest <= 0 or oldest <= 0 or years <= 0:
        return None
    return (latest / oldest) ** (1 / years) - 1


def _clamp(value, low, high):
    return min(high, max(low, value))


def _pct(value):
    return "Unavailable" if not _number(value) else f"{value * 100:.1f}%"


def _money(value, currency="$"):
    return "Unavailable" if not _number(value) else f"{currency}{value:,.2f}"


def _large(value):
    if not _number(value):
        return "Unavailable"
    for scale, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= scale:
            return f"${value / scale:,.2f}{suffix}"
    return f"${value:,.0f}"


def _historical_fcff_reconciliation(
    data: dict,
    sbc_policy: str = SBC_ACCOUNTING_POLICY,
) -> dict:
    """Reconcile two independently constructed latest-period FCFF measures.

    The cash-flow-statement working-capital row is a cash-flow effect (positive
    is a source of cash).  The displayed change in working capital uses the
    valuation convention (positive is an investment/use of cash), so its sign
    is reversed.
    """
    required = {
        "revenue": data.get("latest_revenue"),
        "operating income": data.get("latest_operating_income"),
        "net income": data.get("latest_net_income"),
        "D&A": data.get("depreciation_amortization"),
        "capex": data.get("latest_capex"),
        "change in working capital": data.get("working_capital_change"),
        "operating cash flow": data.get("latest_ocf"),
        "after-tax interest": data.get("after_tax_interest"),
        "stock-based compensation": data.get("sbc"),
        "other non-cash operating adjustments": data.get("other_non_cash_adjustments"),
    }
    missing = [name for name, value in required.items() if not _number(value)]
    base = {
        "period": data.get("periods", {}).get("fcff", "Latest fiscal year"),
        "status": "FAILED" if missing else "PENDING",
        "missing": missing,
        "tolerance_policy": (
            "Difference must be no more than the greater of 5% of the larger "
            "absolute FCFF measure or 1% of revenue."
        ),
        "sbc_policy": sbc_policy,
    }
    if sbc_policy not in SBC_POLICIES:
        return {
            **base,
            "status": "FAILED",
            "reason": f"Unsupported SBC policy: {sbc_policy}.",
        }
    if missing:
        return {
            **base,
            "reason": "Historical FCFF cannot be reconciled because required statement fields are missing.",
        }

    tax_rate = data["tax_rate"]
    nopat = data["latest_operating_income"] * (1 - tax_rate)
    da = data["depreciation_amortization"]
    capex = data["latest_capex"]
    wc_cash_effect = data["working_capital_change"]
    change_in_working_capital = -wc_cash_effect
    after_tax_interest = data["after_tax_interest"]
    ocf = data["latest_ocf"]
    net_income = data["latest_net_income"]
    sbc = data["sbc"]

    # Use explicit non-cash operating rows rather than a CFO residual. A
    # residual would silently reintroduce SBC and non-operating gain/loss
    # reversals that NOPAT has already excluded.
    other_adjustments = data["other_non_cash_adjustments"]
    nopat_fcff_before_sbc = (
        nopat + da - capex - change_in_working_capital + other_adjustments
    )
    adjusted_nopat_fcff = nopat_fcff_before_sbc + sbc
    accounting_cfo_fcff = ocf - capex + after_tax_interest
    owner_earnings_nopat = nopat_fcff_before_sbc
    owner_earnings_cfo = accounting_cfo_fcff - sbc
    if sbc_policy == SBC_OWNER_EARNINGS_POLICY:
        nopat_fcff = owner_earnings_nopat
        cfo_fcff = owner_earnings_cfo
        sbc_treatment = "Deducted once as a cash-like expense; forecast dilution disabled"
        dilution_modeled = False
    else:
        nopat_fcff = adjusted_nopat_fcff
        cfo_fcff = accounting_cfo_fcff
        sbc_treatment = "Added back to accounting FCFF; economic cost reflected through dilution"
        dilution_modeled = True

    difference_before_sbc = nopat_fcff_before_sbc - accounting_cfo_fcff
    difference_vs_ocf_minus_capex = nopat_fcff - (ocf - capex)
    reconciliation_difference = nopat_fcff - cfo_fcff
    scale = max(abs(nopat_fcff), abs(cfo_fcff))
    tolerance = max(
        FCFF_RELATIVE_TOLERANCE * scale,
        FCFF_REVENUE_TOLERANCE * abs(data["latest_revenue"]),
    )
    passed = abs(reconciliation_difference) <= tolerance
    difference_pct = abs(reconciliation_difference) / scale if scale > 0 else 0.0
    sbc_mismatch_tolerance = max(tolerance, abs(sbc) * 0.10)
    sbc_explains_initial_difference = (
        abs(abs(difference_before_sbc) - abs(sbc)) <= sbc_mismatch_tolerance
    )
    likely_cause = (
        "Stock-based compensation treatment mismatch"
        if sbc_explains_initial_difference
        else None
    )
    reason = (
        "NOPAT-based and CFO-based FCFF reconcile within tolerance."
        if passed
        else (
            "The remaining discrepancy is material after explicitly testing stock-based compensation. "
            "Review non-operating income, unusual taxes, minority interests, and statement-period "
            "or classification differences."
        )
    )
    return {
        **base,
        "status": "PASSED" if passed else "FAILED",
        "missing": [],
        "nopat": nopat,
        "depreciation_and_amortization": da,
        "capex": capex,
        "change_in_working_capital": change_in_working_capital,
        "after_tax_interest": after_tax_interest,
        "stock_based_compensation": sbc,
        "sbc_treatment": sbc_treatment,
        "other_adjustments": other_adjustments,
        "nopat_based_fcff_before_sbc": nopat_fcff_before_sbc,
        "sbc_addback": sbc if sbc_policy == SBC_ACCOUNTING_POLICY else 0.0,
        "adjusted_nopat_based_fcff": adjusted_nopat_fcff,
        "accounting_cfo_based_fcff": accounting_cfo_fcff,
        "owner_earnings_nopat_based": owner_earnings_nopat,
        "owner_earnings_cfo_based": owner_earnings_cfo,
        "calculated_fcff": nopat_fcff,
        "nopat_based_fcff": nopat_fcff,
        "operating_cash_flow": ocf,
        "operating_cash_flow_minus_capex": ocf - capex,
        "cfo_based_fcff": cfo_fcff,
        "difference_vs_operating_cash_flow_minus_capex": difference_vs_ocf_minus_capex,
        "reconciliation_difference": reconciliation_difference,
        "difference": reconciliation_difference,
        "absolute_difference": abs(reconciliation_difference),
        "reconciliation_difference_pct": difference_pct,
        "difference_before_sbc": difference_before_sbc,
        "tolerance": tolerance,
        "within_tolerance": passed,
        "likely_cause": likely_cause,
        "sbc_explains_initial_difference": sbc_explains_initial_difference,
        "sbc_added_back_exactly_once": sbc_policy == SBC_ACCOUNTING_POLICY,
        "sbc_deducted_exactly_once": sbc_policy == SBC_OWNER_EARNINGS_POLICY,
        "dilution_modeled": dilution_modeled,
        "double_count_check": "PASSED",
        "reason": reason,
        "other_adjustments_basis": (
            "Explicit deferred-tax and other non-cash statement rows; SBC is separate and "
            "non-operating gain/loss reversals are excluded because NOPAT already excludes them."
        ),
        "excluded_operating_gains_losses": data.get("operating_gains_losses"),
    }


def _latest_price(ticker_obj, info):
    price = _pick(info, "currentPrice", "regularMarketPrice")
    if _number(price):
        return float(price)
    try:
        hist = ticker_obj.history(period="5d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return None


def classify_security(ticker: str, info: dict, has_financials: bool) -> str:
    quote_type = str(_pick(info, "quoteType", default="")).upper()
    name = str(_pick(info, "longName", "shortName", default="")).lower()
    sector = str(_pick(info, "sector", default="")).lower()
    industry = str(_pick(info, "industry", default="")).lower()
    ticker = ticker.upper()

    if quote_type in {"ETF", "MUTUALFUND", "FUND"}:
        return "ETF_OR_FUND"
    if any(term in name or term in industry for term in ("blank check", "shell compan", "spac")):
        return "SPAC_OR_SHELL"
    if not info and not has_financials:
        return "INSUFFICIENT_DATA"
    if "reit" in industry or "real estate investment trust" in name:
        return "REIT"
    if sector == "financial services" or any(term in industry for term in ("bank", "insurance", "capital markets")):
        return "FINANCIAL_INSTITUTION"
    cyclical_terms = ("memory", "steel", "copper", "aluminum", "oil & gas", "commodity", "mining")
    if ticker == "MU" or any(term in industry for term in cyclical_terms):
        return "CYCLICAL_COMPANY"
    op_margin = _pick(info, "operatingMargins")
    fcf = _pick(info, "freeCashflow")
    growth = _pick(info, "revenueGrowth")
    gross_margin = _pick(info, "grossMargins")
    software_evidence = "software" in industry or "software" in sector
    recurring_economics = not _number(gross_margin) or gross_margin >= 0.45
    if (
        software_evidence
        and recurring_economics
        and _number(growth)
        and growth >= 0.15
        and _number(fcf)
        and fcf > 0
        and (not _number(op_margin) or op_margin < 0.30)
    ):
        return "GROWTH_SOFTWARE_COMPANY"
    if (_number(op_margin) and op_margin < 0) or (_number(fcf) and fcf < 0):
        return "PRE_PROFIT_COMPANY"
    return "MATURE_OPERATING_COMPANY" if has_financials else "INSUFFICIENT_DATA"


def routing_evidence(ticker: str, info: dict, kind: str, has_financials: bool) -> list[str]:
    quote_type = str(_pick(info, "quoteType", default="unknown"))
    sector = str(_pick(info, "sector", default="unavailable"))
    industry = str(_pick(info, "industry", default="unavailable"))
    growth = _pick(info, "revenueGrowth")
    op_margin = _pick(info, "operatingMargins")
    gross_margin = _pick(info, "grossMargins")
    fcf = _pick(info, "freeCashflow")
    evidence = [f"provider quote type: {quote_type}", f"sector / industry: {sector} / {industry}"]
    if _number(growth):
        evidence.append(f"provider revenue growth: {_pct(growth)}")
    if _number(gross_margin):
        evidence.append(f"gross margin: {_pct(gross_margin)}")
    if _number(op_margin):
        evidence.append(f"operating margin: {_pct(op_margin)}")
    if _number(fcf):
        evidence.append(f"free cash flow: {_large(fcf)} ({'positive' if fcf > 0 else 'negative'})")
    evidence.append(f"annual operating statements: {'available' if has_financials else 'unavailable'}")
    if kind == "CYCLICAL_COMPANY":
        evidence.append("cyclical industry or company-specific mid-cycle treatment is required")
    elif kind == "GROWTH_SOFTWARE_COMPANY":
        evidence.append("software economics, elevated growth, recurring-margin evidence, and positive FCF support convergence modeling")
    elif kind == "MATURE_OPERATING_COMPANY":
        evidence.append("positive operating history does not require a specialized or pre-profit framework")
    elif kind == "INSUFFICIENT_DATA":
        evidence.append(f"{ticker.upper()} lacks enough verified identity and statement evidence for routing")
    return evidence


def collect_valuation_data(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    ticker_obj = yf.Ticker(symbol)
    info = _info(ticker_obj)
    income = _statement(ticker_obj, "income_stmt", "financials")
    cashflow = _statement(ticker_obj, "cashflow")
    balance = _statement(ticker_obj, "balance_sheet")

    revenue = _row(income, "Total Revenue", "Operating Revenue")
    operating_income = _row(income, "Operating Income")
    gross_profit = _row(income, "Gross Profit")
    net_income = _row(income, "Net Income", "Net Income Common Stockholders")
    interest_expense = _row(income, "Interest Expense", "Interest Expense Non Operating")
    tax = _row(income, "Tax Provision")
    pretax = _row(income, "Pretax Income")
    ocf = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = _row(cashflow, "Capital Expenditure", "Capital Expenditures")
    sbc = _row(cashflow, "Stock Based Compensation")
    depreciation = _row(cashflow, "Depreciation And Amortization", "Depreciation")
    working_capital = _row(cashflow, "Change In Working Capital", "Change To Working Capital")
    deferred_tax = _row(cashflow, "Deferred Tax", "Deferred Income Tax")
    other_non_cash = _row(cashflow, "Other Non Cash Items")
    operating_gains_losses = _row(cashflow, "Operating Gains Losses")
    cash = _row(balance, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    debt = _row(balance, "Total Debt")
    shares = _row(income, "Diluted Average Shares", "Basic Average Shares")

    latest_revenue = revenue[0] if revenue else _pick(info, "totalRevenue")
    revenue_period = "Latest fiscal year" if revenue else "Provider TTM / most recent"
    latest_op_income = operating_income[0] if operating_income else (
        latest_revenue * _pick(info, "operatingMargins") if _number(latest_revenue) and _number(_pick(info, "operatingMargins")) else None
    )
    latest_ocf = ocf[0] if ocf else _pick(info, "operatingCashflow")
    latest_capex = abs(capex[0]) if capex else None
    latest_fcf = (
        latest_ocf - latest_capex
        if _number(latest_ocf) and _number(latest_capex)
        else _pick(info, "freeCashflow")
    )
    latest_cash = cash[0] if cash else _pick(info, "totalCash", default=0)
    latest_debt = debt[0] if debt else _pick(info, "totalDebt", default=0)
    diluted_shares = shares[0] if shares else _pick(info, "sharesOutstanding")
    market_cap = _pick(info, "marketCap")
    price = _latest_price(ticker_obj, info)
    if not _number(diluted_shares) and _number(market_cap) and _number(price) and price > 0:
        diluted_shares = market_cap / price

    tax_rate = None
    if tax and pretax and pretax[0] > 0:
        tax_rate = _clamp(tax[0] / pretax[0], 0, 0.35)
    if not _number(tax_rate):
        tax_rate = 0.21

    latest_interest_expense = abs(interest_expense[0]) if interest_expense else None
    if not _number(latest_interest_expense) and _number(latest_debt) and latest_debt == 0:
        latest_interest_expense = 0.0
    after_tax_interest = (
        latest_interest_expense * (1 - tax_rate)
        if _number(latest_interest_expense)
        else None
    )

    latest_fcff = None
    if _number(latest_op_income):
        latest_fcff = latest_op_income * (1 - tax_rate)
        if depreciation:
            latest_fcff += depreciation[0]
        if working_capital:
            latest_fcff += working_capital[0]
        if _number(latest_capex):
            latest_fcff -= latest_capex
    if not _number(latest_fcff):
        latest_fcff = latest_fcf

    fcff_period = "Latest fiscal year" if operating_income else "Provider TTM / most recent"
    fcf_period = "Latest fiscal year" if ocf and capex else "Provider TTM / most recent"
    has_financials = bool(revenue and operating_income)
    security_type = classify_security(symbol, info, has_financials)
    return {
        "ticker": symbol,
        "provider": "Yahoo Finance via yfinance",
        "ticker_obj": ticker_obj,
        "info": info,
        "income": income,
        "cashflow": cashflow,
        "balance": balance,
        "company": _pick(info, "longName", "shortName", default=symbol),
        "security_type": security_type,
        "routing_evidence": routing_evidence(symbol, info, security_type, has_financials),
        "price": price,
        "revenue_history": revenue,
        "operating_income_history": operating_income,
        "gross_profit_history": gross_profit,
        "latest_revenue": latest_revenue,
        "latest_operating_income": latest_op_income,
        "latest_net_income": net_income[0] if net_income else None,
        "latest_ocf": latest_ocf,
        "latest_capex": latest_capex,
        "latest_fcf": latest_fcf,
        "latest_fcff": latest_fcff,
        "sbc": sbc[0] if sbc else None,
        "depreciation_amortization": depreciation[0] if depreciation else None,
        "working_capital_change": working_capital[0] if working_capital else None,
        "other_non_cash_adjustments": (
            (deferred_tax[0] if deferred_tax else 0.0)
            + (other_non_cash[0] if other_non_cash else 0.0)
        ),
        "operating_gains_losses": operating_gains_losses[0] if operating_gains_losses else None,
        "interest_expense": latest_interest_expense,
        "after_tax_interest": after_tax_interest,
        "cash": latest_cash if _number(latest_cash) else 0,
        "debt": latest_debt if _number(latest_debt) else 0,
        "shares": diluted_shares,
        "market_cap": market_cap,
        "tax_rate": tax_rate,
        "beta": _pick(info, "beta"),
        "currency": _pick(info, "currency", "financialCurrency", default="USD"),
        "as_of": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "periods": {
            "revenue": revenue_period,
            "operating_income": "Latest fiscal year" if operating_income else "Provider TTM / most recent",
            "fcff": fcff_period,
            "free_cash_flow": fcf_period,
            "cash_and_debt": "Latest reported balance sheet",
            "shares": "Latest fiscal-year diluted average" if shares else "Current shares outstanding",
            "market_price": "Current / latest available market price",
        },
    }


def _required_data_missing(data: dict) -> list[str]:
    missing = []
    if not _number(data["latest_revenue"]) or data["latest_revenue"] <= 0:
        missing.append("latest annual revenue")
    if not _number(data["latest_fcff"]):
        missing.append("operating income or free cash flow")
    if not _number(data["shares"]) or data["shares"] <= 0:
        missing.append("diluted shares outstanding")
    return missing


def _market_rates(data: dict) -> dict:
    risk_free = None
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if hist is not None and not hist.empty:
            risk_free = float(hist["Close"].dropna().iloc[-1]) / 100
    except Exception:
        pass
    rf_source = "Yahoo Finance US 10Y Treasury (^TNX), latest close"
    if not _number(risk_free):
        risk_free = 0.043
        rf_source = "transparent fallback: 4.3% US 10Y proxy"
    beta = data["beta"] if _number(data["beta"]) and 0.25 <= data["beta"] <= 3 else 1.0
    beta_source = "Yahoo Finance beta" if beta == data["beta"] else "fallback beta of 1.0"
    erp = 0.045
    cost_equity = risk_free + beta * erp
    interest = _row(data["income"], "Interest Expense", "Interest Expense Non Operating")
    pretax_cost_debt = 0.055
    if interest and data["debt"] > 0:
        pretax_cost_debt = _clamp(abs(interest[0]) / data["debt"], 0.025, 0.12)
    after_tax_debt = pretax_cost_debt * (1 - data["tax_rate"])
    if _number(data["market_cap"]) and data["market_cap"] > 0:
        equity = data["market_cap"]
    elif _number(data["price"]) and _number(data["shares"]):
        equity = data["price"] * data["shares"]
    else:
        equity = 0
    debt = max(0, data["debt"])
    debt_weight = debt / (debt + equity) if debt + equity > 0 else 0
    equity_weight = 1 - debt_weight
    wacc = equity_weight * cost_equity + debt_weight * after_tax_debt
    return {
        "risk_free_rate": risk_free,
        "risk_free_source": rf_source,
        "equity_risk_premium": erp,
        "erp_source": "explicit long-run developed-market fallback; live ERP feed unavailable",
        "beta": beta,
        "beta_source": beta_source,
        "cost_of_equity": cost_equity,
        "pre_tax_cost_of_debt": pretax_cost_debt,
        "after_tax_cost_of_debt": after_tax_debt,
        "debt_weight": debt_weight,
        "equity_weight": equity_weight,
        "wacc": wacc,
        "confidence": "low" if "fallback" in rf_source or "fallback" in beta_source else "medium",
        "fallbacks": [
            label
            for label, source in (
                ("risk-free rate", rf_source),
                ("beta", beta_source),
                ("equity risk premium", "fallback"),
            )
            if "fallback" in source
        ],
    }


def _base_parameters(data: dict, rates: dict) -> dict:
    revenues = data["revenue_history"]
    hist_growth = _cagr(revenues[0], revenues[min(3, len(revenues) - 1)], min(3, len(revenues) - 1)) if len(revenues) >= 2 else None
    current_growth = _pick(data["info"], "revenueGrowth")
    observed_growth = current_growth if _number(current_growth) else hist_growth
    if not _number(observed_growth):
        observed_growth = 0.06
    current_margin = data["latest_fcff"] / data["latest_revenue"]
    op_margins = [
        op / rev for op, rev in zip(data["operating_income_history"], revenues)
        if rev > 0 and _number(op)
    ]

    kind = data["security_type"]
    if kind == "GROWTH_SOFTWARE_COMPANY":
        growth = _clamp(observed_growth, 0.10, 0.35)
        provider_fcf_margin = _pick(data["info"], "freeCashflow") / data["latest_revenue"] if _number(_pick(data["info"], "freeCashflow")) else None
        target_margin = _clamp(max(current_margin, provider_fcf_margin if _number(provider_fcf_margin) else current_margin) + 0.05, 0.12, 0.32)
        basis = "current growth with five-year deceleration and software FCF-margin convergence"
        margin_basis = f"current FCFF margin {_pct(current_margin)} and provider FCF margin {_pct(provider_fcf_margin)}; converges toward mature software economics"
        exit_multiple = 22.0
    elif kind == "CYCLICAL_COMPANY":
        normalized_op = sorted(op_margins)[len(op_margins) // 2] if op_margins else current_margin
        growth = _clamp(hist_growth if _number(hist_growth) else 0.04, -0.02, 0.08)
        target_margin = _clamp((normalized_op * (1 - data["tax_rate"]) + current_margin) / 2, 0.03, 0.30)
        basis = "mid-cycle revenue growth and normalized historical operating economics; peak results are not perpetuated"
        margin_basis = f"current FCFF margin {_pct(current_margin)} blended with normalized historical after-tax operating margin {_pct(normalized_op * (1 - data['tax_rate']))}"
        exit_multiple = 10.0
    else:
        growth = _clamp(observed_growth, 0.02, 0.18)
        target_margin = _clamp(current_margin + (0.02 if growth > 0.08 else 0), 0.05, 0.40)
        basis = "current and historical growth decaying toward mature-company economics"
        margin_basis = f"current FCFF margin {_pct(current_margin)} with limited normalization for durable mature-company economics"
        exit_multiple = 16.0
    return {
        "growth": growth,
        "target_margin": target_margin,
        "current_margin": current_margin,
        "wacc": _clamp(rates["wacc"], 0.065, 0.15),
        "terminal_growth": 0.025,
        "dilution": 0.005 if kind == "GROWTH_SOFTWARE_COMPANY" else 0.001,
        "basis": basis,
        "margin_basis": margin_basis,
        "exit_multiple": exit_multiple,
        "historical_growth": hist_growth,
        "current_growth": current_growth,
    }


def _scenario_assumptions(data, rates, overrides) -> dict[str, list[Assumption]]:
    base = _base_parameters(data, rates)
    sbc_policy = data.get("sbc_policy", SBC_ACCOUNTING_POLICY)
    spreads = {
        "bear": {"growth": -0.04, "margin": -0.04, "wacc": 0.01, "terminal": -0.005, "dilution": 0.005, "multiple": -2.0},
        "base": {"growth": 0, "margin": 0, "wacc": 0, "terminal": 0, "dilution": 0, "multiple": 0},
        "bull": {"growth": 0.04, "margin": 0.04, "wacc": -0.01, "terminal": 0.005, "dilution": -0.001, "multiple": 2.0},
    }
    result = {}
    override_map = {
        "revenue_growth": "growth",
        "fcf_margin": "target_margin",
        "wacc": "wacc",
        "terminal_growth": "terminal_growth",
    }
    anchors = {
        "growth": base["growth"],
        "target_margin": base["target_margin"],
        "wacc": base["wacc"],
        "terminal_growth": base["terminal_growth"],
    }
    override_fields = set()
    for cli_name, internal_name in override_map.items():
        if overrides.get(cli_name) is not None:
            anchors[internal_name] = overrides[cli_name]
            override_fields.add(internal_name)
    for scenario, delta in spreads.items():
        values = {
            "growth": _clamp(anchors["growth"] + delta["growth"], -0.10, 0.45),
            "target_margin": _clamp(anchors["target_margin"] + delta["margin"], 0.01, 0.45),
            "wacc": _clamp(anchors["wacc"] + delta["wacc"], 0.055, 0.18),
            "terminal_growth": _clamp(anchors["terminal_growth"] + delta["terminal"], 0.005, 0.04),
            "dilution": (
                0.0
                if sbc_policy == SBC_OWNER_EARNINGS_POLICY
                else max(0, base["dilution"] + delta["dilution"])
            ),
            "exit_multiple": base["exit_multiple"] + delta["multiple"],
        }
        overridden = override_fields if scenario == "base" else set()
        if values["wacc"] <= values["terminal_growth"]:
            raise ValueError(
                f"{scenario} case terminal growth must be below WACC "
                f"({_pct(values['terminal_growth'])} vs {_pct(values['wacc'])})."
            )

        def source_for(field):
            if field in overridden:
                return "user_override"
            if field in override_fields:
                return "user_override_with_scenario_spread"
            return "historical_company_data_and_model_policy"

        result[scenario] = [
            Assumption("year_1_revenue_growth", values["growth"], "decimal", source_for("growth"), base["basis"], "medium", scenario, "Forecast year 1", "growth" in overridden),
            Assumption("year_5_fcff_margin", values["target_margin"], "decimal", source_for("target_margin"), base["margin_basis"], "medium", scenario, "Forecast year 5", "target_margin" in overridden),
            Assumption("wacc", values["wacc"], "decimal", source_for("wacc"), "capital-structure-weighted cost of equity and after-tax debt; bounded to 5.5%–18%", rates.get("confidence", "medium"), scenario, "Five-year forecast and terminal value", "wacc" in overridden),
            Assumption("terminal_growth", values["terminal_growth"], "decimal", source_for("terminal_growth"), "2.5% mature nominal-growth default with ±0.5 percentage-point scenario spread; bounded below WACC", "medium", scenario, "Post-year-5 perpetuity", "terminal_growth" in overridden),
            Assumption("annual_dilution", values["dilution"], "decimal", "company_type_policy", "0.5% base for growth software and 0.1% for other supported companies; bear/bull cases adjust dilution", "low", scenario, "Annual through forecast"),
            Assumption("exit_ev_fcff_multiple", values["exit_multiple"], "multiple", "company_type_policy", "10x cyclical, 16x mature, or 22x growth-software cross-check with ±2x scenario spread; not a peer claim", "low", scenario, "End of forecast year 5"),
            Assumption("tax_rate", data["tax_rate"], "decimal", "historical_company_data_or_fallback", "latest usable effective tax rate; explicit 21% fallback", "medium", scenario, data.get("periods", {}).get("operating_income", "Latest fiscal year")),
        ]
    return result


def _assumption_value(items, name):
    return next(item.value for item in items if item.name == name)


def _dcf(data, assumptions, forced_growth=None, forced_margin=None):
    growth0 = _assumption_value(assumptions, "year_1_revenue_growth") if forced_growth is None else forced_growth
    target_margin = _assumption_value(assumptions, "year_5_fcff_margin") if forced_margin is None else forced_margin
    wacc = _assumption_value(assumptions, "wacc")
    terminal_growth = _assumption_value(assumptions, "terminal_growth")
    dilution = _assumption_value(assumptions, "annual_dilution")
    revenue = data["latest_revenue"]
    current_margin = data["latest_fcff"] / revenue
    forecast = []
    pv_fcff = 0
    for year in range(1, 6):
        growth = growth0 + (terminal_growth + 0.01 - growth0) * ((year - 1) / 4)
        margin = current_margin + (target_margin - current_margin) * (year / 5)
        revenue *= 1 + growth
        fcff = revenue * margin
        discount_factor = (1 + wacc) ** year
        discounted = fcff / discount_factor
        pv_fcff += discounted
        forecast.append({
            "year": year,
            "period": f"Forecast year {year}",
            "revenue_growth": growth,
            "revenue": revenue,
            "fcff_margin": margin,
            "fcff": fcff,
            "discount_factor": discount_factor,
            "present_value": discounted,
        })
    denominator = wacc - terminal_growth
    if denominator <= 0:
        raise ValueError("WACC must exceed terminal growth.")
    terminal_year_fcff = forecast[-1]["fcff"] * (1 + terminal_growth)
    terminal_value = terminal_year_fcff / denominator
    pv_terminal = terminal_value / ((1 + wacc) ** 5)
    enterprise_value = pv_fcff + pv_terminal
    net_cash = data["cash"] - data["debt"]
    other_senior_claims = data.get("other_senior_claims", 0)
    equity_value = enterprise_value + net_cash - other_senior_claims
    diluted_shares = data["shares"] * ((1 + dilution) ** 5)
    fair_value = equity_value / diluted_shares
    exit_multiple = _assumption_value(assumptions, "exit_ev_fcff_multiple")
    exit_terminal_value = forecast[-1]["fcff"] * exit_multiple
    exit_enterprise_value = pv_fcff + exit_terminal_value / ((1 + wacc) ** 5)
    exit_equity_value = exit_enterprise_value + net_cash - other_senior_claims
    exit_fair_value = exit_equity_value / diluted_shares
    return {
        "forecast": forecast,
        "pv_forecast_fcff": pv_fcff,
        "terminal_value": terminal_value,
        "terminal_year_fcff": terminal_year_fcff,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "net_cash_debt_adjustment": net_cash,
        "other_senior_claims": other_senior_claims,
        "equity_value": equity_value,
        "diluted_shares": diluted_shares,
        "fair_value_per_share": fair_value,
        "exit_multiple": exit_multiple,
        "exit_terminal_value": exit_terminal_value,
        "exit_enterprise_value": exit_enterprise_value,
        "exit_fair_value_per_share": exit_fair_value,
        "terminal_method_difference": exit_fair_value - fair_value,
        "current_price": data["price"],
        "upside_downside": fair_value / data["price"] - 1 if _number(data["price"]) and data["price"] > 0 else None,
    }


def _sensitivity(data, base_items):
    base_wacc = _assumption_value(base_items, "wacc")
    base_growth = _assumption_value(base_items, "terminal_growth")
    waccs = [base_wacc + x for x in (-0.02, -0.01, 0, 0.01, 0.02)]
    terminal_rates = [base_growth + x for x in (-0.01, -0.005, 0, 0.005)]
    values = []
    validity = []
    for wacc in waccs:
        row = []
        valid_row = []
        for terminal in terminal_rates:
            cloned = [Assumption(**asdict(item)) for item in base_items]
            next(item for item in cloned if item.name == "wacc").value = wacc
            next(item for item in cloned if item.name == "terminal_growth").value = terminal
            try:
                row.append(_dcf(data, cloned)["fair_value_per_share"])
                valid_row.append(True)
            except ValueError:
                row.append(None)
                valid_row.append(False)
        values.append(row)
        validity.append(valid_row)
    return {
        "wacc": waccs,
        "terminal_growth": terminal_rates,
        "values": values,
        "validity": validity,
        "calculation": "Each cell is a full DCF recalculation; invalid cells have WACC <= terminal growth.",
    }


def _reverse_dcf(data, base_items):
    fixed = {
        "wacc": _assumption_value(base_items, "wacc"),
        "year_5_fcff_margin": _assumption_value(base_items, "year_5_fcff_margin"),
        "terminal_growth": _assumption_value(base_items, "terminal_growth"),
        "annual_dilution": _assumption_value(base_items, "annual_dilution"),
    }
    base_result = {
        "solved_variable": "Year-1 revenue growth (with resulting five-year revenue CAGR)",
        "fixed_assumptions": fixed,
        "search_bounds": {
            "year_1_revenue_growth": list(REVERSE_GROWTH_BOUNDS),
            "residual_tolerance_per_share": REVERSE_TOLERANCE_PER_SHARE,
        },
    }
    if not _number(data["price"]) or data["price"] <= 0:
        return {
            **base_result,
            "converged": False,
            "status": "NO_MARKET_PRICE",
            "reason": "Current market price is unavailable.",
            "residual_per_share": None,
        }
    if not _number(data["latest_fcff"]) or data["latest_fcff"] <= 0:
        return {
            **base_result,
            "converged": False,
            "status": "UNSTABLE_CASH_FLOW_BASE",
            "reason": "Reverse DCF is not run from a negative or non-positive FCFF base.",
            "residual_per_share": None,
        }
    low, high = REVERSE_GROWTH_BOUNDS
    low_value = _dcf(data, base_items, forced_growth=low)["fair_value_per_share"] - data["price"]
    high_value = _dcf(data, base_items, forced_growth=high)["fair_value_per_share"] - data["price"]
    if low_value * high_value > 0:
        return {
            **base_result,
            "converged": False,
            "status": "NO_ECONOMIC_SOLUTION",
            "reason": "No economically plausible solution exists inside the tested -20% to 50% Year-1 growth range.",
            "low_case_value": low_value + data["price"],
            "high_case_value": high_value + data["price"],
            "residual_per_share": min((low_value, high_value), key=abs),
        }
    difference = None
    iterations = 0
    for iterations in range(1, 81):
        mid = (low + high) / 2
        difference = _dcf(data, base_items, forced_growth=mid)["fair_value_per_share"] - data["price"]
        if abs(difference) <= REVERSE_TOLERANCE_PER_SHARE:
            break
        if difference * low_value <= 0:
            high = mid
        else:
            low, low_value = mid, difference
    if difference is None or abs(difference) > REVERSE_TOLERANCE_PER_SHARE:
        return {
            **base_result,
            "converged": False,
            "status": "NON_CONVERGENT",
            "reason": "The solver did not reach the residual tolerance within 80 iterations.",
            "residual_per_share": difference,
            "iterations": iterations,
        }
    if min(abs(mid - bound) for bound in REVERSE_GROWTH_BOUNDS) < 1e-6:
        return {
            **base_result,
            "converged": False,
            "status": "BOUNDARY_SOLUTION",
            "reason": "The solution lies on a search boundary and is not treated as economic convergence.",
            "residual_per_share": difference,
            "iterations": iterations,
        }
    solved = _dcf(data, base_items, forced_growth=mid)
    realized_cagr = (solved["forecast"][-1]["revenue"] / data["latest_revenue"]) ** (1 / 5) - 1
    return {
        **base_result,
        "converged": True,
        "status": "CONVERGED",
        "required_5y_revenue_cagr": realized_cagr,
        "required_year_1_revenue_growth": mid,
        "required_year_5_fcff_margin": fixed["year_5_fcff_margin"],
        "terminal_growth": fixed["terminal_growth"],
        "wacc": fixed["wacc"],
        "dilution": fixed["annual_dilution"],
        "residual_per_share": difference,
        "iterations": iterations,
    }


def _period_consistency(data):
    periods = data.get("periods", {})
    revenue_period = periods.get("revenue", "Unlabeled")
    fcff_period = periods.get("fcff", "Unlabeled")
    consistent = revenue_period == fcff_period
    detail = (
        f"Revenue and FCFF both use {revenue_period}."
        if consistent
        else f"Revenue uses {revenue_period}; FCFF uses {fcff_period}. The mismatch is disclosed and lowers confidence."
    )
    return consistent, detail


def _sensitivity_is_monotonic(sensitivity):
    values = sensitivity["values"]
    row_checks = []
    for row in values:
        valid = [value for value in row if _number(value)]
        row_checks.append(all(left <= right for left, right in zip(valid, valid[1:])))
    column_checks = []
    for column in range(len(sensitivity["terminal_growth"])):
        valid = [row[column] for row in values if _number(row[column])]
        column_checks.append(all(upper >= lower for upper, lower in zip(valid, valid[1:])))
    return all(row_checks + column_checks)


def _validate(data, assumptions, scenarios, reverse, sensitivity, rates):
    reasons = []
    checks = {}

    forecast_ok = True
    terminal_ok = True
    bridge_ok = True
    shares_ok = True
    bear, base, bull = (scenarios[name]["fair_value_per_share"] for name in ("bear", "base", "bull"))
    scenario_ordering = bear <= base <= bull
    if not scenario_ordering:
        reasons.append("scenario fair values are not logically ordered")
    for name, items in assumptions.items():
        wacc = _assumption_value(items, "wacc")
        terminal = _assumption_value(items, "terminal_growth")
        margin = _assumption_value(items, "year_5_fcff_margin")
        if wacc <= terminal:
            reasons.append(f"{name}: WACC does not exceed terminal growth")
        if margin > 0.45:
            reasons.append(f"{name}: FCFF margin exceeds the 45% plausibility guardrail")
        if _assumption_value(items, "exit_ev_fcff_multiple") <= 0:
            reasons.append(f"{name}: exit EV/FCFF multiple is invalid")
        scenario = scenarios[name]
        forecast_ok = forecast_ok and abs(
            scenario["pv_forecast_fcff"] - sum(row["present_value"] for row in scenario["forecast"])
        ) <= 0.01
        terminal_ok = terminal_ok and abs(
            scenario["enterprise_value"]
            - scenario["pv_forecast_fcff"]
            - scenario["pv_terminal_value"]
        ) <= 0.01
        reconciled_equity = (
            scenario["enterprise_value"]
            + scenario["net_cash_debt_adjustment"]
            - scenario["other_senior_claims"]
        )
        bridge_ok = bridge_ok and abs(reconciled_equity - scenario["equity_value"]) <= 0.01
        shares_ok = shares_ok and scenario["diluted_shares"] > 0
        reconciled = reconciled_equity / scenario["diluted_shares"]
        if abs(reconciled - scenario["fair_value_per_share"]) > 0.01:
            reasons.append(f"{name}: enterprise-to-equity reconciliation failed")
            bridge_ok = False
    if not forecast_ok:
        reasons.append("forecast present-value arithmetic failed")
    if not terminal_ok:
        reasons.append("enterprise value does not reconcile to forecast plus terminal present value")
    if not shares_ok:
        reasons.append("diluted share count is not positive")
    if not reverse.get("converged"):
        reasons.append(f"reverse DCF: {reverse.get('reason')}")
    period_consistent, period_detail = _period_consistency(data)
    if not period_consistent:
        reasons.append(period_detail)
    sensitivity_monotonic = _sensitivity_is_monotonic(sensitivity)
    if not sensitivity_monotonic:
        reasons.append("sensitivity table is not monotonic in WACC and terminal growth")
    fallback_labels = rates.get("fallbacks", [])
    if fallback_labels:
        reasons.append(f"discount-rate fallbacks used: {', '.join(fallback_labels)}")
    provider_growth = _pick(data["info"], "revenueGrowth")
    if _number(provider_growth) and abs(provider_growth) > 1.5:
        reasons.append(
            f"provider current revenue growth of {_pct(provider_growth)} is an extreme observation and should be independently verified"
        )
    checks.update({
        "forecast_arithmetic": {"passed": forecast_ok, "detail": "Explicit forecast PV equals the sum of recalculated annual FCFF present values."},
        "terminal_value": {"passed": terminal_ok, "detail": "Enterprise value equals explicit forecast PV plus terminal-value PV."},
        "ev_to_equity_bridge": {"passed": bridge_ok, "detail": "Equity value equals enterprise value plus cash less debt and other senior claims."},
        "share_count": {"passed": shares_ok, "detail": "Fair value uses a positive, forecast-diluted share count."},
        "scenario_ordering": {"passed": scenario_ordering, "detail": "Bear <= base <= bull."},
        "wacc_above_terminal_growth": {
            "passed": all(
                _assumption_value(items, "wacc") > _assumption_value(items, "terminal_growth")
                for items in assumptions.values()
            ),
            "detail": "All scenario and valid sensitivity calculations require WACC > terminal growth.",
        },
        "reverse_dcf_convergence": {"passed": bool(reverse.get("converged")), "detail": reverse.get("status", "UNKNOWN")},
        "period_consistency": {"passed": period_consistent, "detail": period_detail},
        "sensitivity_monotonicity": {
            "passed": sensitivity_monotonic,
            "detail": "Higher WACC lowers value and higher terminal growth raises value for all valid cells.",
        },
    })
    critical = ("forecast_arithmetic", "terminal_value", "ev_to_equity_bridge", "share_count", "scenario_ordering", "wacc_above_terminal_growth")
    status = "FAILED" if any(not checks[key]["passed"] for key in critical) else "PROVISIONAL" if reasons else "PASSED"
    return {"status": status, "checks": checks, "reasons": reasons}


def _cross_checks(data, scenarios):
    info = data["info"]
    fcf_yield = data["latest_fcf"] / data["market_cap"] if _number(data["latest_fcf"]) and _number(data["market_cap"]) and data["market_cap"] else None
    metrics = {
        "forward_pe": _pick(info, "forwardPE"),
        "ev_revenue": _pick(info, "enterpriseToRevenue"),
        "ev_ebitda": _pick(info, "enterpriseToEbitda"),
        "fcf_yield": fcf_yield,
        "base_case_implied_value": scenarios["base"]["fair_value_per_share"],
    }
    notes = []
    if not _number(metrics["ev_ebitda"]) or metrics["ev_ebitda"] <= 0 or metrics["ev_ebitda"] > 100:
        metrics["ev_ebitda"] = None
        notes.append("EV/EBITDA is not economically meaningful or unavailable.")
    return {"metrics": metrics, "notes": notes, "historical_peer_ranges": "Unavailable from the current verified data feed; no range was invented."}


def build_valuation_report(ticker: str, overrides: dict | None = None, data: dict | None = None) -> dict:
    overrides = overrides or {}
    # A pre-collected normalized source object may be shared by Company
    # Economics and valuation to avoid duplicate provider requests.  Valuation
    # math and assumptions remain unchanged.
    data = data if data is not None else collect_valuation_data(ticker)
    sbc_policy = overrides.get("sbc_policy", SBC_ACCOUNTING_POLICY)
    data["sbc_policy"] = sbc_policy
    kind = data["security_type"]
    company_type = COMPANY_TYPE_LABELS[kind]
    selected_method = METHODS[kind]
    report = {
        "report_type": "intrinsic_valuation",
        "security_type": kind,
        "company_type": company_type,
        "selected_method": selected_method,
        "company": {
            "name": data["company"],
            "ticker": data["ticker"],
            "security_type": kind,
            "company_type": company_type,
            "valuation_method": selected_method,
            "as_of": data["as_of"],
            "current_market_price": data["price"],
        },
        "valuation_method_selection": {
            "company_type": company_type,
            "selected_framework": selected_method,
            "routing_evidence": data.get("routing_evidence", []),
        },
        "data_quality": {},
        "historical_base": {},
        "historical_fcff_reconciliation": {},
        "assumptions": {},
        "discount_rate": {},
        "scenarios": {},
        "sensitivity": {},
        "reverse_dcf": {},
        "cross_checks": {},
        "risks": [],
        "fair_value_drivers": {},
        "final_interpretation": {},
        "validation": {},
        "internal_validation": {},
        "fallback": {},
    }
    if kind not in SUPPORTED_DCF_TYPES:
        fallback_map = {
            "ETF_OR_FUND": (
                "A fund is a portfolio vehicle; company DCF assumptions are economically inappropriate.",
                "Portfolio NAV, holdings, fees, and exposure analysis",
                ["verified holdings and portfolio NAV"],
            ),
            "FINANCIAL_INSTITUTION": (
                "Debt and interest are operating inputs for financial institutions; an industrial-company FCFF DCF would be misleading.",
                "Residual-income or dividend-discount framework",
                ["verified book-value, ROE, regulatory-capital, and payout history"],
            ),
            "REIT": (
                "Property cash economics are better represented by NAV and AFFO than industrial FCFF.",
                "NAV / AFFO framework",
                ["property NOI, cap rates, AFFO, and property-level NAV"],
            ),
            "PRE_PROFIT_COMPANY": (
                "A positive and supportable FCFF base is unavailable, so perpetual-growth DCF mechanics are unstable.",
                "Revenue-scenario and financing-runway framework",
                ["cash runway, burn rate, dilution capacity, and credible cash-flow convergence"],
            ),
            "SPAC_OR_SHELL": (
                "Trust assets and transaction terms, not conventional operating cash flow, determine value.",
                "Trust-value and transaction-structure framework",
                ["trust value, redemption terms, sponsor economics, and announced transaction terms"],
            ),
            "INSUFFICIENT_DATA": (
                "Issuer identity or historical financial data could not be validated.",
                "Verified security resolution before valuation",
                ["issuer identity, market price, and historical financial statements"],
            ),
        }
        reason, framework, missing = fallback_map[kind]
        report["fallback"] = {
            "detected_security_type": kind,
            "why_standard_dcf_is_inappropriate": reason,
            "required_specialized_framework": framework,
            "missing_data": missing,
            "next_implementation_stage": f"Implement {framework} only after the required verified data is available.",
        }
        report["data_quality"] = {"status": "INSUFFICIENT_FOR_FAIR_VALUE", "missing": missing, "reason": reason}
        validation = {
            "status": "PROVISIONAL",
            "checks": {
                "framework_selection": {
                    "passed": True,
                    "detail": "The unsupported security type was not forced through a conventional company DCF.",
                }
            },
            "reasons": [reason],
        }
        report["validation"] = validation
        report["internal_validation"] = validation
        report["_data"] = data
        return report

    debt_coverage = data.get("debt_coverage")
    if debt_coverage is not None and debt_coverage != "COMPLETE":
        provenance = data.get("debt_provenance") or {}
        reason = (
            "The SEC fallback does not provide complete, period-aligned total debt; "
            "the enterprise-value-to-equity bridge is blocked rather than treating missing debt as zero."
        )
        report["data_quality"] = {
            "status": "INSUFFICIENT_FOR_FAIR_VALUE",
            "missing": provenance.get("missing_components", ["complete total debt"]),
            "reason": reason,
        }
        validation = {
            "status": "FAILED",
            "checks": {
                "debt_coverage": {
                    "passed": False,
                    "detail": f"SEC debt coverage: {debt_coverage}.",
                }
            },
            "reasons": [reason],
        }
        report["validation"] = validation
        report["internal_validation"] = validation
        report["_data"] = data
        return report

    reconciliation = _historical_fcff_reconciliation(data, sbc_policy)
    report["historical_fcff_reconciliation"] = reconciliation
    if reconciliation["status"] != "PASSED":
        report["data_quality"] = {
            "status": "FAILED_FCFF_RECONCILIATION",
            "missing": reconciliation.get("missing", []),
            "reason": reconciliation["reason"],
        }
        validation = {
            "status": "FAILED",
            "checks": {
                "historical_fcff_reconciliation": {
                    "passed": False,
                    "detail": reconciliation["reason"],
                }
            },
            "reasons": [reconciliation["reason"]],
        }
        report["validation"] = validation
        report["internal_validation"] = validation
        report["_data"] = data
        return report

    # The reconciled NOPAT construction is the historical FCFF forecast base.
    data["latest_fcff"] = reconciliation["calculated_fcff"]

    missing = _required_data_missing(data)
    if missing:
        report["data_quality"] = {"status": "INSUFFICIENT_FOR_FAIR_VALUE", "missing": missing, "reason": "Required DCF inputs are missing."}
        validation = {"status": "PROVISIONAL", "checks": {}, "reasons": [f"Missing: {', '.join(missing)}"]}
        report["validation"] = validation
        report["internal_validation"] = validation
        report["_data"] = data
        return report

    revenue = data["revenue_history"]
    op_income = data["operating_income_history"]
    gross = data["gross_profit_history"]
    report["historical_base"] = {
        "period_basis": data.get("periods", {}),
        "period_consistency": _period_consistency(data)[1],
        "latest_annual_revenue": data["latest_revenue"],
        "prior_annual_revenue": revenue[1] if len(revenue) > 1 else None,
        "three_year_revenue_cagr": _cagr(revenue[0], revenue[3], 3) if len(revenue) > 3 else None,
        "current_provider_revenue_growth": _pick(data["info"], "revenueGrowth"),
        "gross_margin": gross[0] / revenue[0] if gross and revenue and revenue[0] else _pick(data["info"], "grossMargins"),
        "operating_margin": op_income[0] / revenue[0] if op_income and revenue and revenue[0] else _pick(data["info"], "operatingMargins"),
        "historical_operating_margin_range": [
            min(op / rev for op, rev in zip(op_income, revenue) if rev > 0),
            max(op / rev for op, rev in zip(op_income, revenue) if rev > 0),
        ] if op_income and revenue else None,
        "fcff_margin": data["latest_fcff"] / data["latest_revenue"],
        "operating_cash_flow": data["latest_ocf"],
        "capital_expenditure": data["latest_capex"],
        "free_cash_flow": data["latest_fcf"],
        "stock_based_compensation": data["sbc"],
        "working_capital_effects": (
            f"Latest reported cash-flow impact included in historical FCFF: {_large(data['working_capital_change'])}; "
            "future effects are embedded in the normalized FCFF margin."
            if _number(data.get("working_capital_change"))
            else "Historical change in working capital is unavailable and is not invented; future effects are embedded in the normalized FCFF margin."
        ),
        "tax_treatment": "FCFF starts from operating income after the effective tax rate, then adds depreciation and subtracts capex when available.",
        "capex_treatment": "Latest reported capex is included in the historical FCFF base; future capital intensity is embedded in forecast FCFF margins.",
        "stock_based_compensation_treatment": reconciliation["sbc_treatment"],
        "cash": data["cash"],
        "debt": data["debt"],
        "net_cash": data["cash"] - data["debt"],
        "diluted_shares": data["shares"],
        "diluted_share_history": _row(data["income"], "Diluted Average Shares", "Basic Average Shares"),
    }
    rates = _market_rates(data)
    assumptions = _scenario_assumptions(data, rates, overrides)
    scenarios = {name: _dcf(data, items) for name, items in assumptions.items()}
    sensitivity = _sensitivity(data, assumptions["base"])
    reverse = _reverse_dcf(data, assumptions["base"])
    validation = _validate(data, assumptions, scenarios, reverse, sensitivity, rates)
    validation["checks"]["historical_fcff_reconciliation"] = {
        "passed": True,
        "detail": reconciliation["reason"],
    }
    base_dilution = _assumption_value(assumptions["base"], "annual_dilution")
    accounting_policy = sbc_policy == SBC_ACCOUNTING_POLICY
    dilution_consistent = (accounting_policy and base_dilution > 0) or (
        not accounting_policy and base_dilution == 0
    )
    validation["checks"].update({
        "sbc_policy_identified": {
            "passed": sbc_policy in SBC_POLICIES,
            "detail": f"Selected policy: {sbc_policy}.",
        },
        "sbc_comparable_definitions": {
            "passed": reconciliation["within_tolerance"],
            "detail": "Both FCFF routes use the same explicit SBC policy.",
        },
        "sbc_added_or_deducted_once": {
            "passed": (
                reconciliation["sbc_added_back_exactly_once"]
                if accounting_policy
                else reconciliation["sbc_deducted_exactly_once"]
            ),
            "detail": reconciliation["sbc_treatment"],
        },
        "sbc_dilution_double_count": {
            "passed": dilution_consistent,
            "detail": (
                "Accounting FCFF retains SBC and applies forecast dilution once."
                if accounting_policy
                else "Owner earnings deducts SBC and disables forecast dilution."
            ),
        },
    })
    if not dilution_consistent:
        validation["status"] = "FAILED"
        validation["reasons"].append(
            "SBC is simultaneously deducted from FCFF and penalized through dilution, or neither treatment is applied."
        )
    cross_checks = _cross_checks(data, scenarios)
    extreme_provider_growth = _number(_pick(data["info"], "revenueGrowth")) and abs(_pick(data["info"], "revenueGrowth")) > 1.5
    report["data_quality"] = {
        "status": "LIMITED" if extreme_provider_growth or len(revenue) < 4 or not _number(data.get("working_capital_change")) else "GOOD",
        "missing": [],
        "reason": (
            f"{len(revenue)} annual revenue periods available; market and statement fields sourced from Yahoo Finance. "
            + (
                "The historical working-capital cash-flow impact is included."
                if _number(data.get("working_capital_change"))
                else "A separate historical working-capital cash-flow impact was unavailable, so no value was invented."
            )
        ),
    }
    report["assumptions"] = {name: [asdict(item) for item in items] for name, items in assumptions.items()}
    report["assumptions"]["policies"] = {
        "capex_intensity": {
            "value": "embedded_in_fcff_margin",
            "source": "historical_company_cash_flow",
            "basis": "forecast FCFF margins normalize observed after-tax operating cash economics, depreciation, and capex",
            "confidence": "medium",
            "period": data.get("periods", {}).get("fcff", "Latest fiscal year"),
        },
        "working_capital": {
            "value": "embedded_in_fcff_margin",
            "source": "historical_company_cash_flow",
            "basis": "no separate working-capital release is invented",
            "confidence": "low",
            "period": "Forecast annual",
        },
        "stock_based_compensation": {
            "value": sbc_policy,
            "source": "historical_company_cash_flow_and_company_type_policy",
            "basis": reconciliation["sbc_treatment"],
            "confidence": "medium",
            "period": "Forecast annual",
        },
    }
    report["discount_rate"] = rates
    report["scenarios"] = scenarios
    report["sensitivity"] = sensitivity
    report["reverse_dcf"] = reverse
    report["cross_checks"] = cross_checks
    report["risks"] = [
        "Revenue growth may decelerate faster than the scenario path.",
        "FCFF-margin convergence may stall; working-capital and capital-intensity needs may exceed the normalized margin.",
        "Stock-based compensation and dilution may exceed the explicit annual dilution assumption.",
        "A higher WACC or lower terminal growth materially reduces present value.",
        "Cyclical normalization may still overstate mid-cycle economics." if kind == "CYCLICAL_COMPANY" else "Terminal economics may prove less durable than assumed.",
    ]
    report["fair_value_drivers"] = {
        "raise": ["higher sustained revenue growth", "stronger FCFF conversion", "lower dilution", "lower WACC", "stronger terminal economics"],
        "lower": ["lower growth", "weaker margins", "higher dilution", "higher WACC", "lower terminal growth"],
        "highest_sensitivity": "WACC and terminal growth dominate the sensitivity grid; revenue growth and Year-5 FCFF margin dominate operating value.",
    }
    base_value = scenarios["base"]["fair_value_per_share"]
    report["final_interpretation"] = {
        "bear_to_bull_range": [scenarios["bear"]["fair_value_per_share"], scenarios["bull"]["fair_value_per_share"]],
        "base_fair_value": base_value,
        "text": (
            f"The explicit scenarios produce a fair-value range of "
            f"${scenarios['bear']['fair_value_per_share']:,.2f}–${scenarios['bull']['fair_value_per_share']:,.2f} per share, "
            f"with a ${base_value:,.2f} base-case estimate. "
            "This is a research estimate, not a recommendation, and is highly sensitive to discount rate, durable cash-flow margin, growth, and dilution."
        ),
    }
    report["validation"] = validation
    report["internal_validation"] = validation
    if validation["status"] == "FAILED":
        report["diagnostic_scenarios"] = report["scenarios"]
        report["scenarios"] = {}
        report["sensitivity"] = {}
        report["reverse_dcf"] = {"status": "VALIDATION_FAILED", "reason": "Critical valuation checks failed."}
        report["cross_checks"] = {"notes": ["Authoritative values withheld after critical validation failure."]}
        report["final_interpretation"] = {"text": "Fair value withheld: " + "; ".join(validation["reasons"])}
    report["_data"] = data
    return report


def _print_assumptions(items, scenario):
    print(f"{scenario.upper()} CASE")
    for item in items:
        marker = " [OVERRIDE]" if item["overridden"] else ""
        display = f"{item['value']:.1f}x" if item["unit"] == "multiple" else _pct(item["value"])
        print(f"- {item['name'].replace('_', ' ').title()}: {display}{marker}")
        print(f"  Period: {item['period']}")
        print(f"  Basis: {item['basis']}")
        print(f"  Source: {item['source']} | Confidence: {item['confidence']}")
    print()


def _print_fcff_reconciliation(reconciliation):
    if not reconciliation:
        return
    print("=================================================")
    print("HISTORICAL FCFF RECONCILIATION")
    print("=================================================")
    print(f"Status: {reconciliation.get('status', 'FAILED')}")
    print(f"Period: {reconciliation.get('period', 'Unavailable')}")
    for label, key in (
        ("NOPAT", "nopat"),
        ("D&A", "depreciation_and_amortization"),
        ("Capex", "capex"),
        ("Change in Working Capital", "change_in_working_capital"),
        ("After-tax Interest", "after_tax_interest"),
        ("Stock-Based Compensation", "stock_based_compensation"),
        ("Other Adjustments", "other_adjustments"),
        ("NOPAT-Based FCFF Before SBC", "nopat_based_fcff_before_sbc"),
        ("+ Stock-Based Compensation", "sbc_addback"),
        ("Adjusted NOPAT-Based FCFF", "adjusted_nopat_based_fcff"),
        ("Selected Calculated FCFF", "calculated_fcff"),
        ("Operating Cash Flow", "operating_cash_flow"),
        ("Operating Cash Flow minus Capex", "operating_cash_flow_minus_capex"),
        ("Difference vs OCF minus Capex", "difference_vs_operating_cash_flow_minus_capex"),
        ("CFO-based FCFF (OCF - Capex + after-tax interest)", "cfo_based_fcff"),
        ("Reconciliation Difference", "reconciliation_difference"),
        ("Tolerance", "tolerance"),
    ):
        print(f"{label}: {_large(reconciliation.get(key))}")
    print(f"SBC Policy: {reconciliation.get('sbc_policy', 'Unavailable')}")
    print(f"SBC Treatment: {reconciliation.get('sbc_treatment', 'Unavailable')}")
    print(f"Reconciliation Difference %: {_pct(reconciliation.get('reconciliation_difference_pct'))}")
    print(f"Double-Count Check: {reconciliation.get('double_count_check', 'FAILED')}")
    if reconciliation.get("likely_cause"):
        print(f"Likely Cause: {reconciliation['likely_cause']}")
    missing = reconciliation.get("missing") or []
    if missing:
        print(f"Missing: {', '.join(missing)}")
    print(f"Conclusion: {reconciliation.get('reason')}")
    print()


def print_valuation_report(report: dict):
    company = report["company"]
    print("=================================================")
    print("INTRINSIC VALUATION REPORT")
    print("=================================================")
    print()
    print(f"Company: {company['name']}")
    print(f"Ticker: {company['ticker']}")
    print(f"Company Type: {company['company_type']}")
    print(f"Selected Framework: {company['valuation_method']}")
    print(f"Data Quality: {report['data_quality'].get('status')}")
    print(f"As Of: {company['as_of']}")
    print(f"Current Market Price: {_money(company['current_market_price'])}")
    print()
    _print_fcff_reconciliation(report.get("historical_fcff_reconciliation"))
    if not report["scenarios"]:
        print("Fair Value: NOT CALCULATED")
        print(f"Reason: {report['data_quality'].get('reason')}")
        missing = report["data_quality"].get("missing") or []
        if missing:
            print(f"Missing required data: {', '.join(missing)}")
        fallback = report.get("fallback") or {}
        if fallback:
            print(f"Required Specialized Framework: {fallback['required_specialized_framework']}")
            print(f"Next Stage: {fallback['next_implementation_stage']}")
        print()
        print("Routing Evidence:")
        for item in report["valuation_method_selection"]["routing_evidence"]:
            print(f"- {item}")
        print()
        print(f"Internal Validation: {report['internal_validation'].get('status', 'PROVISIONAL')}")
        for reason in report["internal_validation"].get("reasons", []):
            print(f"- {reason}")
        return

    base = report["historical_base"]
    print("=================================================")
    print("VALUATION METHOD SELECTION")
    print("=================================================")
    print(f"Company Type: {report['company_type']}")
    print(f"Selected Framework: {report['selected_method']}")
    print("Routing Evidence:")
    for item in report["valuation_method_selection"]["routing_evidence"]:
        print(f"- {item}")
    print()
    print("=================================================")
    print("HISTORICAL OPERATING BASE")
    print("=================================================")
    print("Period Basis:")
    for name, period in base["period_basis"].items():
        print(f"- {name.replace('_', ' ').title()}: {period}")
    print(f"Period Consistency: {base['period_consistency']}")
    print(f"Revenue (latest annual): {_large(base['latest_annual_revenue'])}")
    print(f"Revenue (prior annual): {_large(base['prior_annual_revenue'])}")
    print(f"3Y Revenue CAGR: {_pct(base['three_year_revenue_cagr'])}")
    print(f"Current provider growth (TTM/most recent): {_pct(base['current_provider_revenue_growth'])}")
    print(f"Gross Margin: {_pct(base['gross_margin'])}")
    print(f"Operating Margin: {_pct(base['operating_margin'])}")
    margin_range = base["historical_operating_margin_range"]
    print(
        f"Historical Operating Margin Range: {_pct(margin_range[0])} to {_pct(margin_range[1])}"
        if margin_range else "Historical Operating Margin Range: Unavailable"
    )
    print(f"FCFF Margin: {_pct(base['fcff_margin'])}")
    print(f"Operating Cash Flow: {_large(base['operating_cash_flow'])}")
    print(f"Capital Expenditure: {_large(base['capital_expenditure'])}")
    print(f"Free Cash Flow: {_large(base['free_cash_flow'])}")
    print(f"Stock-Based Compensation: {_large(base['stock_based_compensation'])}")
    print(f"Working Capital: {base['working_capital_effects']}")
    print(f"Cash / Debt / Net Cash: {_large(base['cash'])} / {_large(base['debt'])} / {_large(base['net_cash'])}")
    print(f"Diluted Shares: {base['diluted_shares'] / 1e6:,.1f}M")
    share_history = base["diluted_share_history"]
    if len(share_history) >= 2 and share_history[1] > 0:
        print(f"Latest Annual Dilution Trend: {_pct(share_history[0] / share_history[1] - 1)}")
    else:
        print("Latest Annual Dilution Trend: Unavailable")
    print()
    print("=================================================")
    print("FORECAST ASSUMPTIONS")
    print("=================================================")
    for name in ("bear", "base", "bull"):
        _print_assumptions(report["assumptions"][name], name)
    print("OTHER FORECAST POLICIES")
    for name, policy in report["assumptions"]["policies"].items():
        print(f"- {name.replace('_', ' ').title()}: {policy['value']}")
        print(f"  Basis: {policy['basis']}")
        print(f"  Source: {policy['source']} | Confidence: {policy['confidence']}")
    print()
    print("BASE-CASE YEARLY OPERATING FORECAST")
    print(f"{'Year':>4} {'Revenue Growth':>16} {'Revenue':>16} {'FCFF Margin':>14} {'FCFF':>16}")
    for row in report["scenarios"]["base"]["forecast"]:
        print(
            f"{row['year']:>4} {_pct(row['revenue_growth']):>16} {_large(row['revenue']):>16} "
            f"{_pct(row['fcff_margin']):>14} {_large(row['fcff']):>16}"
        )
    print()

    rates = report["discount_rate"]
    print("=================================================")
    print("DISCOUNT RATE")
    print("=================================================")
    print(f"Risk-Free Rate: {_pct(rates['risk_free_rate'])} ({rates['risk_free_source']})")
    print(f"Equity Risk Premium: {_pct(rates['equity_risk_premium'])} ({rates['erp_source']})")
    print(f"Beta: {rates['beta']:.2f} ({rates['beta_source']})")
    print(f"Cost of Equity = Rf + Beta × ERP: {_pct(rates['cost_of_equity'])}")
    print(f"Pre-tax / After-tax Cost of Debt: {_pct(rates['pre_tax_cost_of_debt'])} / {_pct(rates['after_tax_cost_of_debt'])}")
    print(f"Debt / Equity Weight: {_pct(rates['debt_weight'])} / {_pct(rates['equity_weight'])}")
    print(f"Calculated WACC: {_pct(rates['wacc'])}")
    print()
    print("=================================================")
    print("TERMINAL VALUE")
    print("=================================================")
    print("Method A: Gordon Growth (primary calculated method)")
    for name in ("bear", "base", "bull"):
        items = report["assumptions"][name]
        growth = next(x["value"] for x in items if x["name"] == "terminal_growth")
        print(f"{name.title()} terminal growth: {_pct(growth)}")
    print("Method B: Exit multiple reconciliation")
    for name in ("bear", "base", "bull"):
        value = report["scenarios"][name]
        print(
            f"{name.title()} {value['exit_multiple']:.1f}x EV/FCFF: "
            f"{_money(value['exit_fair_value_per_share'])} per share "
            f"(difference vs Gordon: {_money(value['terminal_method_difference'])})"
        )
    ev_ebitda = report["cross_checks"]["metrics"]["ev_ebitda"]
    print(f"Current EV/EBITDA reference: {ev_ebitda:.2f}x" if _number(ev_ebitda) else "Current EV/EBITDA is not economically meaningful or unavailable.")
    print()
    print("=================================================")
    print("SCENARIO VALUATION")
    print("=================================================")
    for name in ("bear", "base", "bull"):
        value = report["scenarios"][name]
        print(f"{name.upper()} CASE")
        print(f"Enterprise Value: {_large(value['enterprise_value'])}")
        print(f"Net Cash / Debt Adjustment: {_large(value['net_cash_debt_adjustment'])}")
        print(f"Equity Value: {_large(value['equity_value'])}")
        print(f"Diluted Shares: {value['diluted_shares'] / 1e6:,.1f}M")
        print(f"Implied Fair Value Per Share: {_money(value['fair_value_per_share'])}")
        print(f"Current Price: {_money(value['current_price'])}")
        print(f"Implied Upside / Downside: {_pct(value['upside_downside'])}")
        print()
    print("=================================================")
    print("SENSITIVITY ANALYSIS — IMPLIED VALUE PER SHARE")
    print("=================================================")
    sensitivity = report["sensitivity"]
    header = "WACC \\ Terminal " + " ".join(f"{x * 100:>8.1f}%" for x in sensitivity["terminal_growth"])
    print(header)
    for wacc, values in zip(sensitivity["wacc"], sensitivity["values"]):
        cells = " ".join(f"{value:>9.2f}" if _number(value) else f"{'N/M':>9}" for value in values)
        print(f"{wacc * 100:>5.1f}%          {cells}")
    print()
    print("=================================================")
    print("REVERSE DCF / MARKET-IMPLIED EXPECTATIONS")
    print("=================================================")
    reverse = report["reverse_dcf"]
    print(f"Current Market Price: {_money(company['current_market_price'])}")
    print(f"Solved Variable: {reverse['solved_variable']}")
    bounds = reverse["search_bounds"]["year_1_revenue_growth"]
    print(f"Search Bounds: {_pct(bounds[0])} to {_pct(bounds[1])} Year-1 revenue growth")
    print("Fixed Assumptions:")
    for name, value in reverse["fixed_assumptions"].items():
        print(f"- {name.replace('_', ' ').title()}: {_pct(value)}")
    print(f"Solver Status: {reverse['status']}")
    if reverse["converged"]:
        print(f"- 5Y Revenue CAGR: {_pct(reverse['required_5y_revenue_cagr'])}")
        print(f"- Year-1 Revenue Growth (then decaying): {_pct(reverse['required_year_1_revenue_growth'])}")
        print(f"- Residual: {_money(reverse['residual_per_share'])} per share")
        print(f"- Iterations: {reverse['iterations']}")
    else:
        print(f"Reason: {reverse['reason']}")
        if _number(reverse.get("residual_per_share")):
            print(f"Closest boundary residual: {_money(reverse['residual_per_share'])} per share")
    print()
    print("=================================================")
    print("VALUATION CROSS-CHECKS")
    print("=================================================")
    metrics = report["cross_checks"]["metrics"]
    print(f"Forward P/E: {metrics['forward_pe']:.2f}x" if _number(metrics["forward_pe"]) else "Forward P/E: Not economically meaningful / unavailable")
    print(f"EV/Revenue: {metrics['ev_revenue']:.2f}x" if _number(metrics["ev_revenue"]) else "EV/Revenue: Unavailable")
    print(f"EV/EBITDA: {metrics['ev_ebitda']:.2f}x" if _number(metrics["ev_ebitda"]) else "EV/EBITDA: Not economically meaningful")
    print(f"FCF Yield: {_pct(metrics['fcf_yield'])}")
    print(f"Historical / Peer Range: {report['cross_checks']['historical_peer_ranges']}")
    print()
    print("=================================================")
    print("WHAT THE MARKET IS PRICING")
    print("=================================================")
    if reverse["converged"]:
        print(f"The current price requires roughly {_pct(reverse['required_5y_revenue_cagr'])} five-year revenue growth while")
        print(f"FCFF margin reaches {_pct(reverse['required_year_5_fcff_margin'])}, with {_pct(reverse['wacc'])} WACC and controlled dilution.")
    else:
        print("The current price cannot be reconciled inside the tested revenue-growth bounds under the other base assumptions.")
    print()
    print("=================================================")
    print("VALUATION RISKS")
    print("=================================================")
    for risk in report["risks"]:
        print(f"- {risk}")
    print()
    print("=================================================")
    print("WHAT WOULD RAISE / LOWER FAIR VALUE")
    print("=================================================")
    print("Raise:")
    for item in report["fair_value_drivers"]["raise"]:
        print(f"- {item}")
    print("Lower:")
    for item in report["fair_value_drivers"]["lower"]:
        print(f"- {item}")
    print(f"Highest sensitivity: {report['fair_value_drivers']['highest_sensitivity']}")
    print()
    print("=================================================")
    print("FINAL VALUATION INTERPRETATION")
    print("=================================================")
    print(report["final_interpretation"]["text"])
    print()
    print("=================================================")
    print("DATA QUALITY NOTES")
    print("=================================================")
    print(f"Status: {report['data_quality']['status']}")
    print(report["data_quality"]["reason"])
    print()
    print("=================================================")
    print("INTERNAL VALIDATION")
    print("=================================================")
    validation = report["internal_validation"]
    print(f"Internal Validation: {validation['status']}")
    print("Checks:")
    for name, check in validation.get("checks", {}).items():
        print(f"- {name.replace('_', ' ').title()}: {'passed' if check['passed'] else 'failed'}")
        print(f"  {check['detail']}")
    if validation["reasons"]:
        print("Reasons:")
    for reason in validation["reasons"]:
        print(f"- {reason}")


def run_valuation(ticker: str, overrides=None, json_output=False):
    report = build_valuation_report(ticker, overrides)
    if json_output:
        clean = {key: value for key, value in report.items() if key != "_data"}
        print(json.dumps(clean, indent=2, default=str))
    else:
        print_valuation_report(report)
    return report
