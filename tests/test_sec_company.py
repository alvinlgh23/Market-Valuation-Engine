import unittest
from unittest.mock import patch

from data_sources import sec_company as sec
from data_sources.sec_company import _reconciliation_inputs, _select_debt, _working_capital_cash_effect


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

    def test_combined_short_and_long_term_debt_concept_is_complete(self):
        result = _select_debt(facts([
            ("DebtLongtermAndShorttermCombinedAmount", 425, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 400, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 425)
        self.assertEqual(result["coverage"], "COMPLETE")

    def test_noncurrent_with_verified_zero_current_maturities_is_complete(self):
        result = _select_debt(facts([
            ("LongTermDebt", 500, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 500, "2025-12-31", "USD", 2025),
            ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths", 0, "2025-12-31", "USD", 2025),
        ]))
        self.assertEqual(result["value"], 500)
        self.assertEqual(result["coverage"], "COMPLETE")
        self.assertEqual(result["methodology"], "noncurrent_with_verified_zero_current_maturities")

    def test_short_term_borrowings_block_zero_current_maturity_shortcut(self):
        result = _select_debt(facts([
            ("LongTermDebt", 500, "2025-12-31", "USD", 2025),
            ("LongTermDebtNoncurrent", 500, "2025-12-31", "USD", 2025),
            ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths", 0, "2025-12-31", "USD", 2025),
            ("ShortTermBorrowings", 50, "2025-12-31", "USD", 2025),
        ]))
        self.assertIsNone(result["value"])
        self.assertEqual(result["coverage"], "PARTIAL")


def _flow(val, end="2025-12-31", start="2025-01-01", fy=2025, form="10-K"):
    return {"val": val, "start": start, "end": end, "filed": f"{fy + 1}-02-15", "fy": fy, "fp": "FY", "form": form}


def _inst(val, end="2025-12-31", fy=2025, form="10-K"):
    return {"val": val, "end": end, "filed": f"{fy + 1}-02-15", "fy": fy, "fp": "FY", "form": form}


class SecReconciliationInputTests(unittest.TestCase):
    def test_split_depreciation_and_amortization_sum_without_double_counting_combined(self):
        split_facts = {
            "facts": {
                "us-gaap": {
                    "Depreciation": {"units": {"USD": [_flow(300)]}},
                    "AmortizationOfIntangibleAssets": {"units": {"USD": [_flow(70)]}},
                }
            }
        }
        res = _reconciliation_inputs(
            split_facts, taxonomy="us-gaap", unit="USD", forms=("10-K",), period_end="2025-12-31", latest_debt=100.0
        )
        self.assertEqual(res["depreciation_amortization"], 370.0)

        both_facts = {
            "facts": {
                "us-gaap": {
                    "DepreciationAndAmortization": {"units": {"USD": [_flow(370)]}},
                    "Depreciation": {"units": {"USD": [_flow(300)]}},
                    "AmortizationOfIntangibleAssets": {"units": {"USD": [_flow(70)]}},
                }
            }
        }
        res2 = _reconciliation_inputs(
            both_facts, taxonomy="us-gaap", unit="USD", forms=("10-K",), period_end="2025-12-31", latest_debt=100.0
        )
        self.assertEqual(res2["depreciation_amortization"], 370.0)

    def test_working_capital_signs_and_overlap_guards(self):
        wc_facts = {
            "facts": {
                "us-gaap": {
                    "IncreaseDecreaseInAccountsReceivable": {"units": {"USD": [_flow(50)]}},
                    "IncreaseDecreaseInInventories": {"units": {"USD": [_flow(20)]}},
                    "IncreaseDecreaseInAccountsPayableAndAccruedLiabilities": {"units": {"USD": [_flow(35)]}},
                    "IncreaseDecreaseInAccountsPayable": {"units": {"USD": [_flow(15)]}},
                    "IncreaseDecreaseInDeferredIncomeTaxes": {"units": {"USD": [_flow(-10)]}},
                    "IncreaseDecreaseInCashAndCashEquivalents": {"units": {"USD": [_flow(999)]}},
                }
            }
        }
        value, concepts = _working_capital_cash_effect(
            wc_facts, "2025-12-31", "USD", taxonomy="us-gaap", forms=("10-K",)
        )
        # -50 (AR up) - 20 (Inv up) + 35 (AP & accrued up; standalone AP skipped as child) = -35
        self.assertEqual(value, -35.0)
        self.assertNotIn("IncreaseDecreaseInAccountsPayable", concepts)
        self.assertNotIn("IncreaseDecreaseInDeferredIncomeTaxes", concepts)

    def test_sec_company_data_passes_fcff_reconciliation_and_produces_dcf(self):
        from intrinsic_valuation import build_valuation_report

        # Coherent accounting identity:
        # Revenue=1000, OpInc=250, Interest=10, Pretax=240, Tax=48 (tax_rate=0.20) => NOPAT=200, NetIncome=192
        # D&A=40, SBC=20, DefTax=5, OtherNoncashIncomeExpense=+3 (subtracted -> -3), WC cash effect=-15 (AR +25, AP +10)
        # OCF = NetIncome(192) + D&A(40) + SBC(20) + DefTax(5) - OtherNoncash(3) + WC(-15) = 239? Wait:
        # NOPAT(200) + D&A(40) - CapEx(30) - (-WC=-15 -> +15 => -15) + OtherAdj(5 - 3 = 2) + SBC(20) = 217
        # CFO FCFF = OCF(239) - CapEx(30) + AfterTaxInterest(10 * 0.8 = 8) = 217! Exact reconciliation = 0 diff!
        synthetic_facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {"units": {"USD": [
                        _flow(1000, "2025-12-31", "2025-01-01", 2025),
                        _flow(900, "2024-12-31", "2024-01-01", 2024),
                    ]}},
                    "GrossProfit": {"units": {"USD": [_flow(600)]}},
                    "OperatingIncomeLoss": {"units": {"USD": [
                        _flow(250, "2025-12-31", "2025-01-01", 2025),
                        _flow(220, "2024-12-31", "2024-01-01", 2024),
                    ]}},
                    "NetIncomeLoss": {"units": {"USD": [_flow(192)]}},
                    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": {
                        "units": {"USD": [_flow(240)]}
                    },
                    "IncomeTaxExpenseBenefit": {"units": {"USD": [_flow(48)]}},
                    "InterestExpense": {"units": {"USD": [_flow(10)]}},
                    "DepreciationDepletionAndAmortization": {"units": {"USD": [_flow(40)]}},
                    "ShareBasedCompensation": {"units": {"USD": [_flow(20)]}},
                    "DeferredIncomeTaxExpenseBenefit": {"units": {"USD": [_flow(5)]}},
                    "OtherNoncashIncomeExpense": {"units": {"USD": [_flow(3)]}},
                    "IncreaseDecreaseInAccountsReceivable": {"units": {"USD": [_flow(25)]}},
                    "IncreaseDecreaseInAccountsPayable": {"units": {"USD": [_flow(10)]}},
                    "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [_flow(239)]}},
                    "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [_flow(30)]}},
                    "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_inst(120)]}},
                    "LongTermDebtAndFinanceLeaseObligations": {"units": {"USD": [_inst(200)]}},
                    "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [_flow(100)]}},
                }
            }
        }
        with (
            patch.object(sec, "_company_record", return_value={"cik_str": 999999, "title": "Synthetic Corp"}),
            patch.object(
                sec,
                "_fetch",
                side_effect=lambda url, path, max_age_days=7: (
                    synthetic_facts if "companyfacts" in url else {"name": "Synthetic Corp", "sicDescription": "Industrial Machinery", "exchanges": ["NYSE"]}
                ),
            ),
            patch("intrinsic_valuation._risk_free", return_value=(0.04, "fixture")),
        ):
            data = sec.collect_sec_company_data("SYNT")
            data["price"] = 25.0
            data["market_cap"] = 2500.0
            data["beta"] = 1.1
            report = build_valuation_report("SYNT", data=data)
        self.assertEqual(report["historical_fcff_reconciliation"]["status"], "PASSED")
        self.assertAlmostEqual(report["historical_fcff_reconciliation"]["reconciliation_difference"], 0.0, places=6)
        self.assertIn(report["data_quality"]["status"], {"GOOD", "LIMITED"})
        self.assertGreater(report["fair_value"]["fair_value"]["base"], 0)
        self.assertTrue(report["validation"]["checks"]["period_consistency"]["passed"])


if __name__ == "__main__":
    unittest.main()
