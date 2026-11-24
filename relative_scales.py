"""Relative quality and valuation scales (checklist 7.3).

company_quality_rows and heat_rows use absolute scales: a 55% gross margin or a forward P/E
of 45 means the same for every industry, so software and chip companies look high quality
and fast growers always look "hot". These relative readings sit beside the old scores; the
old scores are unchanged.

Quality percentile
    Each metric's percentile among the company's sector peer group: the names listed for its
    sector ETF in Valuation_model.SECTOR_CANDIDATES. The archetype groups in the research cache
    are too small (one to three companies) to rank within, so the sector group is used and
    labelled as a proxy. Fewer than five peers with data gives no percentile.

Valuation percentile
    Price-to-sales in the company's own history: daily price x current share count divided by
    the latest fiscal-year revenue that would have been public (fiscal year end + 75 days).
    Using today's share count for past dates is an approximation that ignores buybacks and
    dilution. Fewer than three fiscal years of revenue gives no percentile.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
from typing import Any

QUALITY_METRICS = ("rev_growth", "earnings_growth", "op_margin", "margin_expansion", "accel", "score")
FILING_LAG_DAYS = 75
MIN_PEERS = 5


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def percentile_of(value: float | None, values: list[float]) -> float | None:
    if value is None or len(values) < MIN_PEERS:
        return None
    return sum(item <= value for item in values) / len(values)


def peer_quality_percentiles(ticker: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """rows: quality rows for the company and its peers (the company included)."""
    own = next((row for row in rows if row.get("ticker") == ticker), None)
    if own is None:
        return {"state": "UNAVAILABLE", "reason": "company row missing", "peers": 0}
    output: dict[str, Any] = {"peers": len(rows), "metrics": {}}
    for metric in QUALITY_METRICS:
        values = [number for number in (_num(row.get(metric)) for row in rows) if number is not None]
        output["metrics"][metric] = {"value": _num(own.get(metric)), "percentile": percentile_of(_num(own.get(metric)), values), "peers_with_data": len(values)}
    available = [item["percentile"] for item in output["metrics"].values() if item["percentile"] is not None]
    output["state"] = "AVAILABLE" if available else "INSUFFICIENT_SAMPLE"
    output["quality_percentile"] = output["metrics"]["score"]["percentile"]
    return output


def price_to_sales_history(close, revenue_by_fiscal_end: dict[dt.date, float], shares: float) -> list[tuple[str, float]]:
    """Daily P/S using the latest fiscal-year revenue public on each date."""
    known = sorted((end + dt.timedelta(days=FILING_LAG_DAYS), revenue) for end, revenue in revenue_by_fiscal_end.items() if revenue and revenue > 0)
    output = []
    for day, price in close.items():
        date = day.date() if hasattr(day, "date") else day
        public = [revenue for available, revenue in known if available <= date]
        if public and price and price > 0:
            output.append((date.isoformat(), float(price) * shares / public[-1]))
    return output


def valuation_percentile(ticker: str, close, revenue_by_fiscal_end: dict[dt.date, float], shares: float | None) -> dict[str, Any]:
    if not shares or len([value for value in revenue_by_fiscal_end.values() if value]) < 3:
        return {"state": "INSUFFICIENT_HISTORY", "reason": "needs three fiscal years of revenue and a share count", "metric": "price_to_sales"}
    history = price_to_sales_history(close, revenue_by_fiscal_end, shares)
    if len(history) < 250:
        return {"state": "INSUFFICIENT_HISTORY", "reason": "less than a year of price-to-sales history", "metric": "price_to_sales"}
    current = history[-1][1]
    values = [value for _, value in history]
    return {"state": "AVAILABLE", "metric": "price_to_sales", "current": current, "percentile": sum(value <= current for value in values) / len(values),
            "first": history[0][0], "last": history[-1][0], "observations": len(history),
            "note": "Uses today's share count for past dates; ignores buybacks and dilution."}


def fetch_valuation_inputs(ticker: str) -> tuple[Any, dict[dt.date, float], float | None, dict[str, Any]]:
    import yfinance as yf
    from data_sources.market_history import fetch_yahoo_history
    import pandas as pd

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        handle = yf.Ticker(ticker)
        income = handle.income_stmt
        info = handle.info or {}
        shares = info.get("sharesOutstanding")
    revenue = {}
    if income is not None and "Total Revenue" in getattr(income, "index", []):
        for column, value in income.loc["Total Revenue"].items():
            if _num(value):
                revenue[pd.Timestamp(column).date()] = float(value)
    result = fetch_yahoo_history(ticker, period="5y")
    close = pd.Series({pd.Timestamp(item.date): item.value for item in result.observations}).sort_index()
    return close, revenue, _num(shares), {"financial_currency": info.get("financialCurrency"), "quote_currency": info.get("currency")}


def relative_readings(ticker: str, peers: list[str], quality_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    import Valuation_model as vm
    names = list(dict.fromkeys([ticker, *peers]))
    if quality_rows is None:
        with contextlib.redirect_stdout(io.StringIO()):
            quality_rows = vm.company_quality_rows(names)
    rows = [row for row in quality_rows if row.get("ticker") in names]
    try:
        close, revenue, shares, currencies = fetch_valuation_inputs(ticker)
        if currencies["financial_currency"] and currencies["quote_currency"] and currencies["financial_currency"] != currencies["quote_currency"]:
            valuation = {"state": "CURRENCY_MISMATCH", "metric": "price_to_sales",
                         "reason": f"Revenue is reported in {currencies['financial_currency']} and the price is quoted in {currencies['quote_currency']}; no FX conversion is applied."}
        else:
            valuation = valuation_percentile(ticker, close, revenue, shares)
    except Exception as exc:  # noqa: BLE001
        valuation = {"state": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}", "metric": "price_to_sales"}
    return {"ticker": ticker, "peer_group": names[1:], "quality": peer_quality_percentiles(ticker, rows), "valuation": valuation,
            "peer_basis": "sector ETF candidate list (proxy for archetype)"}
