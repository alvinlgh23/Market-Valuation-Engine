#!/usr/bin/env python3
"""Test-only configured interpreter shim. Never selected by production defaults."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.environ.get("CHAINSTOX_TEST_MODE") != "1":
    raise SystemExit("Test bridge requires CHAINSTOX_TEST_MODE=1")
if sys.argv[1:] == ["--version"]:
    print("Python 3.14 (deterministic integration harness)")
    raise SystemExit(0)
state = json.loads(Path(os.environ["CHAINSTOX_TEST_STATE"]).read_text())
if state.get("failure"):
    print("ModuleNotFoundError: deterministic missing dependency", file=sys.stderr)
    raise SystemExit(1)
script, action = sys.argv[2:4]
if script == "research_system.py":
    import pandas as pd
    import Valuation_model as market
    import research_system as research
    def history(ticker, period="1y"):
        if ticker not in {"SMH", "SPY"} or state.get("empty"):
            return None
        values = [100.] * 259 + [100. * (1 + (state.get("strength", .42) if ticker == "SMH" else 0))]
        return pd.DataFrame({"Close": values}, index=pd.date_range(end="2026-10-20", periods=260))
    with patch.object(market, "fetch_history", side_effect=history), patch.object(market, "SECTOR_ETFS", {"SMH": "Semiconductors"}), patch.object(market, "compute_macro", return_value={"tnx_level": 4.5, "front_rate_level": 4, "front_rate_ticker": "^FVX", "tnx_observed_at": "2026-10-20", "front_rate_observed_at": "2026-10-19"}), patch.object(market, "compute_macro_fragility", return_value={}), patch.object(market, "compute_macro_catalysts", return_value={}), patch.object(market, "compute_risk_regime_report", return_value={}):
        core = research.build_core_market()
    original = research.isolated
    def isolated(name, loader, refresh):
        return {"state": "STALE" if state.get("stale") else "CACHED", "payload": core, "error": None} if name == "core-market" else original(name, loader, False)
    with patch.object(research, "isolated", side_effect=isolated):
        result = research.build_research_system(False)
    # Remove Compass curve only for the controlled alternative-maturity test.
    world = result["world"]
    world["regions"]["US"]["engine_specific"]["central_bank_compass"]["indicator_values"].pop("yield_curve", None)
    result["market_transmission"] = research.build_market_transmission(world, core, result["engine_states"])
    print(json.dumps(research.json_safe(result)))
elif script == "company_research.py":
    ticker = sys.argv[4].upper() if len(sys.argv) > 4 else "MSFT"
    resolution = {"ticker": ticker, "supported": ticker != "SPY", "research_state": "UNSUPPORTED" if ticker == "SPY" else "AVAILABLE", "reason": "Fund requires portfolio research" if ticker == "SPY" else "Deterministic test security", "company_name": ticker}
    print(json.dumps({"status": "OK", "resolution": resolution, "recent_research": [], "profile": None}))
elif script == "model.py":
    ticker = sys.argv[4].upper()
    reports = json.loads((ROOT / "frontend/lib/fixtures/valuation-research.json").read_text())
    report = reports.get(ticker, reports["MSFT"])
    report["company"]["ticker"] = ticker
    if ticker in {"FAIL", "MISS"}:
        report["validation"] = {"status": "FAILED", "reasons": ["Material FCFF reconciliation discrepancy" if ticker == "FAIL" else "Missing critical cash-flow input"], "checks": {"historical_fcff": {"passed": False, "detail": "Deterministic failure case"}}}
        report["historical_fcff_reconciliation"]["status"] = "FAILED"
        report["scenarios"] = {}
    if ticker == "NOPRICE":
        report["company"]["current_market_price"] = None
        report["reverse_dcf"] = {"status": "NO_MARKET_PRICE"}
    print(json.dumps(report))
else:
    raise SystemExit("Unsupported test action")
