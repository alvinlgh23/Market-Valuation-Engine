"""Checklist 7.4: macro factor states use the same inputs as the macro scores."""
import pandas as pd

import Valuation_model as vm
from signal_history import SignalStore, observation


def test_factor_states_read_the_scored_inputs(tmp_path):
    store = SignalStore(tmp_path)
    days = pd.bdate_range("2025-01-01", periods=100)
    store.append([observation("macro.tnx_3m", day, i / 1000, source="t", source_state="BACKFILL") for i, day in enumerate(days)])
    macro = {"tnx_level": 4.5, "tnx_3m": 0.095, "dxy_3m": 0.01, "hyg_ief": -0.01, "vix_level": 17.0, "front_rate_level": 4.0, "front_rate_3m": 0.0,
             "yield_curve": 0.005, "m2_6m": 0.03, "tnx_observed_at": str(days[-1].date())}
    states = vm.macro_factor_states(macro, store)
    scores = vm.macro_scores(macro["tnx_3m"], macro["front_rate_3m"], macro["dxy_3m"], macro["yield_curve"], macro["hyg_ief"], macro["vix_level"])
    assert states["long_rates"]["change_3m"] == macro["tnx_3m"] and states["long_rates"]["level"] == macro["tnx_level"]
    assert states["long_rates"]["state"] == "Rising" and states["long_rates"]["percentile_in_own_history"] >= 0.9
    assert states["usd"]["state"] == "Insufficient history"
    assert states["volatility"]["reading_used"] == "vix_level"
    assert set(states) == {"long_rates", "front_rates", "usd", "credit", "volatility", "curve", "money_supply"}
    assert scores["rate_score"] == vm.score_from_change(macro["tnx_3m"], bullish_when_positive=False, scale=0.12)


def test_missing_inputs_are_unavailable_not_zero(tmp_path):
    states = vm.macro_factor_states({"tnx_3m": None}, SignalStore(tmp_path))
    assert states["long_rates"]["state"] == "Unavailable" and states["long_rates"]["percentile_in_own_history"] is None
