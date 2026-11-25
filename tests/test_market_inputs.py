"""Solution plan C1: price, beta and market cap derived from chart history."""

import datetime as dt
import random
from types import SimpleNamespace

import pytest

import market_inputs as mi
from evidence_contracts import ProviderStatus


def _daily(start: dt.date, closes: list[float]):
    rows, day = [], start
    for value in closes:
        while day.weekday() >= 5:
            day += dt.timedelta(days=1)
        rows.append({"date": day.isoformat(), "value": value})
        day += dt.timedelta(days=1)
    return rows


def _series_with_beta(beta: float, weeks: int = 104, seed: int = 7):
    rng = random.Random(seed)
    bench, stock = [100.0], [50.0]
    for _ in range(weeks * 5):
        r = rng.gauss(0.0005, 0.01)
        bench.append(bench[-1] * (1 + r))
        stock.append(stock[-1] * (1 + beta * r))
    start = dt.date(2024, 1, 1)
    return _daily(start, stock), _daily(start, bench)


def _result(observations, currency="USD", status=ProviderStatus.OK):
    return SimpleNamespace(provider="Yahoo Finance chart API", provider_status=status, retrieved_at="2026-01-01T00:00:00+00:00",
                           currency=currency, observations=observations, error=None if status == ProviderStatus.OK else "HTTP 429")


def test_regression_beta_recovers_known_slope():
    stock, bench = _series_with_beta(1.6)
    detail = mi.regression_beta(stock, bench)
    assert detail["beta"] == pytest.approx(1.6, abs=0.02)
    assert detail["weeks"] >= 100
    assert detail["r_squared"] > 0.99


def test_regression_beta_withheld_when_sample_short():
    stock, bench = _series_with_beta(1.2, weeks=20)
    detail = mi.regression_beta(stock, bench)
    assert detail["beta"] is None
    assert "at least 52" in detail["reason"]


def test_weekly_closes_take_last_close_of_week():
    rows = [{"date": "2026-01-05", "value": 1.0}, {"date": "2026-01-09", "value": 3.0}, {"date": "2026-01-07", "value": 2.0}]
    assert mi.weekly_closes(rows) == {"2026-W02": 3.0}


def test_latest_close_rejects_stale_history():
    rows = [{"date": "2026-01-02", "value": 10.0}]
    assert mi.latest_close(rows, today=dt.date(2026, 1, 5))["price"] == 10.0
    stale = mi.latest_close(rows, today=dt.date(2026, 2, 1))
    assert stale["price"] is None and "days old" in stale["reason"]


def _fetch_factory(stock, bench, currency="USD", stock_status=ProviderStatus.OK):
    def fetch(ticker, period):
        return _result(bench) if ticker == "SPY" else _result(stock, currency, stock_status)
    return fetch


def test_fill_missing_inputs_on_sec_style_payload():
    stock, bench = _series_with_beta(1.3)
    today = dt.date.fromisoformat(stock[-1]["date"])
    data = {"ticker": "TEST", "currency": "USD", "shares": 1_000.0, "price": None, "market_cap": None, "beta": None,
            "periods": {"shares": "SEC annual shares"}}
    mi.fill_missing_market_inputs(data, fetch=_fetch_factory(stock, bench), today=today)
    assert data["price"] == pytest.approx(stock[-1]["value"])
    assert data["market_cap"] == pytest.approx(stock[-1]["value"] * 1_000.0)
    assert data["beta"] == pytest.approx(1.3, abs=0.02)
    assert set(data["derived_market_inputs"]["filled"]) == {"price", "market_cap", "beta"}
    assert data["input_sources"]["beta"].startswith("Derived: OLS slope")
    assert "SEC annual shares" in data["input_sources"]["market_cap"]


def test_provider_values_are_never_replaced():
    stock, bench = _series_with_beta(1.3)
    today = dt.date.fromisoformat(stock[-1]["date"])
    data = {"ticker": "TEST", "currency": "USD", "shares": 10.0, "price": 99.0, "market_cap": None, "beta": 0.8}
    mi.fill_missing_market_inputs(data, fetch=_fetch_factory(stock, bench), today=today)
    assert data["price"] == 99.0 and data["beta"] == 0.8
    assert data["market_cap"] == pytest.approx(990.0)  # one price basis: provider price x shares


def test_market_cap_withheld_on_currency_mismatch():
    stock, bench = _series_with_beta(1.0)
    today = dt.date.fromisoformat(stock[-1]["date"])
    data = {"ticker": "ADR", "currency": "TWD", "shares": 1e9, "price": None, "market_cap": None, "beta": None}
    mi.fill_missing_market_inputs(data, fetch=_fetch_factory(stock, bench, currency="USD"), today=today)
    assert data["market_cap"] is None
    assert any("listing currency USD differs" in item for item in data["derived_market_inputs"]["limitations"])
    assert data["price"] is not None  # price itself is still a valid observation


def test_rate_limited_history_leaves_fields_missing():
    data = {"ticker": "TEST", "currency": "USD", "shares": 10.0, "price": None, "market_cap": None, "beta": None}
    mi.fill_missing_market_inputs(data, fetch=_fetch_factory([], [], stock_status=ProviderStatus.RATE_LIMITED))
    assert data["price"] is None and data["market_cap"] is None and data["beta"] is None
    assert data["derived_market_inputs"]["filled"] == []


def test_env_switch_disables_live_fetch(monkeypatch):
    monkeypatch.setenv("CHAINSTOX_DERIVE_MARKET_INPUTS", "0")
    data = {"ticker": "TEST", "price": None, "market_cap": None, "beta": None}
    assert mi.fill_missing_market_inputs(data) is data
    assert "derived_market_inputs" not in data


def test_prefer_derived_beta_uses_regression_and_keeps_provider_beta_for_comparison():
    stock, bench = _series_with_beta(1.6)
    today = dt.date.fromisoformat(stock[-1]["date"])
    data = {"ticker": "TEST", "currency": "USD", "shares": 10.0, "price": 99.0, "market_cap": 990.0, "beta": 0.9}
    mi.fill_missing_market_inputs(data, fetch=_fetch_factory(stock, bench), today=today, prefer_derived_beta=True)
    assert data["price"] == 99.0 and data["market_cap"] == 990.0
    assert data["beta"] == pytest.approx(1.6, abs=0.02)
    assert data["provider_beta"] == 0.9
    assert "Yahoo Finance beta 0.90 kept for comparison" in data["input_sources"]["beta"]


def test_prefer_derived_beta_falls_back_to_provider_beta_when_history_unavailable():
    data = {"ticker": "TEST", "currency": "USD", "shares": 10.0, "price": 99.0, "market_cap": 990.0, "beta": 0.9}
    mi.fill_missing_market_inputs(
        data, fetch=_fetch_factory([], [], stock_status=ProviderStatus.RATE_LIMITED), prefer_derived_beta=True
    )
    assert data["beta"] == 0.9
    assert data["provider_beta"] == 0.9


def test_cost_of_equity_labels_derived_beta(monkeypatch):
    import intrinsic_valuation as iv
    monkeypatch.setattr(iv, "_risk_free", lambda: (0.04, "fixture"))
    data = {"beta": 1.25, "provider_beta": 1.05, "input_sources": {"beta": "Derived: OLS slope of weekly returns"}}
    result = iv._cost_of_equity(data)
    assert result["beta"] == 1.25 and result["beta_source"].startswith("Derived")
    assert result["provider_beta"] == 1.05
    assert iv._cost_of_equity({"beta": 1.1})["beta_source"] == "Yahoo Finance beta"
    assert iv._cost_of_equity({"beta": None})["beta_source"] == "fallback beta of 1.0"
