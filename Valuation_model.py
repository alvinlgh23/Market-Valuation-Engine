"""
Market Structure and Capital Rotation Framework - Live Version

The model follows a five-layer flow:
    Macro Environment
    -> Liquidity / Cost of Capital
    -> Sector Rotation
    -> Narrative Formation
    -> Institutional Capital Flow
    -> Quality Companies Get Rerated
    -> Valuation Expansion / Overheating

Install dependency:
    pip install yfinance pandas

Usage:
    python model.py
    python model.py full
    python model.py macro
    python model.py sectors
    python model.py sector semis
    python model.py company MU
"""

import contextlib
import io
import math
import statistics
import sys

import yfinance as yf


SECTOR_ETFS = {
    # Core GICS sector ETFs
    "SMH": "Semiconductors",
    "XLK": "Technology",
    "XLY": "Consumer Discretionary",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLV": "Healthcare",
    "XLU": "Utilities",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    # Major industry / thematic ETFs
    "IGV": "Software",
    "CIBR": "Cybersecurity",
    "XBI": "Biotech",
    "KRE": "Regional Banks",
    "KBE": "Banks",
    "ITB": "Homebuilders",
    "XRT": "Retail",
    "IYT": "Transports",
    "ITA": "Aerospace & Defense",
    "JETS": "Airlines",
    "URA": "Uranium / Nuclear",
    "TAN": "Solar",
    "ICLN": "Clean Energy",
    "COPX": "Copper Miners",
    "SLV": "Silver",
    "DBA": "Agriculture",
    "KWEB": "China Internet",
    "IBIT": "Bitcoin / Crypto",
    "GLD": "Gold",
    "DBC": "Broad Commodities",
}

SECTOR_ALIASES = {
    "semis": "SMH",
    "semiconductors": "SMH",
    "ai": "SMH",
    "ai-infrastructure": "SMH",
    "tech": "XLK",
    "technology": "XLK",
    "software": "IGV",
    "saas": "IGV",
    "cyber": "CIBR",
    "cybersecurity": "CIBR",
    "biotech": "XBI",
    "regional-banks": "KRE",
    "regionalbanks": "KRE",
    "banks": "KBE",
    "banking": "KBE",
    "homebuilders": "ITB",
    "housing": "ITB",
    "retail": "XRT",
    "transport": "IYT",
    "transports": "IYT",
    "aerospace": "ITA",
    "defense": "ITA",
    "airlines": "JETS",
    "uranium": "URA",
    "nuclear": "URA",
    "solar": "TAN",
    "clean-energy": "ICLN",
    "cleanenergy": "ICLN",
    "copper": "COPX",
    "silver": "SLV",
    "agriculture": "DBA",
    "china-internet": "KWEB",
    "china": "KWEB",
    "crypto": "IBIT",
    "bitcoin": "IBIT",
    "energy": "XLE",
    "utilities": "XLU",
    "defensives": "XLP",
    "healthcare": "XLV",
    "financials": "XLF",
    "industrials": "XLI",
    "materials": "XLB",
    "real-estate": "XLRE",
    "commodities": "DBC",
    "gold": "GLD",
}

SECTOR_CANDIDATES = {
    "SMH": ["MU", "WDC", "SNDK", "AVGO", "NVDA", "AMD", "TSM", "ASML", "LRCX", "KLAC", "AMAT", "MRVL"],
    "XLK": ["MSFT", "AAPL", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "NOW", "PANW"],
    "IBIT": ["COIN", "MSTR", "MARA", "RIOT", "CLSK", "IREN", "HOOD", "XYZ", "CME", "IBIT"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY", "HAL"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "VST", "AEP", "SRE", "D", "EXC", "PEG"],
    "XLP": ["WMT", "COST", "PG", "KO", "PEP", "PM", "MDLZ", "CL", "MO", "KMB"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "ISRG", "AMGN", "DHR"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK"],
    "XLI": ["GE", "CAT", "RTX", "UNP", "HON", "ETN", "DE", "BA", "LMT", "UPS"],
    "XLB": ["LIN", "SHW", "FCX", "NEM", "ECL", "APD", "CTVA", "DOW", "NUE", "MLM"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "SPG", "O", "DLR", "PSA", "CCI", "CBRE"],
    "IGV": ["MSFT", "ORCL", "CRM", "ADBE", "NOW", "INTU", "SNOW", "DDOG", "MDB", "TEAM"],
    "CIBR": ["PANW", "CRWD", "FTNT", "ZS", "OKTA", "NET", "S", "CHKP", "CYBR", "TENB"],
    "XBI": ["VRTX", "REGN", "ALNY", "BMRN", "INCY", "EXAS", "TECH", "SRPT", "HALO", "IONS"],
    "KRE": ["FITB", "HBAN", "RF", "KEY", "CFG", "TFC", "MTB", "CMA", "WAL", "ZION"],
    "KBE": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "BK", "SCHW"],
    "ITB": ["DHI", "LEN", "PHM", "NVR", "TOL", "KBH", "MTH", "BLDR", "LOW", "HD"],
    "XRT": ["AMZN", "WMT", "COST", "TGT", "TJX", "ROST", "BBY", "ANF", "GPS", "BURL"],
    "IYT": ["UNP", "UPS", "FDX", "CSX", "NSC", "ODFL", "JBHT", "CHRW", "EXPD", "XPO"],
    "ITA": ["RTX", "LMT", "NOC", "GD", "BA", "TXT", "HWM", "TDG", "LHX", "HII"],
    "JETS": ["DAL", "UAL", "AAL", "LUV", "ALK", "JBLU", "SAVE", "RYAAY", "CPA", "SKYW"],
    "URA": ["CCJ", "CEG", "VST", "UEC", "UUUU", "LEU", "NXE", "DNN", "SMR", "BWXT"],
    "TAN": ["FSLR", "ENPH", "SEDG", "RUN", "NXT", "ARRY", "SHLS", "CSIQ", "JKS", "DQ"],
    "ICLN": ["FSLR", "ENPH", "PLUG", "BE", "NXT", "RUN", "ORA", "CWEN", "AY", "NEE"],
    "COPX": ["FCX", "SCCO", "TECK", "BHP", "RIO", "VALE", "ERO", "HBM", "IVPAF", "LUNMF"],
    "SLV": ["PAAS", "AG", "HL", "WPM", "SILV", "MAG", "FSM", "EXK", "CDE", "SSRM"],
    "DBA": ["ADM", "BG", "MOS", "CF", "NTR", "DE", "CTVA", "TSN", "CALM", "FMC"],
    "KWEB": ["BABA", "PDD", "JD", "BIDU", "TME", "NTES", "BILI", "BEKE", "TAL", "VIPS"],
    "DBC": ["XOM", "CVX", "FCX", "NEM", "AA", "MOS", "CF", "TECK", "VALE", "RIO"],
    "GLD": ["NEM", "GOLD", "AEM", "WPM", "FNV", "KGC", "PAAS", "AGI", "GFI", "HMY"],
}

SECTOR_THEME_NAMES = {
    "SMH": "Semiconductors / AI Memory",
    "XLK": "Technology / AI Software",
    "IBIT": "Crypto Infrastructure",
    "XLE": "Energy",
    "XLU": "Utilities / Power Demand",
    "XLP": "Defensives / Staples",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "IGV": "Software / SaaS",
    "CIBR": "Cybersecurity",
    "XBI": "Biotech",
    "KRE": "Regional Banks",
    "KBE": "Banks",
    "ITB": "Homebuilders / Housing",
    "XRT": "Retail",
    "IYT": "Transports",
    "ITA": "Aerospace & Defense",
    "JETS": "Airlines",
    "URA": "Uranium / Nuclear Power",
    "TAN": "Solar",
    "ICLN": "Clean Energy",
    "COPX": "Copper / Electrification",
    "SLV": "Silver",
    "DBA": "Agriculture",
    "KWEB": "China Internet",
    "DBC": "Commodities",
    "GLD": "Gold / Miners",
}

ASSET_PROXIES = {
    "SPY": "US equities",
    "QQQ": "Growth equities",
    "IWM": "Small caps",
    "IBIT": "Crypto",
    "GLD": "Gold",
    "DBC": "Commodities",
    "TLT": "Long duration bonds",
    "UUP": "US dollar",
}

TICKER_ALIASES = {
    "SQ": "XYZ",
}

MANUAL_MACRO_INDICATORS = [
    "Fed Funds Rate",
    "M2 Liquidity",
    "Reverse Repo",
    "CPI / Inflation",
    "Credit Spread",
]


def pct(v):
    return f"{v * 100:.2f}%" if is_number(v) else "-"


def signed_pct(v):
    return f"{v * 100:+.2f}%" if is_number(v) else "-"


def fmt(v, decimals=2, prefix="", suffix=""):
    if not is_number(v):
        return "-"
    return f"{prefix}{v:,.{decimals}f}{suffix}"


def divider(title=""):
    if title:
        print(f"\n{'=' * 72}")
        print(f"  {title}")
        print(f"{'=' * 72}")
    else:
        print("-" * 72)


def safe(info, *keys, default=None):
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return default


def resolve_ticker(ticker):
    return TICKER_ALIASES.get(ticker.upper(), ticker.upper())


def is_number(value):
    return isinstance(value, (int, float)) and not math.isnan(value)


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


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


def fetch_first_history(tickers, period="1y"):
    for ticker in tickers:
        hist = fetch_history(ticker, period)
        if hist is not None:
            return ticker, hist
    return tickers[0], None


def last_close(ticker):
    hist = fetch_history(ticker, "1mo")
    if hist is None or "Close" not in hist:
        return None
    return float(hist["Close"].iloc[-1])


def price_change(hist, days):
    if hist is None or len(hist) <= days or "Close" not in hist:
        return None
    current = float(hist["Close"].iloc[-1])
    previous = float(hist["Close"].iloc[-days])
    if previous == 0:
        return None
    return current / previous - 1


def moving_average(hist, days):
    if hist is None or len(hist) < days or "Close" not in hist:
        return None
    return float(hist["Close"].tail(days).mean())


def rsi(hist, period=14):
    if hist is None or len(hist) < period + 1 or "Close" not in hist:
        return None
    delta = hist["Close"].diff().dropna()
    gains = delta.clip(lower=0).tail(period).mean()
    losses = -delta.clip(upper=0).tail(period).mean()
    if losses == 0:
        return 100.0
    rs = gains / losses
    return float(100 - (100 / (1 + rs)))


def relative_change(ticker, benchmark="SPY", days=63):
    asset = fetch_history(ticker, "1y")
    bench = fetch_history(benchmark, "1y")
    asset_ret = price_change(asset, days)
    bench_ret = price_change(bench, days)
    if asset_ret is None or bench_ret is None:
        return None
    return asset_ret - bench_ret


def score_from_change(change, bullish_when_positive=True, scale=0.08):
    if change is None:
        return 50
    signed = change if bullish_when_positive else -change
    return clamp(50 + (signed / scale) * 50)


def band(score):
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Constructive"
    if score >= 45:
        return "Neutral"
    if score >= 30:
        return "Weak"
    return "Stress"


def print_row(label, value, note=""):
    print(f"  {label:<34} {value:<16} {note}")


def emoji_for_sector(name):
    lowered = name.lower()
    if "semiconductor" in lowered or "technology" in lowered:
        return "🚀"
    if "utilities" in lowered:
        return "⚡"
    if "crypto" in lowered or "bitcoin" in lowered:
        return "₿"
    if "gold" in lowered or "commod" in lowered:
        return "⛏"
    if "staples" in lowered or "healthcare" in lowered:
        return "🛡"
    return "→"


def macro_label(score):
    if score >= 65:
        return "Liquidity Easing 🚀"
    if score >= 45:
        return "Neutral-to-Tight Liquidity ⚠"
    return "Liquidity Tightening ⚠"


def preferred_environment(macro_score, dxy_3m, tnx_3m):
    if macro_score < 45 or (dxy_3m and dxy_3m > 0) or (tnx_3m and tnx_3m > 0):
        return ["Cash-flow-heavy sectors", "Defensives", "Balance-sheet strength"]
    if macro_score > 65:
        return ["Growth sectors", "Long-duration equities", "Crypto / high-beta risk assets"]
    return ["Selective growth", "Strong free-cash-flow compounders", "Narratives with earnings support"]


def compute_macro():
    tnx_ticker, tnx = fetch_first_history(["^TNX"], "1y")
    front_rate_ticker, front_rate = fetch_first_history(["2YY=F", "^IRX", "^FVX"], "1y")
    dxy = fetch_history("DX-Y.NYB", "1y")
    vix = fetch_history("^VIX", "1y")
    hyg_ief = relative_change("HYG", "IEF", 63)

    tnx_level = last_close(tnx_ticker)
    front_rate_level = last_close(front_rate_ticker)
    dxy_level = last_close("DX-Y.NYB")
    vix_level = last_close("^VIX")

    tnx_3m = price_change(tnx, 63)
    front_rate_3m = price_change(front_rate, 63)
    dxy_3m = price_change(dxy, 63)

    yield_curve = None
    if is_number(tnx_level) and is_number(front_rate_level) and front_rate_ticker != "^IRX":
        yield_curve = (tnx_level - front_rate_level) / 100

    rate_score = score_from_change(tnx_3m, bullish_when_positive=False, scale=0.12)
    front_rate_score = score_from_change(front_rate_3m, bullish_when_positive=False, scale=0.12)
    usd_score = score_from_change(dxy_3m, bullish_when_positive=False, scale=0.06)
    curve_score = 60 if yield_curve and yield_curve > 0 else 40 if yield_curve and yield_curve < 0 else 50
    vix_score = 75 if vix_level and vix_level < 16 else 60 if vix_level and vix_level < 22 else 35 if vix_level else 50
    credit_score = score_from_change(hyg_ief, bullish_when_positive=True, scale=0.05)

    liquidity_score = (rate_score * 0.30) + (front_rate_score * 0.15) + (usd_score * 0.25) + (curve_score * 0.10) + (credit_score * 0.20)
    risk_score = (vix_score * 0.55) + (credit_score * 0.45)
    macro_score = (liquidity_score * 0.60) + (risk_score * 0.40)

    spy_info = {}
    try:
        spy_info = yf.Ticker("SPY").info
    except Exception:
        pass
    forward_pe = safe(spy_info, "forwardPE")
    earning_yield = (1 / forward_pe) if forward_pe else None
    treasury = (tnx_level / 100) if tnx_level else None
    erp = earning_yield - treasury if earning_yield and treasury else None

    return {
        "tnx_level": tnx_level,
        "tnx_3m": tnx_3m,
        "front_rate_ticker": front_rate_ticker,
        "front_rate_level": front_rate_level,
        "front_rate_3m": front_rate_3m,
        "yield_curve": yield_curve,
        "dxy_level": dxy_level,
        "dxy_3m": dxy_3m,
        "vix_level": vix_level,
        "hyg_ief": hyg_ief,
        "forward_pe": forward_pe,
        "erp": erp,
        "liquidity_score": liquidity_score,
        "risk_score": risk_score,
        "macro_score": macro_score,
    }


def compute_sectors():
    rows = []
    for ticker, name in SECTOR_ETFS.items():
        hist = fetch_history(ticker, "1y")
        if hist is None:
            continue

        rel_1m = relative_change(ticker, "SPY", 21)
        rel_3m = relative_change(ticker, "SPY", 63)
        rel_6m = relative_change(ticker, "SPY", 126)
        close = float(hist["Close"].iloc[-1])
        high_252 = float(hist["Close"].tail(252).max())
        breakout = (close / high_252 - 1) if high_252 else None

        momentum_score = (
            score_from_change(rel_1m, True, 0.06) * 0.35
            + score_from_change(rel_3m, True, 0.10) * 0.40
            + score_from_change(rel_6m, True, 0.16) * 0.25
        )
        breakout_score = score_from_change(breakout, True, 0.08)
        score = momentum_score * 0.75 + breakout_score * 0.25

        rows.append({
            "ticker": ticker,
            "name": name,
            "rel_1m": rel_1m,
            "rel_3m": rel_3m,
            "rel_6m": rel_6m,
            "breakout": breakout,
            "score": score,
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def company_quality_rows(tickers):
    rows = []
    for ticker in tickers:
        ticker = resolve_ticker(ticker)
        t = yf.Ticker(ticker)
        try:
            info = t.info
        except Exception:
            info = {}

        rev_growth = safe(info, "revenueGrowth")
        earnings_growth = safe(info, "earningsGrowth", "earningsQuarterlyGrowth")
        op_margin = safe(info, "operatingMargins")
        gross_margin = safe(info, "grossMargins")
        roe = safe(info, "returnOnEquity", "returnOnAssets")
        fcf = safe(info, "freeCashflow")
        cash = safe(info, "totalCash", default=0)
        debt = safe(info, "totalDebt", default=0)
        accel = revenue_acceleration(t)
        margin_expansion = operating_margin_expansion(t)
        op_margin = op_margin if op_margin is not None else latest_operating_margin(t)
        fcf = fcf if fcf is not None else trailing_free_cash_flow(t)

        growth_score = (
            score_from_change(rev_growth, True, 0.25) * 0.45
            + score_from_change(earnings_growth, True, 0.35) * 0.35
            + score_from_change(accel, True, 0.10) * 0.20
        )
        profitability_score = (
            score_from_change(op_margin, True, 0.30) * 0.35
            + score_from_change(gross_margin, True, 0.55) * 0.25
            + score_from_change(roe, True, 0.30) * 0.25
            + score_from_change(margin_expansion, True, 0.08) * 0.15
        )
        cash_score = 50
        if is_number(fcf):
            cash_score += 20 if fcf > 0 else -20
        if is_number(cash) and is_number(debt):
            cash_score += 15 if cash > debt else -10
        cash_score = clamp(cash_score)

        quality_score = growth_score * 0.40 + profitability_score * 0.35 + cash_score * 0.25
        rows.append({
            "ticker": ticker,
            "name": safe(info, "shortName", "longName", default=ticker),
            "rev_growth": rev_growth,
            "earnings_growth": earnings_growth,
            "op_margin": op_margin,
            "margin_expansion": margin_expansion,
            "fcf": fcf,
            "accel": accel,
            "score": quality_score,
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def heat_rows(tickers):
    rows = []
    for ticker in tickers:
        ticker = resolve_ticker(ticker)
        t = yf.Ticker(ticker)
        try:
            info = t.info
        except Exception:
            info = {}
        hist = fetch_history(ticker, "1y")

        current = float(hist["Close"].iloc[-1]) if hist is not None else safe(info, "currentPrice", "regularMarketPrice")
        ma50 = moving_average(hist, 50)
        ma200 = moving_average(hist, 200)
        ticker_rsi = rsi(hist)
        one_month = price_change(hist, 21)
        three_month = price_change(hist, 63)
        six_month = price_change(hist, 126)
        vertical = one_month - (three_month / 3) if one_month is not None and three_month is not None else None

        forward_pe = safe(info, "forwardPE")
        peg = safe(info, "pegRatio", "trailingPegRatio")
        ev_sales = safe(info, "enterpriseToRevenue", "priceToSalesTrailing12Months")
        dist_50 = (current / ma50 - 1) if current and ma50 else None
        dist_200 = (current / ma200 - 1) if current and ma200 else None

        valuation_heat = 0
        valuation_heat += 25 if forward_pe and forward_pe > 45 else 15 if forward_pe and forward_pe > 30 else 5
        valuation_heat += 20 if peg and peg > 2.5 else 10 if peg and peg > 1.5 else 0
        valuation_heat += 20 if ev_sales and ev_sales > 12 else 10 if ev_sales and ev_sales > 7 else 0

        momentum_heat = 0
        momentum_heat += 25 if ticker_rsi and ticker_rsi > 75 else 15 if ticker_rsi and ticker_rsi > 65 else 0
        momentum_heat += 20 if dist_50 and dist_50 > 0.18 else 10 if dist_50 and dist_50 > 0.10 else 0
        momentum_heat += 20 if dist_200 and dist_200 > 0.45 else 10 if dist_200 and dist_200 > 0.25 else 0
        momentum_heat += 15 if vertical and vertical > 0.10 else 8 if vertical and vertical > 0.05 else 0

        heat_score = clamp(valuation_heat + momentum_heat)
        rows.append({
            "ticker": ticker,
            "forward_pe": forward_pe,
            "peg": peg,
            "ev_sales": ev_sales,
            "rsi": ticker_rsi,
            "dist_50": dist_50,
            "dist_200": dist_200,
            "one_month": one_month,
            "three_month": three_month,
            "six_month": six_month,
            "vertical": vertical,
            "valuation_heat": valuation_heat,
            "momentum_heat": momentum_heat,
            "heat": heat_score,
        })
    return sorted(rows, key=lambda row: row["heat"], reverse=True)


def pe_expansion_score(heat):
    if not heat:
        return 50

    score = 50
    forward_pe = heat.get("forward_pe")
    peg = heat.get("peg")
    ev_sales = heat.get("ev_sales")

    if forward_pe and forward_pe > 45:
        score += 20
    elif forward_pe and forward_pe > 30:
        score += 10
    elif forward_pe and forward_pe < 18:
        score -= 5

    if peg and peg > 2.5:
        score += 15
    elif peg and peg > 1.5:
        score += 8

    if ev_sales and ev_sales > 12:
        score += 15
    elif ev_sales and ev_sales > 7:
        score += 8

    return clamp(score)


def implied_prior_forward_pe(heat):
    forward_pe = heat.get("forward_pe")
    six_month = heat.get("six_month")
    if not forward_pe or six_month is None or six_month <= -0.95:
        return None
    prior_pe = forward_pe / (1 + six_month)
    if prior_pe < 8 or prior_pe > 80 or forward_pe < 8 or forward_pe > 150:
        return None
    return prior_pe


def momentum_structure(heat):
    vertical = heat.get("vertical")
    three_month = heat.get("three_month")
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    ticker_rsi = heat.get("rsi")

    if (six_month is not None and six_month < 0) or (dist_200 is not None and dist_200 < 0):
        return "Correction / Base-Building ⚠"

    parabolic = (
        (vertical is not None and vertical > 0.10 and ((six_month is not None and six_month > 0.25) or (dist_200 is not None and dist_200 > 0.20)))
        or (dist_200 is not None and dist_200 > 0.30)
        or (ticker_rsi is not None and ticker_rsi > 72)
    )
    if parabolic:
        return "Parabolic Acceleration Detected ⚠"
    if dist_200 is not None and dist_200 > 0.15:
        return "Strong Uptrend, Not Fully Parabolic"
    if three_month is not None and three_month > 0 and dist_200 is not None and dist_200 > 0.10:
        return "Moderate Momentum Recovery"
    if three_month is not None and three_month > 0:
        return "Constructive Momentum"
    return "Momentum Cooling / Base-Building"


def momentum_stage(heat):
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    three_month = heat.get("three_month")

    if (six_month is not None and six_month < 0) or (dist_200 is not None and dist_200 < 0):
        return "Cooling / Base-Building Phase"
    if (six_month is not None and six_month > 0.80) or (dist_200 is not None and dist_200 > 0.40):
        return "Late Momentum Phase"
    if (six_month is not None and six_month > 0.35) or (dist_200 is not None and dist_200 > 0.20):
        return "Mid-to-Late Momentum Phase"
    if three_month is not None and three_month > 0 and dist_200 is not None and dist_200 > 0.10:
        return "Early-to-Mid Momentum Repair Phase"
    if six_month is not None and six_month > 0.10:
        return "Early-to-Mid Momentum Phase"
    if three_month is not None and three_month > 0:
        return "Early Momentum Repair Phase"
    return "Accumulation / Reset Phase"


def valuation_risk_label(heat):
    if heat.get("forward_pe") is not None and heat["forward_pe"] < 0:
        return "Moderate Valuation Risk"
    score = heat.get("valuation_heat", 0)
    if score >= 60:
        return "Extreme Valuation Risk"
    if score >= 40:
        return "High Valuation Risk"
    if score >= 20:
        return "Moderate Valuation Risk"
    return "Low Valuation Risk"


def chase_risk_label(heat):
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    momentum = heat.get("momentum_heat", 0)

    if (six_month is not None and six_month < 0) or (dist_200 is not None and dist_200 < 0):
        return "Low Chase Risk"
    if momentum >= 55:
        return "High Chase Risk"
    if momentum >= 25:
        return "Moderate Chase Risk"
    return "Chase Risk Not Excessive"


def momentum_weakness_label(heat):
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    three_month = heat.get("three_month")

    weak_points = 0
    if six_month is not None and six_month < 0:
        weak_points += 1
    if dist_200 is not None and dist_200 < 0:
        weak_points += 1
    if three_month is not None and three_month < 0:
        weak_points += 1

    if weak_points >= 2:
        return "Moderate Momentum Weakness"
    if weak_points == 1:
        return "Mild Momentum Weakness"
    return None


def narrative_classification(quality, heat, rel_strength, pe_score):
    accel = quality.get("accel")
    fcf = quality.get("fcf")
    margin_expansion = quality.get("margin_expansion")
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    forward_pe = heat.get("forward_pe")

    stable_fcf = is_number(fcf) and fcf > 0
    mature_profile = (
        (accel is not None and accel < 0.10)
        and stable_fcf
        and (forward_pe is not None and forward_pe < 18)
    )
    market_weak = (
        (six_month is not None and six_month < 0)
        or (dist_200 is not None and dist_200 < 0)
        or (rel_strength is not None and rel_strength < 0.05)
    )
    unstable_earnings_base = forward_pe is not None and forward_pe < 0

    if accel is not None and accel > 0.25 and rel_strength is not None and rel_strength > 0.10 and pe_score >= 55:
        return {
            "label": "Accelerating 🚀",
            "drivers": [
                "earnings acceleration",
                "sector / stock outperformance",
                "institutional rerating interest",
            ],
            "interpretation": [
                "The company is participating in an active narrative with improving fundamentals and market confirmation.",
            ],
        }

    if accel is not None and accel > 0.20 and unstable_earnings_base and market_weak:
        return {
            "label": "Controversial / Uncertain ⚠",
            "drivers": [
                "strong user and revenue growth",
                "improving platform monetization",
                "weak institutional conviction",
                "unresolved long-term platform narrative",
            ],
            "interpretation": [
                "The company continues to show operational growth,",
                "but market confidence in long-term strategic relevance remains unstable.",
                "",
                "The stock is currently trading more as a controversial narrative asset",
                "than a fully validated institutional-quality platform.",
            ],
            "market_interpretation": [
                f"{quality.get('ticker', 'The company')} is no longer being treated as a straightforward",
                "high-growth platform leader by the market.",
                "",
                "The company continues to demonstrate user engagement",
                "and monetization progress, but institutional capital",
                "has not fully validated the long-term strategic narrative.",
                "",
                "The stock currently trades more as a controversial",
                "future-platform speculation rather than a fully trusted",
                "institutional compounder.",
            ],
        }

    if mature_profile and market_weak:
        return {
            "label": "Weakening Mature Platform ⚠",
            "drivers": [
                "stable free cash flow",
                "mature business profile",
                "slowing strategic relevance",
                "limited institutional rerating interest",
            ],
            "interpretation": [
                "The company remains financially stable,",
                "but current market behavior suggests declining narrative leadership.",
            ],
        }

    if stable_fcf and accel is not None and accel >= 0.10 and market_weak:
        return {
            "label": "Fundamentally Supported, Market Momentum Weakening",
            "drivers": [
                "positive earnings acceleration",
                "cash-flow support",
                "weak relative strength",
            ],
            "interpretation": [
                "Fundamentals remain supported, but market momentum has weakened.",
                "The stock needs confirmation before the narrative can be treated as active again.",
            ],
        }

    if stable_fcf and (accel is None or accel < 0.10):
        return {
            "label": "Stable Mature 🟡",
            "drivers": [
                "stable free cash flow",
                "mature growth profile",
                "limited rerating evidence",
            ],
            "interpretation": [
                "The business remains financially stable,",
                "but the market is not assigning strong narrative leadership.",
            ],
        }

    if quality.get("score", 50) < 60 and rel_strength is not None and rel_strength > 0:
        return {
            "label": "Market Momentum Improving, Fundamentals Mixed",
            "drivers": [
                "improving relative strength",
                "mixed financial quality",
                "limited cash-flow confirmation",
            ],
            "interpretation": [
                "The market is showing interest,",
                "but fundamentals are not yet strong enough to confirm durable narrative leadership.",
            ],
        }

    return {
        "label": "Developing / Neutral",
        "drivers": [
            "mixed earnings acceleration",
            "limited relative strength confirmation",
            "unclear institutional rerating interest",
        ],
        "interpretation": [
            "The narrative is still developing,",
            "and market confirmation is not decisive yet.",
        ],
    }


def overheat_assessment(narrative):
    heat = narrative["heat"]
    quality = narrative.get("quality", {})
    cooling = (
        (heat.get("six_month") is not None and heat["six_month"] < 0)
        or (heat.get("dist_200") is not None and heat["dist_200"] < 0)
    )
    classification = narrative.get("classification", {})
    if classification.get("label") == "Controversial / Uncertain ⚠":
        return [
            "Operational metrics remain resilient,",
            "but market behavior suggests ongoing uncertainty around",
            "long-term narrative durability and institutional conviction.",
        ]
    if classification.get("label") in {"Weakening Mature Platform ⚠", "Stable Mature 🟡"}:
        return classification.get("interpretation", [])
    if cooling and (narrative["score"] >= 55 or narrative.get("earnings_acceleration", 0) > 0.15):
        return [
            "Fundamentals remain strong, but market momentum has weakened.",
            "The stock is not in active chase mode; current risk is more about growth expectations and broader tech weakness than overheating.",
        ]
    if cooling:
        return [
            "Momentum is cooling and the stock is trying to rebuild a base.",
            "Wait for market confirmation before treating the narrative as active again.",
        ]
    if heat["momentum_heat"] >= 55:
        return [
            "Narrative remains fundamentally strong,",
            "but positioning appears increasingly crowded.",
        ]
    if heat["momentum_heat"] >= 25:
        if quality.get("score", 0) >= 75 and is_number(quality.get("fcf")) and quality["fcf"] > 0 and heat.get("valuation_heat", 0) >= 40:
            return [
                "The company remains financially high-quality with strong cash-flow support,",
                "but valuation risk is elevated and momentum is only moderately recovering.",
            ]
        return [
            "Narrative remains fundamentally supported,",
            "but entry discipline matters as momentum is warming.",
        ]
    if narrative["score"] >= 65:
        return [
            "Narrative remains fundamentally strong,",
            "and positioning is not yet showing extreme crowding.",
        ]
    return [
        "Narrative strength is still developing,",
        "and positioning does not show a clear chase-risk signal yet.",
    ]


def print_overheat_analysis(narrative):
    heat = narrative["heat"]
    prior_pe = implied_prior_forward_pe(heat)

    print("=================================================")
    print("POSITIONING / OVERHEAT ANALYSIS")
    print("=================================================")
    print()
    print("Price Performance:")
    print(signed_pct(heat.get("six_month")) + " (6M)")
    print()
    print("Forward PE Expansion:")
    if heat.get("forward_pe") is not None and heat["forward_pe"] < 0:
        print("Current forward PE: Negative / unstable earnings base")
        print("Valuation rerating proxy: High uncertainty")
    elif prior_pe and heat.get("forward_pe"):
        print(f"{fmt(prior_pe, 1)}x -> {fmt(heat['forward_pe'], 1)}x")
    elif heat.get("forward_pe"):
        print(f"Current forward PE: {fmt(heat['forward_pe'], 1)}x")
        print(f"Valuation rerating proxy: {intensity_label(narrative['pe_score'])}")
    else:
        print(f"Valuation rerating proxy: {intensity_label(narrative['pe_score'])}")
    print()
    print("Distance from 200MA:")
    print(signed_pct(heat.get("dist_200")))
    print()
    print("Momentum Structure:")
    print(momentum_structure(heat))
    print()
    print("Assessment:")
    for line in overheat_assessment(narrative):
        print(line)
    print()
    print("Current Stage:")
    if narrative.get("classification", {}).get("label") == "Controversial / Uncertain ⚠":
        print("Narrative Repricing / Identity Uncertainty Phase ⚠")
    else:
        print(momentum_stage(heat))
    print()
    print("Risk:")
    if narrative.get("classification", {}).get("label") == "Controversial / Uncertain ⚠":
        print("⚠ Narrative Credibility Risk")
        print("⚠ Institutional Conviction Uncertainty")
        weakness = momentum_weakness_label(heat)
        if weakness:
            print(f"⚠ {weakness}")
    else:
        print(f"⚠ {valuation_risk_label(heat)}")
        print(f"⚠ {chase_risk_label(heat)}")
        weakness = momentum_weakness_label(heat)
        if weakness:
            print(f"⚠ {weakness}")


def sector_positioning(key, sector_row=None):
    key = sector_key(key)
    tickers = SECTOR_CANDIDATES.get(key, [])
    sector_hist = fetch_history(key, "1y")
    spy_hist = fetch_history("SPY", "1y")
    sector_6m = price_change(sector_hist, 126)
    spy_6m = price_change(spy_hist, 126)
    rel_6m = sector_row.get("rel_6m") if sector_row else None
    if rel_6m is None and sector_6m is not None and spy_6m is not None:
        rel_6m = sector_6m - spy_6m

    ma200 = moving_average(sector_hist, 200)
    close = float(sector_hist["Close"].iloc[-1]) if sector_hist is not None else None
    dist_200 = (close / ma200 - 1) if close and ma200 else None
    one_month = price_change(sector_hist, 21)
    three_month = price_change(sector_hist, 63)
    vertical = one_month - (three_month / 3) if one_month is not None and three_month is not None else None
    sector_heat = {
        "one_month": one_month,
        "three_month": three_month,
        "six_month": sector_6m,
        "vertical": vertical,
        "dist_200": dist_200,
        "rsi": rsi(sector_hist),
        "heat": score_from_change(rel_6m, True, 0.25),
    }

    company_heat = heat_rows(tickers[:10]) if tickers else []
    forward_pes = [row["forward_pe"] for row in company_heat if row.get("forward_pe") and 8 <= row["forward_pe"] <= 120]
    current_sector_pe = statistics.median(forward_pes) if forward_pes else None
    prior_sector_pe = None
    if current_sector_pe and sector_6m is not None and sector_6m > -0.95:
        implied = current_sector_pe / (1 + sector_6m)
        if 8 <= implied <= 80:
            prior_sector_pe = implied

    breadth_rows = []
    for row in company_heat:
        participating = (
            (row.get("six_month") is not None and row["six_month"] > 0.10)
            or (row.get("dist_200") is not None and row["dist_200"] > 0.05)
            or (row.get("three_month") is not None and row["three_month"] > 0.05)
        )
        if participating:
            breadth_rows.append(row["ticker"])

    breadth_ratio = len(breadth_rows) / len(company_heat) if company_heat else 0
    if breadth_ratio >= 0.75:
        breadth_label = "Extremely Broad ⚠"
    elif breadth_ratio >= 0.50:
        breadth_label = "Broad"
    elif breadth_ratio >= 0.30:
        breadth_label = "Selective"
    else:
        breadth_label = "Narrow"

    crowded = (
        breadth_ratio >= 0.65
        and (
            (rel_6m is not None and rel_6m > 0.20)
            or (dist_200 is not None and dist_200 > 0.20)
            or momentum_structure(sector_heat).startswith("Parabolic")
        )
    )
    warming = breadth_ratio >= 0.45 or (rel_6m is not None and rel_6m > 0.10)

    if crowded:
        stage = "Late Sector Momentum Phase ⚠"
        risk = "Elevated thematic overcrowding risk"
        assessment = [
            "Institutional capital rotation remains strong,",
            f"but the {SECTOR_ETFS.get(key, key).lower()} trade is becoming increasingly crowded.",
        ]
    elif warming:
        stage = "Mid Sector Momentum Phase"
        risk = "Moderate thematic crowding risk"
        assessment = [
            "Institutional capital rotation is constructive,",
            "but participation is broadening and should be monitored for crowding.",
        ]
    else:
        stage = "Early / Selective Sector Momentum Phase"
        risk = "Thematic overcrowding risk not yet elevated"
        assessment = [
            "Institutional capital rotation is still selective,",
            "and sector-wide positioning does not yet look crowded.",
        ]

    return {
        "key": key,
        "name": SECTOR_THEME_NAMES.get(key, SECTOR_ETFS.get(key, key)),
        "relative_strength_6m": rel_6m,
        "current_sector_pe": current_sector_pe,
        "prior_sector_pe": prior_sector_pe,
        "breadth_label": breadth_label,
        "breadth_tickers": breadth_rows,
        "momentum_structure": "Parabolic Sector-Wide Acceleration" if momentum_structure(sector_heat).startswith("Parabolic") else momentum_structure(sector_heat),
        "assessment": assessment,
        "stage": stage,
        "risk": risk,
    }


def print_sector_positioning_analysis(positioning):
    print("=================================================")
    print("SECTOR POSITIONING ANALYSIS")
    print("=================================================")
    print()
    print("Sector:")
    print(positioning["name"])
    print()
    print("Relative Strength vs SPY:")
    print(signed_pct(positioning["relative_strength_6m"]) + " (6M)")
    print()
    print("Sector PE Expansion:")
    if positioning["prior_sector_pe"] and positioning["current_sector_pe"]:
        print(f"{fmt(positioning['prior_sector_pe'], 1)}x -> {fmt(positioning['current_sector_pe'], 1)}x")
    elif positioning["current_sector_pe"]:
        print(f"Current sector forward PE: {fmt(positioning['current_sector_pe'], 1)}x")
        print("Rerating proxy: Broad valuation expansion")
    else:
        print("Rerating proxy: Price momentum and breadth")
    print()
    print("Breadth Participation:")
    print(positioning["breadth_label"])
    if positioning["breadth_tickers"]:
        print("(" + ", ".join(positioning["breadth_tickers"][:8]) + " all participating)")
    print()
    print("Momentum Structure:")
    print(positioning["momentum_structure"])
    print()
    print("Assessment:")
    for line in positioning["assessment"]:
        print(line)
    print()
    print("Current Stage:")
    print(positioning["stage"])
    print()
    print("Risk:")
    print(positioning["risk"])


def narrative_strength(ticker):
    ticker = resolve_ticker(ticker)
    quality = company_quality_rows([ticker])[0]
    heat = heat_rows([ticker])[0]
    rel_strength = relative_change(ticker, "SPY", 63)
    rs_score = score_from_change(rel_strength, True, 0.15)
    earnings_accel = quality.get("accel")
    earnings_score = score_from_change(earnings_accel, True, 0.15)
    pe_score = pe_expansion_score(heat)
    total = rs_score * 0.45 + earnings_score * 0.35 + pe_score * 0.20
    quality_score = quality.get("score", 50)
    if quality_score < 60:
        total = min(total, 59)
    if rel_strength is not None and rel_strength < 0:
        total = min(total, 69)
    if heat.get("six_month") is not None and heat["six_month"] < 0:
        total = min(total, 69)

    classification = narrative_classification(quality, heat, rel_strength, pe_score)
    label = classification["label"]

    return {
        "ticker": ticker,
        "score": total,
        "label": label,
        "relative_strength": rel_strength,
        "rs_score": rs_score,
        "earnings_acceleration": earnings_accel,
        "earnings_score": earnings_score,
        "pe_score": pe_score,
        "classification": classification,
        "quality": quality,
        "heat": heat,
    }


def print_narrative_evidence(narrative):
    print(f"Narrative Strength: {narrative['label']}")
    print("Driven by:")
    for driver in narrative["classification"]["drivers"]:
        print(f"- {driver}")
    print()
    print("Interpretation:")
    for line in narrative["classification"]["interpretation"]:
        print(line)


def sector_key(raw):
    key = raw.lower().replace("_", "-")
    return SECTOR_ALIASES.get(key, key.upper())


def intensity_label(score, low="Low", mid="Moderate", high="High", extreme="Extreme"):
    if score >= 75:
        return extreme
    if score >= 50:
        return high
    if score >= 25:
        return mid
    return low


def print_macro_command():
    data = compute_macro()
    erp_negative = data["erp"] is not None and data["erp"] < 0
    dxy_rising = data["dxy_3m"] is not None and data["dxy_3m"] > 0

    print(macro_label(data["macro_score"]))
    print(f"10Y Yield: {pct(data['tnx_level'] / 100 if data['tnx_level'] else None)}")
    print("DXY Rising" if dxy_rising else "DXY Falling / Stable")
    if data["erp"] is None:
        print("ERP Unavailable")
    elif erp_negative:
        print("ERP Negative")
    else:
        print(f"ERP Positive / Neutral ({pct(data['erp'])})")
    print()
    print("Preferred Environment:")
    for item in preferred_environment(data["macro_score"], data["dxy_3m"], data["tnx_3m"]):
        print(item)


def print_sectors_command(show_all=False):
    rows = compute_sectors()
    print("Top Relative Strength Sectors:")
    print()
    limit = len(rows) if show_all else 3
    for idx, row in enumerate(rows[:limit], 1):
        print(f"{idx}. {row['name']} {emoji_for_sector(row['name'])}  ({signed_pct(row['rel_6m'])} 6M vs SPY)")


def print_sector_command(raw_sector):
    key = sector_key(raw_sector)
    tickers = SECTOR_CANDIDATES.get(key)
    if not tickers:
        print(f"No candidate basket found for '{raw_sector}'. Try semis, crypto, tech, utilities, energy, healthcare, or defensives.")
        return

    print("SPECIFIC SECTOR CONDITION REPORT")
    print()
    print(f"Selected sector: {SECTOR_THEME_NAMES.get(key, SECTOR_ETFS.get(key, key))}")
    print()

    quality = company_quality_rows(tickers)
    heat = {row["ticker"]: row for row in heat_rows([row["ticker"] for row in quality[:6]])}

    print("Top Institutional Quality Candidates:")
    print()
    for idx, row in enumerate(quality[:3], 1):
        print(f"{idx}. {row['ticker']}")

    print()
    print("Detail:")
    for row in quality[:3]:
        heat_score = heat.get(row["ticker"], {}).get("heat")
        print(f"{row['ticker']}:")
        print(f"  Revenue acceleration: {pct(row['accel'])}")
        print(f"  Margin expansion: {pct(row['margin_expansion'])}")
        print(f"  FCF: {fmt(row['fcf'] / 1e9 if is_number(row['fcf']) else None, 2, '', 'B')}")
        print(f"  Valuation risk: {intensity_label(heat_score or 0)}")

    print()
    print_sector_positioning_analysis(sector_positioning(key))


def print_risk_command(ticker):
    ticker = resolve_ticker(ticker)
    narrative = narrative_strength(ticker)
    row = narrative["heat"]

    print_narrative_evidence(narrative)
    print(f"Valuation Expansion: {intensity_label(row['valuation_heat'], high='High', extreme='Extreme')}")
    print(f"Momentum Heat: {intensity_label(row['momentum_heat'], high='Elevated', extreme='Extreme')}")
    print()
    print_overheat_analysis(narrative)


def print_company_command(ticker):
    requested_ticker = ticker.upper()
    ticker = resolve_ticker(ticker)
    narrative = narrative_strength(ticker)
    quality = narrative["quality"]
    heat = narrative["heat"]

    print("SPECIFIC COMPANY CONDITION REPORT")
    print()
    if ticker != requested_ticker:
        print(f"Company: {ticker} (alias for {requested_ticker})")
    else:
        print(f"Company: {ticker}")
    print()
    print(f"Revenue acceleration: {pct(quality['accel'])}")
    print(f"Margin expansion: {pct(quality['margin_expansion'])}")
    print(f"FCF: {fmt(quality['fcf'] / 1e9 if is_number(quality['fcf']) else None, 2, '', 'B')}")
    print(f"Quality score: {fmt(quality['score'], 1)}")
    print(f"Valuation risk: {valuation_risk_label(heat).replace(' Valuation Risk', '')}")
    print()
    print_narrative_evidence(narrative)
    print(f"Valuation Expansion: {intensity_label(heat['valuation_heat'], high='High', extreme='Extreme')}")
    print(f"Momentum Heat: {intensity_label(heat['momentum_heat'], high='Elevated', extreme='Extreme')}")
    print()
    print_overheat_analysis(narrative)
    market_interpretation = narrative.get("classification", {}).get("market_interpretation")
    if market_interpretation:
        print()
        print("=================================================")
        print("MARKET INTERPRETATION")
        print("=================================================")
        print()
        for line in market_interpretation:
            print(line)


def print_conclusion_command():
    macro = compute_macro()
    sectors = compute_sectors()
    leader = sectors[0] if sectors else None
    key = leader["ticker"] if leader else "SMH"
    candidates = company_quality_rows(SECTOR_CANDIDATES.get(key, SECTOR_CANDIDATES["SMH"]))
    top_names = ", ".join(row["ticker"] for row in candidates[:3])
    heat = heat_rows([row["ticker"] for row in candidates[:3]])
    avg_heat = sum(row["heat"] for row in heat) / len(heat) if heat else 0

    leader_text = leader["name"] if leader else "AI infrastructure"
    print(f"Institutional capital rotation into {leader_text} remains {'strong' if leader and leader['score'] >= 65 else 'selective'}.")
    print()
    print("Macro conditions:")
    print(macro_label(macro["macro_score"]).replace(" ⚠", "").replace(" 🚀", ""))
    print()
    print("Preferred targets:")
    if key == "SMH":
        print("Strong cash-flow semis with accelerating margins")
    else:
        print(f"Highest-quality leaders in {leader_text}")
    print(f"Current candidates: {top_names}")
    print()
    print("Current risk:")
    print(f"{intensity_label(avg_heat, low='Low valuation stretch', mid='Moderate valuation stretch', high='High valuation stretch', extreme='Extreme valuation stretch')}")


def commentary_lines(macro, leader, candidates, candidate_narrative):
    leader_text = leader["name"] if leader else "the leading risk pocket"
    top = candidates[0]["ticker"] if candidates else "the highest-quality leaders"
    macro_text = macro_label(macro["macro_score"]).replace(" ⚠", "").replace(" 🚀", "").lower()
    heat = candidate_narrative["heat"] if candidate_narrative else {"heat": 0}

    lines = [
        f"Institutional capital rotation remains concentrated in {leader_text}, while the macro backdrop is {macro_text}.",
        f"The strongest candidates are being selected for acceleration and cash-flow quality, with {top} currently screening as the leading institutional target.",
    ]

    if heat["heat"] >= 70:
        lines.append("The opportunity is real, but positioning is crowded; this is a chase-risk environment rather than a clean early entry.")
    elif heat["heat"] >= 45:
        lines.append("The setup remains constructive, but momentum is warming and entries need more discipline.")
    else:
        lines.append("The narrative remains supported without clear evidence of extreme positioning pressure.")

    return lines


def print_full_command():
    macro = compute_macro()
    sectors = compute_sectors()
    leader = sectors[0] if sectors else None
    key = leader["ticker"] if leader else "SMH"
    candidates = company_quality_rows(SECTOR_CANDIDATES.get(key, SECTOR_CANDIDATES["SMH"]))
    top_candidate = candidates[0] if candidates else None
    candidate_narrative = narrative_strength(top_candidate["ticker"]) if top_candidate else None
    candidate_heat = candidate_narrative["heat"] if candidate_narrative else None
    sector_positioning_report = sector_positioning(key, leader) if leader else None

    print("MARKET INTELLIGENCE REPORT")
    print()
    for line in commentary_lines(macro, leader, candidates, candidate_narrative):
        print(line)
    print()
    print("Macro:")
    print(macro_label(macro["macro_score"]))
    print(f"10Y Yield: {pct(macro['tnx_level'] / 100 if macro['tnx_level'] else None)}")
    print("DXY Rising" if macro["dxy_3m"] and macro["dxy_3m"] > 0 else "DXY Falling / Stable")
    print()

    print("Top Relative Strength Sectors:")
    for idx, row in enumerate(sectors[:3], 1):
        print(f"{idx}. {row['name']} {emoji_for_sector(row['name'])}")
    print()

    print("Top Institutional Quality Candidates:")
    for idx, row in enumerate(candidates[:3], 1):
        print(f"{idx}. {row['ticker']}")
    print()

    if top_candidate and candidate_heat:
        print(f"Chase Risk Check: {top_candidate['ticker']}")
        print_narrative_evidence(candidate_narrative)
        print(f"Valuation Expansion: {intensity_label(candidate_heat['valuation_heat'], high='High', extreme='Extreme')}")
        print(f"Momentum Heat: {intensity_label(candidate_heat['momentum_heat'], high='Elevated', extreme='Extreme')}")
        print()
        print_overheat_analysis(candidate_narrative)
        print()

    if sector_positioning_report:
        print_sector_positioning_analysis(sector_positioning_report)
        print()

    print("Conclusion:")
    leader_text = leader["name"] if leader else "AI infrastructure"
    print(f"Institutional capital rotation into {leader_text} remains {'strong' if leader and leader['score'] >= 65 else 'selective'}.")
    print(f"Macro conditions: {macro_label(macro['macro_score']).replace(' ⚠', '').replace(' 🚀', '')}")
    if key == "SMH":
        print("Preferred targets: Strong cash-flow semis with accelerating margins")
    else:
        print(f"Preferred targets: Highest-quality leaders in {leader_text}")
    if candidate_heat:
        print(f"Current risk: {intensity_label(candidate_heat['heat'], low='Low valuation stretch', mid='Moderate valuation stretch', high='High valuation stretch', extreme='Extreme valuation stretch')}")
    if sector_positioning_report:
        print(f"Theme risk: {sector_positioning_report['risk']}")


def print_usage():
    print("Market Intelligence System")
    print()
    print("1. Macro Regime Scan")
    print("2. Hottest Sector Leaderboard")
    print("3. Specific Sector Condition / Crowding")
    print("4. Specific Company Condition / Chase Risk")
    print("5. Company Overheat Check")
    print("6. Full Hottest-Market Report")
    print()
    print("Usage:")
    print("  python model.py                 # or: python Valuation_model.py")
    print("  python model.py full            # hottest sector + hottest company")
    print("  python model.py sectors         # sector leaderboard")
    print("  python model.py sectors all     # full sector leaderboard")
    print("  python model.py sector semis    # specific sector condition")
    print("  python model.py theme utilities # alias for sector")
    print("  python model.py company NVDA    # specific company condition")
    print("  python model.py stock MU        # alias for company")


def normalize_args(raw):
    if isinstance(raw, str):
        parts = raw.strip().split()
    else:
        parts = list(raw)

    if len(parts) >= 2 and parts[0].lower().startswith("python") and parts[1].lower().endswith(".py"):
        parts = parts[2:]
    elif parts and parts[0].lower().endswith(".py"):
        parts = parts[1:]

    return parts


def prompt_value(label, default=None):
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def run_menu():
    print_usage()
    print()
    args = normalize_args(input("Select: "))

    if not args:
        return

    choice = args[0].lower()

    if choice in {"1", "macro"}:
        print_macro_command()
    elif choice in {"2", "sectors"}:
        print_sectors_command(show_all=len(args) >= 2 and args[1].lower() == "all")
    elif choice in {"3", "sector", "theme", "sector-condition", "check-sector"}:
        sector = args[1] if len(args) >= 2 else prompt_value("Sector", "semis")
        print_sector_command(sector)
    elif choice in {"4", "company", "stock", "company-condition", "check-company"}:
        ticker = args[1] if len(args) >= 2 else prompt_value("Ticker", "NVDA")
        print_company_command(ticker)
    elif choice in {"5", "risk"}:
        ticker = args[1] if len(args) >= 2 else prompt_value("Ticker", "NVDA")
        print_risk_command(ticker)
    elif choice in {"6", "full"}:
        print_full_command()
    elif choice == "conclusion":
        print_conclusion_command()
    else:
        print("Invalid selection.")


def run_cli(args):
    args = normalize_args(args)
    if not args:
        run_menu()
        return

    command = args[0].lower()
    if command in {"1", "macro"}:
        print_macro_command()
    elif command in {"2", "sectors"}:
        print_sectors_command(show_all=len(args) >= 2 and args[1].lower() == "all")
    elif command in {"3", "sector", "theme", "sector-condition", "check-sector"}:
        sector = args[1] if len(args) >= 2 else "semis"
        print_sector_command(sector)
    elif command in {"4", "company", "stock", "company-condition", "check-company"}:
        ticker = args[1] if len(args) >= 2 else "NVDA"
        print_company_command(ticker)
    elif command in {"5", "risk"}:
        ticker = args[1] if len(args) >= 2 else "NVDA"
        print_risk_command(ticker)
    elif command in {"6", "full"}:
        print_full_command()
    elif command == "conclusion":
        print_conclusion_command()
    else:
        print_usage()


# Layer 1
def macro_regime_engine():
    divider("LAYER 1 - MACRO REGIME ENGINE")
    print("  Mapping which asset class is attracting capital through rates, USD, and risk preference.")

    tnx_ticker, tnx = fetch_first_history(["^TNX"], "1y")
    front_rate_ticker, front_rate = fetch_first_history(["2YY=F", "^IRX", "^FVX"], "1y")
    dxy = fetch_history("DX-Y.NYB", "1y")
    vix = fetch_history("^VIX", "1y")
    hyg_ief = relative_change("HYG", "IEF", 63)

    tnx_level = last_close(tnx_ticker)
    front_rate_level = last_close(front_rate_ticker)
    dxy_level = last_close("DX-Y.NYB")
    vix_level = last_close("^VIX")

    tnx_3m = price_change(tnx, 63)
    front_rate_3m = price_change(front_rate, 63)
    dxy_3m = price_change(dxy, 63)

    yield_curve = None
    if is_number(tnx_level) and is_number(front_rate_level) and front_rate_ticker != "^IRX":
        yield_curve = (tnx_level - front_rate_level) / 100

    rate_score = score_from_change(tnx_3m, bullish_when_positive=False, scale=0.12)
    front_rate_score = score_from_change(front_rate_3m, bullish_when_positive=False, scale=0.12)
    usd_score = score_from_change(dxy_3m, bullish_when_positive=False, scale=0.06)
    curve_score = 60 if yield_curve and yield_curve > 0 else 40 if yield_curve and yield_curve < 0 else 50
    vix_score = 75 if vix_level and vix_level < 16 else 60 if vix_level and vix_level < 22 else 35 if vix_level else 50
    credit_score = score_from_change(hyg_ief, bullish_when_positive=True, scale=0.05)

    liquidity_score = (rate_score * 0.30) + (front_rate_score * 0.15) + (usd_score * 0.25) + (curve_score * 0.10) + (credit_score * 0.20)
    risk_score = (vix_score * 0.55) + (credit_score * 0.45)
    macro_score = (liquidity_score * 0.60) + (risk_score * 0.40)

    print()
    print_row("10Y yield", pct(tnx_level / 100 if tnx_level else None), f"3M change {pct(tnx_3m)}")
    print_row("2Y / front-rate proxy", pct(front_rate_level / 100 if front_rate_level else None), f"{front_rate_ticker}; 3M change {pct(front_rate_3m)}")
    print_row("2Y / 10Y curve", pct(yield_curve), "positive curve supports easier capital allocation")
    print_row("DXY", fmt(dxy_level), f"3M change {pct(dxy_3m)}")
    print_row("VIX", fmt(vix_level), "risk appetite gauge")
    print_row("HYG vs IEF", pct(hyg_ief), "credit risk preference proxy")
    print()
    print_row("Liquidity / cost of capital", fmt(liquidity_score, 1), band(liquidity_score))
    print_row("Market risk preference", fmt(risk_score, 1), band(risk_score))
    print_row("Macro regime score", fmt(macro_score, 1), band(macro_score))

    asset_rows = []
    for ticker, label in ASSET_PROXIES.items():
        hist = fetch_history(ticker, "1y")
        one_month = price_change(hist, 21)
        three_month = price_change(hist, 63)
        six_month = price_change(hist, 126)
        rel = three_month if ticker == "SPY" else relative_change(ticker, "SPY", 63)
        score = (
            score_from_change(one_month, True, 0.08) * 0.30
            + score_from_change(three_month, True, 0.14) * 0.35
            + score_from_change(six_month, True, 0.22) * 0.20
            + score_from_change(rel, True, 0.12) * 0.15
        )
        asset_rows.append({
            "ticker": ticker,
            "label": label,
            "score": score,
            "one_month": one_month,
            "three_month": three_month,
            "six_month": six_month,
            "rel": rel,
        })

    asset_rows.sort(key=lambda row: row["score"], reverse=True)
    print("\n  Asset attraction map:")
    print(f"  {'Proxy':<6} {'Asset':<22} {'Score':>7} {'1M':>9} {'3M':>9} {'6M':>9} {'3M vs SPY':>11}")
    print(f"  {'-' * 76}")
    for row in asset_rows[:5]:
        print(
            f"  {row['ticker']:<6} {row['label']:<22} {row['score']:>7.1f} "
            f"{pct(row['one_month']):>9} {pct(row['three_month']):>9} {pct(row['six_month']):>9} {pct(row['rel']):>11}"
        )

    unavailable = ", ".join(MANUAL_MACRO_INDICATORS)
    print(f"\n  Manual / external data needed for full macro stack: {unavailable}.")

    if macro_score >= 65:
        narrative = "Liquidity easing: valuation pressure falls, growth and long-duration narratives can rerate."
    elif macro_score <= 40:
        narrative = "Liquidity tightening: USD/rates/risk stress can compress multiples and pull capital defensive."
    else:
        narrative = "Mixed macro: capital rotates selectively toward sectors with clear earnings and narrative support."

    print(f"\n  Regime read: {narrative}")

    return {
        "macro_score": macro_score,
        "liquidity_score": liquidity_score,
        "risk_score": risk_score,
        "narrative": narrative,
    }


# Layer 2
def sector_rotation_engine():
    divider("LAYER 2 - WHERE CAPITAL IS GOING")
    print("  Ranking sectors by relative strength vs SPY, multi-period momentum, and breakout strength.")

    rows = []
    for ticker, name in SECTOR_ETFS.items():
        hist = fetch_history(ticker, "1y")
        if hist is None:
            continue

        rel_1m = relative_change(ticker, "SPY", 21)
        rel_3m = relative_change(ticker, "SPY", 63)
        rel_6m = relative_change(ticker, "SPY", 126)
        absolute_3m = price_change(hist, 63)
        close = float(hist["Close"].iloc[-1])
        high_252 = float(hist["Close"].tail(252).max())
        breakout = (close / high_252 - 1) if high_252 else None

        momentum_score = (
            score_from_change(rel_1m, True, 0.06) * 0.35
            + score_from_change(rel_3m, True, 0.10) * 0.40
            + score_from_change(rel_6m, True, 0.16) * 0.25
        )
        breakout_score = score_from_change(breakout, True, 0.08)
        score = momentum_score * 0.75 + breakout_score * 0.25

        rows.append({
            "ticker": ticker,
            "name": name,
            "rel_1m": rel_1m,
            "rel_3m": rel_3m,
            "rel_6m": rel_6m,
            "absolute_3m": absolute_3m,
            "breakout": breakout,
            "score": score,
        })

    rows.sort(key=lambda row: row["score"], reverse=True)

    print()
    print(f"  {'ETF':<6} {'Sector / Asset':<28} {'Score':>7} {'1M RS':>10} {'3M RS':>10} {'6M RS':>10} {'Breakout':>10}")
    print(f"  {'-' * 88}")
    for row in rows[:10]:
        print(
            f"  {row['ticker']:<6} {row['name']:<28} {row['score']:>7.1f} "
            f"{pct(row['rel_1m']):>10} {pct(row['rel_3m']):>10} {pct(row['rel_6m']):>10} {pct(row['breakout']):>10}"
        )

    if rows:
        leader = rows[0]
        print(f"\n  Rotation read: capital is most visibly rotating toward {leader['name']} ({leader['ticker']}).")

    return rows


# Layer 3
def revenue_acceleration(ticker_obj):
    try:
        income = ticker_obj.quarterly_income_stmt
        if income is None or income.empty or "Total Revenue" not in income.index:
            return None
        revenue = income.loc["Total Revenue"].dropna()
        if len(revenue) < 5:
            return None
        latest_yoy = (float(revenue.iloc[0]) / float(revenue.iloc[4])) - 1
        previous_yoy = (float(revenue.iloc[1]) / float(revenue.iloc[5])) - 1 if len(revenue) >= 6 else None
        if previous_yoy is None:
            return latest_yoy
        return latest_yoy - previous_yoy
    except Exception:
        return None


def operating_margin_expansion(ticker_obj):
    try:
        income = ticker_obj.quarterly_income_stmt
        if income is None or income.empty:
            return None
        if "Total Revenue" not in income.index:
            return None
        margin_row = None
        for candidate in ["Operating Income", "Pretax Income", "Net Income"]:
            if candidate in income.index:
                margin_row = candidate
                break
        if margin_row is None:
            return None
        revenue = income.loc["Total Revenue"].dropna()
        margin_income = income.loc[margin_row].dropna()
        if len(revenue) < 5 or len(margin_income) < 5:
            return None
        latest_margin = float(margin_income.iloc[0]) / float(revenue.iloc[0])
        prior_year_margin = float(margin_income.iloc[4]) / float(revenue.iloc[4])
        return latest_margin - prior_year_margin
    except Exception:
        return None


def latest_operating_margin(ticker_obj):
    try:
        income = ticker_obj.quarterly_income_stmt
        if income is None or income.empty:
            return None
        if "Total Revenue" not in income.index:
            return None
        margin_row = None
        for candidate in ["Operating Income", "Pretax Income", "Net Income"]:
            if candidate in income.index:
                margin_row = candidate
                break
        if margin_row is None:
            return None
        revenue = income.loc["Total Revenue"].dropna()
        margin_income = income.loc[margin_row].dropna()
        if len(revenue) < 1 or len(margin_income) < 1 or float(revenue.iloc[0]) == 0:
            return None
        return float(margin_income.iloc[0]) / float(revenue.iloc[0])
    except Exception:
        return None


def trailing_free_cash_flow(ticker_obj):
    try:
        cashflow = ticker_obj.quarterly_cashflow
        if cashflow is None or cashflow.empty or "Free Cash Flow" not in cashflow.index:
            cashflow = ticker_obj.cashflow
        if cashflow is None or cashflow.empty or "Free Cash Flow" not in cashflow.index:
            return None
        fcf = cashflow.loc["Free Cash Flow"].dropna()
        if len(fcf) == 0:
            return None
        if len(fcf) >= 4:
            return float(fcf.iloc[:4].sum())
        return float(fcf.iloc[0])
    except Exception:
        return None


def company_quality_engine(tickers):
    divider("LAYER 3 - INSTITUTIONAL TARGET QUALITY")
    print("  Looking for companies in the active narrative that have growth, margin, cash flow, and execution quality.")

    rows = []
    for ticker in tickers:
        t = yf.Ticker(ticker)
        try:
            info = t.info
        except Exception:
            info = {}

        rev_growth = safe(info, "revenueGrowth")
        earnings_growth = safe(info, "earningsGrowth", "earningsQuarterlyGrowth")
        op_margin = safe(info, "operatingMargins")
        gross_margin = safe(info, "grossMargins")
        roe = safe(info, "returnOnEquity", "returnOnAssets")
        fcf = safe(info, "freeCashflow")
        cash = safe(info, "totalCash", default=0)
        debt = safe(info, "totalDebt", default=0)
        accel = revenue_acceleration(t)
        margin_expansion = operating_margin_expansion(t)

        growth_score = (
            score_from_change(rev_growth, True, 0.25) * 0.45
            + score_from_change(earnings_growth, True, 0.35) * 0.35
            + score_from_change(accel, True, 0.10) * 0.20
        )
        profitability_score = (
            score_from_change(op_margin, True, 0.30) * 0.35
            + score_from_change(gross_margin, True, 0.55) * 0.25
            + score_from_change(roe, True, 0.30) * 0.25
            + score_from_change(margin_expansion, True, 0.08) * 0.15
        )
        cash_score = 50
        if is_number(fcf):
            cash_score += 20 if fcf > 0 else -20
        if is_number(cash) and is_number(debt):
            cash_score += 15 if cash > debt else -10
        cash_score = clamp(cash_score)

        quality_score = growth_score * 0.40 + profitability_score * 0.35 + cash_score * 0.25

        rows.append({
            "ticker": ticker,
            "name": safe(info, "shortName", "longName", default=ticker),
            "rev_growth": rev_growth,
            "earnings_growth": earnings_growth,
            "op_margin": op_margin,
            "roe": roe,
            "fcf": fcf,
            "net_cash": (cash - debt) if is_number(cash) and is_number(debt) else None,
            "accel": accel,
            "margin_expansion": margin_expansion,
            "score": quality_score,
        })

    rows.sort(key=lambda row: row["score"], reverse=True)

    print()
    print(f"  {'Ticker':<8} {'Company':<28} {'Score':>7} {'Rev':>9} {'EPS':>9} {'Op Mrg':>9} {'ROE/ROA':>9} {'Accel':>9}")
    print(f"  {'-' * 96}")
    for row in rows:
        print(
            f"  {row['ticker']:<8} {row['name'][:28]:<28} {row['score']:>7.1f} "
            f"{pct(row['rev_growth']):>9} {pct(row['earnings_growth']):>9} {pct(row['op_margin']):>9} "
            f"{pct(row['roe']):>9} {pct(row['accel']):>9}"
        )

    return rows


# Layer 4
def heat_engine(tickers):
    divider("LAYER 4 - CHASE RISK / OVERHEATING")
    print("  Measuring valuation stretch, momentum heat, distance from moving averages, and vertical price acceleration.")

    rows = []
    for ticker in tickers:
        t = yf.Ticker(ticker)
        try:
            info = t.info
        except Exception:
            info = {}
        hist = fetch_history(ticker, "1y")

        current = float(hist["Close"].iloc[-1]) if hist is not None else safe(info, "currentPrice", "regularMarketPrice")
        ma50 = moving_average(hist, 50)
        ma200 = moving_average(hist, 200)
        ticker_rsi = rsi(hist)
        one_month = price_change(hist, 21)
        three_month = price_change(hist, 63)
        vertical = one_month - (three_month / 3) if one_month is not None and three_month is not None else None

        forward_pe = safe(info, "forwardPE")
        peg = safe(info, "pegRatio", "trailingPegRatio")
        ev_sales = safe(info, "enterpriseToRevenue", "priceToSalesTrailing12Months")

        dist_50 = (current / ma50 - 1) if current and ma50 else None
        dist_200 = (current / ma200 - 1) if current and ma200 else None

        valuation_heat = 0
        valuation_heat += 25 if forward_pe and forward_pe > 45 else 15 if forward_pe and forward_pe > 30 else 5
        valuation_heat += 20 if peg and peg > 2.5 else 10 if peg and peg > 1.5 else 0
        valuation_heat += 20 if ev_sales and ev_sales > 12 else 10 if ev_sales and ev_sales > 7 else 0

        momentum_heat = 0
        momentum_heat += 25 if ticker_rsi and ticker_rsi > 75 else 15 if ticker_rsi and ticker_rsi > 65 else 0
        momentum_heat += 20 if dist_50 and dist_50 > 0.18 else 10 if dist_50 and dist_50 > 0.10 else 0
        momentum_heat += 20 if dist_200 and dist_200 > 0.45 else 10 if dist_200 and dist_200 > 0.25 else 0
        momentum_heat += 15 if vertical and vertical > 0.10 else 8 if vertical and vertical > 0.05 else 0

        heat_score = clamp(valuation_heat + momentum_heat)
        rows.append({
            "ticker": ticker,
            "forward_pe": forward_pe,
            "peg": peg,
            "ev_sales": ev_sales,
            "rsi": ticker_rsi,
            "dist_50": dist_50,
            "dist_200": dist_200,
            "vertical": vertical,
            "heat": heat_score,
        })

    rows.sort(key=lambda row: row["heat"], reverse=True)

    print()
    print(f"  {'Ticker':<8} {'Heat':>7} {'Fwd PE':>9} {'PEG':>8} {'EV/Sales':>10} {'RSI':>8} {'>50MA':>9} {'>200MA':>9}")
    print(f"  {'-' * 84}")
    for row in rows:
        print(
            f"  {row['ticker']:<8} {row['heat']:>7.1f} {fmt(row['forward_pe']):>9} {fmt(row['peg']):>8} "
            f"{fmt(row['ev_sales']):>10} {fmt(row['rsi']):>8} {pct(row['dist_50']):>9} {pct(row['dist_200']):>9}"
        )

    return rows


# Layer 5
def final_output(macro, sectors, quality_rows, heat_rows):
    divider("LAYER 5 - MARKET STRUCTURE OUTPUT")

    leading_sector = sectors[0] if sectors else None
    quality_by_ticker = {row["ticker"]: row for row in quality_rows}
    heat_by_ticker = {row["ticker"]: row for row in heat_rows}

    print("  This is not a buy/sell engine. It describes liquidity, capital flow, rerating, narrative acceleration, and positioning risk.")
    print()
    print_row("Macro regime", fmt(macro["macro_score"], 1), macro["narrative"])
    if leading_sector:
        print_row("Capital flow leader", f"{leading_sector['ticker']} / {leading_sector['name']}", f"rotation score {leading_sector['score']:.1f}")

    if quality_rows:
        best = quality_rows[0]
        heat = heat_by_ticker.get(best["ticker"], {})
        heat_score = heat.get("heat")
        if heat_score is None:
            risk = "heat not measured"
        elif heat_score >= 70:
            risk = "rerating is hot; chase risk is elevated"
        elif heat_score >= 45:
            risk = "rerating is active; entry discipline matters"
        else:
            risk = "quality is present without obvious momentum overheating"

        print_row("Institutional target", f"{best['ticker']} / {best['name'][:22]}", f"quality score {best['score']:.1f}; {risk}")

    print("\n  Framework read:")
    if macro["macro_score"] >= 65 and leading_sector and leading_sector["score"] >= 65:
        print("  Liquidity and sector rotation are aligned. The market is rewarding the leading narrative with multiple expansion.")
    elif macro["macro_score"] <= 40:
        print("  Macro pressure is dominant. Capital may prefer defensives, cash-flow durability, USD exposure, or commodities until rates/USD/risk improve.")
    elif leading_sector and leading_sector["score"] >= 65:
        print("  Sector rotation is strong even though macro is mixed. This is a selective narrative market, not broad beta expansion.")
    else:
        print("  No clean capital rotation signal yet. Watch for improving relative strength plus falling cost-of-capital pressure.")

    if quality_rows:
        print("\n  Company lens:")
        for row in quality_rows:
            heat = heat_by_ticker.get(row["ticker"], {}).get("heat")
            heat_label = "overheated" if heat and heat >= 70 else "warm" if heat and heat >= 45 else "not stretched"
            print(f"  - {row['ticker']}: quality {row['score']:.1f}, heat {fmt(heat, 1)} ({heat_label}).")


def run_framework(tickers):
    macro = macro_regime_engine()
    sectors = sector_rotation_engine()
    quality_rows = company_quality_engine(tickers) if tickers else []
    heat_rows = heat_engine(tickers) if tickers else []
    final_output(macro, sectors, quality_rows, heat_rows)


if __name__ == "__main__":
    run_cli(sys.argv[1:])
