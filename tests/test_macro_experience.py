from pathlib import Path
from unittest.mock import patch
import json

import research_system
from research_system import build_research_system, coverage_state, yield_return_to_bps


class TestMacroExperience:
    def test_treasury_yield_moves_are_absolute_basis_points(self):
        assert round(yield_return_to_bps(4.5, 0.10), 2) == 40.91
        assert yield_return_to_bps(None, 0.10) is None

    @classmethod
    def setup_class(cls):
        load_cache = research_system.load_cache
        fixture = json.loads((Path(__file__).resolve().parents[1] / "frontend/lib/fixtures/research-system.json").read_text())
        insufficient_core = fixture["modules"]["core_market"]["payload"]
        with patch("research_system.load_cache", side_effect=lambda name: insufficient_core if name == "core-market" else load_cache(name)):
            cls.system = build_research_system(refresh=False)

    def test_market_transmission_has_explicit_coverage_state(self):
        transmission = self.system["market_transmission"]
        assert transmission["coverage"]["coverage_status"] == "PARTIAL"
        assert transmission["coverage"]["source_state"] == "CACHED"
        assert transmission["coverage"]["available_fields"]
        assert transmission["coverage"]["missing_fields"]

    def test_coverage_state_supports_full_partial_stale_and_unavailable(self):
        assert coverage_state(["a", "b"], []) == "FULL"
        assert coverage_state(["a"], ["b"]) == "PARTIAL"
        assert coverage_state([], [], ["b"]) == "STALE"
        assert coverage_state([], ["a", "b"]) == "UNAVAILABLE"

    def test_compass_rates_are_not_lost_when_core_feed_is_missing(self):
        rates = {item["key"]: item for item in self.system["market_transmission"]["rates"]["metrics"]}
        assert rates["us_2y"]["raw_value"] == 4.26
        assert rates["us_10y"]["raw_value"] == 4.63
        assert rates["us_2y"]["source_state"] == "CACHED"
        assert "US 30Y current yield" in self.system["market_transmission"]["rates"]["missing_fields"]

    def test_risk_gate_is_preserved_as_research_state(self):
        risk = self.system["market_transmission"]["risk"]
        assert risk["coverage_status"] == "INSUFFICIENT"
        assert risk["state"] == "INSUFFICIENT EVIDENCE"
        assert risk["coverage"] == 0
        assert "Cap-weight market" in risk["missing_fields"]

    def test_country_briefs_have_distinct_coverage(self):
        regions = self.system["world"]["regions"]
        assert regions["US"]["availability"] == "AVAILABLE"
        for region_id in ("JP", "KR", "SG", "EURO_AREA"):
            assert regions[region_id]["availability"] == "PARTIAL"
        assert regions["US"]["confidence"] != regions["SG"]["confidence"]

    def test_neer_cache_maps_history_and_all_components(self):
        neer = self.system["modules"]["neer"]["payload"]
        assert self.system["modules"]["neer"]["state"] == "CACHED"
        history = neer["history"]
        # The cache grows with every refresh, so assert structure rather than a fixed length.
        assert len(history) >= 250
        assert all({"date", "index", "center", "upper", "lower", "deviation_pct"} <= set(row) for row in history)
        assert all(earlier["date"] < later["date"] for earlier, later in zip(history, history[1:]))
        assert history[-1]["date"] == neer["as_of"]
        assert len(neer["fx_components"]) == 12
        assert all(isinstance(item["weight"], (int, float)) for item in neer["fx_components"])
        assert all(isinstance(item["contribution_63d_pct"], (int, float)) for item in neer["fx_components"])

    def test_kospi_cache_maps_factors_and_garch(self):
        kospi = self.system["modules"]["kospi"]["payload"]["sweep"]
        assert self.system["modules"]["kospi"]["state"] == "CACHED"
        assert len(kospi["results"]) == 5
        assert sum(int(item["detail"].get("obs") or 0) > 0 for item in kospi["results"]) == 4
        assert isinstance(kospi["volatility"]["current_vol"], (int, float))
        assert isinstance(kospi["volatility"]["avg_vol"], (int, float))

    def test_transmission_states_separate_structure_from_current_state(self):
        edges = {item["id"]: item for item in self.system["world"]["transmissions"]}
        assert edges["jp-us-yen-carry"]["structural_state"]
        # The fixture's core feed has no USD/JPY or VIX, so the single carry definition is INSUFFICIENT.
        assert edges["jp-us-yen-carry"]["current_state"] == "INSUFFICIENT"
        assert edges["us-kr-dollar-kospi"]["current_state"] == "WATCH"
        assert edges["us-sg-dollar-neer"]["current_state"] == "WATCH"

    def test_overview_no_longer_renders_generic_unavailable_grid(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "frontend/components/research/ObjectResearchSurfaces.tsx").read_text()
        overview = (root / "frontend/components/macro/MacroOverviewSurface.tsx").read_text()
        assert "<MacroOverviewSurface system={system}" in source
        assert "<RecordGrid record={macro} limit={12}" not in source
        assert "macro-transmission-summary" in overview
