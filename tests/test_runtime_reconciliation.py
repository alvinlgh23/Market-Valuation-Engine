"""Exercise the existing last-valid cache boundary with captured provider data."""
import json
from pathlib import Path
import pytest
import research_system

@pytest.mark.parametrize("failure", ["exception", "empty"])
def test_failed_provider_refresh_preserves_captured_sector_snapshot(tmp_path, monkeypatch, failure):
    captured = json.loads((Path(__file__).resolve().parents[1] / "frontend/artifacts/runtime-reconciliation/before-api.json").read_text())
    payload = captured["data"]["modules"]["core_market"]["payload"]
    monkeypatch.setattr(research_system, "CACHE_DIR", tmp_path)
    research_system.save_cache("core-market", payload)
    def provider():
        if failure == "exception":
            raise TimeoutError("Provider refresh timed out")
        return {"sectors": []}
    result = research_system.isolated("core-market", provider, True)
    assert result["state"] == "STALE"
    assert result["error"]
    assert len(result["payload"]["sectors"]) == 34
    assert result["payload"] == payload
    assert research_system.load_cache("core-market") == payload
