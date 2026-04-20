"""
Predict Model (Market) - Live Version
Fetches real data from Yahoo Finance via yfinance.

Install dependency:
    pip install yfinance

Usage:
    python predict_model_live.py                  # S&P 500 snapshot + long-term model
    python predict_model_live.py AAPL             # DCF for a specific company
    python predict_model_live.py AAPL MSFT NVDA   # DCF for multiple tickers
"""

import sys
import yfinance as yf

TREASURY_10YR = 0.0422   # Update manually or fetch from ^TNX
TARGET_PE_10Y = 20.0
LT_EPS_GROWTH = 0.06
DIVIDEND_YIELD_LTM = 0.015
YEARS = 10
TAX_RATE = 0.21
WACC = 0.09
TERMINAL_GROWTH = 0.03
DEP_PCT = 0.06
CAPEX_PCT = 0.08
WC_PCT = 0.01


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def pct(v):
    return f"{v*100:.2f}%" if v is not None else "—"

def fmt(v, decimals=2, prefix="", suffix=""):
    if v is None:
        return "—"
    return f"{prefix}{v:,.{decimals}f}{suffix}"

def divider(title=""):
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print("-" * 60)

def safe(info, *keys, default=None):
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return default


# ─────────────────────────────────────────────
# 1. MARKET SNAPSHOT
# ─────────────────────────────────────────────

def market_snapshot():
    divider("S&P 500 MARKET SNAPSHOT")
    print("  Fetching live data...")

    sp = yf.Ticker("^GSPC")
    info = sp.info

    index_level  = safe(info, "regularMarketPrice", "previousClose")
    trailing_eps = safe(info, "trailingEps")
    forward_eps  = safe(info, "forwardEps")
    trailing_pe  = safe(info, "trailingPE")
    forward_pe   = safe(info, "forwardPE")
    div_yield    = safe(info, "dividendYield", default=0.0)

    # Derive if not directly available
    if trailing_pe is None and index_level and trailing_eps:
        trailing_pe = index_level / trailing_eps
    if forward_pe is None and index_level and forward_eps:
        forward_pe = index_level / forward_eps

    earning_yield = (1 / forward_pe) if forward_pe else None
    erp = (earning_yield - TREASURY_10YR) if earning_yield else None

    print(f"\n  {'S&P 500 Index':<30} {fmt(index_level, 2)}")
    print(f"  {'Trailing EPS':<30} {fmt(trailing_eps, 2, '$')}")
    print(f"  {'Forward EPS':<30} {fmt(forward_eps, 2, '$')}")
    print(f"  {'Trailing PE':<30} {fmt(trailing_pe, 2, suffix='×')}")
    print(f"  {'Forward PE':<30} {fmt(forward_pe, 2, suffix='×')}")
    print(f"  {'Earning Yield (1/PE)':<30} {pct(earning_yield)}")
    print(f"  {'10-Yr Treasury Yield':<30} {pct(TREASURY_10YR)}")
    print(f"  {'Dividend Yield':<30} {pct(div_yield)}")
    print(f"  {'Long-Term EPS Growth':<30} {pct(LT_EPS_GROWTH)}")

    signal = "✅ Positive — market undervalued vs bonds" if erp and erp > 0 else "⚠️  Negative — bonds more attractive than equities"
    print(f"  {'Equity Risk Premium':<30} {pct(erp)}  ← {signal}")

    return forward_pe


# ─────────────────────────────────────────────
# 2. LONG-TERM RETURN MODEL
# ─────────────────────────────────────────────

def long_term_model(forward_pe=None):
    divider("LONG-TERM RETURN MODEL (10-YEAR)")

    if forward_pe is None:
        print("  Fetching live S&P 500 forward PE...")
        info = yf.Ticker("^GSPC").info
        forward_pe = safe(info, "forwardPE", default=27.86)

    val_drag = (TARGET_PE_10Y / forward_pe) ** (1 / YEARS) - 1
    base_return = LT_EPS_GROWTH + DIVIDEND_YIELD_LTM + val_drag

    print(f"\n  {'Current Forward PE':<35} {forward_pe:.2f}×")
    print(f"  {'Target PE (10Y)':<35} {TARGET_PE_10Y:.1f}×")
    print(f"  {'Valuation Change (Annualised)':<35} {pct(val_drag)}")
    print(f"  {'EPS Growth Assumption':<35} {pct(LT_EPS_GROWTH)}")
    print(f"  {'Dividend Yield Assumption':<35} {pct(DIVIDEND_YIELD_LTM)}")
    print(f"\n  {'Expected Annual Return (10Y)':<35} {pct(base_return)}")

    print(f"\n  {'Scenario':<10} {'EPS Growth':>12} {'Target PE':>12} {'Expected Return':>16}")
    print(f"  {'-'*52}")
    scenarios = [
        ("Bull",  0.08, 25.0),
        ("Base",  0.06, 20.0),
        ("Bear",  0.04, 16.0),
    ]
    for name, g, pe in scenarios:
        vd = (pe / forward_pe) ** (1 / YEARS) - 1
        r = g + DIVIDEND_YIELD_LTM + vd
        print(f"  {name:<10} {pct(g):>12} {pe:>11.1f}× {pct(r):>16}")


# ─────────────────────────────────────────────
# 3. COMPANY DCF MODEL
# ─────────────────────────────────────────────

def company_dcf(ticker: str):
    divider(f"COMPANY DCF — {ticker.upper()}")
    print("  Fetching live financials...")

    t = yf.Ticker(ticker)
    info = t.info

    name         = info.get("longName", ticker.upper())
    current_price = safe(info, "currentPrice", "regularMarketPrice", "previousClose")
    revenue      = safe(info, "totalRevenue")
    op_margin    = safe(info, "operatingMargins", default=0.20)
    rev_growth   = safe(info, "revenueGrowth", default=0.08)
    shares       = safe(info, "sharesOutstanding", default=1)
    total_debt   = safe(info, "totalDebt", default=0)
    cash         = safe(info, "totalCash", default=0)

    if revenue is None:
        print(f"  ❌  Could not retrieve revenue for {ticker}. Check the ticker symbol.")
        return

    net_debt = (total_debt - cash) / 1e9
    revenue_b = revenue / 1e9

    print(f"\n  Company      : {name}")
    print(f"  Revenue (TTM): ${revenue_b:.2f}B")
    print(f"  Rev Growth   : {pct(rev_growth)}  (Yahoo Finance TTM)")
    print(f"  Op Margin    : {pct(op_margin)}")
    print(f"  Net Debt     : ${net_debt:.2f}B")
    print(f"  WACC         : {pct(WACC)}")
    print(f"  Terminal g   : {pct(TERMINAL_GROWTH)}")

    print(f"\n  {'Year':>5} {'Revenue':>12} {'EBIT':>10} {'NOPAT':>10} {'FCF':>10} {'Disc.FCF':>10}")
    print(f"  {'-'*57}")

    r = revenue_b
    total_pv = 0
    last_fcf = 0

    for yr in range(1, 6):
        r = r * (1 + rev_growth)
        ebit  = r * op_margin
        nopat = ebit * (1 - TAX_RATE)
        dep   = r * DEP_PCT
        capex = r * CAPEX_PCT
        dwc   = r * WC_PCT
        fcf   = nopat + dep - capex - dwc
        df    = 1 / (1 + WACC) ** yr
        dfcf  = fcf * df
        total_pv += dfcf
        last_fcf = fcf
        print(f"  {yr:>5} {r:>11.2f}B {ebit:>9.2f}B {nopat:>9.2f}B {fcf:>9.2f}B {dfcf:>9.2f}B")

    tv      = last_fcf * (1 + TERMINAL_GROWTH) / (WACC - TERMINAL_GROWTH)
    dtv     = tv / (1 + WACC) ** 5
    ev      = total_pv + dtv
    equity  = ev - net_debt
    iv      = (equity * 1e9) / shares

    mos = ((iv - current_price) / current_price * 100) if current_price and current_price > 0 else None
    verdict = ""
    if mos is not None:
        if mos >= 20:
            verdict = "✅  Potentially undervalued"
        elif mos <= -20:
            verdict = "⚠️  Potentially overvalued"
        else:
            verdict = "➡️  Fairly valued"

    print(f"\n  {'Terminal Value (Yr5)':<30} ${tv:.2f}B")
    print(f"  {'Discounted Terminal Value':<30} ${dtv:.2f}B")
    print(f"  {'Enterprise Value (EV)':<30} ${ev:.2f}B")
    print(f"  {'Net Debt':<30} ${net_debt:.2f}B")
    print(f"  {'Equity Value':<30} ${equity:.2f}B")
    print(f"  {'Intrinsic Value / Share':<30} ${iv:.2f}")
    print(f"  {'Current Price':<30} ${current_price:.2f}" if current_price else "")
    print(f"  {'Margin of Safety':<30} {mos:.1f}%  {verdict}" if mos is not None else "")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    tickers = [a.upper() for a in sys.argv[1:]]

    if not tickers:
        fpe = market_snapshot()
        long_term_model(fpe)
    else:
        for ticker in tickers:
            company_dcf(ticker)

    print()


