"""Market inputs derived from daily price history (solution plan C1).

The quote-summary endpoint behind ``yfinance.Ticker.info`` is the most frequently
rate-limited Yahoo surface, and the SEC fallback path has no market data at all.
Both leave valuation without price, market capitalisation, or beta. The chart
history endpoint (``data_sources.market_history``) is far more reliable, so this
module derives the three inputs from it with explicit, inspectable methods:

    price       latest daily close in the history
    beta        OLS slope of weekly stock returns on weekly benchmark (SPY) returns
    market cap  price x the share count the valuation already uses for per-share value

Every derived value carries its method, window, observation count, and limitations.
Nothing here alters valuation formulas; callers only fill inputs that are missing.
"""

from __future__ import annotations

import datetime as dt
import math
import os
from typing import Any, Callable, Iterable

BETA_BENCHMARK = "SPY"
BETA_HISTORY_PERIOD = "2y"
BETA_MIN_WEEKS = 52
BETA_METHOD = "OLS slope of weekly returns on SPY weekly returns, 2-year window"
PRICE_MAX_AGE_DAYS = 7


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _pairs(observations: Iterable[Any]) -> list[tuple[str, float]]:
    """Accept MarketObservation objects, dicts, or (date, value) tuples; drop invalid rows."""
    rows = []
    for item in observations or []:
        if isinstance(item, dict):
            date, value = item.get("date"), item.get("value")
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            date, value = item
        else:
            date, value = getattr(item, "date", None), getattr(item, "value", None)
        if isinstance(date, str) and _number(value) and value > 0:
            rows.append((date, float(value)))
    return sorted(rows)


def weekly_closes(observations: Iterable[Any]) -> dict[str, float]:
    """Last close of each ISO week, keyed by ``YYYY-Www``."""
    weeks: dict[str, float] = {}
    for date, value in _pairs(observations):
        year, week, _ = dt.date.fromisoformat(date).isocalendar()
        weeks[f"{year}-W{week:02d}"] = value  # sorted input: the last write is the week's last close
    return weeks


def _returns(closes: dict[str, float]) -> dict[str, float]:
    keys = sorted(closes)
    return {current: closes[current] / closes[prior] - 1 for prior, current in zip(keys, keys[1:])}


def regression_beta(stock_observations, benchmark_observations, *, min_weeks: int = BETA_MIN_WEEKS) -> dict[str, Any]:
    """Weekly-return OLS beta. Returns ``beta=None`` with a reason when the sample is too short or degenerate."""
    stock_closes, bench_closes = weekly_closes(stock_observations), weekly_closes(benchmark_observations)
    common = sorted(set(stock_closes) & set(bench_closes))
    stock_r = _returns({week: stock_closes[week] for week in common})
    bench_r = _returns({week: bench_closes[week] for week in common})
    weeks = sorted(set(stock_r) & set(bench_r))
    result = {"beta": None, "method": BETA_METHOD, "benchmark": BETA_BENCHMARK, "weeks": len(weeks),
              "window_start": weeks[0] if weeks else None, "window_end": weeks[-1] if weeks else None,
              "r_squared": None, "reason": None}
    if len(weeks) < min_weeks:
        result["reason"] = f"{len(weeks)} aligned weekly returns; at least {min_weeks} are required."
        return result
    xs, ys = [bench_r[w] for w in weeks], [stock_r[w] for w in weeks]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0:
        result["reason"] = "Benchmark returns have zero variance."
        return result
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    result["beta"] = cov / var_x
    result["r_squared"] = (cov * cov) / (var_x * var_y) if var_y > 0 else None
    return result


def latest_close(observations, *, today: dt.date | None = None, max_age_days: int = PRICE_MAX_AGE_DAYS) -> dict[str, Any]:
    rows = _pairs(observations)
    if not rows:
        return {"price": None, "date": None, "reason": "No valid price observations."}
    date, value = rows[-1]
    age = ((today or dt.date.today()) - dt.date.fromisoformat(date)).days
    if age > max_age_days:
        return {"price": None, "date": date, "reason": f"Latest close is {age} days old (limit {max_age_days})."}
    return {"price": value, "date": date, "reason": None}


def _currency_compatible(history_currency: str | None, financial_currency: str | None) -> bool:
    if not history_currency or not financial_currency:
        return False
    return history_currency.upper() == financial_currency.upper()


def derive_market_inputs(
    ticker: str,
    *,
    financial_currency: str | None,
    shares: float | None,
    shares_basis: str,
    fetch: Callable[..., Any] | None = None,
    today: dt.date | None = None,
) -> dict[str, Any]:
    """Derive price, beta, and market cap from chart history; each field is independently nullable.

    Market cap is only formed when the listing currency matches the financial-statement
    currency. A mismatch (for example a USD-quoted ADR of a TWD reporter) usually also
    means the listed unit is not one ordinary share, so the product would be wrong.
    """
    if fetch is None:
        from data_sources.market_history import fetch_yahoo_history as fetch
    stock = fetch(ticker, period=BETA_HISTORY_PERIOD)
    stock_status = getattr(getattr(stock, "provider_status", None), "value", str(getattr(stock, "provider_status", "")))
    output: dict[str, Any] = {
        "provider": getattr(stock, "provider", "Yahoo Finance chart API"),
        "provider_status": stock_status,
        "retrieved_at": getattr(stock, "retrieved_at", None),
        "listing_currency": getattr(stock, "currency", None),
        "price": None, "price_date": None, "beta": None, "market_cap": None,
        "beta_detail": None, "market_cap_basis": None, "limitations": [],
    }
    observations = getattr(stock, "observations", None) or []
    if stock_status != "OK" or not observations:
        output["limitations"].append(f"Price history unavailable: {getattr(stock, 'error', None) or stock_status}.")
        return output

    close = latest_close(observations, today=today)
    output["price"], output["price_date"] = close["price"], close["date"]
    if close["reason"]:
        output["limitations"].append(f"Price withheld: {close['reason']}")

    bench = fetch(BETA_BENCHMARK, period=BETA_HISTORY_PERIOD)
    bench_status = getattr(getattr(bench, "provider_status", None), "value", str(getattr(bench, "provider_status", "")))
    if bench_status == "OK" and getattr(bench, "observations", None):
        detail = regression_beta(observations, bench.observations)
        output["beta_detail"] = detail
        output["beta"] = detail["beta"]
        if detail["reason"]:
            output["limitations"].append(f"Beta withheld: {detail['reason']}")
    else:
        output["limitations"].append(f"Beta withheld: benchmark {BETA_BENCHMARK} history unavailable ({bench_status}).")

    if not _number(output["price"]):
        pass
    elif not _number(shares) or shares <= 0:
        output["limitations"].append("Market cap withheld: no verified share count.")
    elif not _currency_compatible(output["listing_currency"], financial_currency):
        output["limitations"].append(
            f"Market cap withheld: listing currency {output['listing_currency']} differs from financial currency "
            f"{financial_currency}; the listed unit may not be one ordinary share."
        )
    else:
        output["market_cap"] = output["price"] * shares
        output["market_cap_basis"] = f"latest close x {shares_basis}"
    return output


def fill_missing_market_inputs(data: dict[str, Any], *, fetch: Callable[..., Any] | None = None,
                               today: dt.date | None = None, prefer_derived_beta: bool = False) -> dict[str, Any]:
    """Fill ``price``, ``market_cap``, and ``beta`` on a normalized data dict.

    Provider-supplied ``price`` and ``market_cap`` are never replaced. When ``prefer_derived_beta`` is
    true, the 2-year weekly regression beta becomes the primary ``beta`` and any provider beta is kept
    on ``data["provider_beta"]`` for comparison (and as fallback if price history is unavailable).
    Records what was filled under ``data["derived_market_inputs"]`` and per-field sources under
    ``data["input_sources"]``.
    """
    provider_beta = data.get("beta") if _number(data.get("beta")) else None
    if provider_beta is not None:
        data.setdefault("provider_beta", provider_beta)
    missing = [key for key in ("price", "market_cap", "beta") if not _number(data.get(key))]
    want_beta = "beta" in missing or prefer_derived_beta
    if not missing and not want_beta:
        return data
    if fetch is None and os.environ.get("CHAINSTOX_DERIVE_MARKET_INPUTS", "1") == "0":
        return data
    requested = list(dict.fromkeys(missing + (["beta"] if want_beta else [])))
    shares_basis = (data.get("periods") or {}).get("shares") or "latest fiscal-year diluted shares"
    derived = derive_market_inputs(
        data.get("ticker", ""), financial_currency=data.get("currency"), shares=data.get("shares"),
        shares_basis=shares_basis, fetch=fetch, today=today,
    )
    filled = []
    sources = dict(data.get("input_sources") or {})
    if "price" in missing and _number(derived["price"]):
        data["price"] = derived["price"]
        sources["price"] = f"{derived['provider']} latest close ({derived['price_date']})"
        data.setdefault("periods", {})["market_price"] = f"Latest daily close {derived['price_date']}"
        filled.append("price")
    if "market_cap" in missing and _number(derived["market_cap"]):
        if "price" in filled or not _number(data.get("price")):
            data["market_cap"] = derived["market_cap"]
        else:  # keep one price basis: provider price x shares
            data["market_cap"] = data["price"] * data["shares"]
        sources["market_cap"] = f"Derived: {derived['market_cap_basis']}"
        filled.append("market_cap")
    if want_beta and _number(derived["beta"]):
        data["beta"] = derived["beta"]
        detail = derived["beta_detail"]
        comparison = f"; Yahoo Finance beta {provider_beta:.2f} kept for comparison" if provider_beta is not None else ""
        sources["beta"] = (
            f"Derived: {detail['method']} ({detail['weeks']} weeks, {detail['window_start']} to {detail['window_end']})"
            + comparison
        )
        filled.append("beta")
    data["input_sources"] = sources
    data["derived_market_inputs"] = {**derived, "filled": filled, "requested": requested, "provider_beta": provider_beta}
    return data
