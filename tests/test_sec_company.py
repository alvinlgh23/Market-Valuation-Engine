import unittest

from data_sources.sec_company import _select_debt


def facts(rows):
    payload = {"facts": {"us-gaap": {}}}
    for concept, value, end, unit, fy in rows:
        payload["facts"]["us-gaap"][concept] = {
            "units": {
                unit: [{
                    "val": value,
                    "end": end,
                    "filed": f"{fy + 1}-02-15",
                    "fy": fy,
                    "fp": "FY",
                    "form": "10-K",
                }]
            }
        }
    return payload


class SecDebtSelectionTests(unittest.TestCase):
    def test_current_plus_noncurrent_are_aggregated_once(self):
        result = _select_debt(facts([
            ("LongTermDebtCurrent", 10, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 90, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 100)
        self.assertEqual(result["coverage"], "COMPLETE")
        self.assertEqual(result["methodology"], "aligned_current_plus_noncurrent")

    def test_consolidated_total_wins_over_components_without_double_counting(self):
        result = _select_debt(facts([
            ("LongTermDebtAndFinanceLeaseObligations", 100, "2025-12-31", "USD", 2025),
            ("LongTermDebtCurrent", 10, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 90, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 100)
        self.assertEqual(result["selected_concepts"], ["LongTermDebtAndFinanceLeaseObligations"])

    def test_missing_noncurrent_is_partial_not_total_debt(self):
        result = _select_debt(facts([
            ("LongTermDebtCurrent", 10, "2025-12-31", "USD", 2025),
        ]))
        self.assertIsNone(result["value"])
        self.assertEqual(result["coverage"], "PARTIAL")
        self.assertIn("noncurrent debt", result["missing_components"])

    def test_period_mismatch_is_partial(self):
        result = _select_debt(facts([
            ("LongTermDebtCurrent", 10, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 90, "2024-12-31", "USD", 2024),
        ]))
        self.assertIsNone(result["value"])
        self.assertEqual(result["coverage"], "PARTIAL")
        self.assertIn("aligned reporting period", result["missing_components"])

    def test_newer_aligned_components_win_over_stale_total(self):
        result = _select_debt(facts([
            ("LongTermDebtAndFinanceLeaseObligations", 80, "2024-12-31", "USD", 2024),
            ("LongTermDebtCurrent", 10, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 90, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 100)
        self.assertEqual(result["methodology"], "aligned_current_plus_noncurrent")

    def test_finance_lease_total_is_complete_and_zero_debt_is_preserved(self):
        result = _select_debt(facts([
            ("LongTermDebtAndFinanceLeaseObligations", 0, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 0)
        self.assertEqual(result["coverage"], "COMPLETE")

    def test_missing_values_are_insufficient(self):
        result = _select_debt({"facts": {"us-gaap": {}}})
        self.assertIsNone(result["value"])
        self.assertEqual(result["coverage"], "INSUFFICIENT_DATA")

    def test_wrong_units_do_not_mix_into_usd_debt(self):
        result = _select_debt(facts([
            ("LongTermDebtCurrent", 10, "2025-12-31", "EUR", 2025),
            ("LongTermDebtNoncurrent", 90, "2025-12-31", "EUR", 2025),
        ]))
        self.assertEqual(result["coverage"], "INSUFFICIENT_DATA")


if __name__ == "__main__":
    unittest.main()
