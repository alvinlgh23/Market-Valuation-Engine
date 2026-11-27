"""2026-11-27: M2 and the Fed balance sheet are read from the offline cache even without a FRED_API_KEY."""
import types

import pandas as pd

import macro_world as mw


def _fake_modules():
    calls = {}
    liquidity = types.SimpleNamespace()
    liquidity.fred_yoy = lambda *a: None                       # Compass's original: nothing without an API key
    liquidity.yoy = lambda series, periods: round((series.iloc[-1] / series.iloc[-1 - periods] - 1) * 100, 2)
    fred = types.SimpleNamespace()

    def fetch_series(series_id, config):
        calls["series"] = series_id
        return pd.Series([100.0] * 12 + [105.0])
    fred.fetch_series = fetch_series
    return liquidity, fred, calls


def test_money_trend_reads_the_cached_series_without_an_api_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    liquidity, fred, calls = _fake_modules()
    mw._read_cached_money_trends(liquidity, fred)
    config = {"liquidity": {"fred_series": {"US": {"m2": "M2SL"}}}}
    assert liquidity.fred_yoy(config, "US", "m2", 12) == 5.0
    assert calls["series"] == "M2SL"


def test_unknown_series_and_empty_cache_stay_missing(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    liquidity, fred, _ = _fake_modules()
    fred.fetch_series = lambda series_id, config: pd.Series(dtype=float)
    mw._read_cached_money_trends(liquidity, fred)
    assert liquidity.fred_yoy({"liquidity": {"fred_series": {"US": {"m2": "M2SL"}}}}, "US", "m2", 12) is None   # missing stays missing
    assert liquidity.fred_yoy({}, "US", "m2", 12) is None


def test_patch_is_applied_once():
    liquidity, fred, _ = _fake_modules()
    mw._read_cached_money_trends(liquidity, fred)
    first = liquidity.fred_yoy
    mw._read_cached_money_trends(liquidity, fred)
    assert liquidity.fred_yoy is first
