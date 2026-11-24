import contextlib
import io
import json
import unittest
from copy import deepcopy

import Valuation_model as cli
from company_economics import CompanySnapshot, DataGap, build_company_economics
from company_economics_fixtures import benchmark_snapshot, benchmark_valuation_report
from company_economics_report import render_company_economics_report


class CompanyEconomicsReportTests(unittest.TestCase):
    def render(self, ticker):
        return render_company_economics_report(
            build_company_economics(benchmark_snapshot(ticker), benchmark_valuation_report(ticker))
        )

    def test_all_fifteen_sections_are_present_in_order(self):
        report = self.render("PLTR")
        titles = [
            "BUSINESS MODEL ARCHITECTURE", "GROWTH ENGINE", "PRIMARY SCALING CONSTRAINT",
            "CONSTRAINT EVIDENCE", "IS THE BOTTLENECK TIGHTENING OR EASING?",
            "SECONDARY CONSTRAINTS", "SCALING ECONOMICS", "GROWTH SUSTAINABILITY",
            "WHAT WOULD BREAK THE GROWTH THESIS?", "FINANCIAL TRANSLATION",
            "VALUATION CONNECTION", "MARKET EXPECTATIONS VS COMPANY ECONOMICS", "DATA GAPS",
            "FINAL COMPANY ECONOMIC INTERPRETATION", "EVIDENCE TRACE",
        ]
        offsets = [report.index(f"{number}. {title}") for number, title in enumerate(titles, 1)]
        self.assertEqual(offsets, sorted(offsets))

    def test_human_archetype_names_and_no_raw_enums(self):
        report = self.render("PLTR")
        self.assertIn("Primary Archetype: Enterprise AI Platform", report)
        self.assertIn("Secondary Archetype: Usage-Based Enterprise Software", report)
        self.assertNotIn("ENTERPRISE_AI_SOFTWARE", report)
        self.assertNotIn("DEPLOYMENT_CAPACITY", report)
        self.assertNotIn("incremental_operating_margin", report)

    def test_direct_and_indirect_constraint_evidence_are_separate(self):
        report = self.render("PLTR")
        section = report.split("4. CONSTRAINT EVIDENCE", 1)[1].split("5. IS THE BOTTLENECK", 1)[0]
        self.assertIn("Direct Evidence:", section)
        self.assertIn("Indirect Evidence:", section)
        self.assertNotIn("Deployment Capacity Growth", section)
        self.assertIn("not directly verified", section)

    def test_data_gaps_are_not_tightening_evidence(self):
        report = self.render("PLTR")
        section = report.split("Evidence of Tightening:\n", 1)[1].split("\n\nEvidence Limitations:", 1)[0]
        limitations = report.split("Evidence Limitations:\n", 1)[1].split("\n\nConclusion:", 1)[0]
        self.assertNotIn("Unavailable", section)
        self.assertIn("bottleneck evidence is unavailable", limitations)

    def test_single_period_productivity_does_not_claim_improvement(self):
        snapshot = CompanySnapshot(
            "PLTR", "Palantir Technologies", "2026-01-01",
            business_description="enterprise artificial intelligence platform",
            metrics={"revenue": 1000.0, "revenue_growth": .20, "employees": 1000},
            histories={"revenue": [1000.0]},
        )
        report = render_company_economics_report(build_company_economics(snapshot))
        productivity = report.split("Revenue / Employee:", 1)[1].split("\n\n", 3)
        self.assertIn("Direction:\nUnavailable", "\n\n".join(productivity))
        self.assertNotIn("Revenue productivity is improving", report)

    def test_duplicate_data_gaps_are_removed_in_report(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        duplicate = DataGap("deployment_time", None, "DEPLOYMENT_CAPACITY", "Needed.", "Confidence reduced.")
        profile.data_gaps.extend([duplicate, deepcopy(duplicate)])
        section = render_company_economics_report(profile).split("13. DATA GAPS", 1)[1].split("14. FINAL", 1)[0]
        self.assertEqual(section.count("Deployment Time unavailable"), 1)

    def test_overall_confidence_is_not_classification_confidence(self):
        report = self.render("PLTR")
        self.assertIn("Analysis Confidence: Insufficient", report)
        self.assertIn("Classification Confidence: High", report)

    def test_raw_evidence_ids_remain_traceable_for_humans(self):
        report = self.render("PLTR")
        self.assertIn("E1 — Fact / Reported", report)
        self.assertIn("Used In:", report)
        self.assertIn("Reporting Period:", report)

    def test_valuation_review_is_read_only(self):
        valuation = benchmark_valuation_report("PLTR")
        before = deepcopy(valuation)
        profile = build_company_economics(benchmark_snapshot("PLTR"), valuation)
        render_company_economics_report(profile, valuation)
        self.assertEqual(valuation, before)
        self.assertFalse(profile.valuation_assumption_review.mutates_dcf_inputs)

    def test_json_cli_remains_pure_json(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = cli.run_cli(["company-economics", "PLTR", "--fixture", "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["company_economics"]["company_economics_schema_version"], "1.1")
        self.assertNotIn("COMPANY ECONOMICS INTELLIGENCE REPORT", stdout.getvalue())

    def test_pltr_benchmark_structure(self):
        report = self.render("PLTR")
        self.assertIn("Customer Acquisition\n        ↓\nInitial Deployment", report)
        self.assertIn("More Engineering / Deployment Resources", report)
        self.assertIn("No numerical sustainability score is assigned.", report)

    def test_nvda_uses_semiconductor_language(self):
        report = self.render("NVDA")
        self.assertIn("Primary Archetype: Fabless Semiconductor", report)
        self.assertIn("Foundry / Packaging / Memory Capacity", report)
        self.assertIn("Advanced Packaging / Supply Capacity", report)
        self.assertNotIn("Initial Deployment", report)

    def test_jpm_uses_bank_language(self):
        report = self.render("JPM")
        self.assertIn("Deposits / Funding", report)
        self.assertIn("Earning Assets × Net Interest Spread", report)
        self.assertIn("Structural candidate: Deposit Funding", report)

    def test_cost_uses_physical_network_language(self):
        report = self.render("COST")
        self.assertIn("Warehouse Expansion", report)
        self.assertIn("Membership Economics", report)
        self.assertIn("Structural candidate: Productive Warehouse Expansion", report)

    def test_proxy_only_direction_is_calibrated(self):
        snapshot = benchmark_snapshot("PLTR")
        snapshot.operational_metrics = {}
        profile = build_company_economics(snapshot)
        report = render_company_economics_report(profile)
        self.assertIn("Evidence Basis:\nProxy-based", report)
        self.assertRegex(report, r"Constraint Direction:\n(?:Possibly .* / Unconfirmed|No Direction Confirmed|Unknown)")
        self.assertIn("Direct operating evidence is insufficient", report)


if __name__ == "__main__":
    unittest.main()
