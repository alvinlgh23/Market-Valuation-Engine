"""Checklist 7.5: bear/bull spreads from company history are the default. Checklist 7.6: the ten-year model is phased in above the cap."""
from unittest.mock import patch

import pandas as pd

import intrinsic_valuation as iv
from test_intrinsic_valuation import fixture_data, fixture_rates


def report_for(data):
    with patch("intrinsic_valuation._market_rates", return_value=fixture_rates()):
        return iv.build_valuation_report("TEST", data=data)


def test_default_scenarios_use_company_spreads_and_keep_the_old_values_beside_them():
    data = fixture_data()
    data["cashflow"] = pd.DataFrame({"2025": [150.0], "2024": [120.0], "2023": [60.0], "2022": [100.0]}, index=["Free Cash Flow"])
    report = report_for(data)
    rates = fixture_rates()
    spreads, _ = iv.company_scenario_spreads(data)
    expected = {name: iv._dcf(data, items)["fair_value_per_share"] for name, items in iv._scenario_assumptions(data, rates, {}, spreads=spreads).items()}
    legacy = {name: iv._dcf(data, items)["fair_value_per_share"] for name, items in iv._scenario_assumptions(data, rates, {}).items()}
    assert {name: value["fair_value_per_share"] for name, value in report["scenarios"].items()} == expected
    record = report["scenario_spreads"]
    assert record["source"] == "COMPANY_HISTORY" and record["default_spread_fair_value"] == legacy
    assert record["spreads"]["bull"] == {"growth": spreads["bull"]["growth"], "margin": spreads["bull"]["margin"]}
    assert expected["base"] == legacy["base"]   # spreads move bear and bull only
    assert expected["bear"] <= expected["base"] <= expected["bull"]


def test_short_history_keeps_the_four_point_default():
    data = fixture_data(); data["revenue_history"] = [1000.0, 900.0, 800.0]
    report = report_for(data)
    assert report["scenario_spreads"]["source"] == "DEFAULT"
    assert report["scenario_spreads"]["spreads"]["bull"] == {"growth": 0.04, "margin": 0.04}
    rates = fixture_rates()
    expected = {name: iv._dcf(data, items)["fair_value_per_share"] for name, items in iv._scenario_assumptions(data, rates, {}).items()}
    assert {name: value["fair_value_per_share"] for name, value in report["scenarios"].items()} == expected


def test_company_spreads_follow_history_and_respect_bounds():
    data = fixture_data()
    data["cashflow"] = pd.DataFrame({"2025": [150.0], "2024": [120.0], "2023": [60.0], "2022": [100.0]}, index=["Free Cash Flow"])
    spreads, basis = iv.company_scenario_spreads(data)
    assert iv.SPREAD_BOUNDS["growth"][0] <= basis["growth_spread"] <= iv.SPREAD_BOUNDS["growth"][1]
    assert iv.SPREAD_BOUNDS["margin"][0] <= basis["margin_spread"] <= iv.SPREAD_BOUNDS["margin"][1]
    assert spreads["bull"]["growth"] == basis["growth_spread"] and spreads["bear"]["margin"] == -basis["margin_spread"]
    assert spreads["bull"]["wacc"] == iv.DEFAULT_SCENARIO_SPREADS["bull"]["wacc"]
    short = fixture_data(); short["revenue_history"] = [1000.0, 900.0, 800.0]
    assert iv.company_scenario_spreads(short)[0] is None


def test_ten_year_bear_and_bull_use_the_same_growth_spreads():
    data = fixture_data(); data["info"]["revenueGrowth"] = 0.65
    report = report_for(data)
    spreads, _ = iv.company_scenario_spreads(data)
    assumptions = iv._scenario_assumptions(data, fixture_rates(), {}, spreads=spreads)
    bull = iv._dcf_extended(data, assumptions["bull"], 0.50 + spreads["bull"]["growth"])["fair_value_per_share"]
    assert abs(report["extended_horizon"]["fair_value"]["bull"] - bull) < 1e-9


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


def test_extended_weight_is_continuous_from_the_cap():
    cap = 0.18
    assert iv.extended_weight(0.12, cap) == 0.0 and iv.extended_weight(cap, cap) == 0.0
    assert abs(iv.extended_weight(cap + 0.01, cap) - 0.1) < 1e-12
    assert abs(iv.extended_weight(cap + iv.PHASE_IN_BAND / 2, cap) - 0.5) < 1e-12
    assert iv.extended_weight(cap + iv.PHASE_IN_BAND, cap) == 1.0 and iv.extended_weight(1.03, cap) == 1.0
    assert iv.extended_weight(None, cap) == 0.0 and iv.extended_weight(0.5, None) == 0.0


def test_headline_is_five_year_within_the_cap():
    report = report_for(fixture_data())
    five = {name: value["fair_value_per_share"] for name, value in report["scenarios"].items()}
    assert report["fair_value"]["method"] == "FIVE_YEAR" and report["fair_value"]["extended_weight"] == 0.0
    assert report["fair_value"]["fair_value"] == five
    assert report["final_interpretation"]["base_fair_value"] == five["base"]


def test_headline_blends_by_weight_and_has_no_jump_at_the_cap():
    def headline(growth):
        data = fixture_data(); data["info"]["revenueGrowth"] = growth
        return report_for(data)
    just_above = headline(0.18 + 1e-6)
    assert just_above["fair_value"]["extended_weight"] < 1e-4
    assert abs(just_above["fair_value"]["fair_value"]["base"] - just_above["fair_value"]["five_year"]["base"]) < 1e-2 * abs(just_above["fair_value"]["five_year"]["base"])
    mid = headline(0.23)
    weight = mid["fair_value"]["extended_weight"]
    assert abs(weight - 0.5) < 1e-9 and mid["fair_value"]["method"] == "PHASED"
    for name in ("bear", "base", "bull"):
        expected = (1 - weight) * mid["fair_value"]["five_year"][name] + weight * mid["fair_value"]["ten_year"][name]
        assert abs(mid["fair_value"]["fair_value"][name] - expected) < 1e-9
    assert mid["final_interpretation"]["base_fair_value"] == mid["fair_value"]["fair_value"]["base"]
    # The five-year scenarios stay intact beside the headline.
    assert mid["scenarios"]["base"]["fair_value_per_share"] == mid["fair_value"]["five_year"]["base"]


def test_blended_reverse_dcf_reprices_the_phased_model():
    data = fixture_data(); data["info"]["revenueGrowth"] = 0.23
    report = report_for(data)
    reverse = report["fair_value"]["reverse_dcf"]
    weight = report["fair_value"]["extended_weight"]
    assert reverse["status"] == "CONVERGED"
    items = iv._scenario_assumptions(data, fixture_rates(), {})["base"]
    growth = reverse["required_year_1_revenue_growth"]
    value = (1 - weight) * iv._dcf(data, items, forced_growth=growth)["fair_value_per_share"] + weight * iv._dcf_extended(data, items, growth)["fair_value_per_share"]
    assert abs(value - data["price"]) <= iv.REVERSE_TOLERANCE_PER_SHARE


def test_withheld_valuation_withholds_the_headline():
    data = fixture_data(); data["info"]["revenueGrowth"] = 0.23
    data["depreciation_amortization"] = None   # a missing FCFF input still withholds (checklist 12.1 runs both bases only when nothing is missing)
    report = report_for(data)
    assert report["validation"]["status"] == "FAILED"
    assert report["fair_value"]["method"] == "WITHHELD" and report["fair_value"]["fair_value"] == {}
