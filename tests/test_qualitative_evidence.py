"""Stage 3 tests: Gemini extraction boundary, deterministic validator, MACHINE_EXTRACTED gate, and CLI."""

import json
from pathlib import Path

import pytest

from company_economics import QualitativeCompanyEconomicsExtractor
from company_economics_registry import Archetype
from data_sources.operational_evidence import load_operational_evidence
from evidence_contracts import ConstraintStatus, DirectionStatus, ValidationStatus, assess_constraint_claim
from qualitative_evidence import (
    accept_candidate,
    empty_candidate_store,
    evaluate_against_gold_standard,
    extract_from_filing_text,
    kpi_catalog_for_archetype,
    reject_candidate,
    run_evidence_cli,
    validate_kpi_candidate,
    validate_quote_in_text,
)


PLTR_FILING_EXCERPT = """
Item 1. Business — Our Customers
As of December 31, 2025, we had 954 customers across the commercial and government sectors,
compared with 711 customers as of December 31, 2024. Our remaining performance obligations
were $4.1 billion as of December 31, 2025, while implementation engineers remained focused
on shortening customer onboarding cycles.
Management noted that enterprise customer deployment capacity remained a pacing factor on
converting pilot bootcamps into full production contracts during 2025.
"""


def test_verbatim_quote_gate_accepts_exact_and_rejects_paraphrase():
    ok, err = validate_quote_in_text(
        "As of December 31, 2025, we had 954 customers across the commercial and government sectors",
        PLTR_FILING_EXCERPT,
    )
    assert ok and err is None

    # One paraphrased word ("clients" instead of "customers") must fail.
    bad_ok, bad_err = validate_quote_in_text(
        "As of December 31, 2025, we had 954 clients across the commercial and government sectors",
        PLTR_FILING_EXCERPT,
    )
    assert not bad_ok and bad_err == "quote_not_verbatim_in_source"


def test_numeric_grounding_and_period_gates():
    allowed = set(kpi_catalog_for_archetype(Archetype.ENTERPRISE_AI_SOFTWARE))

    # Valid scaled billion -> USD and exact count
    valid_rpo = validate_kpi_candidate(
        {
            "metric": "remaining_performance_obligations",
            "value": 4_100_000_000,
            "unit": "USD",
            "reporting_period": "FY ended 2025-12-31",
            "observation_date": "2025-12-31",
            "metric_definition": "Remaining performance obligations under non-cancelable contracts.",
            "verbatim_quote": "Our remaining performance obligations were $4.1 billion as of December 31, 2025",
            "locator": "Item 1 — Our Customers",
        },
        issuer="PLTR",
        source_text=PLTR_FILING_EXCERPT,
        allowed_metrics=allowed,
        filing_date="2026-02-17",
        report_date="2025-12-31",
    )
    assert valid_rpo["status"] == "VALIDATED"

    # Hallucinated number (1200 not in quote) is rejected
    bad_num = validate_kpi_candidate(
        {
            "metric": "customers",
            "value": 1200,
            "unit": "customers",
            "reporting_period": "FY ended 2025-12-31",
            "observation_date": "2025-12-31",
            "metric_definition": "Customer count.",
            "verbatim_quote": "As of December 31, 2025, we had 954 customers across the commercial and government sectors",
            "locator": "Item 1",
        },
        issuer="PLTR",
        source_text=PLTR_FILING_EXCERPT,
        allowed_metrics=allowed,
        filing_date="2026-02-17",
        report_date="2025-12-31",
    )
    assert bad_num["status"] == "REJECTED"
    assert "value_not_grounded_in_quote" in bad_num["rejection_reasons"]

    # Future observation_date after filing_date is rejected
    future_obs = validate_kpi_candidate(
        {
            "metric": "customers",
            "value": 954,
            "unit": "customers",
            "reporting_period": "FY2026",
            "observation_date": "2026-12-31",
            "metric_definition": "Customer count.",
            "verbatim_quote": "As of December 31, 2025, we had 954 customers across the commercial and government sectors",
            "locator": "Item 1",
        },
        issuer="PLTR",
        source_text=PLTR_FILING_EXCERPT,
        allowed_metrics=allowed,
        filing_date="2026-02-17",
        report_date="2025-12-31",
    )
    assert future_obs["status"] == "REJECTED"
    assert "observation_after_filing_date" in future_obs["rejection_reasons"]


def test_machine_extracted_evidence_caps_at_possibly_and_blocks_observed():
    unverified_claim = assess_constraint_claim(
        claim_id="deploy-test",
        entity_identifier="PLTR",
        mechanism="Deployment Capacity",
        direct_ids=["QE1"],
        proxy_ids=[],
        counter_ids=[],
        direct_direction="TIGHTENING",
        evidence_current=True,
        explicitly_binding=True,
        direct_verified=False,
    )
    assert unverified_claim.constraint_status == ConstraintStatus.POTENTIALLY_BINDING
    assert unverified_claim.direction_status == DirectionStatus.POSSIBLY_TIGHTENING
    assert unverified_claim.source_reliability == ValidationStatus.UNVERIFIED

    verified_claim = assess_constraint_claim(
        claim_id="deploy-test",
        entity_identifier="PLTR",
        mechanism="Deployment Capacity",
        direct_ids=["E1"],
        proxy_ids=[],
        counter_ids=[],
        direct_direction="TIGHTENING",
        evidence_current=True,
        explicitly_binding=True,
        direct_verified=True,
    )
    assert verified_claim.constraint_status == ConstraintStatus.OBSERVED_BINDING
    assert verified_claim.direction_status == DirectionStatus.OBSERVED_TIGHTENING
    assert verified_claim.source_reliability == ValidationStatus.VALID


def test_recorded_gemini_flow_cache_conflict_accept_and_gold_benchmark(tmp_path: Path):
    cand_path = tmp_path / "candidates.json"
    gold_path = tmp_path / "verified.json"
    cache_dir = tmp_path / "gemini_cache"

    gold_payload = {
        "schema_version": "1.0",
        "entries": [
            {
                "id": "PLTR-2025-CUSTOMERS",
                "issuer": "PLTR",
                "entity_identifier": "CIK0001321655",
                "metric": "customers",
                "metric_definition": "Customer count.",
                "value": 954,
                "unit": "customers",
                "reporting_period": "FY ended 2025-12-31",
                "observation_date": "2025-12-31",
                "publication_date": "2026-02-17",
                "source_title": "Palantir 2025 10-K",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1321655/000132165526000010/pltr-20251231.htm",
                "source_type": "issuer_annual_report",
                "extraction_method": "curated_manual_entry",
                "verification_status": "DOCUMENTARY_VERIFIED",
                "locator": "Our Customers",
                "limitation": "None",
            }
        ],
    }
    gold_path.write_text(json.dumps(gold_payload), encoding="utf-8")

    calls = {"n": 0}

    def fake_gemini(**_kwargs):
        calls["n"] += 1
        return {
            "kpis": [
                {
                    "metric": "customers",
                    "value": 954,
                    "unit": "customers",
                    "reporting_period": "FY ended 2025-12-31",
                    "observation_date": "2025-12-31",
                    "metric_definition": "Organizations from which revenue was recognized.",
                    "verbatim_quote": "As of December 31, 2025, we had 954 customers across the commercial and government sectors",
                    "locator": "Item 1 — Our Customers",
                },
                {
                    "metric": "customers",
                    "value": 711,
                    "unit": "customers",
                    "reporting_period": "FY ended 2024-12-31",
                    "observation_date": "2024-12-31",
                    "metric_definition": "Organizations from which revenue was recognized.",
                    "verbatim_quote": "compared with 711 customers as of December 31, 2024.",
                    "locator": "Item 1 — Our Customers",
                },
                {
                    # Paraphrased / hallucinated quote -> must be rejected by code validator
                    "metric": "remaining_performance_obligations",
                    "value": 9.9,
                    "unit": "USD billion",
                    "reporting_period": "FY ended 2025-12-31",
                    "observation_date": "2025-12-31",
                    "metric_definition": "Invented RPO.",
                    "verbatim_quote": "Our remaining performance obligations reached $9.9 billion in 2025.",
                    "locator": "Item 1",
                },
            ],
            "constraint_statements": [
                {
                    "constraint_category": "SUPPLY_CONSTRAINED",
                    "mechanism": "DEPLOYMENT_CAPACITY",
                    "reporting_period": "FY2025",
                    "observation_date": "2025-12-31",
                    "explicitly_binding": True,
                    "verbatim_quote": "Management noted that enterprise customer deployment capacity remained a pacing factor on converting pilot bootcamps into full production contracts during 2025.",
                    "locator": "Item 1",
                }
            ],
            "archetype_second_opinion": {
                "suggested_archetype": "TRADITIONAL_SAAS",
                "confidence": "MODERATE",
                "rationale": "Recurring commercial contracts.",
                "verbatim_quote": "Our remaining performance obligations were $4.1 billion as of December 31, 2025",
            },
        }

    summary = extract_from_filing_text(
        ticker="PLTR",
        company_name="Palantir Technologies Inc.",
        cik_key="CIK0001321655",
        form="10-K",
        filing_date="2026-02-17",
        report_date="2025-12-31",
        source_title="Palantir 2025 Form 10-K",
        source_url="https://www.sec.gov/Archives/edgar/data/1321655/000132165526000010/pltr-20251231.htm",
        filing_text=PLTR_FILING_EXCERPT,
        deterministic_archetype=Archetype.ENTERPRISE_AI_SOFTWARE,
        deterministic_confidence="HIGH",
        model="gemini-2.5-flash",
        transport=fake_gemini,
        cache_dir=cache_dir,
        candidate_store_path=cand_path,
        verified_store_path=gold_path,
    )
    assert calls["n"] == 1
    assert summary["validated_count"] == 2
    assert summary["rejected_count"] == 1
    assert summary["constraint_statement_count"] == 1
    assert summary["archetype_review_draft"]["mutates_live_classification"] is False

    # Second run hits content-addressed cache without calling transport again
    summary2 = extract_from_filing_text(
        ticker="PLTR",
        company_name="Palantir Technologies Inc.",
        cik_key="CIK0001321655",
        form="10-K",
        filing_date="2026-02-17",
        report_date="2025-12-31",
        source_title="Palantir 2025 Form 10-K",
        source_url="https://www.sec.gov/Archives/edgar/data/1321655/000132165526000010/pltr-20251231.htm",
        filing_text=PLTR_FILING_EXCERPT,
        deterministic_archetype=Archetype.ENTERPRISE_AI_SOFTWARE,
        deterministic_confidence="HIGH",
        model="gemini-2.5-flash",
        transport=fake_gemini,
        cache_dir=cache_dir,
        candidate_store_path=cand_path,
        verified_store_path=gold_path,
    )
    assert calls["n"] == 1 and summary2["cached_response"] is True

    # Gold-standard precision check passes >=95% gate
    bench = evaluate_against_gold_standard(["PLTR"], candidate_store_path=cand_path, gold_store_path=gold_path)
    assert bench["precision"] == 1.0 and bench["passes_gate"] is True

    # Promote the 2024 customer count candidate -> becomes DOCUMENTARY_VERIFIED in verified store
    promoted = accept_candidate(
        "PLTR-2024-12-31-CUSTOMERS-CAND",
        candidate_store_path=cand_path,
        verified_store_path=gold_path,
    )
    assert promoted["verification_status"] == "DOCUMENTARY_VERIFIED"
    loaded = load_operational_evidence("PLTR", gold_path)
    assert len(loaded) == 2

    # Rejecting a candidate marks it REJECTED
    rej = reject_candidate("PLTR-2025-12-31-CUSTOMERS-CAND", reason="Already in gold store", candidate_store_path=cand_path)
    assert rej["review_state"] == "REJECTED"


def test_missing_api_key_graceful_fallback_and_cli_help(monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    extractor = QualitativeCompanyEconomicsExtractor(Path("/nonexistent/candidates.json"))
    res = extractor.extract("PLTR")
    assert res["status"] == "API_KEY_MISSING"

    rc = run_evidence_cli(["--help"])
    assert rc == 0
    assert "python model.py evidence review" in capsys.readouterr().out
