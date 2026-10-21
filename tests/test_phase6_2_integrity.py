import math
import pytest
from treasury_semantics import treasury_curve
from research_system import yield_return_to_bps, build_core_market
from unittest.mock import patch


@pytest.mark.parametrize("ticker,maturity,value", [("2YY=F", "2Y", -.5), ("^FVX", "5Y", -.5), ("^IRX", "3M", -.5), (None, None, None)])
def test_curve_maturity(ticker, maturity, value):
    result = treasury_curve(4, 4.5, ticker, "2026-10-19", "2026-10-19", "STALE")
    assert result["value"] == value
    assert result["short_maturity"] == maturity
    assert result["fallback"] == (maturity != "2Y")
    assert result["source_state"] == "STALE"
    assert result["units"] == "pp"


def test_curve_missing_and_different_dates():
    assert treasury_curve(None, 4, "2YY=F")["value"] is None
    assert treasury_curve(4, None, "2YY=F")["value"] is None
    curve = treasury_curve(4.5, 4, "2YY=F", "2026-10-19", "2026-10-18")
    assert curve["value"] == .5
    assert curve["period_alignment"] == "MISMATCH"
    assert curve["observation_timestamp"] is None


@pytest.mark.parametrize("level,change,expected", [(4.5, .125, 50), (4, -.2, -100), (4, 0, 0), (None, .1, None), (4, None, None), (math.nan, .1, None)])
def test_yield_moves(level, change, expected):
    result = yield_return_to_bps(level, change)
    assert result is None if expected is None else round(result, 6) == expected


def test_sector_orchestration_preserves_engine_measurements():
    rows = [{"ticker": "SMH", "rel_1m": .1, "rel_3m": .2, "rel_6m": .3, "as_of": "2026-10-19"}]
    with patch("Valuation_model.compute_macro", return_value={}), patch("Valuation_model.compute_macro_fragility", return_value={}), patch("Valuation_model.compute_macro_catalysts", return_value={}), patch("Valuation_model.compute_risk_regime_report", return_value={}), patch("Valuation_model.compute_sectors", return_value=rows):
        result = build_core_market()
    assert result["sectors"] == rows
    assert result["data_quality"]["sector_rows"] == 1


def test_empty_refresh_preserves_last_valid_sector_data():
    from research_system import isolated
    with patch("research_system.load_cache", return_value={"sectors": [{"ticker": "SMH", "rel_6m": .2}]}), patch("research_system.save_cache") as save:
        result = isolated("core-market", lambda: {"sectors": []}, True)
    assert result["state"] == "STALE"
    assert result["payload"]["sectors"][0]["rel_6m"] == .2
    save.assert_not_called()


def test_critical_arithmetic_failure_is_failed_not_provisional():
    from test_intrinsic_valuation import fixture_data, fixture_rates
    from intrinsic_valuation import _scenario_assumptions, _dcf, _validate, _reverse_dcf, _sensitivity
    data, rates = fixture_data(), fixture_rates()
    assumptions = _scenario_assumptions(data, rates, {})
    scenarios = {name: _dcf(data, items) for name, items in assumptions.items()}
    scenarios["base"]["pv_forecast_fcff"] += 100
    result = _validate(data, assumptions, scenarios, _reverse_dcf(data, assumptions["base"]), _sensitivity(data, assumptions["base"]), rates)
    assert result["status"] == "FAILED"
    assert not result["checks"]["forecast_arithmetic"]["passed"]


def test_failed_report_withholds_authoritative_values_but_preserves_diagnostics():
    from test_intrinsic_valuation import fixture_data, fixture_rates
    from intrinsic_valuation import build_valuation_report
    with patch("intrinsic_valuation._market_rates", return_value=fixture_rates()), patch("intrinsic_valuation._validate", return_value={"status": "FAILED", "checks": {}, "reasons": ["arithmetic failed"]}):
        result = build_valuation_report("TEST", data=fixture_data())
    assert not result["scenarios"]
    assert "base" in result["diagnostic_scenarios"]
    assert "base_fair_value" not in result["final_interpretation"]


def test_transmission_preserves_maturity_and_withholds_mixed_date_curve():
    import json
    from pathlib import Path
    from research_system import build_market_transmission
    world = json.loads((Path(__file__).resolve().parents[1] / "frontend/lib/fixtures/research-system.json").read_text())["world"]
    indicators = world["regions"]["US"]["engine_specific"]["central_bank_compass"]["indicator_values"]
    indicators.pop("yield_curve", None)
    core = {"macro": {"tnx_level": 4.5, "front_rate_level": 4.0, "front_rate_ticker": "^FVX", "tnx_observed_at": "2026-10-20", "front_rate_observed_at": "2026-10-19", "front_rate_3m": .1}}
    result = build_market_transmission(world, core, {"core_market": "STALE"})
    metrics = {item["key"]: item for item in result["rates"]["metrics"]}
    assert metrics["us_10y_5y"]["raw_value"] == .5
    assert metrics["us_10y_5y"]["maturity_metadata"]["fallback"]
    assert metrics["us_2y"]["raw_value"] == indicators["two_year_yield"]
    assert result["rates"]["current_curve"] == []
    assert result["rates"]["moves"][0]["key"] == "us_5y_3m"
