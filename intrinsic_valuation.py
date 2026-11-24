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


UNFILED_KEY_ROWS = {"income": ("Total Revenue", "Operating Revenue"), "cashflow": ("Operating Cash Flow", "Total Cash From Operating Activities")}


def drop_unfiled_periods(income, cashflow, balance):
    """Checklist 9.1: drop fiscal years the provider lists before the annual report is filed.

    Yahoo adds a column for a fiscal year as soon as it ends, with only a few rows filled. A period
    counts as unfiled when its revenue (income statement) or operating cash flow (cash-flow
    statement) is missing. The same period dates are dropped from all three statements, so every
    row still starts at the same fiscal year. Returns the frames and the dropped dates.
    """
    unfiled = set()
    for frame, key in ((income, "income"), (cashflow, "cashflow")):
        if frame is None or frame.empty:
            continue
        row = next((name for name in UNFILED_KEY_ROWS[key] if name in frame.index), None)
        if row is None:
            continue
        unfiled.update(column for column in frame.columns if not _number(frame.at[row, column]))

    def keep(frame):
        if frame is None or frame.empty or not unfiled:
            return frame
        kept = [column for column in frame.columns if column not in unfiled]
        return frame.loc[:, kept] if kept else None

    dates = sorted(str(getattr(column, "date", lambda: column)()) for column in unfiled)
    return keep(income), keep(cashflow), keep(balance), dates


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


def _money_prefix(currency: str | None = None) -> str:
    return "$" if not currency or currency == "USD" else f"{currency} "


def _large(value, currency: str | None = None):
    if not _number(value):
        return "Unavailable"
    prefix = _money_prefix(currency)
    for scale, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= scale:
            return f"{prefix}{value / scale:,.2f}{suffix}"
    return f"{prefix}{value:,.0f}"


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


# Checklist 11.5: card networks (Visa, Mastercard) sit in Yahoo's "Credit Services" industry but carry no
# loan book or deposits, so the bank framework does not fit; lenders in the same industry (AmEx, Capital One,
# SoFi) keep it. Both conditions are read from the business summary.
PAYMENT_NETWORK_TERMS = ("transaction processing", "payments technology company", "payment network")
BALANCE_SHEET_TERMS = ("loan", "lending", "savings account", "checking account", "bank holding", "national association")


def is_payment_network(info: dict) -> bool:
    industry = str(_pick(info, "industry", default="")).lower()
    summary = str(_pick(info, "longBusinessSummary", default="")).lower()
    return (industry == "credit services" and any(term in summary for term in PAYMENT_NETWORK_TERMS)
            and not any(term in summary for term in BALANCE_SHEET_TERMS))


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
    if (sector == "financial services" or any(term in industry for term in ("bank", "insurance", "capital markets"))) and not is_payment_network(info):
        return "FINANCIAL_INSTITUTION"
    # Checklist 9.3: semiconductor equipment follows the chipmaker capex cycle.
    cyclical_terms = ("memory", "steel", "copper", "aluminum", "oil & gas", "commodity", "mining", "semiconductor equipment")
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


def _growth_inputs(symbol, info, revenue):
    """Checklist 9.2: trailing-12-month growth from SEC filings, with the basis stated."""
    try:
        from growth_inputs import revenue_growth_inputs
        return revenue_growth_inputs(symbol, info, revenue)
    except Exception as exc:  # noqa: BLE001
        return {"selected_growth": None, "basis": f"growth inputs failed: {type(exc).__name__}: {exc}"}


# Checklist 11.2: Yahoo's free statements omit some rows (share-based pay at CAT and WMT, interest
# expense at CRM). The filed 10-K value for the same fiscal year is read from SEC company facts
# (already fetched for growth inputs). A field that is not filed stays missing; it never becomes zero.
SEC_FALLBACK_CONCEPTS = {
    "sbc": ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
    "interest_expense": ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense"),
}


def _period_end(frame) -> str | None:
    try:
        return str(frame.columns[0].date())
    except (AttributeError, IndexError, TypeError):
        return None


def sec_annual_value(facts: dict, concepts: tuple[str, ...], period_end: str | None) -> tuple[str | None, float | None]:
    """The 10-K value of the first concept with a full-year row ending on ``period_end``."""
    if not period_end:
        return None, None
    taxonomy = (facts or {}).get("facts", {}).get("us-gaap", {})
    end = dt.date.fromisoformat(period_end)
    for concept in concepts:
        rows = [row for row in taxonomy.get(concept, {}).get("units", {}).get("USD", [])
                if str(row.get("form", "")).startswith("10-K") and row.get("end") == period_end and row.get("start")
                and 350 <= (end - dt.date.fromisoformat(row["start"])).days <= 380 and _number(row.get("val"))]
        if rows:
            return concept, float(rows[-1]["val"])
    return None, None


def _sec_fallback(symbol: str, needed: dict[str, str | None], facts_loader=None) -> dict[str, tuple[str, float]]:
    """``needed`` maps field -> fiscal period end. Returns field -> (concept, value) for what was filed."""
    if not needed:
        return {}
    try:
        if facts_loader is None:
            from growth_inputs import sec_facts as facts_loader
        facts = facts_loader(symbol)
    except Exception:  # noqa: BLE001 - no SEC facts means the field stays missing
        return {}
    found = {}
    for field_name, period_end in needed.items():
        concept, value = sec_annual_value(facts, SEC_FALLBACK_CONCEPTS[field_name], period_end)
        if concept is not None:
            found[field_name] = (concept, value)
    return found


def collect_valuation_data(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    ticker_obj = yf.Ticker(symbol)
    info = _info(ticker_obj)
    income = _statement(ticker_obj, "income_stmt", "financials")
    cashflow = _statement(ticker_obj, "cashflow")
    balance = _statement(ticker_obj, "balance_sheet")
    income, cashflow, balance, unfiled_periods = drop_unfiled_periods(income, cashflow, balance)

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
    depreciation = _row(cashflow, "Depreciation And Amortization", "Depreciation", "Depreciation Amortization Depletion")
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
    latest_debt = debt[0] if debt else _pick(info, "totalDebt")
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
    latest_sbc = sbc[0] if sbc else None
    needed = {}
    if not _number(latest_sbc):
        needed["sbc"] = _period_end(cashflow)
    if not _number(latest_interest_expense):
        needed["interest_expense"] = _period_end(income)
    filed = _sec_fallback(symbol, needed)
    input_sources = {}
    if "sbc" in filed:
        latest_sbc = filed["sbc"][1]
        input_sources["sbc"] = f"SEC 10-K {filed['sbc'][0]} (fiscal year ending {needed['sbc']})"
    if "interest_expense" in filed:
        latest_interest_expense = abs(filed["interest_expense"][1])
        input_sources["interest_expense"] = f"SEC 10-K {filed['interest_expense'][0]} (fiscal year ending {needed['interest_expense']})"
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
        "unfiled_periods_skipped": unfiled_periods,
        "growth_inputs": _growth_inputs(symbol, info, revenue),
        "operating_income_history": operating_income,
        "gross_profit_history": gross_profit,
        "latest_revenue": latest_revenue,
        "latest_operating_income": latest_op_income,
        "latest_net_income": net_income[0] if net_income else None,
        "latest_ocf": latest_ocf,
        "latest_capex": latest_capex,
        "latest_fcf": latest_fcf,
        "latest_fcff": latest_fcff,
        "sbc": latest_sbc,
        "input_sources": input_sources,
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
        "debt": latest_debt if _number(latest_debt) else None,
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
    if not _number(data.get("debt")):
        missing.append("verified total debt (missing is not zero)")
    if not _number(data["latest_revenue"]) or data["latest_revenue"] <= 0:
        missing.append("latest annual revenue")
    if not _number(data["latest_fcff"]):
        missing.append("operating income or free cash flow")
    if not _number(data["shares"]) or data["shares"] <= 0:
        missing.append("diluted shares outstanding")
    return missing


def _risk_free() -> tuple[float, str]:
    risk_free = None
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if hist is not None and not hist.empty:
            risk_free = float(hist["Close"].dropna().iloc[-1]) / 100
    except Exception:
        pass
    if not _number(risk_free):
        return 0.043, "transparent fallback: 4.3% US 10Y proxy"
    return risk_free, "Yahoo Finance US 10Y Treasury (^TNX), latest close"


def _cost_of_equity(data: dict) -> dict:
    risk_free, rf_source = _risk_free()
    beta = data["beta"] if _number(data.get("beta")) and 0.25 <= data["beta"] <= 3 else 1.0
    beta_source = "Yahoo Finance beta" if beta == data.get("beta") else "fallback beta of 1.0"
    erp = 0.045
    return {"risk_free_rate": risk_free, "risk_free_source": rf_source, "beta": beta, "beta_source": beta_source,
            "equity_risk_premium": erp, "cost_of_equity": risk_free + beta * erp}


def _market_rates(data: dict) -> dict:
    equity_inputs = _cost_of_equity(data)
    risk_free, rf_source = equity_inputs["risk_free_rate"], equity_inputs["risk_free_source"]
    beta, beta_source = equity_inputs["beta"], equity_inputs["beta_source"]
    erp = equity_inputs["equity_risk_premium"]
    cost_equity = equity_inputs["cost_of_equity"]
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


DEFAULT_SCENARIO_SPREADS = {
    "bear": {"growth": -0.04, "margin": -0.04, "wacc": 0.01, "terminal": -0.005, "dilution": 0.005, "multiple": -2.0},
    "base": {"growth": 0, "margin": 0, "wacc": 0, "terminal": 0, "dilution": 0, "multiple": 0},
    "bull": {"growth": 0.04, "margin": 0.04, "wacc": -0.01, "terminal": 0.005, "dilution": -0.001, "multiple": 2.0},
}


def _scenario_assumptions(data, rates, overrides, spreads=None) -> dict[str, list[Assumption]]:
    base = _base_parameters(data, rates)
    sbc_policy = data.get("sbc_policy", SBC_ACCOUNTING_POLICY)
    spreads = spreads or DEFAULT_SCENARIO_SPREADS
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


# ---- Checklist 7.5: scenario spreads from the company's own history (default since owner approval 2026-11-22) ----
SPREAD_BOUNDS = {"growth": (0.02, 0.10), "margin": (0.02, 0.08)}


def _stdev(values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def company_scenario_spreads(data):
    """Growth and margin spreads from the standard deviation of the company's annual history.

    Revenue growth: standard deviation of year-on-year growth across the available fiscal
    years, bounded to 2-10 points. Margin: standard deviation of free-cash-flow margin (a
    stated proxy for FCFF margin, whose history is not reconstructed), bounded to 2-8 points.
    Fewer than four fiscal years keeps the default +/-4 points for that input. WACC, terminal
    growth, dilution and exit-multiple spreads are unchanged.
    """
    revenues = [value for value in (data.get("revenue_history") or []) if _number(value)]
    if len(revenues) < 4:
        return None, {"reason": f"{len(revenues)} fiscal years of revenue; at least four are needed. Default spreads kept."}
    growth = [revenues[index] / revenues[index + 1] - 1 for index in range(len(revenues) - 1) if revenues[index + 1] > 0]
    fcf = _row(data.get("cashflow"), "Free Cash Flow")
    margins = [value / revenue for value, revenue in zip(fcf, revenues) if _number(value) and revenue > 0]
    growth_spread = _clamp(_stdev(growth), *SPREAD_BOUNDS["growth"]) if _stdev(growth) is not None else 0.04
    margin_spread = _clamp(_stdev(margins), *SPREAD_BOUNDS["margin"]) if len(margins) >= 4 and _stdev(margins) is not None else 0.04
    spreads = {name: dict(values) for name, values in DEFAULT_SCENARIO_SPREADS.items()}
    spreads["bear"].update(growth=-growth_spread, margin=-margin_spread)
    spreads["bull"].update(growth=growth_spread, margin=margin_spread)
    return spreads, {
        "fiscal_years": len(revenues), "growth_history": growth, "fcf_margin_history": margins,
        "growth_spread": growth_spread, "margin_spread": margin_spread,
        "margin_basis": "free-cash-flow margin history" if len(margins) >= 4 else "default 4 points (fewer than four FCF margins)",
    }


def scenario_spread_record(data, rates, overrides, spreads, basis):
    """What the scenarios used: company-history spreads when available, otherwise the +/-4-point defaults.

    The +/-4-point values are computed beside them so the change stays visible (checklist 7.5).
    """
    record = {"source": "COMPANY_HISTORY" if spreads is not None else "DEFAULT", "basis": basis,
              "spreads": {name: {key: (spreads or DEFAULT_SCENARIO_SPREADS)[name][key] for key in ("growth", "margin")} for name in ("bear", "bull")}}
    if spreads is None:
        return record
    try:
        legacy = {name: _dcf(data, items)["fair_value_per_share"] for name, items in _scenario_assumptions(data, rates, overrides).items()}
    except ValueError as exc:
        return {**record, "default_spread_fair_value": None, "default_spread_reason": str(exc)}
    return {**record, "default_spread_fair_value": legacy,
            "note": "Bear/bull growth and margin spreads come from the company's own history; the +/-4-point values are shown for comparison."}


# ---- Checklist 7.6: longer explicit period for fast growers, phased in above the cap ----
GROWTH_CAPS = {"MATURE_OPERATING_COMPANY": 0.18, "GROWTH_SOFTWARE_COMPANY": 0.35, "CYCLICAL_COMPANY": 0.08}
EXTENDED_POLICY = {"years": 10, "first_year_growth_cap": 0.50, "decay": "linear"}
# Owner decision (2026-11-21): the ten-year model is phased in by how far observed growth exceeds
# the type cap, so there is no jump at the cap. Weight 0 at the cap, 1 at cap + PHASE_IN_BAND.
PHASE_IN_BAND = 0.10


def extended_weight(observed_growth, cap):
    """Share of the ten-year model in the headline value: 0 at or below the cap, linear to 1 at cap + band."""
    if not _number(observed_growth) or cap is None:
        return 0.0
    return _clamp((observed_growth - cap) / PHASE_IN_BAND, 0.0, 1.0)


def _dcf_extended(data, assumptions, first_growth, years=10, decay="linear"):
    """Like _dcf, but with `years` explicit years; growth decays from first_growth to terminal growth.

    decay="linear" reaches terminal growth in the final year; decay="front_loaded" halves the
    gap to terminal growth each year. FCFF margin moves linearly from today's margin to the same
    target margin as the five-year model. Terminal value, the enterprise-to-equity bridge and
    dilution follow _dcf exactly, compounded over `years`.
    """
    target_margin = _assumption_value(assumptions, "year_5_fcff_margin")
    wacc = _assumption_value(assumptions, "wacc")
    terminal_growth = _assumption_value(assumptions, "terminal_growth")
    dilution = _assumption_value(assumptions, "annual_dilution")
    if wacc - terminal_growth <= 0:
        raise ValueError("WACC must exceed terminal growth.")
    revenue = data["latest_revenue"]
    current_margin = data["latest_fcff"] / revenue
    forecast, pv_fcff = [], 0.0
    for year in range(1, years + 1):
        if decay == "front_loaded":
            growth = terminal_growth + (first_growth - terminal_growth) * (0.5 ** (year - 1))
        else:
            growth = first_growth + (terminal_growth - first_growth) * ((year - 1) / (years - 1))
        margin = current_margin + (target_margin - current_margin) * (year / years)
        revenue *= 1 + growth
        fcff = revenue * margin
        present = fcff / ((1 + wacc) ** year)
        pv_fcff += present
        forecast.append({"year": year, "revenue_growth": growth, "revenue": revenue, "fcff_margin": margin, "fcff": fcff, "present_value": present})
    terminal_value = forecast[-1]["fcff"] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** years)
    enterprise_value = pv_fcff + pv_terminal
    net_cash = data["cash"] - data["debt"]
    other_senior_claims = data.get("other_senior_claims", 0)
    equity_value = enterprise_value + net_cash - other_senior_claims
    diluted_shares = data["shares"] * ((1 + dilution) ** years)
    return {"forecast": forecast, "pv_forecast_fcff": pv_fcff, "terminal_value": terminal_value, "pv_terminal_value": pv_terminal,
            "enterprise_value": enterprise_value, "net_cash_debt_adjustment": net_cash, "other_senior_claims": other_senior_claims,
            "equity_value": equity_value, "diluted_shares": diluted_shares, "fair_value_per_share": equity_value / diluted_shares}


def _extended_checks(data, result, assumptions):
    wacc = _assumption_value(assumptions, "wacc")
    years = len(result["forecast"])
    arithmetic = abs(sum(row["present_value"] for row in result["forecast"]) - result["pv_forecast_fcff"]) < 1e-6 * max(1.0, abs(result["pv_forecast_fcff"]))
    terminal = abs(result["pv_terminal_value"] - result["terminal_value"] / ((1 + wacc) ** years)) < 1e-6 * max(1.0, abs(result["terminal_value"]))
    ev = abs(result["enterprise_value"] - result["pv_forecast_fcff"] - result["pv_terminal_value"]) < 1e-6 * max(1.0, abs(result["enterprise_value"]))
    bridge = abs(result["equity_value"] - (result["enterprise_value"] + result["net_cash_debt_adjustment"] - result["other_senior_claims"])) < 1e-6 * max(1.0, abs(result["equity_value"]))
    shares = abs(result["fair_value_per_share"] * result["diluted_shares"] - result["equity_value"]) < 1e-6 * max(1.0, abs(result["equity_value"]))
    return {"forecast_arithmetic": arithmetic, "terminal_value": terminal, "enterprise_value": ev, "ev_to_equity_bridge": bridge, "share_conversion": shares,
            "wacc_above_terminal": wacc > _assumption_value(assumptions, "terminal_growth")}


def _extended_reverse(data, base_items, years, decay):
    """Solve first-year growth on the extended model; same bounds and boundary rule as _reverse_dcf."""
    if not _number(data.get("price")) or data["price"] <= 0 or not _number(data.get("latest_fcff")) or data["latest_fcff"] <= 0:
        return {"converged": False, "status": "NOT_RUN"}
    low, high = REVERSE_GROWTH_BOUNDS
    value = lambda growth: _dcf_extended(data, base_items, growth, years, decay)["fair_value_per_share"] - data["price"]
    low_value, high_value = value(low), value(high)
    if low_value * high_value > 0:
        return {"converged": False, "status": "NO_ECONOMIC_SOLUTION", "low_case_value": low_value + data["price"], "high_case_value": high_value + data["price"]}
    for _ in range(80):
        mid = (low + high) / 2
        difference = value(mid)
        if abs(difference) <= REVERSE_TOLERANCE_PER_SHARE:
            break
        if difference * low_value <= 0:
            high = mid
        else:
            low, low_value = mid, difference
    if min(abs(mid - bound) for bound in REVERSE_GROWTH_BOUNDS) < 1e-6:
        return {"converged": False, "status": "BOUNDARY_SOLUTION"}
    return {"converged": True, "status": "CONVERGED", "required_year_1_revenue_growth": mid}


def extended_horizon(data, assumptions, kind, spreads=None, observed_override=None):
    """Checklist 7.6: run only when observed growth exceeds the company type's first-year cap.

    observed_override (checklist 9.2): trailing-12-month growth, replacing Yahoo's one-quarter revenueGrowth.
    """
    observed = _pick(data["info"], "revenueGrowth") if observed_override is None else observed_override
    cap = GROWTH_CAPS.get(kind)
    if not _number(observed) or cap is None or observed <= cap:
        return {"state": "NOT_TRIGGERED", "observed_growth": observed, "type_cap": cap,
                "reason": "Observed growth is within the five-year model's cap; the existing valuation applies unchanged."}
    years, decay = EXTENDED_POLICY["years"], EXTENDED_POLICY["decay"]
    first = min(observed, EXTENDED_POLICY["first_year_growth_cap"])
    # Same growth spreads as the five-year scenarios (company history when available, checklist 7.5).
    deltas = {name: (spreads or DEFAULT_SCENARIO_SPREADS)[name]["growth"] for name in ("bear", "base", "bull")}
    scenarios, checks, forecasts = {}, {}, {}
    try:
        for name, items in assumptions.items():
            result = _dcf_extended(data, items, first + deltas[name], years, decay)
            scenarios[name] = result["fair_value_per_share"]
            forecasts[name] = result["forecast"]
            checks[name] = _extended_checks(data, result, items)
        base = assumptions["base"]
        wacc_item = next(item for item in base if item.name == "wacc")
        bumped = []
        for shift in (-0.01, 0.0, 0.01):
            cloned = [Assumption(**asdict(item)) for item in base]
            next(item for item in cloned if item.name == "wacc").value = wacc_item.value + shift
            bumped.append(_dcf_extended(data, cloned, first, years, decay)["fair_value_per_share"])
        sensitivity = {
            "first_year_growth_cap": {str(level): _dcf_extended(data, base, min(observed, level), years, decay)["fair_value_per_share"] for level in (0.40, 0.50, 0.60)},
            "explicit_years": {str(length): _dcf_extended(data, base, first, length, decay)["fair_value_per_share"] for length in (8, 10, 12)},
            "decay": {shape: _dcf_extended(data, base, first, years, shape)["fair_value_per_share"] for shape in ("linear", "front_loaded")},
            "wacc_minus_1pp_base_plus_1pp": bumped,
        }
    except ValueError as exc:
        return {"state": "INVALID", "reason": str(exc)}
    passed = all(all(item.values()) for item in checks.values()) and scenarios["bear"] <= scenarios["base"] <= scenarios["bull"] and bumped[0] > bumped[1] > bumped[2]
    return {
        "state": "COMPUTED", "default": False, "observed_growth": observed, "type_cap": cap, "first_year_growth": first,
        "weight": extended_weight(observed, cap),
        "policy": dict(EXTENDED_POLICY), "fair_value": scenarios, "base_forecast": forecasts.get("base"), "checks": checks, "checks_passed": passed,
        "reverse_dcf": _extended_reverse(data, assumptions["base"], years, decay), "sensitivity": sensitivity,
        "assumptions_to_state": "First-year growth cap (50%), linear decay to terminal growth and a 10-year explicit period are model policy without calibration; see sensitivity.",
        "note": "Ten-year values at full weight; the headline fair value blends them with the five-year values by `weight` (see report['fair_value']).",
    }


def _blended_reverse(data, base_items, weight, years, decay):
    """Solve year-1 growth so that (1 - weight) x five-year value + weight x ten-year value equals the price.

    Same bounds, tolerance and boundary rule as _reverse_dcf. Both models take year-1 revenue growth
    as the solved variable; the reported five-year CAGR is the weighted CAGR of the two paths.
    """
    if not _number(data.get("price")) or data["price"] <= 0 or not _number(data.get("latest_fcff")) or data["latest_fcff"] <= 0:
        return {"converged": False, "status": "NOT_RUN", "weight": weight}

    def blended(growth):
        five = _dcf(data, base_items, forced_growth=growth)
        ten = _dcf_extended(data, base_items, growth, years, decay)
        return five, ten, (1 - weight) * five["fair_value_per_share"] + weight * ten["fair_value_per_share"]

    low, high = REVERSE_GROWTH_BOUNDS
    low_value, high_value = blended(low)[2] - data["price"], blended(high)[2] - data["price"]
    base = {"solved_variable": "Year-1 revenue growth on the phased model", "weight": weight}
    if low_value * high_value > 0:
        return {**base, "converged": False, "status": "NO_ECONOMIC_SOLUTION", "low_case_value": low_value + data["price"], "high_case_value": high_value + data["price"]}
    difference = None
    for _ in range(80):
        mid = (low + high) / 2
        difference = blended(mid)[2] - data["price"]
        if abs(difference) <= REVERSE_TOLERANCE_PER_SHARE:
            break
        if difference * low_value <= 0:
            high = mid
        else:
            low, low_value = mid, difference
    if difference is None or abs(difference) > REVERSE_TOLERANCE_PER_SHARE:
        return {**base, "converged": False, "status": "NON_CONVERGENT", "residual_per_share": difference}
    if min(abs(mid - bound) for bound in REVERSE_GROWTH_BOUNDS) < 1e-6:
        return {**base, "converged": False, "status": "BOUNDARY_SOLUTION", "residual_per_share": difference}
    five, ten, _ = blended(mid)
    five_cagr = (five["forecast"][-1]["revenue"] / data["latest_revenue"]) ** (1 / 5) - 1
    ten_cagr = (ten["forecast"][4]["revenue"] / data["latest_revenue"]) ** (1 / 5) - 1
    return {**base, "converged": True, "status": "CONVERGED", "required_year_1_revenue_growth": mid,
            "required_5y_revenue_cagr": (1 - weight) * five_cagr + weight * ten_cagr,
            "five_year_model_5y_cagr": five_cagr, "ten_year_model_first_5y_cagr": ten_cagr, "residual_per_share": difference}


def headline_growth(data):
    """Checklist 9.2 (owner decision 2026-11-22): the phase-in reads trailing-12-month growth.

    Falls back to Yahoo's one-quarter revenueGrowth only when growth inputs were not collected
    (offline data); the basis is always returned.
    """
    growth = data.get("growth_inputs") or {}
    if growth.get("selected_growth") is not None:
        return growth["selected_growth"], growth.get("basis")
    return None, "Yahoo one-quarter revenue growth (twelve-month growth not collected)"


def one_quarter_legacy(data, assumptions, kind, spreads, scenarios, reverse):
    """The pre-9.2 headline (one-quarter growth, no cyclical rule), kept for comparison only."""
    extended = extended_horizon(data, assumptions, kind, spreads)
    return {"default": False, **phased_fair_value(data, assumptions, scenarios, extended, reverse),
            "note": "Previous headline: Yahoo one-quarter revenue growth, cyclical companies not excluded. Comparison only."}


def phased_fair_value(data, assumptions, scenarios, extended, reverse, kind=None):
    """Headline fair value (checklist 7.6, owner decision): five-year values, blended with the ten-year values above the cap.

    kind="CYCLICAL_COMPANY" (owner decision 2026-11-22): no blending; high growth in a cyclical is
    cycle position, and extending it for ten years would value the peak.
    """
    five = {name: scenarios[name]["fair_value_per_share"] for name in ("bear", "base", "bull")}
    output = {"five_year": five, "phase_in_band": PHASE_IN_BAND, "type_cap": extended.get("type_cap"), "observed_growth": extended.get("observed_growth")}
    if extended.get("state") != "COMPUTED":
        return {**output, "method": "FIVE_YEAR", "extended_weight": 0.0, "fair_value": dict(five), "reverse_dcf": reverse,
                "reason": extended.get("reason") or "Ten-year model not computed; five-year values apply."}
    if not extended.get("checks_passed"):
        return {**output, "method": "FIVE_YEAR", "extended_weight": 0.0, "fair_value": dict(five), "reverse_dcf": reverse, "ten_year": extended["fair_value"],
                "reason": "Ten-year model failed its arithmetic, ordering or WACC checks; five-year values apply."}
    if kind == "CYCLICAL_COMPANY":
        return {**output, "method": "FIVE_YEAR", "extended_weight": 0.0, "fair_value": dict(five), "reverse_dcf": reverse, "ten_year": extended["fair_value"],
                "reason": "Cyclical company: the ten-year model is not blended in, so cycle-high growth is not extended (owner decision 2026-11-22)."}
    weight = extended["weight"]
    ten = extended["fair_value"]
    blended = {name: (1 - weight) * five[name] + weight * ten[name] for name in five}
    blended_reverse = _blended_reverse(data, assumptions["base"], weight, EXTENDED_POLICY["years"], EXTENDED_POLICY["decay"]) if weight > 0 else reverse
    return {**output, "method": "PHASED" if weight > 0 else "FIVE_YEAR", "extended_weight": weight, "fair_value": blended, "ten_year": ten,
            "ten_year_forecast": extended.get("base_forecast"),
            "reverse_dcf": blended_reverse,
            "reason": f"Observed growth {extended['observed_growth']:.1%} vs cap {extended['type_cap']:.0%}: ten-year model weighted {weight:.0%}, five-year {1 - weight:.0%}."}


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


# Checklist 12.2 (owner approval 2026-11-23): banks are read by what the price assumes about return on equity.
# Single-stage justified price-to-book: P/B = (ROE - g) / (COE - g), so the sustained ROE the price implies is
# g + P/B x (COE - g). COE = 10Y Treasury + beta x 4.5% and g = 2.5%, the same conventions as the company DCF.
# Book value and ROE come from the annual statements; anything missing leaves the reading unavailable.
BANK_LONG_RUN_GROWTH = 0.025


def bank_implied_roe(data: dict, cost_of_equity: dict | None = None) -> dict:
    equity = _row(data.get("balance"), "Common Stock Equity", "Stockholders Equity")
    income = _row(data.get("income"), "Net Income Common Stockholders", "Net Income")
    market_cap = data.get("market_cap")
    missing = [name for name, ok in (("common equity (two years)", len(equity) >= 2 and equity[0] > 0 and equity[1] > 0),
                                     ("net income to common", bool(income)), ("market capitalisation", _number(market_cap) and market_cap > 0)) if not ok]
    if missing:
        return {"status": "UNAVAILABLE", "missing": missing}
    rates = cost_of_equity or _cost_of_equity(data)
    coe, g = rates["cost_of_equity"], BANK_LONG_RUN_GROWTH
    roe = income[0] / ((equity[0] + equity[1]) / 2)
    price_to_book = market_cap / equity[0]
    implied = g + price_to_book * (coe - g)
    return {"status": "AVAILABLE", "price_to_book": price_to_book, "latest_roe": roe, "implied_roe": implied,
            "cost_of_equity": coe, "beta": rates["beta"], "risk_free_rate": rates["risk_free_rate"], "long_run_growth": g,
            "method": "Justified P/B = (ROE - g) / (COE - g); implied ROE = g + P/B x (COE - g)",
            "basis": "Latest annual net income to common over average common equity; P/B from current market cap over latest common equity."}


# Checklist 12.3 (owner approval 2026-11-23): an ADR whose accounts are in another currency is valued at company
# level. The market value is the provider's quote-currency market cap converted at the latest FX rate, divided by
# the same share count the statements use, so no ADR ratio is needed; per-share results convert back to the quote
# by one factor (quote price / price per model share).
def _fx_rate(base: str, quote: str) -> tuple[float | None, str | None]:
    try:
        hist = yf.Ticker(f"{base}{quote}=X").history(period="5d")
        if hist is not None and not hist.empty:
            close = hist["Close"].dropna()
            return float(close.iloc[-1]), str(close.index[-1].date())
    except Exception:
        pass
    return None, None


def _company_level_bridge(data: dict, fx_loader=None) -> dict | None:
    info = data.get("info") or {}
    financial = info.get("financialCurrency")
    quote = info.get("currency") or data.get("currency")
    market_cap, shares, quote_price = data.get("market_cap"), data.get("shares"), data.get("price")
    if not (financial and quote and financial != quote and _number(market_cap) and market_cap > 0
            and _number(shares) and shares > 0 and _number(quote_price) and quote_price > 0):
        return None
    fx, fx_date = (fx_loader or _fx_rate)(financial, quote)
    if not _number(fx) or fx <= 0:
        return None
    market_cap_financial = market_cap / fx
    price_financial = market_cap_financial / shares
    bridge = {"method": "COMPANY_LEVEL", "financial_currency": financial, "quote_currency": quote,
              "fx_pair": f"{financial}{quote}", "fx": fx, "fx_date": fx_date, "market_cap_quote": market_cap,
              "market_cap_financial": market_cap_financial, "shares": shares, "quote_price": quote_price,
              "price_per_model_share": price_financial, "quote_per_model_share": quote_price / price_financial,
              "note": (f"Valued at company level in {financial}: market cap {quote} {market_cap / 1e9:,.0f}B at {fx:.5f} {quote}/{financial}. "
                       f"Per-share figures are per statement share ({financial} {price_financial:,.2f} at today's price) and convert to the quoted price by one factor.")}
    return {**data, "price": price_financial, "market_cap": market_cap_financial, "currency": financial, "_unit_bridge": bridge}


# Checklist 12.1 (owner approval 2026-11-23): when the two measures of last year's FCFF disagree by more than
# the tolerance, the question is whether the answer depends on which one is used. Both are run; the report keeps
# the operating-profit base (unchanged method) and carries the cash-flow-statement run alongside, and the
# judgment card publishes only a conclusion that holds on both. Formulas and the tolerance are unchanged;
# missing inputs or a non-positive measure still withhold.
def _two_bases_eligible(reconciliation: dict) -> bool:
    return (not reconciliation.get("missing") and _number(reconciliation.get("nopat_based_fcff"))
            and _number(reconciliation.get("cfo_based_fcff"))
            and reconciliation["nopat_based_fcff"] > 0 and reconciliation["cfo_based_fcff"] > 0)


def _scenario_values(report: dict) -> dict:
    return {name: (report.get("scenarios", {}).get(name) or {}).get("fair_value_per_share") for name in ("bear", "base", "bull")}


def _two_base_report(ticker: str, overrides: dict, data: dict, reconciliation: dict) -> dict:
    primary = build_valuation_report(ticker, overrides, {**data, "_fcff_base": "nopat"})
    alternate = build_valuation_report(ticker, overrides, {**data, "_fcff_base": "cfo"})
    nopat, cfo = reconciliation["nopat_based_fcff"], reconciliation["cfo_based_fcff"]
    gap = abs(nopat - cfo) / max(abs(nopat), abs(cfo))
    primary["cash_flow_bases"] = {
        "status": "MEASURES_DIFFER",
        "operating_profit_base": nopat,
        "cash_flow_statement_base": cfo,
        "gap_pct": gap,
        "tolerance": reconciliation.get("tolerance"),
        "shown_base": "operating_profit",
        "alternate": {
            "base": "cash_flow_statement",
            "reverse_dcf": alternate.get("reverse_dcf") or {},
            "fair_value": alternate.get("fair_value") or {},
            "scenarios": _scenario_values(alternate),
            "validation_status": (alternate.get("validation") or {}).get("status"),
        },
    }
    if (primary.get("validation") or {}).get("status") == "FAILED":
        return primary
    currency = data.get("currency")
    note = (
        f"Two measures of last year's free cash flow differ by {gap:.0%} (operating profit {_large(nopat, currency)}, "
        f"cash-flow statement {_large(cfo, currency)}; allowed gap {_large(reconciliation.get('tolerance'), currency)}). "
        "Both were run: this report uses the operating-profit base and carries the cash-flow-statement result alongside. "
    )
    quality = primary.get("data_quality") or {}
    primary["data_quality"] = {**quality, "status": "CASH_FLOW_MEASURES_DIFFER", "reason": note + str(quality.get("reason") or "")}
    validation = primary.get("validation") or {}
    if validation.get("status") == "PASSED":
        validation["status"] = "PROVISIONAL"
    validation.setdefault("reasons", []).append(note.strip())
    primary["validation"] = primary["internal_validation"] = validation
    return primary


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
            "currency": data.get("currency"),
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
        # Headline fair value (checklist 7.6); replaced once the scenarios are computed and validated.
        "fair_value": {"method": "WITHHELD", "fair_value": {}, "reason": "Fair value not calculated."},
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
        if kind == "FINANCIAL_INSTITUTION":
            bank = bank_implied_roe(data)
            report["bank_implied_roe"] = bank
            if bank["status"] == "AVAILABLE":
                report["data_quality"] = {"status": "BANK_IMPLIED_ROE", "missing": ["regulatory capital and payout history", "ROE history (one year used)"],
                                          "reason": (f"No cash-flow DCF for a bank. Price-to-book {bank['price_to_book']:.2f} with a {bank['cost_of_equity']:.1%} cost of equity "
                                                     f"implies a sustained ROE of {bank['implied_roe']:.1%}; the latest annual ROE is {bank['latest_roe']:.1%}.")}
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

    from security_units import valuation_unit_gate
    unit_gate = valuation_unit_gate(data) if not data.get("_unit_bridge") else {"status": "COMPANY_LEVEL", "passed": True, "reasons": [], "bridge": data["_unit_bridge"]}
    report["security_unit_validation"] = unit_gate
    if not unit_gate["passed"]:
        bridged = _company_level_bridge(data)
        if bridged is not None:
            result = build_valuation_report(ticker, overrides, bridged)
            result["unit_bridge"] = bridged["_unit_bridge"]
            quality = result.get("data_quality") or {}
            result["data_quality"] = {**quality, "reason": bridged["_unit_bridge"]["note"] + " " + str(quality.get("reason") or "")}
            return result
        reason = " ".join(unit_gate["reasons"])
        report["data_quality"] = {"status": "SECURITY_UNIT_AMBIGUITY", "reason": reason, "missing": ["validated security-unit bridge"]}
        report["validation"] = {"status": "FAILED", "checks": {"security_units": unit_gate}, "reasons": [reason]}
        report["internal_validation"] = report["validation"]
        report["final_interpretation"] = {"text": "Fair value withheld: " + reason}
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
    forced_base = data.get("_fcff_base")
    if reconciliation["status"] != "PASSED" and not forced_base and _two_bases_eligible(reconciliation):
        return _two_base_report(ticker, overrides, data, reconciliation)
    if reconciliation["status"] != "PASSED" and not forced_base:
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

    # The reconciled NOPAT construction is the historical FCFF forecast base (checklist 12.1: or the
    # cash-flow-statement measure when the two-base run asks for it).
    data["latest_fcff"] = reconciliation["cfo_based_fcff"] if forced_base == "cfo" else reconciliation["calculated_fcff"]

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
    spreads, spread_basis = company_scenario_spreads(data)
    assumptions = _scenario_assumptions(data, rates, overrides, spreads=spreads)
    scenarios = {name: _dcf(data, items) for name, items in assumptions.items()}
    sensitivity = _sensitivity(data, assumptions["base"])
    reverse = _reverse_dcf(data, assumptions["base"])
    validation = _validate(data, assumptions, scenarios, reverse, sensitivity, rates)
    validation["checks"]["historical_fcff_reconciliation"] = {
        "passed": reconciliation["status"] == "PASSED",
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
            + (
                f" Fiscal year(s) ending {', '.join(data['unfiled_periods_skipped'])} listed by the provider without filed figures; the latest filed year is used."
                if data.get("unfiled_periods_skipped")
                else ""
            )
            + (
                " Not in the Yahoo statements, read from the filing instead: "
                + "; ".join(f"{name.replace('_', ' ')} from {source}" for name, source in data["input_sources"].items()) + "."
                if data.get("input_sources")
                else ""
            )
        ),
        "input_sources": data.get("input_sources") or {},
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
    # Checklist 7.5: bear/bull spreads from the company's history. Checklist 7.6: the headline value phases in the ten-year model (report["fair_value"]).
    report["scenario_spreads"] = scenario_spread_record(data, rates, overrides, spreads, spread_basis)
    # Checklist 9.2 (owner decision 2026-11-22): twelve-month growth drives the phase-in; cyclicals are not blended.
    growth, growth_basis = headline_growth(data)
    report["extended_horizon"] = extended_horizon(data, assumptions, kind, spreads, observed_override=growth)
    report["fair_value"] = {**phased_fair_value(data, assumptions, scenarios, report["extended_horizon"], reverse, kind),
                            "growth_basis": growth_basis, "growth_inputs": data.get("growth_inputs")}
    report["fair_value_one_quarter_legacy"] = one_quarter_legacy(data, assumptions, kind, spreads, scenarios, reverse)
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
    headline = report["fair_value"]["fair_value"]
    base_value = headline["base"]
    report["final_interpretation"] = {
        "bear_to_bull_range": [headline["bear"], headline["bull"]],
        "base_fair_value": base_value,
        "text": (
            f"The explicit scenarios produce a fair-value range of "
            f"{_money_prefix(data.get('currency'))}{headline['bear']:,.2f}–{_money_prefix(data.get('currency'))}{headline['bull']:,.2f} per share, "
            f"with a {_money_prefix(data.get('currency'))}{base_value:,.2f} base-case estimate. "
            + (f"{report['fair_value']['reason']} " if report["fair_value"]["method"] == "PHASED" else "")
            + "This is a research estimate, not a recommendation, and is highly sensitive to discount rate, durable cash-flow margin, growth, and dilution."
        ),
    }
    report["validation"] = validation
    report["internal_validation"] = validation
    if validation["status"] == "FAILED":
        report["diagnostic_scenarios"] = report["scenarios"]
        report["scenarios"] = {}
        report["sensitivity"] = {}
        report["reverse_dcf"] = {"status": "VALIDATION_FAILED", "reason": "Critical valuation checks failed."}
        report["fair_value"] = {"method": "WITHHELD", "fair_value": {}, "reason": "Critical valuation checks failed."}
        report["fair_value_one_quarter_legacy"] = {"method": "WITHHELD", "default": False, "fair_value": {}, "reason": "Critical valuation checks failed."}
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
