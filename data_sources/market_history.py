"""Typed, replayable market-history acquisition.

Yahoo remains a best-effort public provider.  This adapter records HTTP and
schema failures instead of collapsing them into an empty DataFrame.  It does
not evade rate limits or access controls.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from evidence_contracts import ProviderStatus, SourceStatus


YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"


class PriceAdjustment(str, Enum):
    ADJUSTED_CLOSE = "ADJUSTED_CLOSE"
    UNADJUSTED_CLOSE = "UNADJUSTED_CLOSE"


@dataclass(frozen=True)
class MarketObservation:
    date: str
    value: float


@dataclass
class MarketHistoryResult:
    ticker: str
    provider: str
    provider_status: ProviderStatus
    source_status: SourceStatus
    retrieved_at: str
    observations: list[MarketObservation] = field(default_factory=list)
    exchange: str | None = None
    instrument_type: str | None = None
    currency: str | None = None
    price_type: str = "daily close"
    adjustment_policy: PriceAdjustment | None = None
    trading_calendar: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    limitation: str | None = None
    error: str | None = None
    http_status: int | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["provider_status"] = self.provider_status.value
        payload["source_status"] = self.source_status.value
        payload["adjustment_policy"] = self.adjustment_policy.value if self.adjustment_policy else None
        return payload


def normalize_yahoo_chart(
    payload: dict,
    ticker: str,
    *,
    expected_currency: str | None = None,
    retrieved_at: str | None = None,
) -> MarketHistoryResult:
    now = retrieved_at or dt.datetime.now(dt.timezone.utc).isoformat()
    chart = payload.get("chart") if isinstance(payload, dict) else None
    if not isinstance(chart, dict):
        return _failure(ticker, ProviderStatus.MALFORMED_RESPONSE, now, "Response lacks a chart object.")
    provider_error = chart.get("error")
    rows = chart.get("result")
    if provider_error:
        code = str(provider_error.get("code") or "") if isinstance(provider_error, dict) else ""
        status = ProviderStatus.UNSUPPORTED_SYMBOL if code in {"Not Found", "Bad Request"} else ProviderStatus.UNAVAILABLE
        return _failure(ticker, status, now, str(provider_error))
    if not isinstance(rows, list) or not rows:
        return _failure(ticker, ProviderStatus.EMPTY_RESPONSE, now, "Provider returned no chart result.")
    row = rows[0]
    timestamps = row.get("timestamp") or []
    indicators = row.get("indicators") or {}
    quote_rows = indicators.get("quote") or []
    adj_rows = indicators.get("adjclose") or []
    meta = row.get("meta") or {}
    currency = meta.get("currency")
    if expected_currency and currency and currency != expected_currency:
        return _failure(ticker, ProviderStatus.CURRENCY_MISMATCH, now, f"Expected {expected_currency}; provider returned {currency}.", currency=currency)
    values = None
    adjustment = None
    if adj_rows and isinstance(adj_rows[0], dict) and isinstance(adj_rows[0].get("adjclose"), list):
        values = adj_rows[0]["adjclose"]
        adjustment = PriceAdjustment.ADJUSTED_CLOSE
    elif quote_rows and isinstance(quote_rows[0], dict) and isinstance(quote_rows[0].get("close"), list):
        values = quote_rows[0]["close"]
        adjustment = PriceAdjustment.UNADJUSTED_CLOSE
    if values is None or len(values) != len(timestamps):
        return _failure(ticker, ProviderStatus.MALFORMED_RESPONSE, now, "Timestamp and price arrays are missing or misaligned.", currency=currency)
    observations_by_date: dict[str, MarketObservation] = {}
    duplicate_dates: list[str] = []
    for timestamp, value in zip(timestamps, values):
        if not isinstance(timestamp, (int, float)) or not isinstance(value, (int, float)):
            continue
        date = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).date().isoformat()
        if date in observations_by_date:
            duplicate_dates.append(date)
        observations_by_date[date] = MarketObservation(date, float(value))
    observations = sorted(observations_by_date.values(), key=lambda item: item.date)
    if not observations:
        return _failure(ticker, ProviderStatus.EMPTY_RESPONSE, now, "Provider returned no valid price observations.", currency=currency)
    limitation = None
    if duplicate_dates:
        limitation = "Duplicate observation dates were de-duplicated using the last provider value: " + ", ".join(sorted(set(duplicate_dates)))
    if adjustment == PriceAdjustment.UNADJUSTED_CLOSE:
        limitation = (limitation + " " if limitation else "") + "Adjusted close was unavailable; results are price returns, not total returns."
    return MarketHistoryResult(
        ticker=ticker.upper(), provider="Yahoo Finance chart API", provider_status=ProviderStatus.OK,
        source_status=SourceStatus.OBSERVED_LIVE, retrieved_at=now, observations=observations,
        exchange=meta.get("exchangeName") or meta.get("fullExchangeName"), instrument_type=meta.get("instrumentType"),
        currency=currency, adjustment_policy=adjustment, trading_calendar=meta.get("exchangeTimezoneName"),
        observation_start=observations[0].date, observation_end=observations[-1].date, limitation=limitation,
    )


def fetch_yahoo_history(ticker: str, *, period: str = "1y", timeout: int = 15) -> MarketHistoryResult:
    symbol = ticker.strip().upper()
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    url = YAHOO_CHART_URL.format(ticker=symbol) + "?" + urlencode({
        "range": period,
        "interval": "1d",
        "events": "div,splits,capitalGains",
        "includeAdjustedClose": "true",
    })
    request = Request(url, headers={"User-Agent": "CHAINSTOX/1.0 evidence-first market research", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = getattr(response, "status", 200)
        if status != 200:
            return _failure(symbol, ProviderStatus.UNAVAILABLE, retrieved_at, f"HTTP {status}", http_status=status)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return _failure(symbol, ProviderStatus.MALFORMED_RESPONSE, retrieved_at, f"JSON decode failed: {exc}", http_status=status)
        return normalize_yahoo_chart(payload, symbol, retrieved_at=retrieved_at)
    except HTTPError as exc:
        status = ProviderStatus.RATE_LIMITED if exc.code == 429 else ProviderStatus.UNSUPPORTED_SYMBOL if exc.code == 404 else ProviderStatus.UNAVAILABLE
        return _failure(symbol, status, retrieved_at, f"HTTP {exc.code}: {exc.reason}", http_status=exc.code)
    except (URLError, TimeoutError, OSError) as exc:
        return _failure(symbol, ProviderStatus.UNAVAILABLE, retrieved_at, f"{type(exc).__name__}: {exc}")


def _failure(
    ticker: str,
    status: ProviderStatus,
    retrieved_at: str,
    error: str,
    *,
    currency: str | None = None,
    http_status: int | None = None,
) -> MarketHistoryResult:
    return MarketHistoryResult(
        ticker=ticker.upper(), provider="Yahoo Finance chart API", provider_status=status,
        source_status=SourceStatus.PROVIDER_UNAVAILABLE if status in {ProviderStatus.RATE_LIMITED, ProviderStatus.UNAVAILABLE} else SourceStatus.INVALID if status in {ProviderStatus.MALFORMED_RESPONSE, ProviderStatus.CURRENCY_MISMATCH} else SourceStatus.MISSING,
        retrieved_at=retrieved_at, currency=currency, error=error, http_status=http_status,
    )
