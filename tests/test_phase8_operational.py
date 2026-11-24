"""Documentary replay and explicitly synthetic accounting identity checks."""
from dataclasses import replace
import pytest

from operational_research import build_operational_research, comparison_reasons, load_series, metric_change, revenue_bridge
from security_units import ADRBridge, per_ads_value


def test_source_replay():
    definition, observations = load_series("PLTR")[0]
    assert definition.issuer == "PLTR"
    assert [o.evidence.value for o in observations] == [711, 954]
    assert metric_change(*observations)["growth"] == pytest.approx(954 / 711 - 1)
    assert all(o.evidence.source_locator and o.evidence.retrieved_at for o in observations)


@pytest.mark.parametrize("field,value", [("issuer", "AMD"), ("scope", "commercial"), ("period_basis", "CALENDAR_ANNUAL"), ("measurement", "STOCK"), ("definition_version", "2"), ("revision_status", "UNRESOLVED"), ("period_end", "2026-12-31")])
def test_incompatible_series(field, value):
    _, (a, b) = load_series("PLTR")[0]
    assert metric_change(a, replace(b, **{field: value}))["status"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("field,value", [("currency", "TWD"), ("unit", "thousand customers")])
def test_incompatible_units(field, value):
    _, (a, b) = load_series("PLTR")[0]
    assert comparison_reasons(a, replace(b, evidence=replace(b.evidence, **{field: value})))


def test_contract_semantics():
    rows = dict((d.id, obs) for d, obs in load_series("PLTR"))
    assert comparison_reasons(rows["pltr_rdv"][-1], rows["pltr_rpo"][-1])
    assert "Not RPO" in load_series("PLTR")[1][0].limitation
    assert "TCV" in load_series("PLTR")[2][0].limitation


@pytest.mark.parametrize("ticker", ["PLTR", "TSM", "NVDA", "AMD", "MSFT", "COST", "AAPL"])
def test_company_isolation_and_no_inferred_binding(ticker):
    research = build_operational_research(ticker)
    assert research["mutates_dcf_inputs"] is False
    for row in research["series"]:
        assert row["definition"]["issuer"] == ticker
        assert row["constraint_status"] == "STRUCTURAL_CANDIDATE"
        assert row["direction_status"] == "DIRECTION_UNKNOWN"
    if ticker in {"AMD", "MSFT", "COST", "AAPL"}:
        assert research["coverage"] == "MISSING"


def test_synthetic_symmetric_identity_not_causality():
    _, population = load_series("PLTR")[0]
    customers = tuple(replace(o, evidence=replace(o.evidence, value=v)) for o, v in zip(population, (10, 20)))
    revenue = tuple(replace(o, metric_id="synthetic_revenue", measurement="FLOW", evidence=replace(o.evidence, value=v, unit="USD", currency="USD")) for o, v in zip(population, (100, 300)))
    result = revenue_bridge(revenue, customers)
    assert result["customer_contribution"] == 125
    assert result["revenue_per_customer_contribution"] == 75
    assert result["total_change"] == 200
    assert "not causality" in result["method"]
    wrong = tuple(replace(o, scope="commercial") for o in customers)
    assert revenue_bridge(revenue, wrong)["status"] == "INSUFFICIENT_EVIDENCE"


def test_shipments_not_utilization_and_revenue_not_units():
    tsm = build_operational_research("TSM")
    assert "utilization" in tsm["series"][0]["definition"]["limitation"]
    assert tsm["security_unit_status"] == "SECURITY_UNIT_AMBIGUITY"
    nvda = build_operational_research("NVDA")
    assert "Not GPU units" in nvda["series"][0]["definition"]["limitation"]


def test_synthetic_adr_bridge():
    bridge = ADRBridge("SYNTHETIC", "TEST", "TEST.TW", 5, "2025-01-01", "2025-12-31", "https://example.org/synthetic", "Test only", "TWD", "USD")
    args = dict(equity_value=3000, shares=100, share_basis="TOTAL_ORDINARY", equity_currency="TWD", valuation_date="2025-12-31", bridge=bridge, fx=1/30, fx_date="2025-12-31", fx_source="synthetic")
    result = per_ads_value(**args)
    assert result["per_ads"] == 5
    assert result["equity_value_unchanged"] == 3000
    for override in ({"share_basis": "ADS"}, {"fx": None}, {"fx_date": "2025-01-01"}, {"equity_currency": "USD"}, {"valuation_date": "2026-01-01"}, {"bridge": replace(bridge, effective_from="")}):
        assert per_ads_value(**(args | override))["per_ads"] is None


def test_assumptions_are_read_only():
    import copy
    report = {"assumptions": {"base": [{"name": "year_1_revenue_growth", "value": 0.3}]}}
    before = copy.deepcopy(report)
    result = build_operational_research("PLTR", report)
    assert report == before
    assert all(t["state"] == "CONTEXT_ONLY" for t in result["assumption_tensions"])


def test_cached_profile_enrichment_preserves_cache_and_time():
    import copy
    from company_research import UniversalCompanyResearchEngine
    payload = {"company_economics": {"company": {"ticker": "PLTR", "as_of": "2025-01-01"}}, "cache_metadata": {"last_analyzed": "2025-01-01"}}
    before = copy.deepcopy(payload)
    public = UniversalCompanyResearchEngine._public_profile(payload)
    assert payload == before
    assert public["cache_metadata"] == before["cache_metadata"]
    assert public["company_economics"]["operational_research"]["coverage"] == "PARTIAL"
