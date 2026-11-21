"""Checklists 7.5 and 7.6: parallel valuation calculations leave the default untouched."""
from unittest.mock import patch

import pandas as pd

import intrinsic_valuation as iv
from test_intrinsic_valuation import fixture_data, fixture_rates


def report_for(data):
    with patch("intrinsic_valuation._market_rates", return_value=fixture_rates()):
        return iv.build_valuation_report("TEST", data=data)


def test_default_scenarios_are_identical_with_and_without_the_parallel_sections():
    data = fixture_data()
    report = report_for(data)
    rates = fixture_rates()
    expected = {name: iv._dcf(data, items)["fair_value_per_share"] for name, items in iv._scenario_assumptions(data, rates, {}).items()}
    assert {name: value["fair_value_per_share"] for name, value in report["scenarios"].items()} == expected
    assert report["company_spread_scenarios"]["default"] is False


def test_company_spreads_follow_history_and_respect_bounds():
    data = fixture_data()
    data["cashflow"] = pd.DataFrame({"2025": [150.0], "2024": [120.0], "2023": [60.0], "2022": [100.0]}, index=["Free Cash Flow"])
    spreads, basis = iv.company_scenario_spreads(data)
    assert iv.SPREAD_BOUNDS["growth"][0] <= basis["growth_spread"] <= iv.SPREAD_BOUNDS["growth"][1]
    assert iv.SPREAD_BOUNDS["margin"][0] <= basis["margin_spread"] <= iv.SPREAD_BOUNDS["margin"][1]
    assert spreads["bull"]["growth"] == basis["growth_spread"] and spreads["bear"]["margin"] == -basis["margin_spread"]
    assert spreads["bull"]["wacc"] == iv.DEFAULT_SCENARIO_SPREADS["bull"]["wacc"]
    result = report_for(data)["company_spread_scenarios"]
    assert result["state"] == "COMPUTED" and result["ordering_valid"]
    short = fixture_data(); short["revenue_history"] = [1000.0, 900.0, 800.0]
    assert iv.company_scenario_spreads(short)[0] is None


def test_extended_horizon_only_runs_above_the_cap_and_passes_its_checks():
    assert report_for(fixture_data())["extended_horizon"]["state"] == "NOT_TRIGGERED"   # 12% growth vs 18% cap
    fast = fixture_data(); fast["info"]["revenueGrowth"] = 0.65
    result = report_for(fast)["extended_horizon"]
    assert result["state"] == "COMPUTED" and result["first_year_growth"] == 0.50
    assert result["checks_passed"] and result["fair_value"]["bear"] <= result["fair_value"]["base"] <= result["fair_value"]["bull"]
    assert set(result["sensitivity"]) == {"first_year_growth_cap", "explicit_years", "decay", "wacc_minus_1pp_base_plus_1pp"}
    five_year = report_for(fast)["scenarios"]["base"]["fair_value_per_share"]
    assert result["fair_value"]["base"] > five_year   # a longer high-growth period adds value for a fast grower


def test_linear_decay_reaches_terminal_growth_in_the_final_year():
    data = fixture_data()
    items = iv._scenario_assumptions(data, fixture_rates(), {})["base"]
    result = iv._dcf_extended(data, items, first_growth=0.30, years=10)
    assert abs(result["forecast"][-1]["revenue_growth"] - iv._assumption_value(items, "terminal_growth")) < 1e-12
    assert all(iv._extended_checks(data, result, items).values())
