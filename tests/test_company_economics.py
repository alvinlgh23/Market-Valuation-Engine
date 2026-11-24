import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Valuation_model as cli
from company_economics import (
    BusinessModelClassifier,
    CompanyEconomicsValidation,
    CompanySnapshot,
    Confidence,
    ConstraintDirection,
    ConstraintType,
    EvidenceItem,
    EvidenceTier,
    EvidenceType,
    MarketExpectationState,
    QualitativeCompanyEconomicsExtractor,
    SourceNature,
    ValuationReviewState,
    build_company_economics,
    cache_structural_profile,
)
from company_economics_fixtures import BENCHMARK_SNAPSHOTS, benchmark_snapshot
from company_economics_overrides import COMPANY_ECONOMICS_OVERRIDES
from company_economics_registry import ARCHETYPE_REGISTRY, CONSTRAINT_REGISTRY, Archetype


EXPECTED = {
    "PLTR": (Archetype.ENTERPRISE_AI_SOFTWARE, ConstraintType.DEPLOYMENT_CAPACITY),
    "NVDA": (Archetype.FABLESS_SEMICONDUCTOR, ConstraintType.ADVANCED_PACKAGING),
    "TSM": (Archetype.SEMICONDUCTOR_FOUNDRY, ConstraintType.FAB_CAPACITY),
    "MSFT": (Archetype.HYPERSCALER_CLOUD_PLATFORM, ConstraintType.COMPUTE_CAPACITY),
    "JPM": (Archetype.BANK, ConstraintType.DEPOSITS),
    "COST": (Archetype.RETAIL_PHYSICAL_NETWORK, ConstraintType.STORE_EXPANSION),
    "XOM": (Archetype.COMMODITY_PRODUCER, ConstraintType.PRODUCTION_CAPACITY),
    "LLY": (Archetype.PHARMA_BIOTECH, ConstraintType.MANUFACTURING_CAPACITY),
    "V": (Archetype.PAYMENT_NETWORK, ConstraintType.CUSTOMER_ADOPTION),
    "UBER": (Archetype.MARKETPLACE_PLATFORM, ConstraintType.CUSTOMER_ADOPTION),
    "AMD": (Archetype.FABLESS_SEMICONDUCTOR, ConstraintType.ADVANCED_PACKAGING),
    "CRM": (Archetype.TRADITIONAL_SAAS, ConstraintType.CHURN),
    "META": (Archetype.CONSUMER_PLATFORM, ConstraintType.CUSTOMER_ADOPTION),
    "WMT": (Archetype.RETAIL_PHYSICAL_NETWORK, ConstraintType.STORE_EXPANSION),
    "BAC": (Archetype.BANK, ConstraintType.DEPOSITS),
    "CAT": (Archetype.INDUSTRIAL, ConstraintType.BACKLOG_EXECUTION),
}


def valuation_fixture(growth=.28, margin=.30, implied_growth=.25):
    return {
        "assumptions": {"base": [
            {"name": "year_1_revenue_growth", "value": growth},
            {"name": "year_5_fcff_margin", "value": margin},
        ]},
        "reverse_dcf": {"converged": True, "required_5y_revenue_cagr": implied_growth, "required_year_5_fcff_margin": margin},
    }


class CompanyEconomicsTests(unittest.TestCase):
    def test_all_required_archetypes_exist(self):
        self.assertEqual(len(ARCHETYPE_REGISTRY), 16)
        self.assertIn(Archetype.GENERIC_OPERATING_COMPANY, ARCHETYPE_REGISTRY)

    def test_constraint_registry_covers_enum(self):
        self.assertEqual(set(CONSTRAINT_REGISTRY), set(ConstraintType))

    def test_benchmark_archetype_and_constraint_routing(self):
        for ticker, (archetype, constraint) in EXPECTED.items():
            with self.subTest(ticker=ticker):
                profile = build_company_economics(benchmark_snapshot(ticker))
                self.assertEqual(profile.classification.primary_archetype, archetype)
                self.assertEqual(profile.constraints.primary_constraint.constraint, ConstraintType.UNKNOWN)
                self.assertIn(constraint, profile.constraints.candidate_constraints)

    def test_hybrid_classification(self):
        result = build_company_economics(benchmark_snapshot("MSFT"))
        self.assertIn(Archetype.TRADITIONAL_SAAS, result.classification.secondary_archetypes)

    def test_fallback_classification(self):
        snapshot = CompanySnapshot("TEST", "Unknown Co", "2026-01-01", metrics={"revenue": 100})
        classification = BusinessModelClassifier().classify(snapshot)
        self.assertEqual(classification.primary_archetype, Archetype.GENERIC_OPERATING_COMPANY)
        self.assertEqual(classification.classification_confidence, Confidence.LOW)

    def test_consumer_sector_alone_does_not_route_to_retail(self):
        """Checklist 11.1: Tesla was routed to warehouse retail on the Consumer Cyclical sector alone."""
        restaurant = CompanySnapshot("TEST", "Burger Co", "2026-01-01", sector="Consumer Cyclical", industry="Restaurants", business_description="operates quick-service restaurants")
        self.assertEqual(BusinessModelClassifier().classify(restaurant).primary_archetype, Archetype.GENERIC_OPERATING_COMPANY)
        carmaker = CompanySnapshot("TEST", "Car Co", "2026-01-01", sector="Consumer Cyclical", industry="Auto Manufacturers", business_description="designs, manufactures and sells electric vehicles")
        self.assertEqual(BusinessModelClassifier().classify(carmaker).primary_archetype, Archetype.INDUSTRIAL)
        retailer = CompanySnapshot("TEST", "Shop Co", "2026-01-01", sector="Consumer Defensive", industry="Discount Stores", business_description="operates retail stores")
        self.assertEqual(BusinessModelClassifier().classify(retailer).primary_archetype, Archetype.RETAIL_PHYSICAL_NETWORK)

    def test_declared_preference_wins_a_tie(self):
        """Checklist 11.7: with Yahoo's 'Software - Infrastructure' industry, MSFT tied enterprise AI with its hyperscaler preference."""
        snapshot = CompanySnapshot("MSFT", "Microsoft", "2026-01-01", sector="Technology", industry="Software - Infrastructure",
                                   business_description="develops software and services", metrics={"gross_margin": 0.69})
        self.assertEqual(BusinessModelClassifier().classify(snapshot).primary_archetype, Archetype.HYPERSCALER_CLOUD_PLATFORM)

    def test_consumer_lender_routes_to_bank_not_payment_network(self):
        """Checklist 11.1: a 'Credit Services' lender with deposit accounts is a bank; card networks keep their route."""
        lender = CompanySnapshot("TEST", "Lend Co", "2026-01-01", sector="Financial Services", industry="Credit Services",
                                 business_description="offers personal loans, student loans, home loans and checking and savings accounts", metrics={"gross_margin": 0.8})
        self.assertEqual(BusinessModelClassifier().classify(lender).primary_archetype, Archetype.BANK)
        network = CompanySnapshot("TEST", "Card Co", "2026-01-01", sector="Financial Services", industry="Credit Services",
                                  business_description="a payments technology company operating a payment network", metrics={"gross_margin": 0.8})
        self.assertEqual(BusinessModelClassifier().classify(network).primary_archetype, Archetype.PAYMENT_NETWORK)

    def test_growth_equation_and_driver_evidence(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        self.assertIn("Customers", profile.growth_architecture.primary_growth_equation)
        self.assertTrue(profile.growth_architecture.primary_driver.evidence_ids)

    def test_unknown_constraint_when_no_evidence(self):
        snapshot = CompanySnapshot("TEST", "Unknown Co", "2026-01-01", business_description="operating company")
        profile = build_company_economics(snapshot)
        self.assertEqual(profile.constraints.primary_constraint.constraint, ConstraintType.UNKNOWN)
        self.assertEqual(profile.constraints.primary_constraint.confidence, Confidence.INSUFFICIENT)

    def test_evidence_types_and_sources(self):
        profile = build_company_economics(benchmark_snapshot("NVDA"))
        self.assertTrue(any(item.type == EvidenceType.FACT for item in profile.evidence_trace))
        self.assertTrue(any(item.type == EvidenceType.PROXY for item in profile.evidence_trace))
        self.assertTrue(any(item.type == EvidenceType.INFERENCE for item in profile.evidence_trace))
        self.assertTrue(all(item.source for item in profile.evidence_trace if item.type == EvidenceType.FACT))

    def test_direct_proxy_distinction(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        proxies = [item for item in profile.evidence_trace if item.type == EvidenceType.PROXY]
        self.assertTrue(all(item.tier == EvidenceTier.INDIRECT for item in proxies))
        self.assertTrue(all(item.source_nature in {SourceNature.CALCULATED, SourceNature.DERIVED_PROXY} for item in proxies))
        revenue_per_employee = next(item for item in proxies if item.metric == "revenue_per_employee")
        self.assertEqual(revenue_per_employee.source_nature, SourceNature.CALCULATED)

    def test_inferences_reference_existing_evidence(self):
        profile = build_company_economics(benchmark_snapshot("TSM"))
        ids = {item.id for item in profile.evidence_trace}
        for item in profile.evidence_trace:
            if item.type == EvidenceType.INFERENCE:
                self.assertTrue(item.supporting_evidence_ids)
                self.assertLessEqual(set(item.supporting_evidence_ids), ids)

    def test_data_gaps_are_structured(self):
        profile = build_company_economics(benchmark_snapshot("MSFT"))
        self.assertTrue(profile.data_gaps)
        self.assertTrue(all(gap.why_it_matters and gap.confidence_impact for gap in profile.data_gaps))

    def test_scaling_metrics_are_archetype_relevant(self):
        profile = build_company_economics(benchmark_snapshot("COST"))
        names = {item.name for item in profile.scaling_economics.metrics}
        self.assertIn("inventory_growth_minus_revenue_growth", names)
        self.assertNotIn("revenue_per_assets", names)

    def test_incremental_margin_math(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        metric = next(item for item in profile.scaling_economics.metrics if item.name == "incremental_operating_margin")
        self.assertAlmostEqual(metric.value, (950 - 520) / (3800 - 2900))

    def test_negative_revenue_delta_is_safe(self):
        snapshot = benchmark_snapshot("PLTR")
        snapshot.histories["revenue"] = [90, 100]
        profile = build_company_economics(snapshot)
        metric = next(item for item in profile.scaling_economics.metrics if item.name == "incremental_operating_margin")
        self.assertIsNone(metric.value)

    def test_constraint_direction_and_contradiction(self):
        snapshot = benchmark_snapshot("PLTR")
        snapshot.operational_metrics["deployment_capacity_growth"] = -.10
        profile = build_company_economics(snapshot)
        self.assertEqual(profile.constraints.primary_constraint.direction, ConstraintDirection.UNKNOWN)
        self.assertEqual(profile.constraints.primary_constraint.direction_status, "DIRECTION_UNKNOWN")

    def test_confidence_is_rule_based(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        self.assertEqual(profile.constraints.primary_constraint.confidence, Confidence.INSUFFICIENT)
        empty = build_company_economics(CompanySnapshot("T", "Test", "2026-01-01"))
        self.assertEqual(empty.constraints.primary_constraint.confidence, Confidence.INSUFFICIENT)

    def test_falsification_is_mechanism_specific(self):
        profile = build_company_economics(benchmark_snapshot("NVDA"))
        conditions = " ".join(item.condition.lower() for item in profile.falsification_conditions)
        self.assertIn("inventory", conditions)
        self.assertNotIn("competition may increase", conditions)

    def test_financial_translation_does_not_change_snapshot(self):
        snapshot = benchmark_snapshot("PLTR")
        before = dict(snapshot.metrics)
        profile = build_company_economics(snapshot)
        self.assertEqual(snapshot.metrics, before)
        self.assertFalse(profile.valuation_assumption_review.mutates_dcf_inputs)

    def test_valuation_assumption_review(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"), valuation_fixture(.30, .30))
        reviews = {item.assumption: item for item in profile.valuation_assumption_review.reviews}
        self.assertEqual(reviews["revenue_growth"].state, ValuationReviewState.INSUFFICIENT_EVIDENCE)

    def test_market_expectations_comparison(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"), valuation_fixture(implied_growth=.45))
        self.assertEqual(profile.market_expectations_comparison.state, MarketExpectationState.INSUFFICIENT_EVIDENCE)

    def test_json_schema_and_serialization(self):
        payload = build_company_economics(benchmark_snapshot("V")).to_dict()
        json.dumps(payload)
        economics = payload["company_economics"]
        expected = {"company", "classification", "core_economic_question", "growth_architecture", "constraints", "scaling_economics", "growth_sustainability", "falsification_conditions", "financial_translation", "valuation_assumption_review", "market_expectations_comparison", "data_gaps", "evidence_trace", "validation"}
        self.assertLessEqual(expected, set(economics))
        self.assertEqual(economics["company_economics_schema_version"], "1.1")

    def test_economic_graph_integrity(self):
        profile = build_company_economics(benchmark_snapshot("UBER"))
        node_ids = {item["id"] for item in profile.economic_graph["nodes"]}
        self.assertTrue(all(edge["from"] in node_ids and edge["to"] in node_ids for edge in profile.economic_graph["edges"]))

    def test_cache_excludes_live_market_price(self):
        profile = build_company_economics(benchmark_snapshot("XOM"))
        with tempfile.TemporaryDirectory() as directory:
            path = cache_structural_profile(profile, directory)
            payload = json.loads(Path(path).read_text())
            self.assertTrue(payload["cache_metadata"]["excludes_live_market_price"])
            self.assertNotIn("market_price", payload["company_economics"]["company"])

    def test_validation_fails_orphan_inference(self):
        profile = build_company_economics(benchmark_snapshot("PLTR"))
        profile.evidence_trace.append(EvidenceItem("E999", EvidenceType.INFERENCE, EvidenceTier.INDIRECT, "bad", "orphan", source_nature=SourceNature.INFERRED))
        result = CompanyEconomicsValidation().validate(profile)
        self.assertEqual(result.status, "FAILED")
        self.assertFalse(result.checks["inferences_cite_evidence"])

    def test_overrides_are_declarative(self):
        self.assertLessEqual(set(COMPANY_ECONOMICS_OVERRIDES), set(BENCHMARK_SNAPSHOTS))
        self.assertTrue(all(not callable(value) for override in COMPANY_ECONOMICS_OVERRIDES.values() for value in override.values()))

    def test_qualitative_provider_is_explicit_noop(self):
        provider = QualitativeCompanyEconomicsExtractor()
        self.assertEqual(provider.collect(benchmark_snapshot("PLTR")), [])
        self.assertEqual(provider.extract()["status"], "UNAVAILABLE")

    def test_cli_alias_json_fixture(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = cli.run_cli(["company-economics", "V", "--fixture", "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue())["company_economics"]["company"]["ticker"], "V")

    def test_cli_company_includes_economics(self):
        resolved = {"ticker": "PLTR", "requested_ticker": "PLTR", "name": "Palantir", "as_of": "2026-01-01", "info": {"sector": "Technology", "industry": "Software - Infrastructure", "longBusinessSummary": "enterprise artificial intelligence platform", "totalRevenue": 100, "revenueGrowth": .2}, "income": None, "cashflow": None, "provider": "fixture", "history": None}
        integrity = {"security_type": "GROWTH_OPERATING_COMPANY"}
        stdout = io.StringIO()
        with patch.object(cli, "resolve_security", return_value=resolved), patch.object(cli, "validate_security_data", return_value=integrity), patch.object(cli, "should_use_standard_company_framework", return_value=False), patch.object(cli, "is_pre_profit_template", return_value=False), patch.object(cli, "print_security_resolution_report"), contextlib.redirect_stdout(stdout):
            cli.print_company_analysis("PLTR")
        self.assertIn("COMPANY ECONOMICS", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
