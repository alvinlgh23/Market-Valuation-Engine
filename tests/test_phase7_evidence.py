from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from company_economics import CompanySnapshot, build_company_economics
from data_sources.market_history import PriceAdjustment, normalize_yahoo_chart
from data_sources.operational_evidence import enrich_snapshot, load_operational_evidence
from data_sources.sec_company import _annual_series
from evidence_contracts import (
    ConstraintStatus,
    DirectionStatus,
    EvidenceEnvelope,
    ProviderStatus,
    ValidationStatus,
    assess_constraint_claim,
    classify_staleness,
    validate_comparable_observations,
)
from research_system import typed_metric


def yahoo_payload(*, currency="USD", timestamps=None, closes=None, adjusted=None):
    timestamps = timestamps or [1_700_000_000, 1_700_086_400]
    closes = closes or [100.0, 101.0]
    indicators = {"quote": [{"close": closes}]}
    if adjusted is not None:
        indicators["adjclose"] = [{"adjclose": adjusted}]
    return {
        "chart": {
            "error": None,
            "result": [{
                "meta": {"currency": currency, "exchangeName": "NMS", "instrumentType": "ETF", "exchangeTimezoneName": "America/New_York"},
                "timestamp": timestamps,
                "indicators": indicators,
            }],
        }
    }


def test_market_history_success_preserves_adjustment_identity_dates_and_currency():
    result = normalize_yahoo_chart(yahoo_payload(adjusted=[99.0, 100.5]), "SPY", expected_currency="USD", retrieved_at="2026-10-21T00:00:00+00:00")
    assert result.provider_status == ProviderStatus.OK
    assert result.adjustment_policy == PriceAdjustment.ADJUSTED_CLOSE
    assert result.currency == "USD"
    assert result.observation_start == "2023-11-14"
    assert result.observation_end == "2023-11-15"
    assert [item.value for item in result.observations] == [99.0, 100.5]


@pytest.mark.parametrize(
    "payload,status",
    [
        ({}, ProviderStatus.MALFORMED_RESPONSE),
        ({"chart": {"error": None, "result": []}}, ProviderStatus.EMPTY_RESPONSE),
        ({"chart": {"error": {"code": "Not Found", "description": "No data"}, "result": None}}, ProviderStatus.UNSUPPORTED_SYMBOL),
        (yahoo_payload(timestamps=[1_700_000_000], closes=[1.0, 2.0]), ProviderStatus.MALFORMED_RESPONSE),
    ],
)
def test_market_history_replay_failure_classes(payload, status):
    assert normalize_yahoo_chart(payload, "BAD").provider_status == status


def test_market_history_deduplicates_dates_and_never_calls_close_total_return():
    result = normalize_yahoo_chart(yahoo_payload(timestamps=[1_700_000_000, 1_700_000_100], closes=[100.0, 101.0]), "SPY")
    assert len(result.observations) == 1
    assert result.adjustment_policy == PriceAdjustment.UNADJUSTED_CLOSE
    assert "not total returns" in result.limitation
    assert "Duplicate" in result.limitation


def test_market_history_currency_mismatch_is_invalid_not_empty():
    result = normalize_yahoo_chart(yahoo_payload(currency="TWD"), "TSM", expected_currency="USD")
    assert result.provider_status == ProviderStatus.CURRENCY_MISMATCH
    assert result.observations == []


def test_sec_series_selects_newer_compatible_concept_without_mixing_concepts():
    facts = {"facts": {"us-gaap": {
        "OldRevenue": {"units": {"USD": [{"form": "10-K", "fp": "FY", "end": "2024-12-31", "filed": "2025-02-01", "val": 10}]}},
        "CurrentRevenue": {"units": {"USD": [
            {"form": "10-K", "fp": "FY", "end": "2024-12-31", "filed": "2025-02-01", "val": 11},
            {"form": "10-K", "fp": "FY", "end": "2025-12-31", "filed": "2026-02-01", "val": 12},
        ]}},
    }}}
    rows = _annual_series(facts, ("OldRevenue", "CurrentRevenue"), "USD")
    assert [row["val"] for row in rows] == [12, 11]
    assert {row["concept"] for row in rows} == {"CurrentRevenue"}


def test_sec_series_supports_ifrs_20f_and_reporting_currency():
    facts = {"facts": {"ifrs-full": {"Revenue": {"units": {"TWD": [
        {"form": "20-F", "fp": "FY", "start": "2024-01-01", "end": "2024-12-31", "filed": "2025-04-01", "val": 100},
    ]}}}}}
    rows = _annual_series(facts, ("Revenue",), "TWD", taxonomy="ifrs-full", forms=("20-F",))
    assert rows[0]["taxonomy"] == "ifrs-full"
    assert rows[0]["unit"] == "TWD"


def test_comparability_rejects_period_and_currency_conflicts():
    a = EvidenceEnvelope("a", "source", value=1, unit="currency", currency="USD", fiscal_period_end="2025-12-31")
    b = EvidenceEnvelope("b", "source", value=2, unit="currency", currency="TWD", fiscal_period_end="2024-12-31")
    status, reasons = validate_comparable_observations([a, b])
    assert status == ValidationStatus.CONFLICTING
    assert set(reasons) == {"currency mismatch", "period mismatch"}


def test_retrieval_freshness_is_not_observation_freshness():
    assert classify_staleness("2024-12-31", as_of=dt.date(2026, 10, 21), max_age_days=365).value == "STALE"


def test_proxy_never_establishes_observed_binding_or_observed_direction():
    claim = assess_constraint_claim(
        claim_id="deployment", entity_identifier="PLTR", mechanism="Deployment Capacity",
        direct_ids=[], proxy_ids=["revenue-per-employee"], counter_ids=[], proxy_direction="IMPROVING",
    )
    assert claim.constraint_status == ConstraintStatus.EVIDENCE_INSUFFICIENT
    assert claim.direction_status == DirectionStatus.POSSIBLY_EASING


def test_archetype_without_measurement_remains_structural_candidate():
    claim = assess_constraint_claim(
        claim_id="packaging", entity_identifier="NVDA", mechanism="Advanced Packaging Capacity",
        direct_ids=[], proxy_ids=[], counter_ids=[],
    )
    assert claim.constraint_status == ConstraintStatus.STRUCTURAL_CANDIDATE
    assert claim.direction_status == DirectionStatus.DIRECTION_UNKNOWN


def test_stale_direct_observation_cannot_support_current_direction():
    claim = assess_constraint_claim(
        claim_id="capacity", entity_identifier="TSM", mechanism="Fab Capacity",
        direct_ids=["capacity-2024"], proxy_ids=[], counter_ids=[], direct_direction="IMPROVING", evidence_current=False,
    )
    assert claim.constraint_status == ConstraintStatus.STRUCTURAL_CANDIDATE
    assert claim.direction_status == DirectionStatus.DIRECTION_UNKNOWN


def test_counterevidence_is_visible_and_qualifies_claim():
    claim = assess_constraint_claim(
        claim_id="capacity", entity_identifier="TSM", mechanism="Fab Capacity",
        direct_ids=["shipments"], proxy_ids=[], counter_ids=["underutilization"], direct_direction="TIGHTENING",
    )
    assert claim.constraint_status == ConstraintStatus.CONFLICTING_EVIDENCE
    assert claim.direction_status == DirectionStatus.MIXED
    assert claim.counterevidence_ids == ("underutilization",)


def test_curated_registry_is_attributed_and_enriches_only_matching_company():
    pltr = load_operational_evidence("PLTR")
    assert [entry.metric for entry in pltr] == ["customers"]
    assert pltr[0].source_url.startswith("https://investors.palantir.com/")
    snapshot = CompanySnapshot("PLTR", "Palantir", "2026-10-21")
    enrich_snapshot(snapshot)
    assert snapshot.operational_metrics["customers"] == 954
    assert snapshot.evidence_envelopes["customers"]["source_status"] == "HISTORICAL_REPORTED"
    assert "deployment capacity" in snapshot.evidence_envelopes["customers"]["limitation"].lower()


def test_missing_manual_attribution_is_rejected(tmp_path: Path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"entries": [{"id": "bad", "issuer": "PLTR"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks"):
        load_operational_evidence("PLTR", path)


def test_pltr_financial_proxy_does_not_promote_deployment_constraint():
    snapshot = CompanySnapshot(
        "PLTR", "Palantir", "2026-10-21", sector="Technology", industry="Software - Infrastructure",
        business_description="Enterprise artificial intelligence platform and data analytics platform.",
        metrics={"revenue": 200, "revenue_growth": 0.30, "operating_margin": 0.20, "employees": 10, "employee_growth": 0.05},
        periods={"revenue": "FY2025", "revenue_growth": "FY2025", "operating_margin": "FY2025", "employees": "FY2025", "employee_growth": "FY2025"},
        sources={key: "deterministic fixture" for key in ("revenue", "revenue_growth", "operating_margin", "employees", "employee_growth")},
    )
    profile = build_company_economics(snapshot)
    deployment = next(claim for claim in profile.research_claims if claim["mechanism"] == "DEPLOYMENT_CAPACITY")
    # Synthetic financial proxies cannot substantiate even a directional claim.
    assert deployment["constraint_status"] == "STRUCTURAL_CANDIDATE"
    assert deployment["direction_status"] == "DIRECTION_UNKNOWN"
    assert profile.constraints.primary_constraint.constraint.value == "UNKNOWN"


def test_evidence_review_never_mutates_dcf_input():
    valuation = {"assumptions": {"base": [{"name": "year_1_revenue_growth", "value": 0.12}, {"name": "year_5_fcff_margin", "value": 0.22}]}}
    before = copy.deepcopy(valuation)
    snapshot = CompanySnapshot("TEST", "Test", "2026-10-21", metrics={"revenue": 100, "revenue_growth": 0.1, "fcf": 10, "fcf_margin": 0.1})
    profile = build_company_economics(snapshot, valuation)
    assert valuation == before
    assert profile.valuation_assumption_review.mutates_dcf_inputs is False


def test_macro_metric_keeps_observation_and_retrieval_freshness_separate():
    metric = typed_metric("us_10y", "US 10Y", 4.25, "%", "2026-10-20", "official source", "CACHED")
    assert metric["observation_date"] == "2026-10-20"
    assert metric["retrieved_at"] != metric["observation_date"]
    assert metric["source_status"] == "OBSERVED_CACHED"
    assert metric["validation_status"] == "VALID"


def test_market_provider_diagnostics_are_compact_by_default(monkeypatch):
    import Valuation_model as market

    monkeypatch.setattr(market, "_MARKET_PROVIDER_DIAGNOSTICS", {
        "history:SPY:1y": {"ticker": "SPY", "provider_status": "OK", "observations": [{"date": "2026-10-20", "value": 1.0}]}
    })
    compact = market.market_provider_diagnostics()["history:SPY:1y"]
    replay = market.market_provider_diagnostics(include_observations=True)["history:SPY:1y"]
    assert compact["observation_count"] == 1
    assert "observations" not in compact
    assert replay["observations"][0]["value"] == 1.0
