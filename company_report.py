"""
Evidence-first company intelligence report.

This module builds a company-level report from operating evidence, valuation
evidence, price action, and narrative support. It avoids buy/sell language and
does not use black-box scores as the primary output.
"""

import contextlib
import datetime as dt
import io
import math

import yfinance as yf
from security_words import looks_like_shell

from company_economics import CompanySnapshot, SourceNature, build_company_economics, print_company_economics


def is_number(value):
    return isinstance(value, (int, float)) and not math.isnan(value)


def safe(info, *keys, default=None):
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return default


def pct(value):
    return f"{value * 100:.2f}%" if is_number(value) else "Unavailable"


def signed_pct(value):
    return f"{value * 100:+.2f}%" if is_number(value) else "Unavailable"


def signed_pp(value):
    return f"{value * 100:+.2f} percentage points" if is_number(value) else "Unavailable"


def fmt(value, decimals=2, prefix="", suffix=""):
    if not is_number(value):
        return "Unavailable"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def money(value):
    if not is_number(value):
        return "Unavailable"
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1e12:
        return f"{sign}${abs_value / 1e12:,.2f}T"
    if abs_value >= 1e9:
        return f"{sign}${abs_value / 1e9:,.2f}B"
    if abs_value >= 1e6:
        return f"{sign}${abs_value / 1e6:,.2f}M"
    return f"{sign}${abs_value:,.0f}"


def line():
    print("=================================================")


def fetch_info(ticker_obj):
    try:
        return ticker_obj.info or {}
    except Exception:
        return {}


def fetch_history(ticker, period="1y"):
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            hist = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if hist.empty:
            return None
        if hasattr(hist.columns, "levels"):
            hist.columns = hist.columns.get_level_values(0)
        return hist.dropna()
    except Exception:
        return None


def get_statement(ticker_obj, attrs):
    for attr in attrs:
        try:
            frame = getattr(ticker_obj, attr)
        except Exception:
            frame = None
        if frame is not None and not frame.empty:
            return frame
    return None


def row_values(frame, row_name):
    if frame is None or frame.empty or row_name not in frame.index:
        return []
    try:
        return [float(v) for v in frame.loc[row_name].dropna().tolist()]
    except Exception:
        return []


def ttm_and_prior(frame, row_name):
    values = row_values(frame, row_name)
    if len(values) >= 8:
        current = sum(values[:4])
        prior = sum(values[4:8])
        growth = current / prior - 1 if prior != 0 else None
        return current, prior, growth
    if len(values) >= 4:
        return sum(values[:4]), None, None
    return None, None, None


def _comparison_from_values(quarterly_values, annual_values):
    """Return one internally aligned comparison; never mix TTM and annual periods."""
    if len(quarterly_values) >= 8:
        current = sum(quarterly_values[:4])
        prior = sum(quarterly_values[4:8])
        growth = current / prior - 1 if prior else None
        previous_growth = None
        if len(quarterly_values) >= 12:
            earlier = sum(quarterly_values[8:12])
            previous_growth = prior / earlier - 1 if earlier else None
        return {
            "basis": "TTM", "current": current, "prior": prior, "growth": growth,
            "previous_growth": previous_growth,
            "acceleration": growth - previous_growth if is_number(growth) and is_number(previous_growth) else None,
            "source_period": "latest four quarters vs preceding four quarters",
        }
    if len(annual_values) >= 2:
        current, prior = annual_values[0], annual_values[1]
        growth = current / prior - 1 if prior else None
        previous_growth = annual_values[1] / annual_values[2] - 1 if len(annual_values) >= 3 and annual_values[2] else None
        return {
            "basis": "Annual", "current": current, "prior": prior, "growth": growth,
            "previous_growth": previous_growth,
            "acceleration": growth - previous_growth if is_number(growth) and is_number(previous_growth) else None,
            "source_period": "latest fiscal year vs previous fiscal year",
        }
    if len(quarterly_values) >= 4:
        return {"basis": "TTM", "current": sum(quarterly_values[:4]), "prior": None, "growth": None, "previous_growth": None, "acceleration": None, "source_period": "latest four quarters; prior TTM unavailable"}
    if annual_values:
        return {"basis": "Annual", "current": annual_values[0], "prior": None, "growth": None, "previous_growth": None, "acceleration": None, "source_period": "latest fiscal year; prior year unavailable"}
    return {"basis": "Unavailable", "current": None, "prior": None, "growth": None, "previous_growth": None, "acceleration": None, "source_period": "Unavailable"}


def financial_comparison(quarterly, annual, row_name):
    return _comparison_from_values(row_values(quarterly, row_name), row_values(annual, row_name))


def margin_comparison(quarterly, annual):
    for frame, basis, minimum in [(quarterly, "TTM", 8), (annual, "Annual", 2)]:
        if frame is None or frame.empty:
            continue
        revenue = row_values(frame, "Total Revenue")
        for row in ["Operating Income", "Pretax Income", "Net Income"]:
            income_values = row_values(frame, row)
            if len(revenue) < minimum or len(income_values) < minimum:
                continue
            if basis == "TTM":
                revenue_current, revenue_prior = sum(revenue[:4]), sum(revenue[4:8])
                income_current, income_prior = sum(income_values[:4]), sum(income_values[4:8])
                source_period = "latest four quarters vs preceding four quarters"
            else:
                revenue_current, revenue_prior = revenue[0], revenue[1]
                income_current, income_prior = income_values[0], income_values[1]
                source_period = "latest fiscal year vs previous fiscal year"
            current = income_current / revenue_current if revenue_current else None
            prior = income_prior / revenue_prior if revenue_prior else None
            return {"basis": basis, "row": row, "current": current, "prior": prior, "change": current - prior if is_number(current) and is_number(prior) else None, "source_period": source_period}
    return {"basis": "Unavailable", "row": None, "current": None, "prior": None, "change": None, "source_period": "Unavailable"}


def fcf_comparison(quarterly, annual):
    def values(frame):
        direct = row_values(frame, "Free Cash Flow")
        if direct:
            return direct
        operating = row_values(frame, "Operating Cash Flow")
        capex = row_values(frame, "Capital Expenditure")
        return [operating[i] + capex[i] for i in range(min(len(operating), len(capex)))]
    return _comparison_from_values(values(quarterly), values(annual))


def latest_and_prior_annual(frame, row_name):
    values = row_values(frame, row_name)
    if len(values) >= 2:
        current = values[0]
        prior = values[1]
        growth = current / prior - 1 if prior != 0 else None
        return current, prior, growth
    if len(values) == 1:
        return values[0], None, None
    return None, None, None


def margin_ttm(income, income_row):
    revenue_current, revenue_prior, _ = ttm_and_prior(income, "Total Revenue")
    income_current, income_prior, _ = ttm_and_prior(income, income_row)
    current_margin = income_current / revenue_current if is_number(income_current) and is_number(revenue_current) and revenue_current != 0 else None
    prior_margin = income_prior / revenue_prior if is_number(income_prior) and is_number(revenue_prior) and revenue_prior != 0 else None
    change = current_margin - prior_margin if is_number(current_margin) and is_number(prior_margin) else None
    return current_margin, prior_margin, change


def operating_margin_detail(income):
    if income is None or income.empty:
        return None, None, None, None
    for row in ["Operating Income", "Pretax Income", "Net Income"]:
        if row in income.index:
            current, prior, change = margin_ttm(income, row)
            return row, current, prior, change
    return None, None, None, None


def annual_margin_detail(income):
    if income is None or income.empty:
        return None, None, None, None
    for row in ["Operating Income", "Pretax Income", "Net Income"]:
        if row in income.index:
            revenue_current, revenue_prior, _ = latest_and_prior_annual(income, "Total Revenue")
            income_current, income_prior, _ = latest_and_prior_annual(income, row)
            current = income_current / revenue_current if is_number(income_current) and is_number(revenue_current) and revenue_current != 0 else None
            prior = income_prior / revenue_prior if is_number(income_prior) and is_number(revenue_prior) and revenue_prior != 0 else None
            return row, current, prior, current - prior if is_number(current) and is_number(prior) else None
    return None, None, None, None


def fcf_ttm(cashflow):
    if cashflow is None or cashflow.empty:
        return None, None, None
    if "Free Cash Flow" in cashflow.index:
        return ttm_and_prior(cashflow, "Free Cash Flow")
    operating_current, operating_prior, _ = ttm_and_prior(cashflow, "Operating Cash Flow")
    capex_current, capex_prior, _ = ttm_and_prior(cashflow, "Capital Expenditure")
    if is_number(operating_current) and is_number(capex_current):
        current = operating_current + capex_current
        prior = operating_prior + capex_prior if is_number(operating_prior) and is_number(capex_prior) else None
        growth = current / prior - 1 if is_number(prior) and prior != 0 else None
        return current, prior, growth
    return None, None, None


def fcf_annual(cashflow):
    if cashflow is None or cashflow.empty:
        return None, None, None
    if "Free Cash Flow" in cashflow.index:
        return latest_and_prior_annual(cashflow, "Free Cash Flow")
    operating_current, operating_prior, _ = latest_and_prior_annual(cashflow, "Operating Cash Flow")
    capex_current, capex_prior, _ = latest_and_prior_annual(cashflow, "Capital Expenditure")
    if is_number(operating_current) and is_number(capex_current):
        current = operating_current + capex_current
        prior = operating_prior + capex_prior if is_number(operating_prior) and is_number(capex_prior) else None
        return current, prior, current / prior - 1 if is_number(prior) and prior != 0 else None
    return None, None, None


def price_change(hist, days):
    if hist is None or "Close" not in hist or len(hist) <= days:
        return None
    current = float(hist["Close"].iloc[-1])
    prior = float(hist["Close"].iloc[-days])
    return current / prior - 1 if prior != 0 else None


def moving_average(hist, days):
    if hist is None or "Close" not in hist or len(hist) < days:
        return None
    return float(hist["Close"].tail(days).mean())


def relative_change(ticker, benchmark="SPY", days=126):
    hist = fetch_history(ticker, "1y")
    bench = fetch_history(benchmark, "1y")
    asset = price_change(hist, days)
    base = price_change(bench, days)
    if asset is None or base is None:
        return None
    return (1 + asset) / (1 + base) - 1 if base > -1 else None


def infer_security_type(info):
    quote_type = str(safe(info, "quoteType", default="")).upper()
    name = str(safe(info, "shortName", "longName", default="")).lower()
    if quote_type in {"ETF", "MUTUALFUND", "FUND"} or any(token in name for token in [" etf", " fund", " trust", "shares", "ishares", "spdr", "invesco"]):
        return "ETF / Fund"
    if quote_type in {"CRYPTOCURRENCY", "CURRENCY"}:
        return "Non-operating market proxy"
    if looks_like_shell(name):
        return "SPAC / Shell"
    return "Operating Company"


def data_quality_label(items):
    available = sum(1 for value in items.values() if value)
    total = len(items)
    if available == total:
        return "High"
    if available >= max(2, total - 2):
        return "Medium"
    return "Low"


def status_from_growth(value, high=0.15, low=0):
    if value is None:
        return "Unavailable"
    if value >= high:
        return "Improving"
    if value >= low:
        return "Stable / modest growth"
    return "Deteriorating"


def status_from_margin(change):
    if change is None:
        return "Unavailable"
    if change >= 0.03:
        return "Improving"
    if change >= -0.03:
        return "Stable"
    return "Deteriorating"


def status_from_fcf(fcf, fcf_growth, fcf_margin):
    if fcf is None:
        return "Unavailable"
    if fcf > 0 and (fcf_growth is None or fcf_growth >= 0) and (fcf_margin is None or fcf_margin >= 0.10):
        return "Cash-flow supported"
    if fcf > 0:
        return "Positive but needs conversion monitoring"
    return "Weak / negative FCF"


def valuation_status(forward_pe, ps, ev_rev, fcf_yield):
    if forward_pe is not None and forward_pe <= 0:
        return "Forward PE not meaningful because expected earnings are negative or near zero"
    expensive_points = 0
    if forward_pe is not None and forward_pe > 45:
        expensive_points += 2
    elif forward_pe is not None and forward_pe > 30:
        expensive_points += 1
    if ps is not None and ps > 15:
        expensive_points += 2
    elif ps is not None and ps > 8:
        expensive_points += 1
    if ev_rev is not None and ev_rev > 15:
        expensive_points += 2
    elif ev_rev is not None and ev_rev > 8:
        expensive_points += 1
    if fcf_yield is not None and fcf_yield < 0.015:
        expensive_points += 1
    if expensive_points >= 4:
        return "Premium valuation with high growth and margin expectations"
    if expensive_points >= 2:
        return "Elevated valuation risk"
    return "Valuation risk not extreme"


def fundamental_direction(revenue_growth, margin_change, fcf_growth):
    positive = sum([is_number(revenue_growth) and revenue_growth > 0.10, is_number(margin_change) and margin_change > 0, is_number(fcf_growth) and fcf_growth > 0])
    negative = sum([is_number(revenue_growth) and revenue_growth < 0, is_number(margin_change) and margin_change < -0.01, is_number(fcf_growth) and fcf_growth < -0.20])
    if positive >= 2 and negative == 0:
        return "Improving"
    if negative >= 2 or (negative and not positive):
        return "Deteriorating"
    return "Mixed"


def price_vs_fundamental_decomposition(revenue_growth, margin_change, fcf_growth, six_month, rel_strength, pe_change=None):
    direction = fundamental_direction(revenue_growth, margin_change, fcf_growth)
    if six_month is None:
        label = "Mixed confirmation"
    elif six_month > 0.10 and direction == "Improving":
        label = "Price confirms fundamentals"
    elif six_month > 0.10 and direction == "Deteriorating":
        label = "Price outruns fundamentals"
    elif six_month > 0.10:
        label = "Market-led rerating"
    elif six_month < -0.10 and direction == "Improving":
        label = "Fundamentals improving faster than price"
    elif six_month < -0.10 and direction == "Deteriorating":
        label = "Fundamental deterioration"
    elif six_month < -0.10:
        label = "Valuation reset"
    else:
        label = "Mixed confirmation"
    evidence = [f"Fundamental direction: {direction}", f"6M price performance: {signed_pct(six_month)}", f"6M relative strength vs SPY: {signed_pct(rel_strength)}"]
    if pe_change is None:
        evidence.append("Historical forward PE unavailable; multiple change is not inferred from price return")
    return {"label": label, "fundamental_direction": direction, "evidence": evidence}


def evidence_narrative(revenue_growth, margin_change, fcf_growth, forward_pe, price_sales, six_month):
    direction = fundamental_direction(revenue_growth, margin_change, fcf_growth)
    premium = (is_number(forward_pe) and forward_pe > 45) or (is_number(price_sales) and price_sales > 12)
    if direction == "Improving" and is_number(revenue_growth) and revenue_growth >= 0.25:
        label = "Fundamental Acceleration"
    elif direction == "Improving" and premium:
        label = "Premium Growth"
    elif direction == "Improving":
        label = "High-Conviction Growth"
    elif direction == "Deteriorating" and is_number(six_month) and six_month < 0:
        label = "Valuation Reset"
    elif direction == "Deteriorating":
        label = "Market-led Rerating"
    elif premium:
        label = "Premium Growth"
    else:
        label = "Mixed Confirmation"
    evidence = [f"revenue growth {pct(revenue_growth)}", f"margin change {signed_pp(margin_change)}", f"FCF growth {pct(fcf_growth)}", f"6M price performance {signed_pct(six_month)}"]
    return label, evidence


def chase_risk(revenue_growth, six_month, dist_200, rel_strength, forward_pe, price_sales):
    premium = (is_number(forward_pe) and forward_pe > 45) or (is_number(price_sales) and price_sales > 12)
    if (is_number(six_month) and six_month > 0.80) or (is_number(dist_200) and dist_200 > 0.40):
        label = "Extreme" if premium else "Elevated"
    elif (is_number(six_month) and six_month > 0.40) or (is_number(dist_200) and dist_200 > 0.25) or (premium and is_number(rel_strength) and rel_strength > 0.20):
        label = "Elevated"
    elif (is_number(six_month) and six_month > 0) or premium:
        label = "Moderate"
    else:
        label = "Low"
    evidence = [f"6M return {signed_pct(six_month)}", f"distance from 200DMA {signed_pct(dist_200)}", f"relative strength vs SPY {signed_pct(rel_strength)}", f"valuation {'premium' if premium else 'not extreme from available metrics'}"]
    return label, evidence


def ev_ebitda_display(ev_ebitda, ebitda, enterprise_value):
    unstable = not is_number(ebitda) or abs(ebitda) < 100_000_000 or (is_number(enterprise_value) and enterprise_value and abs(ebitda / enterprise_value) < 0.005)
    if not is_number(ev_ebitda):
        return "Unavailable", None
    if unstable or abs(ev_ebitda) > 200:
        return "Not economically meaningful", "EBITDA is near zero relative to enterprise value, making EV/EBITDA unstable. Prefer EV/Revenue or FCF Yield."
    return fmt(ev_ebitda, 1, "", "x"), None


def validate_company_metrics(revenue, margin, fcf, pe_change, pe_history_available, decomposition):
    warnings = []
    for name, item in [("Revenue", revenue), ("FCF", fcf)]:
        if is_number(item["current"]) and is_number(item["prior"]) and item["prior"] != 0:
            expected = item["current"] / item["prior"] - 1
            if not is_number(item["growth"]) or abs(expected - item["growth"]) > 1e-8:
                warnings.append(f"{name} growth does not match the displayed current and prior values")
    if is_number(margin["current"]) and is_number(margin["prior"]):
        if not is_number(margin["change"]) or abs((margin["current"] - margin["prior"]) - margin["change"]) > 1e-8:
            warnings.append("Margin change does not match current minus prior margin")
    if is_number(pe_change) and not pe_history_available:
        warnings.append("Forward PE change exists without verified historical forward PE")
    if decomposition["label"] == "Price confirms fundamentals" and decomposition["fundamental_direction"] != "Improving":
        warnings.append("Decomposition claims confirmation without improving fundamentals")
    return warnings


def positioning_phase(six_month, dist_200, momentum_heat=None):
    if six_month is None and dist_200 is None:
        return "Positioning analysis unavailable"
    if six_month is not None and six_month < 0 and dist_200 is not None and dist_200 < 0:
        return "Valuation reset / base-building"
    if (six_month is not None and six_month > 0.80) or (dist_200 is not None and dist_200 > 0.40):
        return "Late momentum / parabolic risk"
    if momentum_heat is not None and momentum_heat >= 55:
        return "Active momentum with elevated crowding risk"
    if six_month is not None and six_month > 0.20:
        return "Constructive momentum"
    return "Selective confirmation / repair phase"


def article_for(text):
    if not text:
        return "a"
    return "an" if text[0].lower() in "aeiou" else "a"


def narrative_support(narrative, revenue_growth, margin_change, fcf, rel_strength, pe_change):
    supporting = []
    against = []
    if revenue_growth is not None and revenue_growth > 0.10:
        supporting.append(f"revenue growth remains positive at {pct(revenue_growth)}")
    elif revenue_growth is not None and revenue_growth < 0:
        against.append(f"revenue growth is negative at {pct(revenue_growth)}")
    if margin_change is not None and margin_change > 0:
        supporting.append(f"margin expanded by {signed_pct(margin_change)}")
    elif margin_change is not None and margin_change < 0:
        against.append(f"margin contracted by {signed_pct(margin_change)}")
    if fcf is not None and fcf > 0:
        supporting.append(f"positive TTM FCF of {money(fcf)}")
    elif fcf is not None:
        against.append(f"negative TTM FCF of {money(fcf)}")
    if rel_strength is not None and rel_strength > 0.05:
        supporting.append(f"stock is outperforming SPY by {signed_pct(rel_strength)} over 6M")
    elif rel_strength is not None and rel_strength < -0.05:
        against.append(f"stock is underperforming SPY by {signed_pct(rel_strength)} over 6M")
    if pe_change is not None and pe_change < -0.10:
        against.append("valuation multiple appears to be compressing")
    return supporting or ["No strong positive narrative evidence available."], against or ["No major contrary narrative evidence visible from available data."]


def strengthen_conditions(revenue_growth, current_margin, fcf_margin, forward_pe, rel_strength):
    rev_floor = max(0.10, revenue_growth * 0.80) if is_number(revenue_growth) and revenue_growth > 0 else 0.10
    margin_floor = current_margin + 0.02 if is_number(current_margin) else None
    fcf_floor = max(0.10, fcf_margin + 0.02) if is_number(fcf_margin) else 0.10
    rs_condition = "relative strength versus SPY remains positive" if is_number(rel_strength) and rel_strength > 0 else "relative strength versus SPY turns positive over a 3M to 6M window"
    items = [
        f"revenue growth remains above {pct(rev_floor)}",
        f"FCF margin improves above {pct(fcf_floor)}",
        rs_condition,
        "forward estimates remain stable or move higher",
    ]
    if margin_floor is not None:
        items.insert(1, f"operating margin expands toward {pct(margin_floor)}")
    if is_number(forward_pe) and forward_pe > 30:
        items.append("forward PE compresses without earnings deterioration")
    return items


def weaken_conditions(revenue_growth, current_margin, fcf_margin, rel_strength):
    rev_break = revenue_growth * 0.50 if is_number(revenue_growth) and revenue_growth > 0 else 0
    items = [
        f"revenue growth decelerates below {pct(rev_break)}",
        "forward EPS or revenue estimates are revised down",
        "stock underperforms while its sector or SPY stabilizes",
        "valuation remains premium while growth slows",
    ]
    if is_number(current_margin):
        items.insert(1, f"operating margin falls below {pct(current_margin - 0.03)}")
    else:
        items.insert(1, "margin expansion stalls or turns negative")
    if is_number(fcf_margin):
        items.insert(2, f"FCF margin falls below {pct(max(0, fcf_margin - 0.05))}")
    else:
        items.insert(2, "FCF conversion weakens or remains unavailable")
    if rel_strength is not None and rel_strength < 0:
        items.append("weak relative strength persists despite stable fundamentals")
    return items


def print_list(items):
    for item in items:
        print(f"- {item}")


def print_non_operating_report(ticker, info, security_type, data_quality, as_of):
    line()
    print("SPECIFIC COMPANY INTELLIGENCE REPORT")
    line()
    print()
    print(f"Company: {safe(info, 'shortName', 'longName', default=ticker)}")
    print(f"Ticker: {ticker}")
    print(f"Security Type: {security_type}")
    print("Analysis Mode: Non-operating security template")
    print(f"Data Quality: {data_quality}")
    print(f"As Of: {as_of}")
    print()
    print("Interpretation:")
    print("This security is not a conventional operating company, so revenue, margin, free-cash-flow, and PE analysis would be misleading.")
    print("Use an exposure, holdings, capital-structure, or proxy-specific template instead of the mature company report.")


def print_company_intelligence_report(requested_ticker, resolved_ticker=None, narrative=None):
    ticker = resolved_ticker or requested_ticker.upper()
    ticker_obj = yf.Ticker(ticker)
    info = fetch_info(ticker_obj)
    hist = fetch_history(ticker, "1y")
    income = get_statement(ticker_obj, ["quarterly_income_stmt"])
    annual_income = get_statement(ticker_obj, ["income_stmt", "financials"])
    cashflow = get_statement(ticker_obj, ["quarterly_cashflow"])
    annual_cashflow = get_statement(ticker_obj, ["cashflow"])
    security_type = infer_security_type(info)
    as_of = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    revenue = financial_comparison(income, annual_income, "Total Revenue")
    revenue_current, revenue_prior, revenue_growth = revenue["current"], revenue["prior"], revenue["growth"]
    margin = margin_comparison(income, annual_income)
    margin_basis, current_margin, prior_margin, margin_change = margin["row"], margin["current"], margin["prior"], margin["change"]
    fcf = fcf_comparison(cashflow, annual_cashflow)
    fcf_current, fcf_prior, fcf_growth = fcf["current"], fcf["prior"], fcf["growth"]
    fcf_margin = fcf_current / revenue_current if is_number(fcf_current) and is_number(revenue_current) and revenue_current != 0 else None
    six_month = price_change(hist, 126)
    rel_strength = relative_change(ticker, "SPY", 126) if hist is not None else None
    ma200 = moving_average(hist, 200)
    current_price = float(hist["Close"].iloc[-1]) if hist is not None and "Close" in hist else safe(info, "currentPrice", "regularMarketPrice")
    dist_200 = current_price / ma200 - 1 if is_number(current_price) and is_number(ma200) and ma200 != 0 else None

    forward_pe = safe(info, "forwardPE")
    price_sales = safe(info, "priceToSalesTrailing12Months")
    ev_revenue = safe(info, "enterpriseToRevenue")
    ev_ebitda = safe(info, "enterpriseToEbitda")
    market_cap = safe(info, "marketCap")
    fcf_yield = fcf_current / market_cap if is_number(fcf_current) and is_number(market_cap) and market_cap != 0 else None
    prior_forward_pe = None
    pe_change = None
    pe_history_available = False
    ebitda = safe(info, "ebitda")
    enterprise_value = safe(info, "enterpriseValue")
    ev_ebitda_text, ev_ebitda_reason = ev_ebitda_display(ev_ebitda, ebitda, enterprise_value)

    heat = narrative.get("heat", {}) if narrative else {}
    effective_growth = revenue_growth if revenue_growth is not None else (narrative.get("earnings_acceleration") if narrative else None)
    phase = positioning_phase(six_month, dist_200, heat.get("momentum_heat") if narrative else None)
    data_quality = data_quality_label({
        "metadata": bool(info),
        "price": hist is not None,
        "revenue": revenue_current is not None and revenue_growth is not None,
        "margin": current_margin is not None,
        "fcf": fcf_current is not None,
        "valuation": forward_pe is not None or price_sales is not None or ev_revenue is not None,
    })

    if security_type != "Operating Company":
        print_non_operating_report(ticker, info, security_type, data_quality, as_of)
        return

    label, narrative_evidence = evidence_narrative(revenue_growth, margin_change, fcf_growth, forward_pe, price_sales, six_month)
    name = safe(info, "shortName", "longName", default=ticker)
    analysis_mode = "Operating Company Evidence Framework"
    decomposition = price_vs_fundamental_decomposition(revenue_growth, margin_change, fcf_growth, six_month, rel_strength, pe_change)
    chase_label, chase_evidence = chase_risk(revenue_growth, six_month, dist_200, rel_strength, forward_pe, price_sales)
    validation_warnings = validate_company_metrics(revenue, margin, fcf, pe_change, pe_history_available, decomposition)

    line()
    print("SPECIFIC COMPANY INTELLIGENCE REPORT")
    line()
    print()
    print(f"Company: {name}")
    print(f"Ticker: {ticker}" + (f" (alias for {requested_ticker.upper()})" if requested_ticker.upper() != ticker else ""))
    print(f"Security Type: {security_type}")
    print(f"Analysis Mode: {analysis_mode}")
    print(f"Data Quality: {data_quality}")
    print(f"As Of: {as_of}")
    if validation_warnings:
        print("Internal Validation: WARNING")
        for warning in validation_warnings:
            print(f"- {warning}")
    else:
        print("Internal Validation: PASSED")
    print()

    line()
    print("1. BUSINESS FUNDAMENTAL EVIDENCE")
    line()
    print()
    print("Revenue:")
    print(f"Comparison Basis: {revenue['basis']} ({revenue['source_period']})")
    print(f"Current {revenue['basis']} Revenue: {money(revenue_current)}")
    print(f"Prior {revenue['basis']} Revenue: {money(revenue_prior)}")
    print(f"Previous Revenue Growth: {pct(revenue['previous_growth'])}")
    print(f"Current Revenue Growth: {pct(revenue_growth)}")
    print(f"Revenue Acceleration: {signed_pp(revenue['acceleration'])}")
    print(f"Status: {status_from_growth(revenue_growth)}")
    print()
    print("Margins:")
    print(f"Comparison Basis: {margin['basis']} ({margin['source_period']})")
    print(f"Margin Basis: {margin_basis or 'Unavailable'}")
    print(f"Current Operating Margin: {pct(current_margin)}")
    print(f"Prior Operating Margin: {pct(prior_margin)}")
    print(f"Margin Change: {signed_pp(margin_change)}")
    print(f"Status: {status_from_margin(margin_change)}")
    print()
    print("Free Cash Flow:")
    print(f"Comparison Basis: {fcf['basis']} ({fcf['source_period']})")
    print(f"Current {fcf['basis']} FCF: {money(fcf_current)}")
    print(f"Prior {fcf['basis']} FCF: {money(fcf_prior)}")
    print(f"FCF Growth: {pct(fcf_growth)}")
    print(f"FCF Margin: {pct(fcf_margin)}")
    print(f"Status: {status_from_fcf(fcf_current, fcf_growth, fcf_margin)}")
    print()
    print("Interpretation:")
    fundamental_status = "fundamentally improving" if status_from_growth(effective_growth) == "Improving" and status_from_margin(margin_change) in {"Improving", "Stable"} and (fcf_current is None or fcf_current > 0) else "fundamentally mixed or needs confirmation"
    if revenue_current is None and current_margin is None and fcf_current is None:
        print("Fundamental evidence is unavailable from the current data provider, so the business trend cannot be assessed with confidence.")
    else:
        print(f"{ticker} appears {fundamental_status} based on {revenue['basis'].lower()} revenue growth of {pct(revenue_growth)}, margin change of {signed_pp(margin_change)}, and {fcf['basis'].lower()} FCF of {money(fcf_current)}.")
    print()

    # Insert the economic mechanism layer between fundamentals and valuation /
    # positioning.  All inputs reuse the statements already fetched above.
    economics_snapshot = CompanySnapshot(
        ticker=ticker,
        company_name=name,
        as_of=as_of,
        sector=str(safe(info, "sector", default="")),
        industry=str(safe(info, "industry", default="")),
        business_description=str(safe(info, "longBusinessSummary", default="")),
        metrics={
            "revenue": revenue_current,
            "revenue_growth": revenue_growth,
            "gross_margin": safe(info, "grossMargins"),
            "operating_income": current_margin * revenue_current if is_number(current_margin) and is_number(revenue_current) else None,
            "operating_margin": current_margin,
            "fcf": fcf_current,
            "fcf_margin": fcf_margin,
            "capex": abs(row_values(annual_cashflow, "Capital Expenditure")[0]) if row_values(annual_cashflow, "Capital Expenditure") else None,
            "employees": safe(info, "fullTimeEmployees"),
            "inventory": safe(info, "inventory"),
            "assets": safe(info, "totalAssets"),
            "market_cap": market_cap,
        },
        histories={
            "revenue": [value for value in (revenue_current, revenue_prior) if is_number(value)],
            "operating_income": [value for value in (
                current_margin * revenue_current if is_number(current_margin) and is_number(revenue_current) else None,
                prior_margin * revenue_prior if is_number(prior_margin) and is_number(revenue_prior) else None,
            ) if is_number(value)],
            "fcf": [value for value in (fcf_current, fcf_prior) if is_number(value)],
        },
        operational_metrics={},
        periods={"revenue": revenue["source_period"], "operating_income": margin["source_period"], "fcf": fcf["source_period"]},
        sources={key: "Yahoo Finance financial statement via yfinance" for key in ("revenue", "revenue_growth", "gross_margin", "operating_income", "operating_margin", "fcf", "fcf_margin", "capex", "employees", "inventory", "assets", "market_cap")},
        source_nature={"revenue_growth": SourceNature.CALCULATED, "operating_income": SourceNature.CALCULATED, "operating_margin": SourceNature.CALCULATED, "fcf_margin": SourceNature.CALCULATED},
    )
    print_company_economics(build_company_economics(economics_snapshot))
    print()

    line()
    print("2. VALUATION REALITY CHECK")
    line()
    print()
    print("Forward PE:")
    print(f"Current: {fmt(forward_pe, 1, '', 'x') if not (is_number(forward_pe) and forward_pe <= 0) else 'Not meaningful'}")
    print("Forward PE History: Unavailable")
    print("Forward PE Change: Unavailable — historical forward PE is not provided by the current source")
    print(f"Status: {valuation_status(forward_pe, price_sales, ev_revenue, fcf_yield)}")
    print()
    print("Price / Sales:")
    print(f"Current: {fmt(price_sales, 1, '', 'x')}")
    print("Historical / Recent Range: Unavailable")
    print()
    print("EV / Revenue or EV / EBITDA:")
    print(f"EV / Revenue Current: {fmt(ev_revenue, 1, '', 'x')}")
    print(f"EV / EBITDA Current: {ev_ebitda_text}")
    if ev_ebitda_reason:
        print(f"Reason: {ev_ebitda_reason}")
    print("Historical / Recent Range: Unavailable")
    print()
    print("FCF Yield:")
    print(f"Current: {pct(fcf_yield)}")
    print()
    print("Valuation Interpretation:")
    if is_number(forward_pe) and forward_pe <= 0:
        print("Forward PE is not meaningful because forward earnings are negative or near zero; valuation should be judged through revenue durability, cash flow, dilution, and path to profitability.")
    else:
        print(f"At {fmt(forward_pe, 1, '', 'x')} forward earnings, {fmt(price_sales, 1, '', 'x')} sales, and {pct(fcf_yield)} FCF yield, valuation risk is tied to growth durability, margin execution, and estimate sensitivity rather than a simple label.")
        if is_number(forward_pe) and forward_pe > 45:
            print(f"The market is still pricing {ticker} as a premium conviction-growth company, so any slowdown in revenue growth or margin expansion can create multiple-compression risk.")
        elif is_number(forward_pe) and forward_pe > 30:
            print("The multiple requires continued growth and margin support, even if the stock is not in active chase mode.")
    print()

    line()
    print("3. PRICE ACTION VS FUNDAMENTALS")
    line()
    print()
    print(f"6M Price Performance: {signed_pct(six_month)}")
    print(f"6M Relative Strength vs SPY: {signed_pct(rel_strength)}")
    print(f"Distance from 200MA: {signed_pct(dist_200)}")
    print("Forward PE Change: Unavailable")
    print("Reason: verified historical forward PE is unavailable; price return is not used as a substitute")
    print("EPS Estimate Change if available: Unavailable")
    print("Revenue Estimate Change if available: Unavailable")
    print()
    print("Decomposition:")
    print(decomposition["label"])
    print_list(decomposition["evidence"])
    print()
    print("Interpretation:")
    if six_month is None and dist_200 is None:
        print("Positioning analysis is unavailable because sufficient price data could not be retrieved.")
    elif six_month is not None and six_month < 0 and revenue_growth is not None and revenue_growth > 0:
        print(f"{ticker}'s fundamentals remain supported by positive revenue growth, but weak 6M price action suggests the market is repricing valuation expectations or factor exposure rather than simply abandoning the business.")
    else:
        print(f"{decomposition['label']}: the conclusion follows the aligned revenue, margin, FCF, price, and relative-strength evidence shown above.")
    print()

    line()
    print("4. NARRATIVE & INSTITUTIONAL CONVICTION")
    line()
    print()
    print(f"Narrative Type: {label}")
    supporting, against = narrative_support(narrative, revenue_growth, margin_change, fcf_current, rel_strength, pe_change)
    print()
    print("Evidence supporting narrative:")
    print_list(supporting)
    print()
    print("Evidence against narrative:")
    print_list(against)
    print()
    print("Interpretation:")
    print(f"The {label} classification is based on the revenue, margin, FCF, valuation, and price evidence listed above; it does not inherit an unrelated generic narrative label.")
    print()

    line()
    print("5. POSITIONING / OVERHEAT / CHASE RISK")
    line()
    print()
    print(f"Price Performance: {signed_pct(six_month)} (6M)")
    print(f"Distance from 200MA: {signed_pct(dist_200)}")
    print(f"Momentum Structure: {phase}")
    print("Valuation Expansion Evidence:")
    print(f"- Forward PE: {fmt(forward_pe, 1, '', 'x')}")
    print("- Forward PE history: Unavailable")
    print(f"- Price / Sales: {fmt(price_sales, 1, '', 'x')}")
    print(f"- FCF Yield: {pct(fcf_yield)}")
    print(f"Crowding Risk: {'Elevated' if chase_label in {'Elevated', 'Extreme'} else 'Moderate' if chase_label == 'Moderate' else 'Low'}")
    print(f"Chase Risk: {chase_label}")
    print_list(chase_evidence)
    print()
    print("Interpretation:")
    if six_month is None and dist_200 is None:
        print("Positioning analysis is unavailable because price data is unavailable.")
    elif six_month is not None and six_month < 0 and dist_200 is not None and dist_200 < 0:
        print("Negative price performance and a negative 200MA distance point to valuation reset / base-building, not active chase risk.")
    else:
        print(f"Chase risk is {chase_label.lower()} based on the displayed return, 200DMA distance, relative strength, and valuation evidence.")
    print()

    line()
    print("6. WHAT WOULD STRENGTHEN THE CASE")
    line()
    print()
    print_list(strengthen_conditions(revenue_growth, current_margin, fcf_margin, forward_pe, rel_strength))
    print()

    line()
    print("7. WHAT WOULD WEAKEN THE CASE")
    line()
    print()
    print_list(weaken_conditions(revenue_growth, current_margin, fcf_margin, rel_strength))
    print()

    line()
    print("8. FINAL COMPANY INTERPRETATION")
    line()
    print()
    if revenue_current is None and fcf_current is None:
        print(f"{ticker} cannot be assessed with high confidence because core operating data is unavailable. The report should be treated as incomplete until verified revenue, margin, cash-flow, valuation, and price evidence are available.")
    else:
        print(f"Business: {revenue['basis']} revenue growth is {pct(revenue_growth)}, margin changed {signed_pp(margin_change)}, and {fcf['basis']} FCF is {money(fcf_current)} with {pct(fcf_growth)} growth.")
        print(f"Valuation: forward PE is {fmt(forward_pe, 1, '', 'x')}, price/sales is {fmt(price_sales, 1, '', 'x')}, and FCF yield is {pct(fcf_yield)}; historical forward PE is unavailable, so multiple expansion is not claimed.")
        print(f"Market and positioning: 6M performance is {signed_pct(six_month)}, relative strength versus SPY is {signed_pct(rel_strength)}, and distance from the 200DMA is {signed_pct(dist_200)}, producing {chase_label.lower()} chase risk.")
        print(f"Reconciliation: {decomposition['label']} and the evidence-based narrative is {label}. This is an analyst-style structural interpretation, not a buy/sell recommendation.")
    print()

    print("Data Quality Notes:")
    missing = []
    if revenue_current is None:
        missing.append("TTM revenue")
    if current_margin is None:
        missing.append("operating margin history")
    if fcf_current is None:
        missing.append("free cash flow")
    if forward_pe is None:
        missing.append("forward PE")
    if hist is None:
        missing.append("price history")
    if missing:
        print("Unavailable or low-confidence fields: " + ", ".join(missing))
    else:
        print("Core revenue, margin, FCF, valuation, and price fields were available from the current provider.")
