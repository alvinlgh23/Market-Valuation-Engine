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
import csv
import io
import math
import re
import statistics
import sys
import urllib.request

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
    "QTUM": "Quantum Computing",
    "UFO": "Space / Satellite Infrastructure",
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
    "quantum": "QTUM",
    "quantum-computing": "QTUM",
    "quantumcomputing": "QTUM",
    "space": "UFO",
    "space-sector": "UFO",
    "satellite": "UFO",
    "satellites": "UFO",
    "rklb": "UFO",
    "consumer-discretionary": "XLY",
    "consumerdiscretionary": "XLY",
    "discretionary": "XLY",
    "communication": "XLC",
    "communication-services": "XLC",
    "communications": "XLC",
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
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "LOW", "BKNG", "TJX", "SBUX", "NKE", "ORLY"],
    "XLC": ["META", "GOOGL", "NFLX", "TMUS", "DIS", "SPOT", "VZ", "T", "CMCSA", "CHTR"],
    "IBIT": ["COIN", "MSTR", "MARA", "RIOT", "CLSK", "IREN", "HOOD", "XYZ", "CME", "IBIT"],
    "QTUM": ["IONQ", "RGTI", "QBTS", "QUBT", "ARQQ", "LAES", "IBM", "HON"],
    "UFO": ["RKLB", "LUNR", "RDW", "PL", "ASTS", "IRDM", "GSAT", "VSAT", "BKSY", "SPIR"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY", "HAL"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "VST", "AEP", "SRE", "D", "EXC", "PEG"],
    "XLP": ["WMT", "COST", "PG", "KO", "PEP", "PM", "MDLZ", "CL", "MO", "KMB"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "ISRG", "AMGN", "DHR"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK"],
    "XLI": ["GE", "CAT", "RTX", "UNP", "HON", "ETN", "DE", "BA", "LMT", "UPS"],
    "XLB": ["LIN", "SHW", "FCX", "NEM", "ECL", "APD", "CTVA", "DOW", "NUE", "MLM"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "SPG", "O", "DLR", "PSA", "CCI", "CBRE"],
    "IGV": ["MSFT", "ORCL", "CRM", "ADBE", "NOW", "INTU", "SNOW", "DDOG", "MDB", "TEAM"],
    "CIBR": ["PANW", "CRWD", "FTNT", "ZS", "OKTA", "NET", "S", "CHKP", "VRNS", "TENB"],
    "XBI": ["VRTX", "REGN", "ALNY", "BMRN", "INCY", "EXAS", "TECH", "SRPT", "HALO", "IONS"],
    "KRE": ["FITB", "HBAN", "RF", "KEY", "CFG", "TFC", "MTB", "FHN", "WAL", "ZION"],
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
    "SLV": ["PAAS", "AG", "HL", "WPM", "SILV", "SVM", "FSM", "EXK", "CDE", "SSRM"],
    "DBA": ["ADM", "BG", "MOS", "CF", "NTR", "DE", "CTVA", "TSN", "CALM", "FMC"],
    "KWEB": ["BABA", "PDD", "JD", "BIDU", "TME", "NTES", "BILI", "BEKE", "TAL", "VIPS"],
    "DBC": ["XOM", "CVX", "FCX", "NEM", "AA", "MOS", "CF", "TECK", "VALE", "RIO"],
    "GLD": ["NEM", "GOLD", "AEM", "WPM", "FNV", "KGC", "PAAS", "AGI", "GFI", "HMY"],
}

SECTOR_THEME_NAMES = {
    "SMH": "Semiconductors / AI Memory",
    "XLK": "Technology / AI Software",
    "XLY": "Consumer Discretionary",
    "XLC": "Communication Services",
    "IBIT": "Crypto Infrastructure",
    "QTUM": "Quantum Computing",
    "UFO": "Space / Satellite Infrastructure",
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
    return f"{v * 100:.2f}%" if is_number(v) else "Unavailable"


def signed_pct(v):
    return f"{v * 100:+.2f}%" if is_number(v) else "Unavailable"


def signed_fmt(v, decimals=1, suffix=""):
    if not is_number(v):
        return "Unavailable"
    return f"{v:+.{decimals}f}{suffix}"


def fmt(v, decimals=2, prefix="", suffix=""):
    if not is_number(v):
        return "Unavailable"
    return f"{prefix}{v:,.{decimals}f}{suffix}"


def signed_number(v, decimals=0):
    if not is_number(v):
        return "Unavailable"
    return f"{v:+,.{decimals}f}"


def point_distance(value, threshold, decimals=2):
    if not is_number(value) or not is_number(threshold):
        return "Unavailable"
    diff = value - threshold
    direction = "above" if diff >= 0 else "below"
    return f"{abs(diff):.{decimals}f} points {direction} threshold"


def pct_point_distance(value, threshold):
    if not is_number(value) or not is_number(threshold):
        return "Unavailable"
    diff = value - threshold
    direction = "above" if diff >= 0 else "below"
    return f"{abs(diff):.2f} percentage points {direction} threshold"


def trend_distance(value):
    if not is_number(value):
        return "Unavailable"
    direction = "above" if value >= 0 else "below"
    return f"{abs(value) * 100:.2f} percentage points {direction} flat trend line"


def trend_threshold_distance(value, threshold):
    if not is_number(value) or not is_number(threshold):
        return "Unavailable"
    diff = value - threshold
    direction = "above" if diff >= 0 else "below"
    return f"{abs(diff) * 100:.2f} percentage points {direction} threshold"


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
    if "quantum" in lowered:
        return "⚛"
    if "space" in lowered or "satellite" in lowered:
        return "🛰"
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


def liquidity_regime_label(score):
    if score >= 65:
        return "Loose"
    if score >= 50:
        return "Neutral"
    if score >= 40:
        return "Neutral-to-Tight"
    return "Tight"


def risk_perception_label(vix_level):
    if vix_level is None:
        return "Unavailable"
    if vix_level < 15:
        return "Complacent"
    if vix_level < 22:
        return "Normal"
    return "Fearful"


def carry_condition_label(usdjpy_3m, vix_level):
    if usdjpy_3m is None and vix_level is None:
        return "Unavailable"
    if (usdjpy_3m is not None and usdjpy_3m < -0.03) or (vix_level is not None and vix_level > 24):
        return "Unwind Risk"
    if usdjpy_3m is not None and usdjpy_3m > 0.02 and (vix_level is None or vix_level < 20):
        return "Supportive"
    return "Neutral"


def m2_trend_label(m2_trend):
    if m2_trend is None:
        return "Unavailable"
    if m2_trend > 0.005:
        return "Expanding"
    if m2_trend < -0.005:
        return "Contracting"
    return "Flat"


def m2_backdrop_label(m2_trend):
    trend = m2_trend_label(m2_trend)
    if trend == "Expanding":
        return "Supportive"
    if trend == "Contracting":
        return "Tightening"
    if trend == "Flat":
        return "Neutral"
    return "Unavailable"


def fiscal_stress_label(thirty_year_level, thirty_year_3m):
    if thirty_year_level is None:
        return "Unavailable"
    if thirty_year_level >= 5.0 or (thirty_year_3m is not None and thirty_year_3m > 0.08):
        return "Elevated ⚠"
    if thirty_year_level >= 4.5 or (thirty_year_3m is not None and thirty_year_3m > 0.03):
        return "Moderate"
    return "Contained"


def global_liquidity_interpretation(data):
    m2_trend = data.get("m2_6m")
    m2_backdrop = m2_backdrop_label(m2_trend)
    dxy_rising = data.get("dxy_3m") is not None and data["dxy_3m"] > 0
    yields_rising = data.get("tnx_3m") is not None and data["tnx_3m"] > 0
    thirty_year = data.get("tyx_level")
    thirty_year_3m = data.get("tyx_3m")
    fiscal_stress = fiscal_stress_label(thirty_year, thirty_year_3m)
    vix_low = data.get("vix_level") is not None and data["vix_level"] < 16
    pe_high = data.get("forward_pe") is not None and data["forward_pe"] > 22

    if fiscal_stress == "Elevated ⚠":
        return [
            "Short-term liquidity remains constrained by elevated yields and dollar strength,",
            "while expanding M2 may still support the broader long-term liquidity backdrop.",
            "",
            "However, elevated 30Y yields suggest persistent long-duration fiscal and inflation concerns,",
            "which may structurally limit liquidity easing even if short-term Fed expectations improve.",
        ]
    if m2_backdrop == "Supportive" and vix_low and pe_high:
        return [
            "Long-term liquidity is becoming more supportive, and low volatility alongside elevated market multiples suggests",
            "liquidity may be supporting narrative-driven risk-taking.",
            "",
            "This should still be evaluated against valuation expansion, market breadth, and macro fragility rather than treated as a direct bullish signal.",
        ]
    if m2_backdrop == "Tightening" and dxy_rising and yields_rising:
        return [
            "Long-term liquidity is tightening while both the dollar and yields are rising.",
            "That combination points to increasing liquidity stress and a higher hurdle for duration-sensitive risk assets.",
        ]
    if m2_backdrop == "Supportive":
        return [
            "Global liquidity remains selective in the short term when yields, the dollar, or carry conditions are restrictive,",
            "but expanding M2 suggests the long-term liquidity backdrop is becoming more supportive for risk assets.",
            "",
            "Current market strength should still be evaluated against valuation expansion, market breadth, and macro fragility rather than treated as a direct bullish signal.",
        ]
    if m2_backdrop == "Tightening":
        return [
            "M2 contraction suggests the long-term liquidity backdrop is tightening.",
            "In that environment, capital tends to be more selective and less forgiving of weak fundamentals or excessive valuation expansion.",
        ]
    if m2_backdrop == "Neutral":
        return [
            "M2 is broadly flat, so the long-term liquidity backdrop is neutral rather than strongly supportive or restrictive.",
            "Shorter-term conditions from yields, the dollar, carry, and volatility should carry more weight in the current regime read.",
        ]
    return [
        "M2 data is unavailable, so the long-term liquidity backdrop should be interpreted through rates, the dollar, carry conditions, and volatility.",
    ]


def fetch_fred_series(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            text = response.read().decode("utf-8")
        rows = []
        for row in csv.DictReader(io.StringIO(text)):
            value = row.get(series_id)
            if not value or value == ".":
                continue
            rows.append((row.get("observation_date"), float(value)))
        return rows
    except Exception:
        return []


def fetch_ism_manufacturing_pmi():
    fred_rows = fetch_fred_series("NAPM")
    pmi, trend = latest_and_trend(fred_rows, 3)
    if pmi is not None:
        return pmi, trend, "FRED NAPM"

    url = "https://go.weareism.org/ism-manufacturing-pmi"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            text = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None, None, "Unavailable"

    pmi_match = re.search(r"Manufacturing PMI[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)\s*(?:percent|%)", text, re.IGNORECASE)
    if not pmi_match:
        pmi_match = re.search(r"registered\s+([0-9]+(?:\.[0-9]+)?)\s*percent", text, re.IGNORECASE)
    current = float(pmi_match.group(1)) if pmi_match else None

    previous = None
    previous_match = re.search(r"compared to (?:the reading of |the )?([0-9]+(?:\.[0-9]+)?)\s*percent", text, re.IGNORECASE)
    if previous_match:
        previous = float(previous_match.group(1))

    trend = current - previous if current is not None and previous is not None else None
    return current, trend, "ISM"


def latest_and_trend(rows, periods=3):
    if not rows:
        return None, None
    latest = rows[-1][1]
    if len(rows) <= periods:
        return latest, None
    return latest, latest - rows[-1 - periods][1]


def latest_period_change(rows, periods=1):
    latest, trend = latest_and_trend(rows, periods)
    if latest is None:
        return None, None
    return latest, trend


def latest_yoy(rows, periods=12):
    if not rows or len(rows) <= periods:
        return None, None
    latest = rows[-1][1]
    prior = rows[-1 - periods][1]
    if prior == 0:
        return None, None
    current_yoy = latest / prior - 1
    if len(rows) <= periods + 3:
        return current_yoy, None
    prior_yoy_base = rows[-1 - periods - 3][1]
    prior_yoy_level = rows[-4][1]
    prior_yoy = prior_yoy_level / prior_yoy_base - 1 if prior_yoy_base else None
    return current_yoy, (current_yoy - prior_yoy) if prior_yoy is not None else None


def compute_macro_fragility(macro=None):
    macro = macro or compute_macro()
    sentiment, sentiment_trend = latest_and_trend(fetch_fred_series("UMCSENT"), 3)
    ism, ism_trend, ism_source = fetch_ism_manufacturing_pmi()
    breadth = relative_change("RSP", "SPY", 63)

    fragility_points = 0
    if sentiment is not None and sentiment < 70:
        fragility_points += 1
    if sentiment_trend is not None and sentiment_trend < -3:
        fragility_points += 1
    if ism is not None and ism < 50:
        fragility_points += 1
    if ism_trend is not None and ism_trend < -1:
        fragility_points += 1
    if breadth is not None and breadth < -0.03:
        fragility_points += 1
    if macro.get("vix_level") is not None and macro["vix_level"] > 22:
        fragility_points += 1

    if fragility_points >= 5:
        label = "High"
    elif fragility_points >= 3:
        label = "Elevated"
    elif fragility_points >= 1:
        label = "Moderate"
    else:
        label = "Low"

    if label in {"Elevated", "High"} and breadth is not None and breadth < 0:
        interpretation = [
            "Asset prices are showing signs of divergence from real-economy conditions.",
            "Leadership is more dependent on liquidity, mega-cap concentration, or narrative durability than broad economic confirmation.",
        ]
    elif label == "Moderate":
        interpretation = [
            "Macro fragility is present but not dominant.",
            "Capital can still rotate into strong narratives, but breadth and real-economy confirmation should be monitored.",
        ]
    else:
        interpretation = [
            "Real-economy and market-breadth signals are not showing major stress.",
            "Market expansion has better support from underlying conditions.",
        ]

    return {
        "consumer_sentiment": sentiment,
        "consumer_sentiment_trend": sentiment_trend,
        "ism_pmi": ism,
        "ism_pmi_trend": ism_trend,
        "ism_source": ism_source,
        "breadth_proxy": breadth,
        "label": label,
        "interpretation": interpretation,
    }


def catalyst_state_from_inflation(cpi_yoy, core_cpi_yoy, ppi_yoy, core_cpi_trend):
    if (core_cpi_yoy is not None and core_cpi_yoy > 0.035) or (cpi_yoy is not None and cpi_yoy > 0.035):
        if core_cpi_trend is not None and core_cpi_trend > 0:
            return "Hot / re-accelerating inflation ⚠"
        return "Sticky inflation trend ⚠"
    if (cpi_yoy is not None and cpi_yoy < 0.025) and (core_cpi_yoy is not None and core_cpi_yoy < 0.030):
        return "Disinflationary"
    if ppi_yoy is not None and ppi_yoy > 0.03:
        return "Input-cost pressure rebuilding"
    return "Moderating / mixed inflation"


def labor_market_state(nfp_change, unemployment, unemployment_trend, claims, claims_trend):
    if (unemployment_trend is not None and unemployment_trend > 0.20) or (claims_trend is not None and claims_trend > 50_000) or (nfp_change is not None and nfp_change < 50):
        return "Weakening labor momentum ⚠"
    if (nfp_change is not None and nfp_change > 100) and (unemployment_trend is None or unemployment_trend < 0.20):
        return "Still resilient"
    return "Mixed / cooling"


def fed_sensitivity_label(macro, sector_positioning_report, inflation_state, labor_state):
    liquidity = liquidity_regime_label(macro.get("liquidity_score", 50))
    high_duration_sector = sector_positioning_report and sector_positioning_report.get("key") in {"SMH", "XLK", "IGV", "QTUM", "ICLN", "TAN", "UFO", "IBIT"}
    valuation_expansion = False
    if sector_positioning_report and sector_positioning_report.get("current_sector_pe") and sector_positioning_report.get("prior_sector_pe"):
        valuation_expansion = sector_positioning_report["current_sector_pe"] / sector_positioning_report["prior_sector_pe"] > 1.20
    if (
        liquidity in {"Tight", "Neutral-to-Tight"}
        and (high_duration_sector or valuation_expansion)
        and (inflation_state.startswith("Hot") or inflation_state.startswith("Sticky") or macro.get("vix_level", 99) < 20)
    ):
        return "High ⚠"
    if labor_state.startswith("Weakening") and macro.get("tnx_3m") is not None and macro["tnx_3m"] < 0:
        return "Two-sided"
    return "Moderate"


def compute_macro_catalysts(macro, sector_positioning_report=None):
    cpi_yoy, cpi_yoy_trend = latest_yoy(fetch_fred_series("CPIAUCSL"), 12)
    core_cpi_yoy, core_cpi_yoy_trend = latest_yoy(fetch_fred_series("CPILFESL"), 12)
    ppi_yoy, ppi_yoy_trend = latest_yoy(fetch_fred_series("PPIFIS"), 12)
    payrolls, nfp_change = latest_period_change(fetch_fred_series("PAYEMS"), 1)
    unemployment, unemployment_trend = latest_and_trend(fetch_fred_series("UNRATE"), 3)
    wages_yoy, wages_yoy_trend = latest_yoy(fetch_fred_series("CES0500000003"), 12)
    claims, claims_trend = latest_and_trend(fetch_fred_series("ICSA"), 13)

    fed_future_hist = fetch_history("ZQ=F", "6mo")
    fed_future_rate = None
    fed_future_trend = None
    if fed_future_hist is not None and len(fed_future_hist) > 21:
        current_price = float(fed_future_hist["Close"].iloc[-1])
        prior_price = float(fed_future_hist["Close"].iloc[-21])
        fed_future_rate = 100 - current_price
        fed_future_trend = (100 - current_price) - (100 - prior_price)

    inflation_state = catalyst_state_from_inflation(cpi_yoy, core_cpi_yoy, ppi_yoy, core_cpi_yoy_trend)
    labor_state = labor_market_state(nfp_change, unemployment, unemployment_trend, claims, claims_trend)
    fed_sensitivity = fed_sensitivity_label(macro, sector_positioning_report, inflation_state, labor_state)

    interpretation = []
    if fed_sensitivity == "High ⚠" and (inflation_state.startswith("Hot") or inflation_state.startswith("Sticky")):
        sector_key = sector_positioning_report.get("key") if sector_positioning_report else None
        if sector_key in {"SMH", "XLK", "IGV", "QTUM", "ICLN", "TAN", "UFO", "IBIT"}:
            pressure_target = "particularly across AI and high-duration growth assets"
        else:
            pressure_target = "particularly across richly rerated or valuation-sensitive leadership groups"
        interpretation.extend([
            "Current market positioning remains highly sensitive to inflation surprises and long-duration valuation compression risk.",
            f"Any upside inflation surprise may increase valuation compression risk, long-duration yield pressure, and volatility expansion, {pressure_target}.",
        ])
    elif labor_state.startswith("Weakening") and macro.get("tnx_3m") is not None and macro["tnx_3m"] < 0:
        interpretation.extend([
            "Market conditions may become more supportive for rate-sensitive growth narratives if yields continue to fall.",
            "However, weakening labor momentum also increases macro fragility, so the setup is supportive for duration but not necessarily broad economic risk appetite.",
        ])
    else:
        interpretation.extend([
            "Near-term macro catalysts remain important for Fed expectations and volatility risk.",
            "The current market structure should be evaluated through how inflation and labor data affect yields, liquidity sensitivity, and narrative durability.",
        ])

    return {
        "cpi_yoy": cpi_yoy,
        "cpi_yoy_trend": cpi_yoy_trend,
        "core_cpi_yoy": core_cpi_yoy,
        "core_cpi_yoy_trend": core_cpi_yoy_trend,
        "ppi_yoy": ppi_yoy,
        "ppi_yoy_trend": ppi_yoy_trend,
        "nfp_change": nfp_change,
        "unemployment": unemployment,
        "unemployment_trend": unemployment_trend,
        "wages_yoy": wages_yoy,
        "wages_yoy_trend": wages_yoy_trend,
        "claims": claims,
        "claims_trend": claims_trend,
        "fed_future_rate": fed_future_rate,
        "fed_future_trend": fed_future_trend,
        "inflation_state": inflation_state,
        "labor_state": labor_state,
        "fed_sensitivity": fed_sensitivity,
        "interpretation": interpretation,
    }


def preferred_environment(macro_score, dxy_3m, tnx_3m):
    if macro_score < 45 or (dxy_3m and dxy_3m > 0) or (tnx_3m and tnx_3m > 0):
        return ["Cash-flow-heavy sectors", "Defensives", "Balance-sheet strength"]
    if macro_score > 65:
        return ["Growth sectors", "Long-duration equities", "Crypto / high-beta risk assets"]
    return ["Selective growth", "Strong free-cash-flow compounders", "Narratives with earnings support"]


def macro_provider_warning(label, source, *values):
    if all(is_number(value) for value in values):
        return None
    return f"{label}: Unavailable or incomplete from {source}."


def macro_catalyst_warning(label, source, value):
    if is_number(value):
        return None
    return f"{label}: Unavailable from {source}."


def compute_macro():
    tnx_ticker, tnx = fetch_first_history(["^TNX"], "1y")
    tyx_ticker, tyx = fetch_first_history(["^TYX"], "1y")
    front_rate_ticker, front_rate = fetch_first_history(["2YY=F", "^IRX", "^FVX"], "1y")
    dxy = fetch_history("DX-Y.NYB", "1y")
    usdjpy = fetch_history("JPY=X", "1y")
    vix = fetch_history("^VIX", "1y")
    hyg_ief = relative_change("HYG", "IEF", 63)
    m2_rows = fetch_fred_series("M2SL")

    tnx_level = last_close(tnx_ticker)
    tyx_level = last_close(tyx_ticker)
    front_rate_level = last_close(front_rate_ticker)
    dxy_level = last_close("DX-Y.NYB")
    usdjpy_level = last_close("JPY=X")
    vix_level = last_close("^VIX")

    tnx_3m = price_change(tnx, 63)
    tyx_3m = price_change(tyx, 63)
    front_rate_3m = price_change(front_rate, 63)
    dxy_3m = price_change(dxy, 63)
    usdjpy_3m = price_change(usdjpy, 63)
    m2_level, m2_point_change_6m = latest_and_trend(m2_rows, 6)
    m2_6m = (m2_point_change_6m / (m2_level - m2_point_change_6m)) if is_number(m2_level) and is_number(m2_point_change_6m) and (m2_level - m2_point_change_6m) != 0 else None

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

    spy = yf.Ticker("SPY")
    spy_info = {}
    try:
        spy_info = spy.info
    except Exception:
        pass
    forward_pe_source = "forwardPE"
    forward_pe = safe(spy_info, "forwardPE")
    if not is_number(forward_pe):
        forward_eps = safe(spy_info, "forwardEps")
        spy_price = last_close("SPY")
        if is_number(forward_eps) and is_number(spy_price) and forward_eps > 0:
            forward_pe = spy_price / forward_eps
            forward_pe_source = "forwardEps / SPY price"
    if not is_number(forward_pe):
        trailing_pe = safe(spy_info, "trailingPE")
        if is_number(trailing_pe):
            forward_pe = trailing_pe
            forward_pe_source = "trailingPE fallback"
    earning_yield = (1 / forward_pe) if forward_pe else None
    treasury = (tnx_level / 100) if tnx_level else None
    erp = earning_yield - treasury if earning_yield and treasury else None
    provider_warnings = [
        warning
        for warning in [
            macro_provider_warning("US 10Y yield level / 3M trend", "Yahoo Finance (^TNX)", tnx_level, tnx_3m),
            macro_provider_warning("US 30Y yield level / 3M trend", "Yahoo Finance (^TYX)", tyx_level, tyx_3m),
            macro_provider_warning(f"Front-rate proxy {front_rate_ticker} level / 3M trend", "Yahoo Finance", front_rate_level, front_rate_3m),
            macro_provider_warning("DXY level / 3M trend", "Yahoo Finance (DX-Y.NYB)", dxy_level, dxy_3m),
            macro_provider_warning("USDJPY level / 3M trend", "Yahoo Finance (JPY=X)", usdjpy_level, usdjpy_3m),
            macro_provider_warning("VIX level", "Yahoo Finance (^VIX)", vix_level),
            macro_provider_warning("Credit-risk preference proxy HYG vs IEF", "Yahoo Finance", hyg_ief),
            macro_provider_warning("M2 money supply 6M trend", "FRED M2SL", m2_6m),
            macro_provider_warning("SPY forward PE / earnings yield", "Yahoo Finance SPY quoteSummary", forward_pe, earning_yield),
            macro_provider_warning("Equity risk premium", "SPY earnings yield and US 10Y yield", erp),
        ]
        if warning
    ]

    return {
        "tnx_level": tnx_level,
        "tnx_3m": tnx_3m,
        "tyx_level": tyx_level,
        "tyx_3m": tyx_3m,
        "front_rate_ticker": front_rate_ticker,
        "front_rate_level": front_rate_level,
        "front_rate_3m": front_rate_3m,
        "yield_curve": yield_curve,
        "dxy_level": dxy_level,
        "dxy_3m": dxy_3m,
        "usdjpy_level": usdjpy_level,
        "usdjpy_3m": usdjpy_3m,
        "vix_level": vix_level,
        "m2_level": m2_level,
        "m2_6m": m2_6m,
        "hyg_ief": hyg_ief,
        "forward_pe": forward_pe,
        "forward_pe_source": forward_pe_source if is_number(forward_pe) else "Unavailable",
        "earning_yield": earning_yield,
        "erp": erp,
        "liquidity_score": liquidity_score,
        "risk_score": risk_score,
        "macro_score": macro_score,
        "provider_warnings": provider_warnings,
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
        if (six_month is not None and six_month > 0.80) or (dist_200 is not None and dist_200 > 0.40):
            momentum_heat += 60
        elif (six_month is not None and six_month > 0.40) or (dist_200 is not None and dist_200 > 0.25):
            momentum_heat += 45
        elif (
            six_month is not None
            and dist_200 is not None
            and six_month > 0.10
            and dist_200 > 0
        ):
            momentum_heat += 30
        elif (
            (six_month is not None and six_month > 0)
            or (dist_200 is not None and dist_200 > 0)
        ):
            momentum_heat += 15
        momentum_heat += 12 if ticker_rsi and ticker_rsi > 75 else 8 if ticker_rsi and ticker_rsi > 65 else 0
        momentum_heat += 10 if dist_50 and dist_50 > 0.18 else 5 if dist_50 and dist_50 > 0.10 else 0
        momentum_heat += 8 if vertical and vertical > 0.10 else 4 if vertical and vertical > 0.05 else 0
        if valuation_heat >= 40 and six_month is not None and six_month > 0.10:
            momentum_heat += 5
        if six_month is not None and six_month < 0 and dist_200 is not None and dist_200 < 0:
            momentum_heat = min(momentum_heat, 20)

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
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")

    if six_month is not None and dist_200 is not None and six_month < 0 and dist_200 < 0:
        return "Correction / Base-Building ⚠"
    if (six_month is not None and six_month > 0.80) or (dist_200 is not None and dist_200 > 0.40):
        return "Parabolic Acceleration Detected ⚠"
    if (six_month is not None and six_month > 0.25) or (dist_200 is not None and dist_200 > 0.20):
        return "Strong Uptrend, Not Fully Parabolic"
    if six_month is not None and dist_200 is not None and six_month > 0 and dist_200 > 0:
        return "Moderate Momentum Recovery"
    return "Mixed / Transition Phase"


def momentum_stage(heat):
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    three_month = heat.get("three_month")

    if six_month is not None and dist_200 is not None and six_month < 0 and dist_200 < 0:
        return "Cooling / Base-Building Phase"
    if (six_month is not None and six_month > 0.80) or (dist_200 is not None and dist_200 > 0.40):
        return "Late Momentum Phase"
    if (six_month is not None and six_month > 0.25) or (dist_200 is not None and dist_200 > 0.20):
        return "Mid-to-Late Momentum Phase"
    if six_month is not None and dist_200 is not None and six_month > 0 and dist_200 > 0:
        return "Early-to-Mid Momentum Repair Phase"
    if three_month is not None and three_month > 0:
        return "Early Momentum Repair Phase"
    return "Mixed / Transition Phase"


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
    valuation = heat.get("valuation_heat", 0)

    if (six_month is not None and six_month < 0) or (dist_200 is not None and dist_200 < 0):
        return "Low Chase Risk"
    if valuation < 20 and (
        (six_month is None or six_month < 0.15)
        and (dist_200 is None or dist_200 < 0.15)
    ):
        return "Low Chase Risk"
    if momentum >= 55:
        return "High Chase Risk"
    if momentum >= 45:
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


AI_LEADERS = {"NVDA", "AVGO", "TSM", "ASML", "AMD", "MRVL"}
MATURE_QUALITY = {"AAPL", "MSFT", "GOOGL", "META", "V", "MA", "COST", "BRK-B"}
LIQUIDITY_SENSITIVE = {"COIN", "MSTR", "MARA", "RIOT", "CLSK", "IREN", "HOOD", "IBIT"}
NARRATIVE_DECAY = {"PYPL"}
IDENTITY_UNCERTAINTY = {"RBLX"}
SPECULATIVE_TURNAROUND = {"INTC"}
EXPENSIVE_CONVICTION_GROWTH = {"PLTR"}
HARD_ASSET_ROTATION = {
    "NEM", "GOLD", "AEM", "WPM", "FNV", "KGC", "PAAS", "AGI", "GFI", "HMY",
    "FCX", "SCCO", "TECK", "BHP", "RIO", "VALE", "XOM", "CVX", "COP", "CF", "MOS", "AA",
}


def narrative_template(label, drivers, interpretation, market_interpretation=None):
    result = {
        "label": label,
        "drivers": drivers,
        "interpretation": interpretation,
    }
    if market_interpretation:
        result["market_interpretation"] = market_interpretation
    return result


def narrative_classification(quality, heat, rel_strength, pe_score):
    ticker = quality.get("ticker", "")
    accel = quality.get("accel")
    fcf = quality.get("fcf")
    margin_expansion = quality.get("margin_expansion")
    quality_score = quality.get("score", 50)
    six_month = heat.get("six_month")
    dist_200 = heat.get("dist_200")
    forward_pe = heat.get("forward_pe")

    stable_fcf = is_number(fcf) and fcf > 0
    limited_fundamental_confirmation = (
        quality_score < 65
        or (accel is not None and accel < 0)
        or not stable_fcf
        or (is_number(fcf) and fcf < 100_000_000)
    )
    aggressive_speculative_momentum = (
        (six_month is not None and six_month > 0.80)
        or (dist_200 is not None and dist_200 > 0.60)
        or (heat.get("momentum_heat", 0) >= 60)
    )
    rapid_valuation_expansion = (
        pe_score >= 55
        or (forward_pe is not None and forward_pe > 60)
        or heat.get("valuation_heat", 0) >= 55
    )
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

    if ticker in LIQUIDITY_SENSITIVE:
        return narrative_template(
            "Liquidity-Sensitive Narrative Asset",
            [
                "high sensitivity to liquidity and risk appetite",
                "digital-asset / speculative beta exposure",
                "narrative strength tied to macro liquidity conditions",
            ],
            [
                "The company participates in an active liquidity-sensitive narrative.",
                "Market behavior can shift quickly with Bitcoin price action, USD liquidity, rates, and risk appetite.",
            ],
        )

    if ticker in AI_LEADERS and quality_score >= 70 and stable_fcf:
        return narrative_template(
            "Institutional AI Leader",
            [
                "AI infrastructure leadership",
                "strong financial quality",
                "institutional rerating support",
                "cash-flow-backed narrative strength",
            ],
            [
                "The company is being treated as a core institutional AI infrastructure leader.",
                "Narrative strength is supported by financial quality rather than price action alone.",
            ],
        )

    if ticker in MATURE_QUALITY and stable_fcf and quality_score >= 70:
        return narrative_template(
            "Mature Institutional Quality / Momentum Repair",
            [
                "durable free cash flow",
                "high institutional ownership profile",
                "mature compounder characteristics",
                "momentum confirmation still matters",
            ],
            [
                "The company remains a high-quality institutional compounder.",
                "Current market treatment depends on whether momentum is repairing or valuation compression is still active.",
            ],
        )

    if ticker in NARRATIVE_DECAY:
        return narrative_template(
            "Narrative Decay / Weakening Mature Platform",
            [
                "stable free cash flow",
                "mature business profile",
                "slowing strategic relevance",
                "limited institutional rerating interest",
            ],
            [
                "The company remains financially stable,",
                "but current market behavior suggests declining narrative leadership.",
            ],
        )

    if ticker in IDENTITY_UNCERTAINTY:
        return narrative_template(
            "Identity Uncertainty",
            [
                "strong user and revenue growth",
                "improving platform monetization",
                "weak institutional conviction",
                "unresolved long-term platform narrative",
            ],
            [
                "The company continues to show operational growth,",
                "but market confidence in long-term strategic relevance remains unstable.",
                "",
                "The stock is currently trading more as a controversial narrative asset",
                "than a fully validated institutional-quality platform.",
            ],
            [
                f"{ticker} is no longer being treated as a straightforward",
                "high-growth platform leader by the market.",
                "",
                "The stock currently trades more as a controversial",
                "future-platform speculation rather than a fully trusted",
                "institutional compounder.",
            ],
        )

    if ticker in SPECULATIVE_TURNAROUND:
        return narrative_template(
            "Speculative Turnaround",
            [
                "legacy franchise with challenged execution",
                "turnaround optionality",
                "uncertain institutional conviction",
                "narrative depends on execution proof",
            ],
            [
                "The company is being treated as a turnaround candidate rather than a validated leader.",
                "Narrative strength depends on evidence that execution, margins, and product relevance are improving.",
            ],
        )

    if ticker in EXPENSIVE_CONVICTION_GROWTH and quality_score >= 75:
        drivers = [
            "strong revenue and earnings acceleration",
            "high financial quality",
            "premium valuation structure",
            "institutional conviction narrative",
        ]
        if market_weak:
            drivers.append("market momentum currently weakening")
        return narrative_template(
            "Expensive Conviction Growth",
            drivers,
            [
                "The company remains a high-quality conviction growth narrative,",
                "but valuation risk is elevated and market confirmation matters.",
                "",
                "When relative strength weakens, the setup should be read as valuation-risk plus confirmation risk",
                "rather than an active chase-risk structure.",
            ],
        )

    if ticker in HARD_ASSET_ROTATION:
        if stable_fcf and quality_score >= 55:
            label = "Defensive Hard-Asset Rotation"
            drivers = [
                "hard-asset / commodity exposure",
                "cash-flow support",
                "inflation-sensitive positioning",
                "institutional rotation toward real assets",
            ]
        else:
            label = "Inflation-Hedge Rotation"
            drivers = [
                "hard-asset / commodity exposure",
                "inflation-sensitive market leadership",
                "cyclical capital rotation",
                "fundamental confirmation still varies by company",
            ]
        return narrative_template(
            label,
            drivers,
            [
                "The market is increasingly rotating toward hard-asset exposure",
                "as investors seek inflation-sensitive and defensive cyclical positioning.",
                "",
                "This is better read as a macro rotation narrative than a conventional growth-stock rerating.",
            ],
        )

    if aggressive_speculative_momentum and limited_fundamental_confirmation and rapid_valuation_expansion:
        return {
            "label": "Speculative Narrative Momentum 🚀⚠",
            "drivers": [
                "aggressive speculative momentum",
                "AI / infrastructure narrative exposure",
                "rapid valuation expansion",
                "limited fundamental confirmation",
            ],
            "interpretation": [
                "Market behavior suggests speculative narrative-driven positioning",
                "rather than fundamentally validated institutional accumulation.",
                "",
                "Price action is significantly outperforming underlying business fundamentals.",
            ],
        }

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
    if heat.get("valuation_heat", 0) < 20 and (
        (heat.get("six_month") is None or heat["six_month"] < 0.10)
        and (heat.get("dist_200") is None or heat["dist_200"] < 0.12)
    ):
        return [
            "The company remains fundamentally supported,",
            "but stock-level momentum is still in a repair phase.",
            "This is not an active chase-risk setup.",
        ]
    if classification.get("label") == "Speculative Narrative Momentum 🚀⚠":
        return [
            "Current momentum appears heavily narrative-driven,",
            "with limited financial confirmation supporting the magnitude of the rerating.",
            "",
            "The stock is behaving more like a speculative thematic vehicle",
            "than a stable institutional-quality compounder.",
        ]
    if classification.get("label") in {"Controversial / Uncertain ⚠", "Identity Uncertainty"}:
        return [
            "Operational metrics remain resilient,",
            "but market behavior suggests ongoing uncertainty around",
            "long-term narrative durability and institutional conviction.",
        ]
    if classification.get("label") == "Liquidity-Sensitive Narrative Asset":
        return [
            "Narrative strength is closely tied to liquidity conditions and risk appetite.",
            "Positioning risk can rise quickly when digital-asset beta and macro liquidity move together.",
        ]
    if classification.get("label") == "Expensive Conviction Growth":
        if cooling:
            return [
                "Fundamental quality remains strong, but market momentum has weakened.",
                "The main risk is valuation compression if growth expectations or institutional conviction soften.",
            ]
        return [
            "The company remains a conviction growth narrative with premium valuation risk.",
            "Positioning should be interpreted through valuation discipline and continued execution confirmation.",
        ]
    if classification.get("label") in {"Defensive Hard-Asset Rotation", "Inflation-Hedge Rotation"}:
        return [
            "The stock is participating in a hard-asset rotation rather than a pure growth rerating.",
            "Positioning risk should be interpreted through inflation sensitivity, commodity leadership, and macro fragility.",
        ]
    if classification.get("label") == "Speculative Turnaround":
        return [
            "Turnaround optionality is present, but institutional conviction still requires execution proof.",
            "The main risk is that price action gets ahead of fundamental confirmation.",
        ]
    if classification.get("label") in {"Weakening Mature Platform ⚠", "Stable Mature 🟡", "Narrative Decay / Weakening Mature Platform"}:
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
    if narrative.get("classification", {}).get("label") == "Speculative Narrative Momentum 🚀⚠":
        print("Speculative Momentum Expansion Phase 🚀⚠")
    elif narrative.get("classification", {}).get("label") in {"Controversial / Uncertain ⚠", "Identity Uncertainty"}:
        print("Narrative Repricing / Identity Uncertainty Phase ⚠")
    else:
        print(momentum_stage(heat))
    print()
    print("Risk:")
    if narrative.get("classification", {}).get("label") == "Speculative Narrative Momentum 🚀⚠":
        print("⚠ Extreme Narrative Volatility Risk")
        print("⚠ High Chase Risk")
        print("⚠ Weak Fundamental Confirmation")
    elif narrative.get("classification", {}).get("label") in {"Controversial / Uncertain ⚠", "Identity Uncertainty"}:
        print("⚠ Narrative Credibility Risk")
        print("⚠ Institutional Conviction Uncertainty")
        weakness = momentum_weakness_label(heat)
        if weakness:
            print(f"⚠ {weakness}")
    elif narrative.get("classification", {}).get("label") == "Liquidity-Sensitive Narrative Asset":
        print("⚠ Liquidity Sensitivity Risk")
        print(f"⚠ {chase_risk_label(heat)}")
        print("⚠ Macro Risk Appetite Dependency")
    elif narrative.get("classification", {}).get("label") == "Expensive Conviction Growth":
        print("⚠ High Valuation Risk")
        print(f"⚠ {chase_risk_label(heat)}")
        weakness = momentum_weakness_label(heat)
        if weakness:
            print(f"⚠ {weakness}")
        print("⚠ Growth Expectation Reset Risk")
    elif narrative.get("classification", {}).get("label") in {"Defensive Hard-Asset Rotation", "Inflation-Hedge Rotation"}:
        print("⚠ Commodity Cycle Sensitivity")
        print("⚠ Inflation / Real-Rate Reversal Risk")
        print(f"⚠ {chase_risk_label(heat)}")
    elif narrative.get("classification", {}).get("label") == "Speculative Turnaround":
        print("⚠ Execution Risk")
        print("⚠ Turnaround Validation Risk")
        print(f"⚠ {chase_risk_label(heat)}")
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

    momentum_label = momentum_structure(sector_heat)
    broad_but_inconsistent = (
        breadth_ratio >= 0.50
        and (
            (rel_6m is not None and rel_6m < 0)
            or momentum_label.startswith("Correction")
            or (current_sector_pe is not None and prior_sector_pe is not None and current_sector_pe < prior_sector_pe)
        )
    )
    if broad_but_inconsistent:
        breadth_label = "Broad but Inconsistent ⚠"

    crowded = (
        breadth_ratio >= 0.75
        and rel_6m is not None
        and rel_6m > 0.30
        and current_sector_pe is not None
        and prior_sector_pe is not None
        and current_sector_pe / prior_sector_pe > 1.35
        and (momentum_label.startswith("Parabolic") or (dist_200 is not None and dist_200 > 0.30))
    )
    warming = breadth_ratio >= 0.45 or (rel_6m is not None and rel_6m > 0.10)

    narrative_structure = None
    market_interpretation = None

    narrative_type = "Stable Institutional Rotation"

    if key == "IBIT" and broad_but_inconsistent:
        narrative_type = "Speculative Rebuilding"
        stage = "Narrative Consolidation / Rebuilding Phase ⚠"
        risk = [
            "⚠ High Narrative Volatility",
            "⚠ Speculative Momentum Sensitivity",
            "⚠ Inconsistent Institutional Conviction",
        ]
        assessment = [
            "Current sector behavior suggests speculative rebuilding",
            "rather than aggressive institutional accumulation.",
            "",
            "While capital continues to participate selectively,",
            "relative weakness versus SPY and ongoing valuation compression",
            "indicate that institutional conviction remains inconsistent.",
            "",
            "The sector is currently trading more as a high-beta",
            "narrative-sensitive asset class than a stable structural compounder.",
        ]
        narrative_structure = {
            "strength": "Speculative Rebuilding ⚠",
            "drivers": [
                "persistent Bitcoin / crypto adoption narrative",
                "ETF-related institutional participation",
                "recovering digital-asset liquidity conditions",
                "inconsistent sector-wide momentum confirmation",
            ],
            "interpretation": [
                "The crypto infrastructure narrative remains active,",
                "but market behavior suggests consolidation and rebuilding",
                "rather than a fully validated institutional momentum phase.",
                "",
                "Sector leadership remains highly sensitive to:",
                "• Bitcoin price action",
                "• liquidity conditions",
                "• macro risk appetite",
                "• regulatory developments",
            ],
        }
        market_interpretation = [
            "Crypto infrastructure remains one of the market's",
            "most narrative-sensitive sectors.",
            "",
            "The long-term digital asset narrative remains alive,",
            "but the market has not yet fully transitioned back into",
            "a broad euphoric expansion phase.",
            "",
            "Current behavior is more consistent with:",
            "• consolidation",
            "• speculative rebuilding",
            "• selective institutional participation",
            "",
            "rather than:",
            "• full-cycle momentum expansion",
            "• broad institutional crowding",
            "• aggressive thematic overheating",
        ]
    elif broad_but_inconsistent:
        narrative_type = "Speculative Rebuilding"
        stage = "Sector Consolidation / Uneven Participation Phase ⚠"
        risk = [
            "⚠ Inconsistent Institutional Conviction",
            "⚠ Selective Momentum Risk",
            "⚠ Crowding signal not fully confirmed",
        ]
        assessment = [
            "Participation is broad, but sector confirmation is inconsistent.",
            "Relative strength, valuation trend, or momentum structure does not yet support a clean overcrowding call.",
            "",
            "This looks more like uneven sector rebuilding",
            "than aggressive institutional accumulation.",
        ]
    elif crowded:
        narrative_type = "Crowded Momentum"
        stage = "Late Sector Momentum Phase ⚠"
        risk = "Elevated thematic overcrowding risk"
        assessment = [
            "Institutional capital rotation remains strong,",
            f"but the {SECTOR_ETFS.get(key, key).lower()} trade is becoming increasingly crowded.",
        ]
    elif warming:
        if key in {"GLD", "DBC", "COPX", "SLV", "DBA", "XLB", "XLE"}:
            if rel_6m is not None and rel_6m > 0.20:
                narrative_type = "Inflation-Hedge Rotation"
            else:
                narrative_type = "Defensive Hard-Asset Rotation"
        elif key in {"XLU", "XLP", "XLV"}:
            narrative_type = "Defensive Rerating"
        elif rel_6m is not None and rel_6m > 0.20 and momentum_label.startswith("Strong"):
            narrative_type = "Institutional Momentum"
        elif key in {"ICLN", "TAN", "QTUM", "UFO"}:
            narrative_type = "Early-to-Mid Thematic Rotation"
        else:
            narrative_type = "Stable Institutional Rotation"
        stage = "Early-to-Mid Sector Momentum Phase"
        risk = "Moderate thematic crowding risk"
        assessment = [
            "Institutional capital rotation is constructive,",
            "but current positioning does not yet indicate extreme thematic overcrowding.",
        ]
        if narrative_type in {"Inflation-Hedge Rotation", "Defensive Hard-Asset Rotation"}:
            assessment = [
                "Capital is rotating toward hard-asset exposure",
                "as investors seek inflation-sensitive and defensive cyclical positioning.",
                "",
                "This is a macro rotation structure, not simply a company-level growth rerating.",
            ]
    else:
        if key in {"GLD", "DBC", "COPX", "SLV", "DBA", "XLB", "XLE"}:
            narrative_type = "Defensive Hard-Asset Rotation"
        elif key in {"XLU", "XLP", "XLV"}:
            narrative_type = "Defensive Rerating"
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
        "momentum_structure": "Parabolic Sector-Wide Acceleration" if momentum_label.startswith("Parabolic") else momentum_label,
        "narrative_type": narrative_type,
        "narrative_structure": narrative_structure,
        "assessment": assessment,
        "stage": stage,
        "risk": risk,
        "market_interpretation": market_interpretation,
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
    print("Sector Narrative Type:")
    print(positioning["narrative_type"])
    print()
    print("Momentum Structure:")
    print(positioning["momentum_structure"])
    print()
    if positioning.get("narrative_structure"):
        narrative = positioning["narrative_structure"]
        print("=================================================")
        print("NARRATIVE STRUCTURE")
        print("=================================================")
        print()
        print("Narrative Strength:")
        print(narrative["strength"])
        print()
        print("Driven by:")
        for driver in narrative["drivers"]:
            print(f"- {driver}")
        print()
        print("Interpretation:")
        for line in narrative["interpretation"]:
            print(line)
        print()
        print("=================================================")
        print("POSITIONING / CAPITAL FLOW ANALYSIS")
        print("=================================================")
        print()
    print("Assessment:")
    for line in positioning["assessment"]:
        print(line)
    print()
    print("Current Stage:")
    print(positioning["stage"])
    print()
    print("Risk:")
    risk = positioning["risk"]
    if isinstance(risk, list):
        for line in risk:
            print(line)
    else:
        print(risk)
    if positioning.get("market_interpretation"):
        print()
        print("=================================================")
        print("MARKET INTERPRETATION")
        print("=================================================")
        print()
        for line in positioning["market_interpretation"]:
            print(line)


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


def financial_quality_label(quality):
    score = quality.get("score", 50)
    fcf = quality.get("fcf")
    if score >= 80 and is_number(fcf) and fcf > 0:
        return "High"
    if score >= 65:
        return "Solid"
    if score >= 50:
        return "Mixed"
    return "Weak / Unproven"


def momentum_positioning_label(heat):
    momentum = heat.get("momentum_heat", 0)
    if momentum >= 75:
        return "Crowded / Hot"
    if momentum >= 50:
        return "Strong Uptrend"
    if momentum >= 25:
        return "Healthy / Controlled Momentum"
    structure = momentum_structure(heat)
    if structure.startswith("Correction"):
        return "Cooling / Base-Building"
    return "Mixed / Transition"


def print_narrative_evidence(narrative):
    print(f"Narrative Strength: {narrative['label']}")
    print("Driven by:")
    for driver in narrative["classification"]["drivers"]:
        print(f"- {driver}")
    print()
    print("Interpretation:")
    for line in narrative["classification"]["interpretation"]:
        print(line)


def print_threshold_block(title, current, reference, distance, classification, interpretation):
    print(f"{title}:")
    print(f"Current: {current}")
    print(f"Reference Threshold: {reference}")
    print(f"Distance: {distance}")
    print(f"Classification: {classification}")
    print()
    print("Interpretation:")
    for line in interpretation:
        print(line)
    print()


def ten_year_yield_classification(level):
    if level is None:
        return "Unavailable"
    if level >= 4.50:
        return "Tight-Liquidity Pressure ⚠"
    if level >= 4.25:
        return "Near Tight-Liquidity Zone ⚠"
    return "Below Tight-Liquidity Zone"


def thirty_year_yield_classification(level, trend):
    stress = fiscal_stress_label(level, trend)
    if stress == "Elevated ⚠":
        return "Long-Term Fiscal Stress Elevated ⚠"
    if stress == "Moderate":
        return "Long-Term Fiscal Stress Moderate"
    if stress == "Contained":
        return "Long-Term Fiscal Stress Contained"
    return "Unavailable"


def vix_threshold_classification(vix_level):
    if vix_level is None:
        return "Unavailable"
    if vix_level < 15:
        return "Complacent Risk Perception"
    if vix_level > 25:
        return "Stress / Volatility Expansion ⚠"
    return "Normal Risk Perception"


def vix_threshold_distance(vix_level):
    if vix_level is None:
        return "Unavailable"
    if vix_level < 15:
        return f"{15 - vix_level:.1f} points below complacency threshold"
    if vix_level > 25:
        return f"{vix_level - 25:.1f} points above stress threshold"
    return f"{vix_level - 15:.1f} points above complacency threshold; {25 - vix_level:.1f} points below stress threshold"


def dxy_threshold_classification(dxy_3m):
    if dxy_3m is None:
        return "Unavailable"
    if dxy_3m > 0.02:
        return "Dollar Liquidity Tightening ⚠"
    if dxy_3m > 0:
        return "Dollar Firming"
    if dxy_3m < -0.02:
        return "Dollar Liquidity Easing"
    return "Dollar Stable"


def usdjpy_threshold_classification(usdjpy_3m, vix_level):
    return f"Carry Conditions {carry_condition_label(usdjpy_3m, vix_level)}"


def usdjpy_threshold_distance(usdjpy_3m, vix_level):
    label = carry_condition_label(usdjpy_3m, vix_level)
    if label == "Supportive":
        return trend_threshold_distance(usdjpy_3m, 0.02)
    if label == "Unwind Risk" and usdjpy_3m is not None and usdjpy_3m < -0.03:
        return trend_threshold_distance(usdjpy_3m, -0.03)
    if label == "Unwind Risk" and vix_level is not None and vix_level > 24:
        return point_distance(vix_level, 24, 1)
    if usdjpy_3m is None:
        return "Unavailable"
    return "Between +2.00% supportive and -3.00% unwind thresholds"


def m2_threshold_classification(m2_6m):
    return f"M2 Liquidity Backdrop {m2_backdrop_label(m2_6m)}"


def m2_threshold_distance(m2_6m):
    trend = m2_trend_label(m2_6m)
    if trend == "Expanding":
        return trend_threshold_distance(m2_6m, 0.005)
    if trend == "Contracting":
        return trend_threshold_distance(m2_6m, -0.005)
    if trend == "Flat":
        return "Within +/-0.50 percentage point flat range"
    return "Unavailable"


def consumer_sentiment_classification(sentiment):
    if sentiment is None:
        return "Unavailable"
    if sentiment < 60:
        return "Main Street Stress Elevated ⚠"
    if sentiment < 70:
        return "Consumer Confidence Soft"
    return "Consumer Confidence Stable"


def ism_classification(ism):
    if ism is None:
        return "Unavailable"
    if ism < 50:
        return "Manufacturing Contraction ⚠"
    if ism < 52:
        return "Manufacturing Barely Expanding"
    return "Manufacturing Expansion"


def breadth_classification(breadth):
    if breadth is None:
        return "Unavailable"
    if breadth < -0.03:
        return "Leadership Concentration / Weak Breadth ⚠"
    if breadth < 0:
        return "Slightly Concentrated Leadership"
    return "Improving Equal-Weight Breadth"


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


def print_global_liquidity_conditions(data):
    dxy_rising = data["dxy_3m"] is not None and data["dxy_3m"] > 0
    dxy_label = "Unavailable" if data.get("dxy_3m") is None else "Rising" if dxy_rising else "Falling / Stable"
    ten_year = data.get("tnx_level")
    thirty_year = data.get("tyx_level")
    vix_level = data.get("vix_level")
    dxy_3m = data.get("dxy_3m")
    usdjpy_3m = data.get("usdjpy_3m")
    m2_6m = data.get("m2_6m")
    print("=================================================")
    print("GLOBAL LIQUIDITY CONDITIONS")
    print("=================================================")
    print()
    print(f"Liquidity Regime: {liquidity_regime_label(data['liquidity_score'])}")
    print(f"Risk Perception: {risk_perception_label(data['vix_level'])}")
    print(f"Carry Conditions: {carry_condition_label(data.get('usdjpy_3m'), data['vix_level'])}")
    print()
    print(f"US 10Y Treasury Yield: {pct(data['tnx_level'] / 100 if data['tnx_level'] else None)}")
    print(f"US 30Y Treasury Yield: {pct(data['tyx_level'] / 100 if data.get('tyx_level') else None)}")
    print(f"DXY Trend: {dxy_label} ({signed_pct(data['dxy_3m'])} 3M)")
    print(f"USDJPY / JPY Carry: {fmt(data.get('usdjpy_level'))} ({signed_pct(data.get('usdjpy_3m'))} 3M)")
    print(f"VIX: {fmt(data['vix_level'])}")
    print()
    print("M2 Money Supply Trend:")
    print(f"{m2_trend_label(data.get('m2_6m'))} ({signed_pct(data.get('m2_6m'))} 6M)")
    print()
    print("Long-Term Liquidity Backdrop:")
    print(m2_backdrop_label(data.get("m2_6m")))
    print()
    print("Long-Term Fiscal Stress:")
    print(fiscal_stress_label(data.get("tyx_level"), data.get("tyx_3m")))
    print()
    print("Threshold Diagnostics:")
    print()
    print_threshold_block(
        "US 10Y Treasury Yield",
        pct(ten_year / 100 if ten_year else None),
        "4.50% tight-liquidity threshold",
        pct_point_distance(ten_year, 4.50),
        ten_year_yield_classification(ten_year),
        [
            "The 10Y yield anchors medium-term valuation discount pressure.",
            "Readings near or above 4.50% keep the hurdle rate elevated, especially for long-duration growth assets.",
        ],
    )
    print_threshold_block(
        "US 30Y Treasury Yield",
        pct(thirty_year / 100 if thirty_year else None),
        "5.00% long-term fiscal-stress threshold",
        pct_point_distance(thirty_year, 5.00),
        thirty_year_yield_classification(thirty_year, data.get("tyx_3m")),
        [
            "The 30Y yield measures long-duration compensation for inflation, debt issuance, and fiscal sustainability risk.",
            "Trading above the 5.00% threshold suggests structural bond-market pressure may limit how far liquidity conditions can ease.",
        ],
    )
    print_threshold_block(
        "DXY Trend",
        f"{dxy_label} ({signed_pct(dxy_3m)} 3M)",
        "0.00% 3M change; >+2.00% signals stronger dollar-liquidity pressure",
        trend_distance(dxy_3m),
        dxy_threshold_classification(dxy_3m),
        [
            "A rising dollar tightens global liquidity by increasing pressure on non-US dollar funding conditions.",
            "The larger the positive 3M move, the more restrictive the dollar backdrop becomes for risk assets.",
        ],
    )
    print_threshold_block(
        "USDJPY / JPY Carry",
        f"{fmt(data.get('usdjpy_level'))} ({signed_pct(usdjpy_3m)} 3M)",
        "+2.00% 3M with VIX below 20 supports carry; -3.00% 3M or VIX above 24 signals unwind risk",
        usdjpy_threshold_distance(usdjpy_3m, vix_level),
        usdjpy_threshold_classification(usdjpy_3m, vix_level),
        [
            "USDJPY strength with contained volatility suggests carry conditions remain supportive.",
            "A sharp USDJPY reversal or volatility spike would point to carry unwind risk and tighter liquidity conditions.",
        ],
    )
    print_threshold_block(
        "VIX",
        fmt(vix_level),
        "<15 complacency; >25 stress",
        vix_threshold_distance(vix_level),
        vix_threshold_classification(vix_level),
        [
            "VIX below 15 indicates complacency, while readings above 25 indicate volatility stress.",
            "A normal reading means the market is not yet signaling panic, but volatility risk can still expand if macro catalysts deteriorate.",
        ],
    )
    print_threshold_block(
        "M2 Money Supply Trend",
        f"{m2_trend_label(m2_6m)} ({signed_pct(m2_6m)} 6M)",
        "+0.50% expanding; -0.50% contracting",
        m2_threshold_distance(m2_6m),
        m2_threshold_classification(m2_6m),
        [
            "M2 is treated as a long-term liquidity backdrop rather than a short-term timing signal.",
            "An expanding M2 trend supports the broader liquidity backdrop, while contraction would imply tighter long-term liquidity conditions.",
        ],
    )
    print("Interpretation:")
    for line in global_liquidity_interpretation(data):
        print(line)
    print()


def print_macro_fragility_analysis(fragility):
    sentiment = fragility.get("consumer_sentiment")
    ism = fragility.get("ism_pmi")
    breadth = fragility.get("breadth_proxy")
    print("=================================================")
    print("MACRO FRAGILITY ANALYSIS")
    print("=================================================")
    print()
    print(f"Macro Fragility: {fragility['label']}")
    print()
    print(f"Consumer Sentiment Index: {fmt(fragility['consumer_sentiment'], 1)} ({signed_fmt(fragility['consumer_sentiment_trend'], 1)} 3M point change)")
    print(f"ISM Manufacturing PMI: {fmt(fragility['ism_pmi'], 1)} ({signed_fmt(fragility['ism_pmi_trend'], 1)} change; source: {fragility.get('ism_source', 'Unavailable')})")
    print(f"Market Breadth Proxy (RSP vs SPY): {signed_pct(fragility['breadth_proxy'])} 3M")
    print()
    print("Threshold Diagnostics:")
    print()
    print_threshold_block(
        "Consumer Sentiment",
        fmt(sentiment, 1),
        "60 weak-sentiment threshold",
        point_distance(sentiment, 60, 1),
        consumer_sentiment_classification(sentiment),
        [
            "Consumer sentiment below 60 signals elevated household-confidence pressure.",
            "Weak sentiment does not automatically break market leadership, but it weakens real-economy confirmation behind asset-price strength.",
        ],
    )
    print_threshold_block(
        "ISM Manufacturing PMI",
        fmt(ism, 1),
        "50 expansion / contraction threshold",
        point_distance(ism, 50, 1),
        ism_classification(ism),
        [
            "PMI below 50 indicates manufacturing contraction.",
            "A sub-50 reading suggests market strength is relying more on liquidity, concentration, or narrative durability than broad industrial confirmation.",
        ],
    )
    print_threshold_block(
        "Market Breadth Proxy (RSP vs SPY)",
        f"{signed_pct(breadth)} 3M",
        "0.00% relative performance; negative means equal-weight underperforms cap-weight",
        trend_distance(breadth),
        breadth_classification(breadth),
        [
            "Negative RSP vs SPY means equal-weight breadth is lagging cap-weight leadership.",
            "This supports a concentrated-leadership interpretation rather than a broad-based market expansion claim.",
        ],
    )
    print("Interpretation:")
    for line in fragility["interpretation"]:
        print(line)
    print()


def print_macro_catalyst_monitor(catalysts):
    print("=================================================")
    print("MACRO CATALYST MONITOR")
    print("=================================================")
    print()
    print("CPI:")
    print(f"{catalysts['inflation_state']}")
    print(f"Headline CPI: {pct(catalysts['cpi_yoy'])} YoY ({signed_pct(catalysts['cpi_yoy_trend'])} 3M YoY change)")
    print(f"Core CPI: {pct(catalysts['core_cpi_yoy'])} YoY ({signed_pct(catalysts['core_cpi_yoy_trend'])} 3M YoY change)")
    print(f"PPI: {pct(catalysts['ppi_yoy'])} YoY ({signed_pct(catalysts['ppi_yoy_trend'])} 3M YoY change)")
    print()
    print("Labor Market:")
    print(catalysts["labor_state"])
    print(f"Non-Farm Payrolls: {fmt(catalysts['nfp_change'], 0, '', 'k')} monthly change")
    print(f"Unemployment Rate: {pct(catalysts['unemployment'] / 100 if catalysts['unemployment'] is not None else None)} ({signed_fmt(catalysts['unemployment_trend'], 2)} 3M point change)")
    print(f"Average Hourly Earnings: {pct(catalysts['wages_yoy'])} YoY ({signed_pct(catalysts['wages_yoy_trend'])} 3M YoY change)")
    print(f"Initial Jobless Claims: {fmt(catalysts['claims'], 0)} ({signed_number(catalysts['claims_trend'])} 13W change)")
    print()
    print("Fed Sensitivity:")
    print(catalysts["fed_sensitivity"])
    if catalysts.get("fed_future_rate") is not None:
        print(f"Fed Funds Futures Implied Rate: {fmt(catalysts['fed_future_rate'], 2, '', '%')} ({signed_fmt(catalysts['fed_future_trend'], 2)} 1M point change)")
    else:
        print("Fed Funds Futures Implied Rate: Unavailable")
    print()
    print("Interpretation:")
    for line in catalysts["interpretation"]:
        print(line)
    print()


def combined_provider_warnings(data, fragility, catalysts):
    warnings = list(data.get("provider_warnings") or [])
    warnings.extend(
        warning
        for warning in [
            macro_catalyst_warning("Consumer sentiment", "FRED UMCSENT", fragility.get("consumer_sentiment")),
            macro_catalyst_warning("ISM Manufacturing PMI", fragility.get("ism_source", "FRED/ISM"), fragility.get("ism_pmi")),
            macro_catalyst_warning("Market breadth proxy RSP vs SPY", "Yahoo Finance", fragility.get("breadth_proxy")),
            macro_catalyst_warning("Headline CPI", "FRED CPIAUCSL", catalysts.get("cpi_yoy")),
            macro_catalyst_warning("Core CPI", "FRED CPILFESL", catalysts.get("core_cpi_yoy")),
            macro_catalyst_warning("PPI", "FRED PPIFIS", catalysts.get("ppi_yoy")),
            macro_catalyst_warning("Non-farm payrolls", "FRED PAYEMS", catalysts.get("nfp_change")),
            macro_catalyst_warning("Unemployment rate", "FRED UNRATE", catalysts.get("unemployment")),
            macro_catalyst_warning("Average hourly earnings", "FRED CES0500000003", catalysts.get("wages_yoy")),
            macro_catalyst_warning("Initial jobless claims", "FRED ICSA", catalysts.get("claims")),
            macro_catalyst_warning("Fed funds futures implied rate", "Yahoo Finance ZQ=F", catalysts.get("fed_future_rate")),
        ]
        if warning
    )
    return warnings


def print_provider_warning_section(data, fragility, catalysts):
    warnings = combined_provider_warnings(data, fragility, catalysts)
    if not warnings:
        return

    print("=================================================")
    print("DATA PROVIDER WARNINGS")
    print("=================================================")
    print()
    print("Some live macro inputs were unavailable, delayed, or rate-limited.")
    print("Unavailable values are labeled explicitly; existing neutral fallback scoring remains unchanged.")
    print()
    for warning in warnings:
        print(f"- {warning}")
    print()


def print_macro_command():
    data = compute_macro()
    fragility = compute_macro_fragility(data)
    catalysts = compute_macro_catalysts(data)
    erp_negative = data["erp"] is not None and data["erp"] < 0

    print_global_liquidity_conditions(data)
    print_macro_fragility_analysis(fragility)
    print_macro_catalyst_monitor(catalysts)
    print_provider_warning_section(data, fragility, catalysts)
    print("Macro / ERP Context:")
    if data["erp"] is None:
        print("ERP Unavailable")
    elif erp_negative:
        print("ERP Negative")
    else:
        print(f"ERP Positive / Neutral ({pct(data['erp'])})")
    if data.get("earning_yield") is not None:
        print(f"SPY Earnings Yield: {pct(data['earning_yield'])} ({data.get('forward_pe_source', 'PE source unavailable')})")
    print()
    print("Preferred Environment:")
    for item in preferred_environment(data["macro_score"], data["dxy_3m"], data["tnx_3m"]):
        print(item)


def print_sectors_command(show_all=False):
    rows = compute_sectors()
    print("Sector Rotation Leaderboard:")
    print()
    limit = len(rows) if show_all else 3
    for idx, row in enumerate(rows[:limit], 1):
        print(
            f"{idx}. {row['name']} {emoji_for_sector(row['name'])}  "
            f"(1M {signed_pct(row['rel_1m'])}, 3M {signed_pct(row['rel_3m'])}, 6M {signed_pct(row['rel_6m'])} vs SPY)"
        )


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
    print("Intelligence Breakdown:")
    print(f"- Financial Quality: {financial_quality_label(quality)}")
    print(f"- Narrative Strength: {narrative['label']}")
    print(f"- Momentum / Positioning: {momentum_positioning_label(heat)}")
    print(f"- Valuation Risk: {valuation_risk_label(heat)}")
    print(f"- Chase Risk: {chase_risk_label(heat)}")
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


def market_character_label(macro, fragility, catalysts, sector_positioning_report):
    liquidity = liquidity_regime_label(macro["liquidity_score"])
    fragility_label = fragility["label"]
    breadth = fragility.get("breadth_proxy")
    sector_type = sector_positioning_report.get("narrative_type") if sector_positioning_report else None
    fiscal_stress = fiscal_stress_label(macro.get("tyx_level"), macro.get("tyx_3m"))
    inflation_hot = catalysts.get("inflation_state", "").startswith(("Hot", "Sticky"))

    if sector_type in {"Inflation-Hedge Rotation", "Defensive Hard-Asset Rotation"}:
        return "Inflation-Sensitive Rotation"
    if sector_type == "Crowded Momentum":
        return "Speculative Late-Cycle Momentum"
    if breadth is not None and breadth < -0.03 and fragility_label in {"Elevated", "High"}:
        return "Fragile Mega-Cap Dominance"
    if sector_type in {"Institutional Momentum", "Stable Institutional Rotation"} and breadth is not None and breadth < 0:
        return "Concentrated Institutional Leadership"
    if liquidity in {"Loose", "Neutral"} and fragility_label in {"Low", "Moderate"} and breadth is not None and breadth > 0:
        return "Broad Economic Expansion"
    if liquidity in {"Loose", "Neutral"} and m2_backdrop_label(macro.get("m2_6m")) == "Supportive":
        return "Liquidity-Driven Risk Expansion"
    if inflation_hot or fiscal_stress == "Elevated ⚠":
        return "Selective Narrative Expansion"
    return "Mixed Selective Rotation"


def market_character_interpretation(character):
    if character == "Inflation-Sensitive Rotation":
        return [
            "The dominant structure is hard-asset and inflation-sensitive rotation.",
            "Capital is responding to inflation pressure, fiscal stress, and the search for real-asset exposure rather than broad economic acceleration.",
        ]
    if character == "Speculative Late-Cycle Momentum":
        return [
            "The dominant structure is late-cycle narrative momentum.",
            "Capital is still chasing leadership, but positioning and valuation risk are increasingly important beneath the surface.",
        ]
    if character == "Fragile Mega-Cap Dominance":
        return [
            "The dominant structure is fragile concentrated leadership.",
            "Headline strength is relying more on narrow leadership and narrative durability than broad market participation.",
        ]
    if character == "Concentrated Institutional Leadership":
        return [
            "The dominant structure is concentrated institutional leadership.",
            "Capital is rotating selectively into validated themes, while equal-weight breadth remains weak.",
        ]
    if character == "Broad Economic Expansion":
        return [
            "The dominant structure is broad economic expansion.",
            "Liquidity, macro data, and breadth are more aligned than in a narrow narrative-led regime.",
        ]
    if character == "Liquidity-Driven Risk Expansion":
        return [
            "The dominant structure is liquidity-driven risk expansion.",
            "Risk appetite is being supported by liquidity conditions more than broad real-economy confirmation.",
        ]
    if character == "Selective Narrative Expansion":
        return [
            "The dominant structure is selective narrative expansion.",
            "Leadership can persist, but it remains sensitive to inflation, yields, and valuation compression risk.",
        ]
    return [
        "The dominant structure is mixed selective rotation.",
        "Capital is rotating, but the regime is not yet broad or clean enough to call a durable expansion cycle.",
    ]


def final_market_interpretation(macro, fragility, catalysts, sectors, sector_positioning_report, candidate_narrative):
    leader = sectors[0] if sectors else None
    leader_text = leader["name"] if leader else "no clear sector leader"
    sector_type = sector_positioning_report.get("narrative_type") if sector_positioning_report else "Developing"
    liquidity = liquidity_regime_label(macro["liquidity_score"])
    fragility_label = fragility["label"]
    breadth = fragility.get("breadth_proxy")
    m2_backdrop = m2_backdrop_label(macro.get("m2_6m"))
    character = market_character_label(macro, fragility, catalysts, sector_positioning_report)

    if liquidity in {"Loose", "Neutral"} and fragility_label in {"Low", "Moderate"} and breadth is not None and breadth > 0:
        structure = "broad risk expansion with improving capital rotation"
    elif sector_type in {"Crowded Momentum", "Institutional Momentum"} and fragility_label in {"Elevated", "High"}:
        structure = "selective narrative-led expansion despite macro fragility"
    elif liquidity in {"Neutral-to-Tight", "Tight"}:
        structure = "selective rotation under cost-of-capital pressure"
    else:
        structure = "mixed market structure with selective leadership"

    driver = (
        "liquidity / narrative-driven"
        if liquidity in {"Neutral-to-Tight", "Tight"} or (breadth is not None and breadth < 0) or fragility_label in {"Elevated", "High"}
        else "broader economic expansion-supported"
    )

    if breadth is not None and breadth < 0:
        breadth_line = "Leadership remains relatively concentrated, although selective thematic participation is expanding."
    elif breadth is not None and breadth > 0:
        breadth_line = "Leadership breadth is improving, with broader market participation beyond mega-cap leaders."
    else:
        breadth_line = "Leadership breadth is mixed, with incomplete equal-weight confirmation."

    if fragility_label in {"Elevated", "High"} and m2_backdrop == "Supportive":
        liquidity_line = (
            "Short-term liquidity remains constrained by elevated yields and a strong dollar, "
            "but expanding M2 suggests a more supportive long-term liquidity backdrop."
        )
    else:
        liquidity_line = f"Long-term liquidity backdrop is {m2_backdrop.lower()}, based on the M2 trend."

    lines = [
        f"Market Character: {character}.",
        f"Dominant structure: {structure}.",
    ]
    lines.extend(market_character_interpretation(character))
    cycle_line = (
        f"This should be interpreted as a {driver} market structure, not a mechanical buy/sell signal."
        if character == "Broad Economic Expansion"
        else f"This should be interpreted as a {driver} market structure, not a broad-based economic acceleration cycle or a mechanical buy/sell signal."
    )

    dependency_line = (
        "Current leadership is being confirmed by improving breadth and real-economy support, while liquidity and narrative still shape sector leadership."
        if character == "Broad Economic Expansion"
        else "Current leadership remains dependent on liquidity persistence, selective institutional rotation, and narrative concentration rather than broad-based economic acceleration."
    )

    lines.extend([
        f"Capital is currently rotating most visibly toward {leader_text}, with the leading sector narrative classified as {sector_type}.",
        liquidity_line,
        breadth_line,
        f"Macro catalyst sensitivity is {catalysts['fed_sensitivity'].lower()}, with {catalysts['inflation_state'].lower()} and a labor market that is {catalysts['labor_state'].lower()}.",
        f"Macro fragility is {fragility_label.lower()}, so the durability of leadership depends on whether real-economy data can confirm asset-price strength.",
        dependency_line,
        "Elevated inflation sensitivity and long-duration yield pressure continue to increase fragility beneath headline asset strength.",
        cycle_line,
        "The framework should be read as a map of liquidity, capital flow, narrative strength, and positioning risk.",
    ])
    return lines


def regime_playbook(character):
    playbooks = {
        "Inflation-Sensitive Rotation": {
            "favored": ["hard-asset exposure", "cash-flow-heavy cyclicals", "inflation-sensitive defensives"],
            "vulnerable": ["long-duration growth without earnings support", "margin-sensitive cyclicals", "crowded disinflation trades"],
        },
        "Speculative Late-Cycle Momentum": {
            "favored": ["dominant narrative leaders", "liquid momentum vehicles", "companies with clear earnings confirmation"],
            "vulnerable": ["late entrants", "weak fundamental stories", "high-valuation names losing relative strength"],
        },
        "Fragile Mega-Cap Dominance": {
            "favored": ["mega-cap quality", "balance-sheet strength", "durable free-cash-flow compounders"],
            "vulnerable": ["small caps without credit support", "unprofitable growth", "cyclicals needing broad economic confirmation"],
        },
        "Concentrated Institutional Leadership": {
            "favored": ["validated sector leaders", "strong FCF growth companies", "themes with margin expansion"],
            "vulnerable": ["second-tier sympathy trades", "low-quality catch-up names", "crowded stocks with fading momentum"],
        },
        "Broad Economic Expansion": {
            "favored": ["cyclicals with earnings acceleration", "small and mid-cap participation", "quality growth with reasonable valuation"],
            "vulnerable": ["defensive laggards", "idiosyncratic weak balance sheets", "overcrowded prior-cycle leaders"],
        },
        "Liquidity-Driven Risk Expansion": {
            "favored": ["growth equities", "high-beta leadership", "liquidity-sensitive narratives with confirmation"],
            "vulnerable": ["cash-flow-poor momentum", "assets dependent on falling volatility", "stories vulnerable to yield spikes"],
        },
        "Selective Narrative Expansion": {
            "favored": ["cash-flow-backed narratives", "sector leaders with positive relative strength", "companies with execution proof"],
            "vulnerable": ["valuation-only reratings", "weak-breadth momentum", "long-duration assets sensitive to inflation surprises"],
        },
    }
    return playbooks.get(character, {
        "favored": ["selective growth", "strong balance sheets", "companies with earnings confirmation"],
        "vulnerable": ["unconfirmed narratives", "weak relative strength", "crowded trades without breadth support"],
    })


def market_risk_map(macro, fragility, catalysts, sector_positioning_report, candidate_narrative):
    risks = []
    if catalysts.get("inflation_state", "").startswith(("Hot", "Sticky")):
        risks.append(("Inflation surprise risk", "inflation is still hot or sticky"))
    if fiscal_stress_label(macro.get("tyx_level"), macro.get("tyx_3m")) == "Elevated ⚠":
        risks.append(("Long-duration yield pressure", "30Y yield stress is elevated"))
    if fragility.get("breadth_proxy") is not None and fragility["breadth_proxy"] < 0:
        risks.append(("Narrow leadership breadth", "RSP is underperforming SPY"))
    if sector_positioning_report and sector_positioning_report.get("narrative_type") == "Crowded Momentum":
        risks.append(("Sector overcrowding risk", "sector breadth, momentum, and rerating are extended"))
    if candidate_narrative and candidate_narrative.get("heat", {}).get("valuation_heat", 0) >= 40:
        risks.append(("Valuation compression risk", "the leading candidate carries elevated valuation heat"))
    if catalysts.get("fed_sensitivity") == "High ⚠":
        risks.append(("Fed sensitivity risk", "leadership is vulnerable to rate-expectation repricing"))
    if fragility.get("label") in {"Elevated", "High"}:
        risks.append(("Macro fragility risk", "real-economy confirmation is not fully aligned with asset prices"))

    if not risks:
        risks.append(("Complacency risk", "major stress signals are contained, but low volatility can mask catalyst risk"))
    return risks[:5]


def scenario_analysis(macro, fragility, catalysts, sector_positioning_report):
    bullish = []
    bearish = []

    if macro.get("tnx_level") is not None:
        bullish.append("10Y yield falls back below 4.25% or trends lower for several weeks")
        bearish.append("10Y yield pushes above 4.75% and pressures long-duration valuations")
    if macro.get("dxy_3m") is not None:
        bullish.append("DXY weakens or stays flat, easing global dollar-liquidity pressure")
        bearish.append("DXY rises more than +2% over 3M, tightening global liquidity")
    if fragility.get("breadth_proxy") is not None:
        bullish.append("RSP begins outperforming SPY, confirming broader participation")
        bearish.append("RSP keeps lagging SPY, confirming concentrated leadership")
    if sector_positioning_report:
        bullish.append(f"{sector_positioning_report['name']} keeps relative strength while breadth broadens")
        bearish.append(f"{sector_positioning_report['name']} loses relative strength while valuation heat remains elevated")
    if catalysts.get("inflation_state"):
        bullish.append("Inflation data moderates without a sharp labor-market deterioration")
        bearish.append("Inflation re-accelerates or labor weakens enough to raise macro fragility")

    return bullish[:4], bearish[:4]


def leadership_durability(macro, fragility, catalysts, leader, sector_positioning_report, candidates, candidate_narrative):
    score = 50
    drivers = []

    if leader and leader.get("rel_3m") is not None and leader["rel_3m"] > 0:
        score += 10
        drivers.append("sector relative strength is positive")
    if leader and leader.get("rel_6m") is not None and leader["rel_6m"] > 0:
        score += 10
        drivers.append("sector leadership has multi-month confirmation")
    if sector_positioning_report and sector_positioning_report.get("breadth_label") in {"Broad", "Extremely Broad ⚠"}:
        score += 10
        drivers.append("sector breadth is broad")
    if candidates and candidates[0].get("score", 0) >= 70:
        score += 10
        drivers.append("top candidate has institutional-quality fundamentals")
    if candidate_narrative and candidate_narrative.get("heat", {}).get("heat", 0) >= 75:
        score -= 15
        drivers.append("leading candidate is showing elevated heat")
    if sector_positioning_report and sector_positioning_report.get("narrative_type") == "Crowded Momentum":
        score -= 15
        drivers.append("sector positioning is crowded")
    if fragility.get("label") in {"Elevated", "High"}:
        score -= 10
        drivers.append("macro fragility is elevated")
    if catalysts.get("fed_sensitivity") == "High ⚠":
        score -= 10
        drivers.append("Fed sensitivity is high")
    if liquidity_regime_label(macro.get("liquidity_score", 50)) in {"Loose", "Neutral"}:
        score += 5
        drivers.append("liquidity regime is not restrictive")

    score = clamp(score)
    if score >= 75:
        label = "Durable Leadership"
    elif score >= 60:
        label = "Constructive but Selective"
    elif score >= 45:
        label = "Fragile / Needs Confirmation"
    else:
        label = "Low Durability"
    return score, label, drivers[:5]


def early_rotation_candidates(sectors):
    candidates = []
    for row in sectors:
        rel_1m = row.get("rel_1m")
        rel_3m = row.get("rel_3m")
        rel_6m = row.get("rel_6m")
        if rel_1m is None or rel_3m is None or rel_6m is None:
            continue
        improving = rel_1m > 0 and rel_1m > rel_3m and rel_6m < 0.15
        recovering = rel_1m > 0.02 and rel_3m > -0.03 and rel_6m < 0
        controlled = row.get("score", 0) >= 50 and rel_6m < 0.25
        if improving or recovering or controlled:
            candidates.append(row)
    return sorted(candidates, key=lambda row: (row.get("rel_1m") or 0, row.get("score") or 0), reverse=True)[:3]


def crowding_quality_matrix(candidates, candidate_narrative):
    quality = candidates[0].get("score", 50) if candidates else 50
    heat = candidate_narrative.get("heat", {}).get("heat", 0) if candidate_narrative else 0
    if quality >= 70 and heat < 50:
        return "High Quality + Low Crowding = healthy accumulation profile"
    if quality >= 70 and heat >= 70:
        return "High Quality + High Crowding = validated leader, but chase-risk discipline matters"
    if quality >= 70 and heat >= 50:
        return "High Quality + Moderate Crowding = validated leader with warming positioning"
    if quality < 70 and heat >= 70:
        return "Low Quality + High Crowding = speculative momentum risk"
    if quality < 70 and heat >= 50:
        return "Low Quality + Moderate Crowding = improving momentum, but confirmation is incomplete"
    return "Low Quality + Low Crowding = incomplete confirmation"


def market_phase(macro, fragility, sector_positioning_report, candidate_narrative):
    liquidity = liquidity_regime_label(macro.get("liquidity_score", 50))
    breadth = fragility.get("breadth_proxy")
    sector_type = sector_positioning_report.get("narrative_type") if sector_positioning_report else None
    heat = candidate_narrative.get("heat", {}).get("heat", 0) if candidate_narrative else 0

    if fragility.get("label") in {"Elevated", "High"} and breadth is not None and breadth < -0.03:
        return "Phase 5: Distribution / Fragility"
    if sector_type == "Crowded Momentum" or heat >= 75:
        return "Phase 4: Crowded Momentum"
    if breadth is not None and breadth > 0 and liquidity in {"Loose", "Neutral"}:
        return "Phase 3: Broad Participation"
    if sector_type in {"Institutional Momentum", "Stable Institutional Rotation", "Early-to-Mid Thematic Rotation"}:
        return "Phase 2: Selective Leadership"
    return "Phase 1: Liquidity Repair"


def watchlist_profile(character, sector_positioning_report):
    if character == "Inflation-Sensitive Rotation":
        return ["positive free cash flow", "real-asset or commodity exposure", "pricing-power evidence", "controlled distance from 200MA"]
    if character in {"Concentrated Institutional Leadership", "Selective Narrative Expansion"}:
        return ["strong FCF", "positive revenue acceleration", "margin expansion", "sector relative strength improving", "not excessively extended above 200MA"]
    if character == "Broad Economic Expansion":
        return ["earnings acceleration", "improving breadth", "reasonable valuation", "cyclical participation", "balance-sheet resilience"]
    if character == "Liquidity-Driven Risk Expansion":
        return ["high-beta exposure with confirmation", "improving RS", "manageable valuation heat", "macro sensitivity clearly understood"]
    if sector_positioning_report and sector_positioning_report.get("narrative_type") == "Defensive Rerating":
        return ["cash-flow durability", "low leverage", "defensive earnings stability", "steady relative strength"]
    return ["strong balance sheet", "positive relative strength", "cash-flow support", "clear narrative driver", "limited chase risk"]


def narrative_decay_warnings(candidate_narrative, sector_positioning_report):
    if not candidate_narrative:
        return ["No leading candidate available for narrative-decay analysis."]
    heat = candidate_narrative.get("heat", {})
    quality = candidate_narrative.get("quality", {})
    warnings = []
    if candidate_narrative.get("relative_strength") is not None and candidate_narrative["relative_strength"] < 0:
        warnings.append("stock is underperforming SPY despite the current narrative")
    if heat.get("six_month") is not None and heat["six_month"] < 0:
        warnings.append("6M price performance is negative")
    if heat.get("dist_200") is not None and heat["dist_200"] < 0:
        warnings.append("price remains below the 200MA")
    if quality.get("margin_expansion") is not None and quality["margin_expansion"] < 0:
        warnings.append("margin expansion is fading")
    if sector_positioning_report and sector_positioning_report.get("relative_strength_6m", 0) > 0 and candidate_narrative.get("relative_strength", 0) < 0:
        warnings.append("company is lagging while its sector is still working")
    return warnings or ["No major narrative-decay warning is currently visible."]


def capital_flow_story(macro, leader, sector_positioning_report, candidate_narrative):
    leader_text = leader["name"] if leader else "the leading pocket of the market"
    liquidity = liquidity_regime_label(macro.get("liquidity_score", 50)).lower()
    sector_type = sector_positioning_report.get("narrative_type") if sector_positioning_report else "developing leadership"
    candidate = candidate_narrative["ticker"] if candidate_narrative else "the strongest candidates"
    chase = chase_risk_label(candidate_narrative["heat"]) if candidate_narrative else "unclear chase risk"
    return (
        f"Capital is rotating most visibly toward {leader_text}, with the sector currently behaving like {sector_type.lower()}. "
        f"The liquidity backdrop is {liquidity}, so the market is rewarding {candidate} only to the extent that earnings quality, narrative strength, and positioning discipline remain aligned. "
        f"Current company-level risk reads as {chase.lower()}."
    )


def print_intelligence_extensions(macro, fragility, catalysts, sectors, sector_positioning_report, candidates, candidate_narrative):
    leader = sectors[0] if sectors else None
    character = market_character_label(macro, fragility, catalysts, sector_positioning_report)
    phase = market_phase(macro, fragility, sector_positioning_report, candidate_narrative)
    durability_score, durability_label, durability_drivers = leadership_durability(
        macro, fragility, catalysts, leader, sector_positioning_report, candidates, candidate_narrative
    )
    bullish, bearish = scenario_analysis(macro, fragility, catalysts, sector_positioning_report)
    playbook = regime_playbook(character)
    early = early_rotation_candidates(sectors)

    print("=================================================")
    print("MARKET INTELLIGENCE EXTENSIONS")
    print("=================================================")
    print()
    print("Capital Flow Story:")
    print(capital_flow_story(macro, leader, sector_positioning_report, candidate_narrative))
    print()
    print("Market Phase:")
    print(phase)
    print()
    print("Leadership Durability:")
    print(f"{durability_label} ({fmt(durability_score, 1)}/100)")
    for driver in durability_drivers:
        print(f"- {driver}")
    print()
    print("Regime Playbook:")
    print("Usually favored:")
    for item in playbook["favored"]:
        print(f"- {item}")
    print("Usually vulnerable:")
    for item in playbook["vulnerable"]:
        print(f"- {item}")
    print()
    print("Market Risk Map:")
    for idx, (risk, reason) in enumerate(market_risk_map(macro, fragility, catalysts, sector_positioning_report, candidate_narrative), 1):
        print(f"{idx}. {risk}: {reason}")
    print()
    print("Scenario Analysis:")
    print("Bullish confirmation:")
    for item in bullish:
        print(f"- {item}")
    print("Bearish invalidation:")
    for item in bearish:
        print(f"- {item}")
    print()
    print("Early Rotation Candidates:")
    if early:
        for row in early:
            print(f"- {row['name']} ({row['ticker']}): 1M {signed_pct(row['rel_1m'])}, 3M {signed_pct(row['rel_3m'])}, 6M {signed_pct(row['rel_6m'])} vs SPY")
    else:
        print("- No clean early-rotation candidate detected.")
    print()
    print("Crowding vs Quality Matrix:")
    print(crowding_quality_matrix(candidates, candidate_narrative))
    print()
    print("Current Watchlist Profile:")
    for item in watchlist_profile(character, sector_positioning_report):
        print(f"- {item}")
    print()
    print("Narrative Decay Warnings:")
    for item in narrative_decay_warnings(candidate_narrative, sector_positioning_report):
        print(f"- {item}")
    print()


def print_full_command():
    macro = compute_macro()
    fragility = compute_macro_fragility(macro)
    sectors = compute_sectors()
    leader = sectors[0] if sectors else None
    key = leader["ticker"] if leader else "SMH"
    candidates = company_quality_rows(SECTOR_CANDIDATES.get(key, SECTOR_CANDIDATES["SMH"]))
    top_candidate = candidates[0] if candidates else None
    candidate_narrative = narrative_strength(top_candidate["ticker"]) if top_candidate else None
    candidate_heat = candidate_narrative["heat"] if candidate_narrative else None
    sector_positioning_report = sector_positioning(key, leader) if leader else None
    catalysts = compute_macro_catalysts(macro, sector_positioning_report)

    print("MARKET INTELLIGENCE REPORT")
    print()
    print_global_liquidity_conditions(macro)
    print_macro_fragility_analysis(fragility)
    print_macro_catalyst_monitor(catalysts)

    print("=================================================")
    print("SECTOR ROTATION ANALYSIS")
    print("=================================================")
    print()
    print("Top Sector Rotation Leaders:")
    for idx, row in enumerate(sectors[:3], 1):
        print(
            f"{idx}. {row['name']} {emoji_for_sector(row['name'])} "
            f"(1M {signed_pct(row['rel_1m'])}, 3M {signed_pct(row['rel_3m'])}, 6M {signed_pct(row['rel_6m'])} vs SPY)"
        )
    print()

    if sector_positioning_report:
        print_sector_positioning_analysis(sector_positioning_report)
        print()

    print("=================================================")
    print("COMPANY INTELLIGENCE REPORT")
    print("=================================================")
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

    print("=================================================")
    print("FINAL MARKET INTERPRETATION")
    print("=================================================")
    print()
    for line in final_market_interpretation(macro, fragility, catalysts, sectors, sector_positioning_report, candidate_narrative):
        print(line)
    print()
    print_intelligence_extensions(macro, fragility, catalysts, sectors, sector_positioning_report, candidates, candidate_narrative)


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
    try:
        args = normalize_args(input("Select: "))
    except EOFError:
        return

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
