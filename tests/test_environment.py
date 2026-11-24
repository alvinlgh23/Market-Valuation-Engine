"""Checklist 3.4-3.7: environment layer."""
import pandas as pd

import environment as env
from signal_history import SignalStore, observation


def world(us_bias="Hawkish", us_signal="TIGHTENING", policy_liquidity=(43.0, "Neutral"), quality="Multinomial logistic regression", jgb=1.5, boj_normalization=0.3):
    return {"regions": {
        "US": {"engine_specific": {"central_bank_compass": {
            "available": True, "latest": "2026-07-22", "signal": us_signal, "bias": us_bias,
            "special": {"quality": quality, "probabilities_3m": {"EASING": 0.1, "HOLD": 0.2, "TIGHTENING": 0.7}},
            "liquidity": {"score": policy_liquidity[0], "classification": policy_liquidity[1], "available_drivers": 5, "expected_drivers": 7}}}},
        "JP": {"engine_specific": {"central_bank_compass": {"latest": "2026-07-17", "indicator_values": {"ten_year_yield": jgb},
                                                             "special": {"probabilities": {"normalization": boj_normalization}}}}},
    }}


def core(**macro):
    base = {"tnx_level": 4.5, "tnx_3m": 0.01, "dxy_3m": 0.0, "hyg_ief": 0.0, "vix_level": 17.0, "usdjpy_level": 150.0, "usdjpy_3m": 0.0,
            "liquidity_score": 32.0, "tnx_observed_at": "2026-11-04"}
    return {"macro": {**base, **macro}, "catalysts": {"fed_future_rate": 4.1, "fed_future_trend": 0.2, "fed_sensitivity": "Moderate"},
            "fragility": {"ism_pmi": 47.9, "ism_pmi_trend": -0.3, "consumer_sentiment": 48.1}, "risk": {"regime": "Healthy Rotation"}}


def test_fed_path_uses_compass_and_flags_divergence_from_futures(tmp_path):
    store = SignalStore(tmp_path)
    agree = env.build_environment(core(), world(), {}, None, store=store)["factors"]["fed_path"]
    assert agree["direction"] == 1 and agree["readings"]["market_direction"] == 1 and agree["readings"]["divergence"] is None
    assert any("always-hold baseline" in note for note in agree["notes"])
    split = core(); split["catalysts"]["fed_future_trend"] = -0.3
    result = env.build_environment(split, world(), {}, None, store=store)
    assert result["factors"]["fed_path"]["readings"]["divergence"]
    assert any("fed_path" in item["factors"] for item in result["contradictions"])
    fallback = env.fed_path(core(), world(quality="Heuristic fallback"), {})
    assert any("rule-based fallback" in note for note in fallback["notes"])


def test_two_liquidity_scores_are_shown_side_by_side_and_never_merged(tmp_path):
    result = env.liquidity(core(liquidity_score=32.0), world(policy_liquidity=(43.0, "Neutral")))
    readings = result["readings"]
    assert readings["policy_liquidity"]["name"] == "Policy liquidity (Compass)" and readings["policy_liquidity"]["score"] == 43.0
    assert readings["market_liquidity"]["name"] == "Market liquidity (price-based)" and readings["market_liquidity"]["label"] == "Tight"
    assert readings["relation"] == "DIFFERENT"
    assert env.liquidity(core(liquidity_score=70.0), world(policy_liquidity=(20.0, "Liquidity Contracting")))["readings"]["relation"] == "OPPOSITE"
    assert env.liquidity(core(liquidity_score=55.0), world(policy_liquidity=(50.0, "Neutral")))["readings"]["relation"] == "AGREE"


def test_carry_is_a_switch_with_context():
    result = env.yen_carry(core(usdjpy_3m=-0.05), world(jgb=1.5, boj_normalization=0.6), {"leveraged_net": -40000, "as_of": "2026-11-10"})
    assert result["readings"]["carry_state"] == "UNWIND_RISK" and result["direction"] == -1
    assert result["readings"]["us_jp_10y_spread_pp"] == 3.0
    assert any("normalisation probability is 60%" in note for note in result["notes"])
    assert any("net short yen" in note for note in result["notes"])
    environment = env.build_environment(core(usdjpy_3m=-0.05), world(), {}, None)
    assert environment["tail_risk"]["yen_carry_unwind"] is True


def test_cli_carry_label_uses_the_single_definition():
    import Valuation_model as vm
    for usdjpy_3m, vix, label in [(None, None, "Unavailable"), (-0.04, 15, "Unwind Risk"), (0.03, 15, "Supportive"), (0.0, 15, "Neutral"), (0.03, 30, "Unwind Risk")]:
        assert vm.carry_condition_label(usdjpy_3m, vix) == label


def test_cftc_parser_reads_leveraged_funds():
    row = '"JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",261110,2026-11-10,097741,CME ,00,097 ,  388875,   19338,  145649,    4394,  161322,   70978,    8142,   89089,  105944,    9099,   62127'
    parsed = env.parse_cftc_jpy("header\n" + row + "\n")
    assert parsed["as_of"] == "2026-11-10" and parsed["leveraged_long"] == 89089 and parsed["leveraged_short"] == 105944
    assert parsed["leveraged_net"] == -16855
    assert env.parse_cftc_jpy("nothing here") is None


def test_market_factor_direction_comes_from_own_history_percentile(tmp_path):
    store = SignalStore(tmp_path)
    days = pd.bdate_range("2025-01-01", periods=100)
    store.append([observation("macro.tnx_3m", day, index / 100, source="t", source_state="BACKFILL") for index, day in enumerate(days)])
    as_of = str(days[-1].date())
    high = env.build_environment(core(tnx_3m=0.95, tnx_observed_at=as_of), world(), {}, None, store=store)["factors"]["long_rates"]
    low = env.build_environment(core(tnx_3m=0.05, tnx_observed_at=as_of), world(), {}, None, store=store)["factors"]["long_rates"]
    assert high["direction"] == 1 and low["direction"] == -1
    thin = env.build_environment(core(), world(), {}, None, store=SignalStore(tmp_path / "empty"))["factors"]["long_rates"]
    assert thin["direction"] is None and thin["state"] == "Insufficient history"


def test_semis_cycle_reads_kospi_history_and_flags_missing_monthly_exports():
    history = [{"t": f"d{i}", "signal": 1 + i * 0.01, "benchmark": 1 + i * 0.002} for i in range(200)]
    kospi = {"sweep": {"timestamp": "2026-11-05 09:23 UTC", "results": [{"key": "tech", "corr": 0.29, "pval": 0.0, "strength": "Strong", "detail": {"history": history}}]},
             "exports": {"items": [{"key": "semiconductors", "value_b": 173.4, "period": "2025"}]}}
    result = env.semis_cycle(kospi)
    assert result["direction"] is not None and result["readings"]["korea_semiconductor_exports_usd_b"] == 173.4
    assert any("DATA_GO_KR_SERVICE_KEY" in note for note in result["notes"])
    assert env.semis_cycle(None)["state"] == "Unavailable"


def test_empty_inputs_never_raise(tmp_path):
    result = env.build_environment(None, {"regions": {}}, None, None, store=SignalStore(tmp_path))
    assert set(result["factors"]) >= {"long_rates", "usd", "credit", "volatility", "fed_path", "liquidity", "yen_carry", "semis_cycle", "oil", "inflation", "growth"}
    assert "neer" not in result.get("excluded", {})   # Singapore removed 2026-11-22


def test_track_record_says_whether_a_factor_has_predicted_returns():
    scorecard = {"macro": {
        "hyg_ief": {"verdict": "WEAK", "horizons": {"1M": {"corr": -0.17, "t_stat": -1.0, "samples": 35}}},
        "vix_level": {"verdict": "INFORMATIVE", "horizons": {"1M": {"corr": 0.44, "t_stat": 2.8, "samples": 35}}}}}
    weak = env.track_record("hyg_ief", scorecard)
    assert not weak["predictive"] and weak["text"].startswith("Has not reliably predicted") and "35 months" in weak["text"]
    informative = env.track_record("vix_level", scorecard)
    assert informative["predictive"] and "followed by higher next-month" in informative["text"]
    assert env.track_record(None, scorecard)["verdict"] == "NOT_TESTED"
    assert env.track_record("tnx_3m", None)["verdict"] == "NOT_TESTED"


def test_every_factor_carries_a_track_record(tmp_path):
    factors = env.build_environment(None, {"regions": {}}, None, None, store=SignalStore(tmp_path))["factors"]
    assert all("track_record" in factor for factor in factors.values())
    assert factors["fed_path"]["track_record"]["verdict"] == "NOT_TESTED"
    assert factors["credit"]["track_record"]["signal"] == "hyg_ief"
