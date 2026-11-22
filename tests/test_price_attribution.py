"""Checklist 10.1: price attribution into macro / market / sector / company."""
import math

import numpy as np
import pandas as pd
import pytest

from price_attribution import attribute, build_attribution

WEEKS = 140


def _prices(returns, start=100.0):
    index = pd.date_range("2023-01-06", periods=len(returns) + 1, freq="W-FRI")
    return pd.Series(start * np.exp(np.concatenate([[0.0], np.cumsum(returns)])), index=index)


def _setup(seed=1, company_shock=0.0, macro_beta=1.5):
    rng = np.random.default_rng(seed)
    factor = rng.normal(0, 0.02, WEEKS)
    market_only = rng.normal(0, 0.015, WEEKS)
    spy_r = 0.5 * factor + market_only
    sector_r = spy_r + rng.normal(0, 0.01, WEEKS)
    noise = rng.normal(0, 0.01, WEEKS)
    stock_r = macro_beta * factor + 1.0 * market_only + noise
    stock_r[-13:] += company_shock / 13
    index = pd.date_range("2023-01-13", periods=WEEKS, freq="W-FRI")
    return _prices(stock_r), _prices(spy_r), _prices(sector_r), {"usd": pd.Series(factor, index=index)}


def test_parts_add_up_to_the_actual_log_return():
    stock, spy, sector, factors = _setup()
    result = attribute(stock, spy, sector, factors)
    assert result["status"] == "AVAILABLE"
    for window in result["windows"].values():
        parts = window["parts"]
        assert sum(parts.values()) == pytest.approx(window["total_log"], abs=1e-9)
        assert window["price_change"] == pytest.approx(math.exp(window["total_log"]) - 1)


def test_macro_beta_is_recovered_and_noise_stays_small():
    stock, spy, sector, factors = _setup(macro_beta=1.5)
    result = attribute(stock, spy, sector, factors)
    assert result["betas"]["usd"] == pytest.approx(1.5, abs=0.25)
    assert abs(result["windows"]["3M"]["company_z"]) < 2
    assert result["fit"]["r2"] > 0.5


def test_a_company_shock_shows_up_as_company_specific():
    stock, spy, sector, factors = _setup(company_shock=-0.30)
    window = attribute(stock, spy, sector, factors)["windows"]["3M"]
    assert window["parts"]["company"] < -0.2
    assert window["company_z"] < -2


def test_sensitivities_do_not_use_the_attribution_window():
    stock, spy, sector, factors = _setup()
    base = attribute(stock, spy, sector, factors)
    shocked_stock = stock.copy()
    shocked_stock.iloc[-5:] *= 0.5          # only inside the window
    shocked = attribute(shocked_stock, spy, sector, factors)
    assert shocked["betas"] == pytest.approx(base["betas"])


def test_short_history_is_unavailable_not_zero():
    stock, spy, sector, factors = _setup()
    result = attribute(stock.iloc[-50:], spy, sector, factors)
    assert result["status"] == "UNAVAILABLE" and "aligned weeks" in result["reason"]


def test_build_attribution_uses_archetype_factors_and_reports_missing_history():
    stock, spy, sector, _ = _setup()
    frames = {"AAA": stock, "SPY": spy, "XLK": sector}
    fetch = lambda symbol, period: frames[symbol].to_frame("Close") if symbol in frames else None  # noqa: E731
    result = build_attribution("AAA", "FABLESS_SEMICONDUCTOR", "XLK", fetch=fetch)
    assert result["status"] == "AVAILABLE"
    assert result["factors"] == []                       # no factor histories were available
    assert "semis_cycle" in result["factors_dropped"]
    assert "000660.KS" in result["missing_histories"]
    missing = build_attribution("ZZZ", "BANK", None, fetch=fetch)
    assert missing["status"] == "UNAVAILABLE"
