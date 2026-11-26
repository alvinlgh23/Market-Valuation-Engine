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
        # The split is done in log returns; the shown parts are scaled to add up to the % price change (18.2).
        assert sum(window["log_parts"].values()) == pytest.approx(window["total_log"], abs=1e-9)
        assert sum(window["parts"].values()) == pytest.approx(window["price_change"], abs=1e-9)
        assert sum(window["macro_by_factor"].values()) == pytest.approx(window["parts"]["macro"], abs=1e-9)
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


# ---- Checklist 10.2: fundamentals or noise -------------------------------------------------------
from price_attribution import price_reading  # noqa: E402


def _attr(company, z, macro=-0.20, market=-0.03, sector=-0.01, r2=0.6):
    total = macro + market + sector + company
    return {"status": "AVAILABLE", "fit": {"r2": r2}, "factor_labels": {"volatility": "Equity volatility"},
            "windows": {"3M": {"price_change": math.exp(total) - 1, "parts": {"macro": macro, "market": market, "sector": sector, "company": company},
                               "top_macro": {"factor": "volatility", "value": macro}, "company_z": z}}}


def test_macro_drop_with_normal_company_part_is_noise():
    reading = price_reading(_attr(-0.02, -0.2), "Estimates stable or mixed")
    assert reading["kind"] == "noise"
    assert reading["label"] == "Macro (mainly equity volatility)-driven; company part within its normal range"
    assert reading["short"] == "Macro-driven"


def test_company_drop_with_estimate_cuts_is_fundamentals():
    assert price_reading(_attr(-0.27, -2.4), "Estimates falling")["kind"] == "fundamentals"


def test_company_drop_without_estimate_cuts_is_sentiment_or_flows():
    reading = price_reading(_attr(-0.27, -2.4), "Estimates rising")
    assert reading["kind"] == "company" and "sentiment or flows" in reading["label"]
    assert "estimates unavailable" in price_reading(_attr(-0.27, -2.4), "Consensus data unavailable")["label"]


def test_middle_band_is_watch_and_low_fit_is_flagged():
    reading = price_reading(_attr(0.12, 1.4, r2=0.2))
    assert reading["kind"] == "watch" and reading["confidence"] == "LOW" and reading["low_fit_note"]


def test_unavailable_attribution_is_unknown_not_noise():
    assert price_reading({"status": "UNAVAILABLE", "reason": "no history"})["kind"] == "unknown"
    assert price_reading(None)["kind"] == "unknown"


def test_no_mapped_macro_factors_is_rough():
    attribution = _attr(0.25, 2.2)
    attribution["factors"] = []
    reading = price_reading(attribution, "Estimates stable or mixed")
    assert reading["confidence"] == "LOW" and "No macro exposures" in reading["low_fit_note"]


def test_unfinished_week_is_dropped_not_dated_in_the_future():
    import pandas as pd
    from price_attribution import _weekly_close
    days = pd.bdate_range("2026-11-02", "2026-11-24")          # ends on a Tuesday
    weekly = _weekly_close(pd.DataFrame({"Close": range(1, len(days) + 1)}, index=days))
    assert weekly.index[-1] == pd.Timestamp("2026-11-20")      # last completed Friday, not 27 November
    full = pd.bdate_range("2026-11-02", "2026-11-27")
    assert _weekly_close(pd.DataFrame({"Close": range(1, len(full) + 1)}, index=full)).index[-1] == pd.Timestamp("2026-11-27")


def test_equal_weight_benchmark_and_no_vix_cause():
    """18.17 / 18.19: a heavyweight is measured against an equal-weight sector, and the VIX is not a cause."""
    import numpy as np
    import pandas as pd
    from price_attribution import build_attribution
    days = pd.bdate_range("2023-01-02", periods=900)
    rng = np.random.default_rng(3)
    asked = []

    def fetch(symbol, period):
        asked.append(symbol)
        return pd.DataFrame({"Close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))}, index=days)

    result = build_attribution("NVDA", "FABLESS_SEMICONDUCTOR", "SMH", fetch=fetch)
    assert "XSD" in asked and "SMH" not in asked and "^VIX" not in asked
    assert result["sector_etf"] == "SMH" and result["sector_benchmark"] == "XSD"
    assert "volatility" not in result["factors"] and result["method_version"] == 2


def test_post_friday_daily_bridge_captures_intraweek_move():
    import pandas as pd
    from price_attribution import _recent_daily_move
    days = pd.bdate_range("2026-10-01", "2026-11-24")  # ends Tuesday after 2026-11-20 Friday
    prices = [100.0] * (len(days) - 2) + [112.0, 130.0]
    spy_prices = [500.0] * (len(days) - 2) + [505.0, 510.0]
    daily = pd.DataFrame({"Close": prices}, index=days)
    spy = pd.DataFrame({"Close": spy_prices}, index=days)
    bridge = _recent_daily_move(daily, spy, "2026-11-20")
    assert bridge is not None
    assert bridge["latest_date"] == "2026-11-24"
    assert bridge["since_window_end"] is not None
    assert bridge["since_window_end"]["trading_days"] == 2
    assert abs(bridge["since_window_end"]["stock_change"] - 0.30) < 1e-6
    assert abs(bridge["since_window_end"]["spy_change"] - 0.02) < 1e-6
