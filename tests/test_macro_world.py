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
    assert world["regions"]["EURO_AREA"]["availability"] == world["regions"]["EURO_AREA"]["coverage"]["availability"]
    assert "SG" not in world["regions"]   # Singapore removed 2026-11-22 (global audience)
    # 2026-11-27: Korea's policy slot shows the cached overnight call rate when its FRED file exists.
    kr_policy = world["regions"]["KR"]["components"][0]
    assert kr_policy["state"] == "NOT AVAILABLE" or (kr_policy["state"].startswith("CALL RATE ") and "not a Bank of Korea policy model" in kr_policy["summary"])


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
    assert run_macro_world_cli(["EURO_AREA", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert set(output["regions"]) == {"EURO_AREA"}
    assert output["regions"]["EURO_AREA"]["framework"].startswith("ECB")
    assert output["transmissions"] == []


# --- Coverage is calculated, not typed in (2026-11-22) ---------------------------------------
from macro_world import apply_coverage, region_coverage  # noqa: E402


def _compass_region(region_id="JP", missing_value=True, latest="2026-07-17"):
    evidence = [{"name": "CPI", "value": 2.0}, {"name": "Trend", "value": None if missing_value else 1.0}]
    return {
        "id": region_id, "available": True, "gaps": ["Wage growth", "wage growth"],
        "engine_specific": {"central_bank_compass": {
            "available": True, "latest": latest, "signal": "HOLD", "placeholders": ["inflation expectations"],
            "blocks": {"inflation": {"evidence": evidence}},
            "missing_indicators": [{"block": "inflation", "indicator": "inflation expectations"}],
            "liquidity": {"drivers": [{"name": "Policy", "value": 1.0}]},
        }},
    }


def test_coverage_counts_configured_indicators_and_placeholders():
    coverage = region_coverage(_compass_region(), today=date(2026, 11, 22))
    inflation = next(area for area in coverage["areas"] if area["id"] == "inflation")
    assert (inflation["available"], inflation["expected"], inflation["state"]) == (1, 3, "PARTIAL")
    assert inflation["missing"] == ["Trend", "inflation expectations"]
    labor = next(area for area in coverage["areas"] if area["id"] == "labor")
    assert labor["state"] == "NOT_COVERED"
    assert coverage["availability"] == "PARTIAL"
    assert coverage["freshness"] == "STALE"          # 2026-07-17 is 128 days old
    assert coverage["as_of"] == "2026-07-17"


def test_availability_is_available_only_when_every_area_is_full():
    region = _compass_region(missing_value=False)
    region["engine_specific"]["central_bank_compass"]["placeholders"] = []
    coverage = region_coverage(region)
    assert coverage["availability"] == "PARTIAL"     # labour, growth, markets, FX have no indicators
    empty = {"id": "XX", "available": True, "engine_specific": {}}
    assert region_coverage(empty)["availability"] == "NOT_AVAILABLE"


def test_gaps_are_deduplicated_and_not_modelled_topics_are_separate():
    region = apply_coverage(_compass_region())
    assert [gap.lower() for gap in region["gaps"]].count("wage growth") == 1
    assert "BOJ balance-sheet trend" in region["coverage"]["not_modelled"]
    assert "BOJ balance-sheet trend" not in region["gaps"]


def test_oldest_date_is_reported_when_a_newer_proxy_is_merged():
    region = _compass_region()
    region["engine_specific"]["kospi"] = {"current_sweep": True, "sweep_timestamp": "2026-11-05 09:23 UTC", "has_fx_factor": True,
                                          "has_volatility": True, "export_snapshot": None}
    coverage = region_coverage(region)
    assert (coverage["as_of"], coverage["newest"]) == ("2026-07-17", "2026-11-05")
    fx = next(area for area in coverage["areas"] if area["id"] == "fx")
    assert fx["state"] == "FULL"


def test_korea_without_a_sweep_counts_it_missing():
    region = {"id": "KR", "available": True, "engine_specific": {"kospi": {"current_sweep": False, "export_snapshot": None}}}
    markets = next(area for area in region_coverage(region)["areas"] if area["id"] == "markets")
    assert markets["available"] == 0 and markets["state"] == "MISSING"


# --- Out-of-date inputs (Compass refresh, 2026-11-22) ----------------------------------------
import pandas as pd  # noqa: E402

from macro_world import COMPASS_CACHE_DIR, CentralBankCompassAdapter, input_record  # noqa: E402


def test_input_record_infers_frequency_and_staleness():
    monthly_dead = pd.Series(1.0, index=pd.date_range("2020-01-01", "2021-06-01", freq="MS"))
    record = input_record("cpi_ex_fresh_food", "JPNCPIALLMINMEI", monthly_dead, today=date(2026, 11, 22))
    assert (record["frequency"], record["area"], record["stale"]) == ("monthly", "inflation", True)
    quarterly_lagged = pd.Series(1.0, index=pd.date_range("2024-01-01", "2026-07-01", freq="QS"))
    assert input_record("real_gdp", "GDPC1", quarterly_lagged, today=date(2026, 11, 22))["stale"] is False
    assert input_record("pmi", "X", pd.Series(dtype="float64")) is None


def test_stale_input_marks_its_area_and_keeps_region_partial():
    region = _compass_region(missing_value=False)
    region["engine_specific"]["central_bank_compass"]["inputs"] = [
        {"key": "cpi_ex_fresh_food", "series_id": "JPNCPIALLMINMEI", "area": "inflation", "last": "2021-06-01", "frequency": "monthly", "age_days": 2000, "stale": True},
        {"key": "real_gdp", "series_id": "GDPC1", "area": "growth", "last": "2026-07-01", "frequency": "quarterly", "age_days": 144, "stale": False},
    ]
    coverage = region_coverage(region)
    inflation = next(area for area in coverage["areas"] if area["id"] == "inflation")
    assert inflation["state"] == "STALE"
    assert [item["series_id"] for item in coverage["stale_inputs"]] == ["JPNCPIALLMINMEI"]
    assert coverage["availability"] == "PARTIAL"


def test_compass_cache_points_at_this_repo_not_the_nested_repo():
    assert COMPASS_CACHE_DIR.parts[-2:] == (".cache", "compass_fred")
    adapter = CentralBankCompassAdapter()
    fred = adapter._modules()["fred"]
    if COMPASS_CACHE_DIR.is_dir() and any(COMPASS_CACHE_DIR.glob("*.csv")):
        assert fred.CACHE_DIR == COMPASS_CACHE_DIR
