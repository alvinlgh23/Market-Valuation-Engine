import contextlib
import io
import json
import unittest
from unittest.mock import patch

import pandas as pd

import Valuation_model as cli
from intrinsic_valuation import (
    Assumption,
    SBC_ACCOUNTING_POLICY,
    SBC_OWNER_EARNINGS_POLICY,
    _base_parameters,
    _dcf,
    _historical_fcff_reconciliation,
    _reverse_dcf,
    _row,
    _scenario_assumptions,
    _sensitivity,
    _validate,
    build_valuation_report,
    classify_security,
    run_valuation,
)


def assumptions(wacc=0.09, terminal_growth=0.025):
    return [
        Assumption("year_1_revenue_growth", 0.10, "decimal", "test", "test", "high", "base"),
        Assumption("year_5_fcff_margin", 0.20, "decimal", "test", "test", "high", "base"),
        Assumption("wacc", wacc, "decimal", "test", "test", "high", "base"),
        Assumption("terminal_growth", terminal_growth, "decimal", "test", "test", "high", "base"),
        Assumption("annual_dilution", 0.0, "decimal", "test", "test", "high", "base"),
        Assumption("exit_ev_fcff_multiple", 16.0, "multiple", "test", "test", "high", "base"),
        Assumption("tax_rate", 0.21, "decimal", "test", "test", "high", "base"),
    ]


def fixture_data(kind="MATURE_OPERATING_COMPANY", price=31.0):
    return {
        "ticker": "TEST",
        "ticker_obj": None,
        "info": {
            "quoteType": "EQUITY",
            "sector": "Technology",
            "industry": "Software - Infrastructure",
            "revenueGrowth": 0.12,
            "grossMargins": 0.70,
            "operatingMargins": 0.20,
            "freeCashflow": 140.0,
            "forwardPE": 24.0,
            "enterpriseToRevenue": 4.0,
            "enterpriseToEbitda": 18.0,
        },
        "income": None,
        "cashflow": None,
        "balance": None,
        "company": "Fixture Company",
        "security_type": kind,
        "routing_evidence": ["deterministic fixture"],
        "price": price,
        "revenue_history": [1000.0, 900.0, 810.0, 730.0],
        "operating_income_history": [200.0, 175.0, 150.0, 130.0],
        "gross_profit_history": [700.0, 620.0, 550.0, 490.0],
        "latest_revenue": 1000.0,
        "latest_operating_income": 200.0,
        "latest_net_income": 142.0,
        "latest_ocf": 210.0,
        "latest_capex": 60.0,
        "latest_fcf": 150.0,
        "latest_fcff": 150.0,
        "sbc": 20.0,
        "depreciation_amortization": 40.0,
        "working_capital_change": -10.0,
        "other_non_cash_adjustments": 18.0,
        "operating_gains_losses": None,
        "interest_expense": 20.0,
        "after_tax_interest": 15.8,
        "cash": 200.0,
        "debt": 100.0,
        "other_senior_claims": 0.0,
        "shares": 100.0,
        "market_cap": 3100.0,
        "tax_rate": 0.21,
        "beta": 1.0,
        "currency": "USD",
        "as_of": "2026-07-23 12:00 EDT",
        "periods": {
            "revenue": "Latest fiscal year",
            "operating_income": "Latest fiscal year",
            "fcff": "Latest fiscal year",
            "free_cash_flow": "Latest fiscal year",
            "cash_and_debt": "Latest reported balance sheet",
            "shares": "Latest fiscal-year diluted average",
            "market_price": "Current / latest available market price",
        },
    }


def fixture_rates():
    return {
        "risk_free_rate": 0.04,
        "risk_free_source": "fixture",
        "equity_risk_premium": 0.045,
        "erp_source": "fixture",
        "beta": 1.0,
        "beta_source": "fixture",
        "cost_of_equity": 0.085,
        "pre_tax_cost_of_debt": 0.055,
        "after_tax_cost_of_debt": 0.04345,
        "debt_weight": 0.03,
        "equity_weight": 0.97,
        "wacc": 0.084,
        "confidence": "high",
        "fallbacks": [],
    }


class IntrinsicValuationTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "latest_revenue": 1000.0,
            "latest_fcff": 150.0,
            "cash": 200.0,
            "debt": 100.0,
            "other_senior_claims": 0.0,
            "shares": 100.0,
            "price": 31.0,
        }

    def build_fixture_report(self, kind="MATURE_OPERATING_COMPANY", price=31.0):
        with (
            patch("intrinsic_valuation.collect_valuation_data", return_value=fixture_data(kind, price)),
            patch("intrinsic_valuation._market_rates", return_value=fixture_rates()),
        ):
            return build_valuation_report("TEST")

    def test_precollected_data_reuses_snapshot_without_refetching(self):
        data = fixture_data()
        with (
            patch("intrinsic_valuation.collect_valuation_data", side_effect=AssertionError("unexpected refetch")),
            patch("intrinsic_valuation._market_rates", return_value=fixture_rates()),
        ):
            report = build_valuation_report("TEST", data=data)
        self.assertIn("base", report["scenarios"])

    def test_etf_never_routes_to_company_dcf(self):
        result = classify_security("SPY", {"quoteType": "ETF", "shortName": "SPDR S&P 500 ETF"}, False)
        self.assertEqual(result, "ETF_OR_FUND")

    def test_financial_routes_to_financial_framework(self):
        result = classify_security("JPM", {"sector": "Financial Services", "industry": "Banks - Diversified"}, True)
        self.assertEqual(result, "FINANCIAL_INSTITUTION")

    def test_growth_software_requires_operating_evidence(self):
        result = classify_security(
            "CRWD",
            {
                "sector": "Technology",
                "industry": "Software - Infrastructure",
                "revenueGrowth": 0.25,
                "grossMargins": 0.75,
                "operatingMargins": -0.02,
                "freeCashflow": 100.0,
            },
            True,
        )
        self.assertEqual(result, "GROWTH_SOFTWARE_COMPANY")

    def test_cash_burning_software_routes_to_pre_profit(self):
        result = classify_security(
            "EARLY",
            {
                "sector": "Technology",
                "industry": "Software - Application",
                "revenueGrowth": 0.30,
                "grossMargins": 0.70,
                "operatingMargins": -0.20,
                "freeCashflow": -100.0,
            },
            True,
        )
        self.assertEqual(result, "PRE_PROFIT_COMPANY")

    def test_mu_routes_to_cyclical(self):
        result = classify_security("MU", {"sector": "Technology", "industry": "Semiconductors"}, True)
        self.assertEqual(result, "CYCLICAL_COMPANY")

    def test_msft_routes_to_mature_company(self):
        result = classify_security(
            "MSFT",
            {
                "sector": "Technology",
                "industry": "Software - Infrastructure",
                "revenueGrowth": 0.20,
                "operatingMargins": 0.45,
                "freeCashflow": 10.0,
            },
            True,
        )
        self.assertEqual(result, "MATURE_OPERATING_COMPANY")

    def test_supported_framework_reports_are_built(self):
        expected = {
            "MATURE_OPERATING_COMPANY": "Five-year FCFF",
            "GROWTH_SOFTWARE_COMPANY": "Revenue-to-FCFF",
            "CYCLICAL_COMPANY": "Cycle-adjusted",
        }
        for kind, method_text in expected.items():
            with self.subTest(kind=kind):
                report = self.build_fixture_report(kind)
                self.assertIn(method_text, report["selected_method"])
                self.assertEqual(set(report["scenarios"]), {"bear", "base", "bull"})

    def test_historical_fcff_reconciliation_passes_with_disclosed_bridge(self):
        result = _historical_fcff_reconciliation(fixture_data())
        self.assertEqual(result["status"], "PASSED")
        self.assertAlmostEqual(result["nopat"], 158.0)
        self.assertAlmostEqual(result["change_in_working_capital"], 10.0)
        self.assertAlmostEqual(result["other_adjustments"], 18.0)
        self.assertAlmostEqual(result["nopat_based_fcff_before_sbc"], 146.0)
        self.assertAlmostEqual(result["sbc_addback"], 20.0)
        self.assertAlmostEqual(result["calculated_fcff"], 166.0)
        self.assertAlmostEqual(result["cfo_based_fcff"], 165.8)
        self.assertAlmostEqual(result["difference_vs_operating_cash_flow_minus_capex"], 16.0)
        self.assertAlmostEqual(result["reconciliation_difference"], 0.2)
        self.assertTrue(result["within_tolerance"])
        self.assertEqual(result["double_count_check"], "PASSED")
        self.assertTrue(result["sbc_added_back_exactly_once"])

    def test_statement_alias_does_not_shift_prior_da_into_latest_period(self):
        frame = pd.DataFrame(
            {
                "2025": [float("nan"), 21.14],
                "2024": [13.47, 13.47],
            },
            index=["Depreciation And Amortization", "Depreciation"],
        )
        self.assertEqual(
            _row(frame, "Depreciation And Amortization", "Depreciation"),
            [21.14, 13.47],
        )

    def test_cfo_fcff_contains_sbc_through_operating_cash_flow(self):
        data = fixture_data()
        without_sbc_cash_addback = fixture_data()
        without_sbc_cash_addback["latest_ocf"] -= data["sbc"]
        result = _historical_fcff_reconciliation(data)
        result_without = _historical_fcff_reconciliation(without_sbc_cash_addback)
        self.assertAlmostEqual(
            result["accounting_cfo_based_fcff"] - result_without["accounting_cfo_based_fcff"],
            data["sbc"],
        )

    def test_sbc_is_added_back_exactly_once(self):
        result = _historical_fcff_reconciliation(fixture_data())
        self.assertAlmostEqual(
            result["adjusted_nopat_based_fcff"] - result["nopat_based_fcff_before_sbc"],
            result["stock_based_compensation"],
        )
        self.assertIn("Explicit", result["other_adjustments_basis"])

    def test_accounting_fcff_models_dilution_once(self):
        report = self.build_fixture_report()
        base_dilution = next(
            item for item in report["assumptions"]["base"]
            if item["name"] == "annual_dilution"
        )
        self.assertGreater(base_dilution["value"], 0)
        self.assertTrue(report["validation"]["checks"]["sbc_dilution_double_count"]["passed"])
        self.assertGreater(
            report["scenarios"]["base"]["diluted_shares"],
            fixture_data()["shares"],
        )

    def test_owner_earnings_deducts_sbc_and_disables_dilution(self):
        data = fixture_data()
        with (
            patch("intrinsic_valuation.collect_valuation_data", return_value=data),
            patch("intrinsic_valuation._market_rates", return_value=fixture_rates()),
        ):
            report = build_valuation_report(
                "TEST", {"sbc_policy": SBC_OWNER_EARNINGS_POLICY}
            )
        reconciliation = report["historical_fcff_reconciliation"]
        self.assertAlmostEqual(reconciliation["calculated_fcff"], 146.0)
        self.assertTrue(reconciliation["sbc_deducted_exactly_once"])
        self.assertEqual(
            next(
                item["value"] for item in report["assumptions"]["base"]
                if item["name"] == "annual_dilution"
            ),
            0.0,
        )
        self.assertEqual(
            report["scenarios"]["base"]["diluted_shares"],
            fixture_data()["shares"],
        )
        self.assertTrue(report["validation"]["checks"]["sbc_dilution_double_count"]["passed"])

    def test_goog_like_sbc_mismatch_is_identified_and_reconciled(self):
        data = fixture_data()
        data.update({
            "latest_revenue": 350.0,
            "latest_operating_income": 80.0 / 0.79,
            "latest_net_income": 78.45,
            "latest_ocf": 101.88,
            "latest_capex": 30.0,
            "depreciation_amortization": 20.0,
            "working_capital_change": -5.0,
            "after_tax_interest": 2.0,
            "sbc": 24.95,
            "other_non_cash_adjustments": -16.52,
        })
        result = _historical_fcff_reconciliation(data, SBC_ACCOUNTING_POLICY)
        self.assertAlmostEqual(result["nopat_based_fcff_before_sbc"], 48.48, places=2)
        self.assertAlmostEqual(result["adjusted_nopat_based_fcff"], 73.43, places=2)
        self.assertAlmostEqual(result["cfo_based_fcff"], 73.88, places=2)
        self.assertAlmostEqual(result["reconciliation_difference"], -0.45, places=2)
        self.assertLess(result["reconciliation_difference_pct"], 0.01)
        self.assertEqual(result["likely_cause"], "Stock-based compensation treatment mismatch")
        self.assertEqual(result["status"], "PASSED")

    def test_material_fcff_difference_blocks_valuation(self):
        data = fixture_data()
        data["latest_operating_income"] = 400.0
        with patch("intrinsic_valuation.collect_valuation_data", return_value=data):
            report = build_valuation_report("TEST")
        self.assertEqual(report["validation"]["status"], "FAILED")
        self.assertEqual(report["historical_fcff_reconciliation"]["status"], "FAILED")
        self.assertFalse(report["scenarios"])

    def test_missing_fcff_bridge_input_blocks_valuation(self):
        data = fixture_data()
        data["depreciation_amortization"] = None
        with patch("intrinsic_valuation.collect_valuation_data", return_value=data):
            report = build_valuation_report("TEST")
        self.assertEqual(report["validation"]["status"], "FAILED")
        self.assertIn("D&A", report["historical_fcff_reconciliation"]["missing"])
        self.assertFalse(report["scenarios"])

    def test_partial_sec_debt_blocks_ev_to_equity_bridge(self):
        data = fixture_data()
        data["debt"] = None
        data["debt_coverage"] = "PARTIAL"
        data["debt_provenance"] = {"missing_components": ["noncurrent debt"]}
        with patch("intrinsic_valuation.collect_valuation_data", return_value=data):
            report = build_valuation_report("TEST")
        self.assertEqual(report["validation"]["status"], "FAILED")
        self.assertFalse(report["validation"]["checks"]["debt_coverage"]["passed"])
        self.assertFalse(report["scenarios"])

    def test_cyclical_parameters_normalize_growth_and_margin(self):
        data = fixture_data("CYCLICAL_COMPANY")
        data["revenue_history"] = [1400.0, 900.0, 1200.0, 800.0]
        base = _base_parameters(data, fixture_rates())
        self.assertLessEqual(base["growth"], 0.08)
        self.assertLessEqual(base["target_margin"], 0.30)
        self.assertEqual(base["exit_multiple"], 10.0)

    def test_revenue_compounds_and_margin_interpolates(self):
        result = _dcf(self.data, assumptions())
        self.assertAlmostEqual(result["forecast"][0]["revenue"], 1100.0)
        self.assertAlmostEqual(result["forecast"][0]["fcff_margin"], 0.16)
        self.assertAlmostEqual(
            result["forecast"][0]["present_value"],
            result["forecast"][0]["fcff"] / result["forecast"][0]["discount_factor"],
        )

    def test_dcf_reconciles_all_major_identities(self):
        result = _dcf(self.data, assumptions())
        self.assertAlmostEqual(
            result["enterprise_value"],
            result["pv_forecast_fcff"] + result["pv_terminal_value"],
        )
        self.assertAlmostEqual(result["equity_value"], result["enterprise_value"] + 100.0)
        self.assertAlmostEqual(result["fair_value_per_share"], result["equity_value"] / 100.0)
        self.assertAlmostEqual(
            result["terminal_value"],
            result["terminal_year_fcff"] / (0.09 - 0.025),
        )
        self.assertLess(result["pv_terminal_value"], result["terminal_value"])

    def test_dilution_changes_share_conversion(self):
        diluted = assumptions()
        next(item for item in diluted if item.name == "annual_dilution").value = 0.02
        result = _dcf(self.data, diluted)
        self.assertAlmostEqual(result["diluted_shares"], 100.0 * 1.02**5)
        self.assertAlmostEqual(result["fair_value_per_share"], result["equity_value"] / result["diluted_shares"])

    def test_wacc_must_exceed_terminal_growth(self):
        with self.assertRaisesRegex(ValueError, "WACC must exceed terminal growth"):
            _dcf(self.data, assumptions(wacc=0.025, terminal_growth=0.025))

    def test_scenarios_are_logically_ordered(self):
        scenario_items = _scenario_assumptions(fixture_data(), fixture_rates(), {})
        values = {name: _dcf(self.data, items)["fair_value_per_share"] for name, items in scenario_items.items()}
        self.assertLessEqual(values["bear"], values["base"])
        self.assertLessEqual(values["base"], values["bull"])

    def test_manual_overrides_are_traceable(self):
        scenario_items = _scenario_assumptions(
            fixture_data(),
            fixture_rates(),
            {"wacc": 0.10, "terminal_growth": 0.03},
        )
        base_wacc = next(item for item in scenario_items["base"] if item.name == "wacc")
        base_terminal = next(item for item in scenario_items["base"] if item.name == "terminal_growth")
        self.assertEqual(base_wacc.value, 0.10)
        self.assertTrue(base_wacc.overridden)
        self.assertEqual(base_wacc.source, "user_override")
        self.assertEqual(base_terminal.value, 0.03)

    def test_manual_overrides_anchor_all_scenario_spreads(self):
        scenario_items = _scenario_assumptions(
            fixture_data(), fixture_rates(),
            {"revenue_growth": 0.20, "fcf_margin": 0.25, "wacc": 0.10, "terminal_growth": 0.03},
        )
        def value(case, name):
            return next(item for item in scenario_items[case] if item.name == name)
        self.assertAlmostEqual(value("bear", "year_1_revenue_growth").value, 0.16)
        self.assertAlmostEqual(value("base", "year_1_revenue_growth").value, 0.20)
        self.assertAlmostEqual(value("bull", "year_1_revenue_growth").value, 0.24)
        self.assertAlmostEqual(value("bear", "wacc").value, 0.11)
        self.assertAlmostEqual(value("bull", "wacc").value, 0.09)
        self.assertEqual(value("bear", "wacc").source, "user_override_with_scenario_spread")
        values = {name: _dcf(self.data, items)["fair_value_per_share"] for name, items in scenario_items.items()}
        self.assertLessEqual(values["bear"], values["base"])
        self.assertLessEqual(values["base"], values["bull"])

    def test_sensitivity_uses_recalculation_and_is_monotonic(self):
        result = _sensitivity(self.data, assumptions())
        self.assertEqual(len(result["values"]), 5)
        self.assertEqual(len(result["values"][0]), 4)
        for row in result["values"]:
            valid = [value for value in row if value is not None]
            self.assertEqual(valid, sorted(valid))
        for column in range(4):
            valid = [row[column] for row in result["values"] if row[column] is not None]
            self.assertEqual(valid, sorted(valid, reverse=True))
        self.assertIn("full DCF recalculation", result["calculation"])

    def test_reverse_dcf_converges_with_residual(self):
        target = _dcf(self.data, assumptions(), forced_growth=0.20)["fair_value_per_share"]
        self.data["price"] = target
        result = _reverse_dcf(self.data, assumptions())
        self.assertTrue(result["converged"])
        self.assertEqual(result["status"], "CONVERGED")
        self.assertLessEqual(abs(result["residual_per_share"]), 0.005)
        self.assertAlmostEqual(result["required_year_1_revenue_growth"], 0.20, places=3)

    def test_reverse_dcf_reports_non_convergence(self):
        self.data["price"] = 1_000_000.0
        result = _reverse_dcf(self.data, assumptions())
        self.assertFalse(result["converged"])
        self.assertEqual(result["status"], "NO_ECONOMIC_SOLUTION")
        self.assertIn("search_bounds", result)

    def test_reverse_dcf_handles_missing_price_and_unstable_fcf(self):
        self.data["price"] = None
        self.assertEqual(_reverse_dcf(self.data, assumptions())["status"], "NO_MARKET_PRICE")
        self.data["price"] = 31.0
        self.data["latest_fcff"] = -1.0
        self.assertEqual(_reverse_dcf(self.data, assumptions())["status"], "UNSTABLE_CASH_FLOW_BASE")

    def test_period_mismatch_lowers_validation(self):
        data = fixture_data()
        data["periods"]["fcff"] = "Provider TTM / most recent"
        scenario_items = _scenario_assumptions(data, fixture_rates(), {})
        scenarios = {name: _dcf(data, items) for name, items in scenario_items.items()}
        sensitivity = _sensitivity(data, scenario_items["base"])
        reverse = _reverse_dcf(data, scenario_items["base"])
        validation = _validate(data, scenario_items, scenarios, reverse, sensitivity, fixture_rates())
        self.assertEqual(validation["status"], "PROVISIONAL")
        self.assertFalse(validation["checks"]["period_consistency"]["passed"])

    def test_specialized_framework_fallback_is_explicit(self):
        report = self.build_fixture_report("FINANCIAL_INSTITUTION")
        self.assertFalse(report["scenarios"])
        self.assertIn("Residual-income", report["fallback"]["required_specialized_framework"])
        self.assertEqual(report["validation"]["status"], "PROVISIONAL")

    def test_invalid_ticker_fallback(self):
        report = self.build_fixture_report("INSUFFICIENT_DATA", price=None)
        self.assertEqual(report["security_type"], "INSUFFICIENT_DATA")
        self.assertIn("issuer identity", report["fallback"]["missing_data"][0])

    def test_invalid_cli_flags_are_friendly_and_nonzero(self):
        for args, expected in (
            (["value", "CRWD", "--wacc", "invalid"], "Invalid value for --wacc"),
            (["value", "CRWD", "--unknown"], "Supported flags"),
            (["value", "CRWD", "--wacc", "0.03", "--terminal-growth", "0.04"], "below WACC"),
        ):
            with self.subTest(args=args):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    status = cli.run_cli(args)
                self.assertEqual(status, 2)
                self.assertIn(expected, stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_sbc_policy_cli_option_is_validated(self):
        parsed = cli.parse_valuation_options(["--sbc-policy", "owner-earnings"])
        self.assertEqual(parsed["overrides"]["sbc_policy"], "owner-earnings")
        with self.assertRaisesRegex(ValueError, "accounting-fcff or owner-earnings"):
            cli.parse_valuation_options(["--sbc-policy", "mixed"])

    def test_json_output_is_pure_and_complete(self):
        report = self.build_fixture_report()
        stdout = io.StringIO()
        with (
            patch("intrinsic_valuation.build_valuation_report", return_value=report),
            contextlib.redirect_stdout(stdout),
        ):
            run_valuation("TEST", json_output=True)
        payload = json.loads(stdout.getvalue())
        required = {
            "report_type", "company", "security_type", "company_type", "selected_method",
            "historical_base", "assumptions", "discount_rate", "scenarios", "sensitivity",
            "reverse_dcf", "cross_checks", "risks", "fair_value_drivers", "validation",
            "data_quality", "final_interpretation",
        }
        self.assertTrue(required.issubset(payload))
        self.assertNotIn("_data", payload)


if __name__ == "__main__":
    unittest.main()
