import json
from pathlib import Path

from research_capabilities import capability_payload
from risk_regime import analyze_risk_regime


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "frontend" / "lib" / "fixtures" / "research-system.json"


def test_every_active_engine_has_a_post_integration_surface():
    payload = capability_payload()
    active = [engine for engine in payload["engines"] if engine["status"].startswith("ACTIVE")]
    assert active
    for engine in active:
        assert engine["frontend_after"]
        assert engine["ui_surfaces"], engine["engine_id"]
        assert engine["outputs"], engine["engine_id"]


def test_every_registered_output_has_a_surface_and_disposition():
    allowed = ("interactive", "partial", "report_only", "debug_only")
    for row in capability_payload()["information_surfaces"]:
        assert row["output"]
        assert row["surface"]
        assert row["status"].startswith(allowed), row


def test_integrated_fixture_retains_engine_specific_payloads():
    system = json.loads(FIXTURE.read_text())
    assert system["world"]["regions"]["US"]["engine_specific"]["us_inflation"]["metrics"]
    assert system["world"]["regions"]["US"]["engine_specific"]["central_bank_compass"]["blocks"]
    assert len(system["world"]["regions"]["SG"]["engine_specific"]["shadow_neer_live"]["fx_components"]) == 12
    kospi = system["world"]["regions"]["KR"]["engine_specific"]["kospi_live"]
    assert len(kospi["sweep"]["results"]) == 5
    assert len(kospi["exports"]["items"]) >= 6


def test_insufficient_core_market_does_not_publish_fallback_regime():
    system = json.loads(FIXTURE.read_text())
    assert system["engine_states"]["core_market"] == "INSUFFICIENT"
    risk = next(row for row in system["dashboard"]["reads"] if row["id"] == "risk")
    breadth = next(row for row in system["dashboard"]["reads"] if row["id"] == "breadth")
    assert risk["value"] == "Insufficient evidence"
    assert breadth["value"] == "Insufficient evidence"


def test_specialist_coverage_gaps_are_not_silently_filled():
    system = json.loads(FIXTURE.read_text())
    coverage = system["modules"]["neer"]["payload"]["coverage"]
    for key in ("foreign_reserves", "rates", "bond_flows", "equity_flows", "imported_inflation"):
        assert coverage[key] == "NOT_MODELED"


def test_fixture_inventory_and_surface_registry_are_embedded():
    system = json.loads(FIXTURE.read_text())
    capabilities = system["capabilities"]
    assert len(capabilities["engines"]) >= 12
    assert capabilities["information_surfaces"] == capability_payload()["information_surfaces"]


def test_risk_engine_preserves_internal_classification_but_withholds_publication_without_coverage():
    report = analyze_risk_regime({})
    assert report["regime"] in {"Healthy Rotation", "Narrow Leadership Unwind", "Broad Risk-Off", "Liquidity / Inflation Stress"}
    assert report["published_regime"] == "Insufficient Evidence"
    assert report["publication_state"] == "INSUFFICIENT"
