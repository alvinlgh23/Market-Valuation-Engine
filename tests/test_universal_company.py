import json
import tempfile
import unittest
from pathlib import Path

from company_economics import BusinessModelClassifier, CompanySnapshot, ConstraintType
from company_economics_fixtures import BENCHMARK_SNAPSHOTS, benchmark_snapshot
from company_economics_overrides import COMPANY_ECONOMICS_OVERRIDES
from company_economics_registry import Archetype
from company_research import (
    CompanyProfileCache,
    ResearchState,
    SecurityResolver,
    SecurityType,
    UniversalCompanyResearchEngine,
)


def provider_data(ticker="AMD", quote_type="EQUITY", security_type="MATURE_OPERATING_COMPANY"):
    return {
        "ticker": ticker,
        "company": "Advanced Micro Devices" if ticker == "AMD" else ticker,
        "security_type": security_type,
        "info": {
            "quoteType": quote_type,
            "longName": "Advanced Micro Devices" if ticker == "AMD" else ticker,
            "exchange": "NMS",
            "currency": "USD",
            "country": "United States",
            "sector": "Technology",
            "industry": "Semiconductors",
            "longBusinessSummary": "Designs and develops semiconductor microprocessors and graphics processors using external manufacturing partners.",
            "grossMargins": .53,
            "operatingMargins": .18,
            "revenueGrowth": .16,
            "fullTimeEmployees": 28000,
            "marketCap": 250_000_000_000,
        },
        "income": None,
        "cashflow": None,
        "balance": None,
        "latest_revenue": 30_000_000_000,
        "latest_operating_income": 5_000_000_000,
        "latest_net_income": 4_000_000_000,
        "latest_ocf": 5_500_000_000,
        "latest_capex": 700_000_000,
        "latest_fcf": 4_800_000_000,
        "market_cap": 250_000_000_000,
        "cash": 6_000_000_000,
        "debt": 3_000_000_000,
        "shares": 1_600_000_000,
        "beta": 1.6,
        "currency": "USD",
        "revenue_history": [30_000_000_000, 25_000_000_000],
        "operating_income_history": [5_000_000_000, 3_500_000_000],
        "periods": {"revenue": "FY2025 vs FY2024"},
        "as_of": "2026-08-06T10:00:00-04:00",
    }


class UniversalCompanyTests(unittest.TestCase):
    def test_resolver_normalizes_and_resolves_equity(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = CompanyProfileCache(directory)
            result = SecurityResolver(lambda ticker: provider_data(ticker), cache).resolve(" amd ")
        self.assertEqual(result.ticker, "AMD")
        self.assertEqual(result.security_type, SecurityType.EQUITY)
        self.assertTrue(result.supported)
        self.assertEqual(result.research_state, ResearchState.NOT_ANALYZED)

    def test_resolver_rejects_fund_without_forcing_company_economics(self):
        data = provider_data("SPY", "ETF", "ETF_OR_FUND")
        result = SecurityResolver(lambda _ticker: data, CompanyProfileCache("/tmp/chainstox-test-no-cache")).resolve("SPY")
        self.assertEqual(result.security_type, SecurityType.ETF)
        self.assertFalse(result.supported)
        self.assertEqual(result.research_state, ResearchState.UNSUPPORTED)

    def test_invalid_company_name_query_is_clean(self):
        result = SecurityResolver(lambda _ticker: provider_data(), CompanyProfileCache("/tmp/chainstox-test-no-cache")).resolve("Advanced Micro Devices")
        self.assertEqual(result.research_state, ResearchState.FAILED)
        self.assertIn("ticker", result.reason.lower())

    def test_on_demand_analysis_caches_and_reopens_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = CompanyProfileCache(directory)
            resolver = SecurityResolver(lambda ticker: provider_data(ticker), cache)
            engine = UniversalCompanyResearchEngine(resolver=resolver, cache=cache)
            first = engine.analyze("AMD")
            second = engine.analyze("AMD")
            opened = engine.open_cached("AMD")
            self.assertIn(first["status"], {ResearchState.AVAILABLE.value, ResearchState.PARTIAL.value})
            self.assertEqual(second["source"], "CACHE")
            self.assertIsNotNone(opened["profile"])
            self.assertNotIn("normalized_snapshot", opened["profile"])
            self.assertEqual(first["data_quality"], first["profile"]["company_economics"]["data_quality"])
            self.assertEqual(second["data_quality"], first["data_quality"])
            self.assertEqual(opened["data_quality"], first["data_quality"])
            self.assertEqual(second["errors"], [])
            json.dumps(opened)

    def test_live_financial_proxies_do_not_force_primary_constraint(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = CompanyProfileCache(directory)
            engine = UniversalCompanyResearchEngine(SecurityResolver(lambda ticker: provider_data(ticker), cache), cache)
            result = engine.analyze("AMD")
        constraint = result["profile"]["company_economics"]["constraints"]["primary_constraint"]
        self.assertEqual(constraint["constraint"], ConstraintType.UNKNOWN.value)
        self.assertTrue(result["profile"]["company_economics"]["qualitative_research_needed"])

    def test_broad_archetypes_route_from_metadata_without_new_overrides(self):
        expected = {
            "AMD": Archetype.FABLESS_SEMICONDUCTOR,
            "CRM": Archetype.TRADITIONAL_SAAS,
            "META": Archetype.CONSUMER_PLATFORM,
            "WMT": Archetype.RETAIL_PHYSICAL_NETWORK,
            "BAC": Archetype.BANK,
            "CAT": Archetype.INDUSTRIAL,
        }
        for ticker, archetype in expected.items():
            with self.subTest(ticker=ticker):
                self.assertNotIn(ticker, COMPANY_ECONOMICS_OVERRIDES)
                classification = BusinessModelClassifier().classify(benchmark_snapshot(ticker))
                self.assertEqual(classification.primary_archetype, archetype)
                self.assertFalse(classification.override_used)

    def test_all_six_original_benchmarks_remain_fixtures(self):
        self.assertLessEqual({"PLTR", "NVDA", "MSFT", "JPM", "COST", "TSM"}, set(BENCHMARK_SNAPSHOTS))

    def test_no_ticker_specific_analysis_functions(self):
        root = Path(__file__).resolve().parents[1]
        code = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        for ticker in ("amd", "crm", "meta", "wmt", "bac", "cat", "xom", "lly", "uber"):
            self.assertNotIn(f"def analyze_{ticker}(", code.lower())


if __name__ == "__main__":
    unittest.main()


class ValuationOutcomeTests(unittest.TestCase):
    """Checklist 0.4: the valuation step must never fail silently."""

    def _engine(self, directory, data_factory=provider_data):
        cache = CompanyProfileCache(directory)
        return UniversalCompanyResearchEngine(resolver=SecurityResolver(lambda ticker: data_factory(ticker), cache), cache=cache)

    def test_failed_valuation_is_recorded_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self._engine(directory)
            result = engine.analyze("AMD")
            self.assertEqual(result["valuation_status"]["state"], "FAILED")
            self.assertTrue(result["valuation_status"]["error_type"])
            self.assertTrue(any(error.startswith("Valuation failed:") for error in result["errors"]))
            reopened = engine.open_cached("AMD")["profile"]["valuation_status"]
            self.assertEqual(reopened, result["valuation_status"])

    def test_completed_valuation_reports_its_own_state(self):
        from unittest.mock import patch
        report = {"validation": {"status": "PROVISIONAL"}, "data_quality": {"status": "LIMITED"}, "assumptions": {"base": [{"name": "wacc", "value": 0.09}]}, "reverse_dcf": {"status": "CONVERGED"}}
        with tempfile.TemporaryDirectory() as directory, patch("intrinsic_valuation.build_valuation_report", return_value=report):
            result = self._engine(directory).analyze("AMD")
        status = result["valuation_status"]
        self.assertEqual(status["state"], "COMPLETED")
        self.assertEqual(status["report_validation"], "PROVISIONAL")
        self.assertTrue(status["has_base_assumptions"])
        self.assertEqual(status["reverse_dcf_status"], "CONVERGED")
        self.assertFalse(any(error.startswith("Valuation failed:") for error in result["errors"]))

    def test_financial_institution_is_not_applicable_rather_than_failed(self):
        def bank(ticker):
            data = provider_data(ticker, security_type="FINANCIAL_INSTITUTION")
            data["info"].update(sector="Financial Services", industry="Banks - Diversified", longBusinessSummary="A diversified bank taking deposits and making loans.")
            return data
        with tempfile.TemporaryDirectory() as directory:
            result = self._engine(directory, bank).analyze("JPM")
        self.assertEqual(result["valuation_status"]["state"], "NOT_APPLICABLE")
