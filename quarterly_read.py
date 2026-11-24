"""Each company's latest quarterly report, read the same way every quarter (checklist 15.5).

Rules (owner-approved 2026-11-24)
- Finances: STRONG when free cash flow over the last four quarters is positive and net debt is
  below 2x EBITDA (or the company holds net cash); WEAK when that free cash flow is negative or
  net debt is above 4x EBITDA; FAIR otherwise. Banks: not applicable (deposits are not debt).
- Latest quarter: sales against the same quarter a year earlier, operating margin against a year
  earlier, earnings per share against the analysts' forecast, free cash flow.
- Did the business change: sales growth faster or slower than the previous quarter's by more than
  3 points or a fifth of that growth rate, whichever is larger (18.21), or operating margin more than 1 point higher or lower than a year earlier. Both
  pointing the same way (or one with the other flat): improving / deteriorating; opposite: mixed;
  neither: no change.
Missing data is never zero: a rule without its inputs says so.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import math
from typing import Any

ACCELERATION_PP, MARGIN_PP = 0.03, 0.01
RELATIVE_SHIFT = 0.2
STRONG_LEVERAGE, WEAK_LEVERAGE = 2.0, 4.0
YEAR_TOLERANCE = 20


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def series(rows: dict[str, dict[str, float | None]], *names: str) -> list[tuple[dt.date, float]]:
    """The first named row that has values, as (date, value) oldest first."""
    for name in names:
        values = rows.get(name) or {}
        points = sorted((dt.date.fromisoformat(day[:10]), _num(value)) for day, value in values.items())
        points = [(day, value) for day, value in points if value is not None]
        if points:
            return points
    return []


def year_ago(points: list[tuple[dt.date, float]], day: dt.date) -> float | None:
    for other, value in points:
        if abs((day - other).days - 365) <= YEAR_TOLERANCE:
            return value
    return None


def growth_at(points: list[tuple[dt.date, float]], index: int) -> float | None:
    if len(points) < abs(index):
        return None
    day, value = points[index]
    prior = year_ago(points, day)
    return value / prior - 1 if prior not in (None, 0) and prior > 0 else None


def last_four(points: list[tuple[dt.date, float]]) -> float | None:
    """Sum of the latest four quarters, only if they are four consecutive quarters (about a year)."""
    if len(points) < 4:
        return None
    window = points[-4:]
    if (window[-1][0] - window[0][0]).days > 300:
        return None
    return sum(value for _, value in window)


def health(fcf_ttm: float | None, net_debt: float | None, ebitda_ttm: float | None, is_bank: bool) -> dict[str, Any]:
    if is_bank:
        return {"state": "NOT_APPLICABLE", "label": "Not applicable", "reason": "Banks borrow and lend for a living; deposits are not debt, so this test does not fit."}
    if fcf_ttm is None or net_debt is None:
        return {"state": "UNKNOWN", "label": "Not enough data", "reason": "Free cash flow over four quarters or net debt is unavailable."}
    leverage = None if ebitda_ttm is None or ebitda_ttm <= 0 else net_debt / ebitda_ttm
    net_cash = net_debt <= 0
    if fcf_ttm < 0 or (not net_cash and (leverage is None or leverage > WEAK_LEVERAGE)):
        reason = "free cash flow is negative" if fcf_ttm < 0 else "net debt is more than 4x EBITDA" if leverage is not None else "it has net debt and no positive EBITDA"
        return {"state": "WEAK", "label": "Weak", "reason": reason, "leverage": leverage}
    if net_cash or leverage < STRONG_LEVERAGE:
        return {"state": "STRONG", "label": "Strong", "reason": "positive free cash flow and " + ("more cash than debt" if net_cash else f"net debt {leverage:.1f}x EBITDA"), "leverage": leverage}
    return {"state": "FAIR", "label": "Fair", "reason": f"positive free cash flow, net debt {leverage:.1f}x EBITDA", "leverage": leverage}


def growth_threshold(prior_growth: float | None) -> float:
    """Checklist 18.21: a shift in sales growth counts when it exceeds 3 points or a fifth of last quarter's
    growth rate, whichever is larger, so a fast grower easing from 55% to 50% is not read as deteriorating."""
    return max(ACCELERATION_PP, RELATIVE_SHIFT * abs(prior_growth)) if prior_growth is not None else ACCELERATION_PP


def change(acceleration: float | None, margin_change: float | None, prior_growth: float | None = None) -> dict[str, Any]:
    signals, reasons = [], []
    limit = growth_threshold(prior_growth)
    if acceleration is not None:
        if acceleration > limit:
            signals.append(1); reasons.append(f"sales growth sped up by {acceleration * 100:.0f} points")
        elif acceleration < -limit:
            signals.append(-1); reasons.append(f"sales growth slowed by {abs(acceleration) * 100:.0f} points")
    if margin_change is not None:
        if margin_change > MARGIN_PP:
            signals.append(1); reasons.append(f"operating margin up {margin_change * 100:.1f} points")
        elif margin_change < -MARGIN_PP:
            signals.append(-1); reasons.append(f"operating margin down {abs(margin_change) * 100:.1f} points")
    if acceleration is None and margin_change is None:
        return {"state": "UNKNOWN", "label": "Not enough data", "reasons": []}
    if not signals:
        return {"state": "NO_CHANGE", "label": "No change", "reasons": [f"no shift beyond {limit * 100:.0f} points in sales growth or 1 point in margin"]}
    if all(item > 0 for item in signals):
        return {"state": "IMPROVING", "label": "Improving", "reasons": reasons}
    if all(item < 0 for item in signals):
        return {"state": "DETERIORATING", "label": "Deteriorating", "reasons": reasons}
    return {"state": "MIXED", "label": "Mixed", "reasons": reasons}


def _money(value: float) -> str:
    sign = "−" if value < 0 else ""
    value = abs(value)
    return f"{sign}${value / 1e9:.1f}B" if value >= 1e9 else f"{sign}${value / 1e6:.0f}M"


def read(income: dict[str, dict[str, Any]], cashflow: dict[str, dict[str, Any]], balance: dict[str, dict[str, Any]],
         surprise: dict[str, Any] | None = None, is_bank: bool = False) -> dict[str, Any]:
    revenue = series(income, "Total Revenue", "Operating Revenue")
    if not revenue:
        return {"status": "UNAVAILABLE", "reason": "No quarterly sales on record."}
    operating = series(income, "Operating Income", "EBIT")
    ebitda = series(income, "EBITDA", "Normalized EBITDA")
    fcf = series(cashflow, "Free Cash Flow")
    debt = series(balance, "Total Debt")
    cash = series(balance, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    quarter = revenue[-1][0]
    growth, growth_before = growth_at(revenue, -1), growth_at(revenue, -2)
    acceleration = growth - growth_before if growth is not None and growth_before is not None else None
    margins = {day: value / dict(revenue)[day] for day, value in operating if dict(revenue).get(day)}
    margin = margins.get(quarter)
    margin_prior = next((value for day, value in margins.items() if abs((quarter - day).days - 365) <= YEAR_TOLERANCE), None)
    margin_change = margin - margin_prior if margin is not None and margin_prior is not None else None
    fcf_ttm, ebitda_ttm = last_four(fcf), last_four(ebitda)
    net_debt = debt[-1][1] - (cash[-1][1] if cash else 0.0) if debt else (-cash[-1][1] if cash else None)
    finances = health(fcf_ttm, net_debt, ebitda_ttm, is_bank)
    shift = change(acceleration, margin_change, growth_before)
    eps = surprise or {}
    eps_surprise = _num(eps.get("surprisePercent"))
    parts = []
    if growth is not None:
        limit = growth_threshold(growth_before)
        pace = "" if growth_before is None else f", {'faster than' if acceleration > limit else 'slower than' if acceleration < -limit else 'about the same as'} last quarter's {growth_before * 100:+.0f}%"
        parts.append(f"sales {growth * 100:+.0f}% from a year earlier{pace}")
    if margin is not None:
        parts.append(f"operating margin {margin * 100:.0f}%" + (f", {'up' if margin_change >= 0 else 'down'} {abs(margin_change) * 100:.1f} points" if margin_change is not None else ""))
    if eps_surprise is not None:
        parts.append(f"earnings per share {'beat' if eps_surprise >= 0 else 'missed'} forecasts by {abs(eps_surprise) * 100:.0f}%")
    summary = f"Quarter to {quarter:%b %Y}: " + "; ".join(parts) + "." if parts else f"Quarter to {quarter:%b %Y}."
    money = ""
    if finances["state"] in {"STRONG", "FAIR", "WEAK"}:
        money = f" Finances {finances['label'].lower()}: {finances['reason']}" + (f" (free cash flow {_money(fcf_ttm)} over four quarters)." if fcf_ttm is not None else ".")
    return {"status": "AVAILABLE", "quarter": quarter.isoformat(), "revenue_yoy": growth, "revenue_yoy_prior_quarter": growth_before,
            "revenue_acceleration": acceleration, "operating_margin": margin, "operating_margin_year_ago": margin_prior, "margin_change": margin_change,
            "eps_actual": _num(eps.get("epsActual")), "eps_estimate": _num(eps.get("epsEstimate")), "eps_surprise": eps_surprise,
            "fcf_quarter": fcf[-1][1] if fcf else None, "fcf_ttm": fcf_ttm, "net_debt": net_debt, "ebitda_ttm": ebitda_ttm,
            "health": finances, "change": shift, "summary": summary + money,
            "rules": {"health": "Strong: positive free cash flow over four quarters and net debt under 2x EBITDA or net cash. Weak: negative free cash flow or net debt over 4x EBITDA. Fair: in between. Banks: not applicable.",
                      "change": "Improving or deteriorating: sales growth faster or slower than last quarter's by more than 3 points or a fifth of that growth rate, whichever is larger, or operating margin more than 1 point higher or lower than a year earlier."}}


def _frame_rows(frame) -> dict[str, dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return {}
    return {str(name): {str(day.date()): (None if value != value else float(value)) for day, value in row.items()} for name, row in frame.iterrows()}


def collect(ticker: str, is_bank: bool = False) -> dict[str, Any]:
    import yfinance as yf
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            handle = yf.Ticker(ticker)
            income, cashflow, balance, history = handle.quarterly_income_stmt, handle.quarterly_cashflow, handle.quarterly_balance_sheet, handle.earnings_history
    except Exception as exc:  # noqa: BLE001
        return {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    surprise = None
    if history is not None and not history.empty:
        latest = history.dropna(subset=["epsActual"]).tail(1)
        if not latest.empty:
            surprise = {key: (value.item() if hasattr(value, "item") else value) for key, value in latest.iloc[0].to_dict().items()}
    return read(_frame_rows(income), _frame_rows(cashflow), _frame_rows(balance), surprise, is_bank)
