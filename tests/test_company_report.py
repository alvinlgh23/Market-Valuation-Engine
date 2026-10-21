import unittest

import pandas as pd

from company_report import (
    _comparison_from_values,
    chase_risk,
    ev_ebitda_display,
    financial_comparison,
    margin_comparison,
    price_vs_fundamental_decomposition,
    validate_company_metrics,
)


class CompanyReportAuditTests(unittest.TestCase):
    def test_ttm_growth_matches_displayed_values(self):
        comparison = _comparison_from_values([40, 30, 20, 10, 20, 20, 20, 20], [])
        self.assertEqual(comparison["basis"], "TTM")
        self.assertEqual(comparison["current"], 100)
        self.assertEqual(comparison["prior"], 80)
        self.assertAlmostEqual(comparison["growth"], 0.25)

    def test_incomplete_quarterly_history_uses_fully_aligned_annual_comparison(self):
        comparison = _comparison_from_values([40, 30, 20, 10, 5], [100, 80, 70])
        self.assertEqual(comparison["basis"], "Annual")
        self.assertEqual(comparison["current"], 100)
        self.assertEqual(comparison["prior"], 80)
        self.assertAlmostEqual(comparison["growth"], 0.25)

    def test_revenue_acceleration_is_percentage_point_difference(self):
        comparison = _comparison_from_values([], [121.7, 100, 84.6])
        expected_previous = 100 / 84.6 - 1
        self.assertAlmostEqual(comparison["acceleration"], 0.217 - expected_previous, places=3)

    def test_margin_change_is_current_minus_prior(self):
        quarterly = pd.DataFrame(
            [[25, 25, 25, 25, 20, 20, 20, 20], [-4, -4, -4, -4, -1, -1, -1, -1]],
            index=["Total Revenue", "Operating Income"],
        )
        margin = margin_comparison(quarterly, None)
        self.assertAlmostEqual(margin["current"], -0.16)
        self.assertAlmostEqual(margin["prior"], -0.05)
        self.assertAlmostEqual(margin["change"], -0.11)

    def test_decomposition_cannot_confirm_weak_fundamentals(self):
        result = price_vs_fundamental_decomposition(-0.05, -0.02, -0.30, 0.50, 0.30)
        self.assertEqual(result["label"], "Price outruns fundamentals")

    def test_forward_pe_change_without_history_is_warning(self):
        revenue = {"current": 120, "prior": 100, "growth": 0.20}
        margin = {"current": 0.10, "prior": 0.08, "change": 0.02}
        fcf = {"current": 12, "prior": 10, "growth": 0.20}
        decomposition = {"label": "Price confirms fundamentals", "fundamental_direction": "Improving"}
        warnings = validate_company_metrics(revenue, margin, fcf, 0.50, False, decomposition)
        self.assertIn("Forward PE change exists without verified historical forward PE", warnings)

    def test_absurd_ev_ebitda_is_rejected(self):
        display, reason = ev_ebitda_display(3150, 1_000_000, 3_150_000_000)
        self.assertEqual(display, "Not economically meaningful")
        self.assertIn("near zero", reason)

    def test_chase_risk_is_explicit(self):
        label, evidence = chase_risk(0.20, 0.65, 0.30, 0.35, 100, 20)
        self.assertEqual(label, "Elevated")
        self.assertTrue(evidence)


if __name__ == "__main__":
    unittest.main()
