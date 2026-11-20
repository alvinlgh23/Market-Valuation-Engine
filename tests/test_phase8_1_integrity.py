"""Regressions for the independent Phase 8 audit, using actual export inputs."""
import json
from pathlib import Path
import pytest
from company_economics import build_company_economics
from company_economics_fixtures import benchmark_snapshot, benchmark_valuation_report
from data_sources.sec_company import _annual_series
from operational_research import build_operational_research

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("ticker", ["PLTR", "TSM", "NVDA", "AMD", "MSFT", "COST"])
def test_actual_benchmark_authority(ticker):
    profile = build_company_economics(benchmark_snapshot(ticker), benchmark_valuation_report(ticker)).to_dict()["company_economics"]
    assert profile["constraints"]["primary_constraint"]["direction_status"] == "DIRECTION_UNKNOWN"
    assert profile["constraints"]["primary_constraint"]["constraint"] == "UNKNOWN"
    assert profile["market_expectations_comparison"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert not any(e["type"] == "FACT" and e["source_status"] == "FIXTURE" for e in profile["evidence_trace"])

def test_share_change_is_not_revenue_growth():
    p = build_operational_research("TSM", {"assumptions": {"base": [{"name": "year_1_revenue_growth", "value": .25}]}})
    change = p["series"][1]["changes"][0]
    assert change["absolute"] == 5
    assert change["growth"] is None
    assert not any(t["metric"] == "Advanced technology revenue mix" for t in p["assumption_tensions"])

def test_annual_duration_and_accession_order():
    common = dict(end="2025-12-31", filed="2026-02-01", form="10-K", fp="FY")
    short = dict(common, start="2025-10-01", val=20, accn="a")
    annual = dict(common, start="2025-01-01", val=100, accn="a")
    amended = dict(common, start="2025-01-01", val=101, accn="b")
    for rows in ([short, annual, amended], [amended, annual, short]):
        facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rows}}}}}
        assert _annual_series(facts, ("Revenues",))[0]["val"] == 101
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"] = [short]
    assert _annual_series(facts, ("Revenues",)) == []

def test_explicit_units_win():
    s = benchmark_snapshot("PLTR")
    s.metrics["shares"] = 123
    s.operational_metrics["wafer_volume"] = 15
    s.evidence_envelopes["wafer_volume"] = {"unit": "million 12-inch-equivalent wafers"}
    rows = {e.metric: e for e in build_company_economics(s).evidence_trace}
    assert rows["shares"].unit == "shares"
    assert rows["ticker"].unit == "text"
    assert rows["wafer_volume"].unit == "million 12-inch-equivalent wafers"

@pytest.mark.parametrize("ticker,financial,quote", [("TSM", "TWD", "USD"), ("TSM", "USD", "USD"), ("OTHER", "EUR", "USD")])
def test_real_valuation_execution_blocks_unit_mismatch(ticker, financial, quote):
    from test_intrinsic_valuation import fixture_data
    from intrinsic_valuation import build_valuation_report
    data = fixture_data()
    data["ticker"] = ticker
    data["info"].update(financialCurrency=financial, currency=quote)
    report = build_valuation_report(ticker, data=data)
    assert report["validation"]["status"] == "FAILED"
    assert report["data_quality"]["status"] == "SECURITY_UNIT_AMBIGUITY"
    assert not report["scenarios"] and not report["sensitivity"] and not report["reverse_dcf"]

def test_positive_capacity_does_not_prove_easing():
    from company_economics import CompanySnapshot
    snapshot = CompanySnapshot("TEST", "Foundry", "2026-01-01", business_description="semiconductor foundry", metrics={"revenue": 100, "revenue_growth": .60}, operational_metrics={"fab_capacity_growth": .12})
    profile = build_company_economics(snapshot)
    assert profile.constraints.primary_constraint.direction_status == "DIRECTION_UNKNOWN"
    assert all(c.direction_status == "DIRECTION_UNKNOWN" for c in profile.constraints.candidate_assessments)

def test_instant_fact_requires_no_duration():
    row = dict(end="2025-12-31", filed="2026-02-01", form="10-K", fp="FY", val=123)
    facts = {"facts": {"us-gaap": {"CommonStockSharesOutstanding": {"units": {"shares": [row, dict(row, start="2025-01-01", val=999)]}}}}}
    assert _annual_series(facts, ("CommonStockSharesOutstanding",), "shares")[0]["val"] == 123

@pytest.mark.parametrize("ticker", ["PLTR", "TSM", "NVDA", "AMD", "MSFT", "COST"])
def test_export_synchronization(ticker):
    actual = build_company_economics(benchmark_snapshot(ticker), benchmark_valuation_report(ticker)).to_dict()
    saved = json.loads((ROOT / f"frontend/lib/fixtures/company-economics/{ticker}.json").read_text())
    assert actual == saved

def test_documentary_dates_duplicates_and_fixture_derivations():
    from operational_research import load_series
    rpo = dict((d.id, rows) for d, rows in load_series("PLTR"))["pltr_rpo"]
    assert [r.evidence.value for r in rpo] == [1.7, 4.1]
    assert rpo[0].evidence.filing_date == "2025-02-18"
    for _, rows in load_series("TSM"):
        assert all(r.evidence.filing_date == "2026-03-12" for r in rows)
    p = build_company_economics(benchmark_snapshot("PLTR"))
    assert not any(e.metric == "customers" for e in p.evidence_trace)
    nodes = [n["id"] for n in p.economic_graph["nodes"]]
    assert "customers" not in nodes and nodes.count("pltr_customers") == 1
    derived = next(e for e in p.evidence_trace if e.metric == "revenue_per_employee")
    assert derived.source_status == "FIXTURE"
    assert derived.unit == "currency/employee" and derived.value > 100_000
    tsm = build_company_economics(benchmark_snapshot("TSM"))
    tsm_nodes = [n["id"] for n in tsm.economic_graph["nodes"]]
    assert "node_mix" not in tsm_nodes and "wafer_volume" not in tsm_nodes
    assert tsm_nodes.count("tsm_node_mix") == tsm_nodes.count("tsm_shipments") == 1

def test_cached_old_authority_rebuilt_without_mutation():
    import copy
    from dataclasses import asdict
    from company_research import UniversalCompanyResearchEngine
    payload = build_company_economics(benchmark_snapshot("PLTR")).to_dict()
    payload["normalized_snapshot"] = asdict(benchmark_snapshot("PLTR"))
    payload["company_economics"]["classification_version"] = "old"
    payload["company_economics"]["constraints"]["primary_constraint"]["direction_status"] = "OBSERVED_EASING"
    before = copy.deepcopy(payload)
    public = UniversalCompanyResearchEngine._public_profile(payload)
    assert payload == before
    assert public["company_economics"]["constraints"]["primary_constraint"]["direction_status"] == "DIRECTION_UNKNOWN"

def test_nonfixture_financial_analysis_retains_utility():
    """Controlled provider-contract replay, not a claim about live PLTR data."""
    from company_economics import CompanySnapshot
    snapshot = CompanySnapshot("TEST", "Provider replay", "2025-12-31",
        business_description="Enterprise artificial intelligence platform",
        metrics={"revenue": 1_000_000, "revenue_growth": .30, "employees": 10},
        histories={"revenue": [1_000_000, 800_000], "operating_income": [200_000, 100_000]},
        sources={"revenue": "provider-contract replay", "revenue_growth": "provider-contract replay"})
    report = {"assumptions": {"base": [{"name": "year_1_revenue_growth", "value": .30}]}}
    p = build_company_economics(snapshot, report)
    assert p.valuation_assumption_review.reviews[0].state.value == "SUPPORTED"
    assert p.financial_translation.margin.state.value == "POSITIVE"
    assert next(e for e in p.evidence_trace if e.metric == "revenue").type.value == "FACT"
    assert p.constraints.primary_constraint.direction_status == "DIRECTION_UNKNOWN"

def test_sec_collector_rejects_stale_share_denominator(monkeypatch):
    from data_sources import sec_company as sec
    revenue = {"start": "2025-02-01", "end": "2026-01-31", "filed": "2026-03-01", "form": "10-K", "fp": "FY", "val": 100}
    shares = {"end": "2012-01-31", "filed": "2012-03-01", "form": "10-K", "fp": "FY", "val": 3418000000}
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [revenue]}}, "CommonStockSharesOutstanding": {"units": {"shares": [shares]}}}}}
    monkeypatch.setattr(sec, "_company_record", lambda _: {"cik_str": 104169, "title": "Period replay"})
    monkeypatch.setattr(sec, "_fetch", lambda url, path: facts if "companyfacts" in url else {"name": "Period replay"})
    data = sec.collect_sec_company_data("TEST")
    assert data["latest_revenue"] == 100
    assert data["shares"] is None
