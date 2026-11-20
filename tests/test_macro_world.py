import json
from datetime import date

from macro_world import (
    MacroComponent,
    MacroRegionEngine,
    MacroRegionProfile,
    MacroTransmissionEngine,
    SUPPORTED_REGIONS,
    build_world,
    freshness_for,
    period_alignment,
    run_macro_world_cli,
)


def profile(region, fx="LOW", financial="LOW", evidence=True):
    evidence_ids = [f"{region.lower()}-fact"] if evidence else []
    return MacroRegionProfile(
        id=region,
        name=region,
        available=True,
        availability="AVAILABLE",
        framework="fixture",
        brief="fixture",
        as_of="2026-07-17",
        freshness="CURRENT",
        confidence="MODERATE",
        components=[
            MacroComponent("currency", "FX", fx, "fixture", "MODERATE", evidence_ids),
            MacroComponent("financial", "Financial", financial, "fixture", "MODERATE", evidence_ids),
        ],
        evidence=[] if not evidence else [object()],
    )


def test_coverage_registry_has_only_initial_regions():
    world = build_world()
    assert tuple(world["supported_regions"]) == SUPPORTED_REGIONS
    assert set(world["regions"]) == set(SUPPORTED_REGIONS)


def test_unsupported_region_returns_explicit_not_available():
    profile = MacroRegionEngine().build("BR")
    assert profile.available is False
    assert profile.availability == "NOT_AVAILABLE"
    assert profile.evidence == []


def test_cached_compass_adapter_preserves_evidence_and_gaps():
    world = build_world()
    assert world["regions"]["US"]["engines"][0]["name"] == "Central Bank Compass"
    assert world["regions"]["JP"]["gaps"]
    assert world["regions"]["SG"]["availability"] == "PARTIAL"
    assert world["regions"]["KR"]["components"][0]["state"] == "NOT AVAILABLE"


def test_transmission_state_rules_are_deterministic():
    # Checklist 3.6: yen carry has one definition (environment.yen_carry_state). The world
    # engine only states the structure; the current state is filled in by research_system.
    from environment import CARRY_EDGE_STATE, yen_carry_state
    edges = {edge["id"]: edge for edge in build_world()["transmissions"]}
    assert edges["jp-us-yen-carry"]["current_state"] == "INSUFFICIENT"
    assert not hasattr(MacroTransmissionEngine, "yen_carry_state")
    assert yen_carry_state(None, None) == "INSUFFICIENT"
    assert yen_carry_state(-0.031, 15) == "UNWIND_RISK"
    assert yen_carry_state(0.01, 24.5) == "UNWIND_RISK"
    assert yen_carry_state(0.021, 19.9) == "ACCUMULATING"
    assert yen_carry_state(0.021, None) == "ACCUMULATING"
    assert yen_carry_state(0.021, 20) == "STABLE"
    assert yen_carry_state(0.0, 18) == "STABLE"
    assert CARRY_EDGE_STATE["UNWIND_RISK"] == "ACTIVE" and CARRY_EDGE_STATE["STABLE"] == "DORMANT"


def test_freshness_and_period_mismatch_lower_inference_quality():
    assert freshness_for("2026-07-17", date(2026, 8, 3)) == "CURRENT"
    assert freshness_for("2025-12-31", date(2026, 8, 3)) == "STALE"
    assert period_alignment(["2026-07-17", "2026-07-22"]) == "ALIGNED"
    assert period_alignment(["2024-12-31", "2026-07-22"]) == "MISMATCH"
    assert period_alignment([None, "2026-07-22"]) == "INSUFFICIENT"


def test_cli_json_for_single_region(capsys):
    assert run_macro_world_cli(["SG", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert set(output["regions"]) == {"SG"}
    assert output["regions"]["SG"]["framework"].startswith("Singapore Dollar")
    assert output["transmissions"] == []
