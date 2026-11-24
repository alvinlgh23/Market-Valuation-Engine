"""Audited CHAINSTOX research capability and information-surface registry."""

from __future__ import annotations

from typing import Any


def engine(
    engine_id: str,
    name: str,
    status: str,
    question: str,
    entrypoint: str,
    cli: list[str],
    inputs: list[str],
    sources: list[str],
    outputs: list[str],
    horizons: list[str],
    data_behavior: str,
    json_support: str,
    frontend_before: str,
    frontend_after: str,
    ui_surfaces: list[str],
    intentional_exclusions: list[str] | None = None,
) -> dict[str, Any]:
    return locals()


ENGINE_INVENTORY = [
    engine(
        "market_intelligence", "Market Intelligence System", "ACTIVE / INTEGRATED",
        "What market structure is being created by rates, dollar liquidity, risk appetite, breadth, and capital rotation?",
        "model.py → Valuation_model.run_cli",
        ["python model.py", "python model.py full", "python model.py macro", "python model.py sectors", "python model.py sectors all"],
        ["US 10Y", "US 30Y", "front-rate proxy", "DXY", "USD/JPY", "VIX", "M2", "HYG/IEF", "SPY valuation"],
        ["Yahoo Finance", "FRED M2SL", "official ISM fallback"],
        ["global liquidity", "threshold diagnostics", "macro score", "fragility", "catalysts", "ERP", "preferred environment", "full market interpretation"],
        ["current", "1M", "3M", "6M", "1Y"], "Live fetch with explicit unavailable fallbacks", "Structured Python functions; terminal text; integrated research-system JSON",
        "SUMMARY ONLY", "FULL / progressive", ["Dashboard", "Macro / United States", "Research Priority", "What Changed", "Data Freshness"],
    ),
    engine(
        "sector_rotation", "Sector Rotation and Positioning", "ACTIVE / INTEGRATED",
        "Where is capital rotating, how broad is leadership, and is positioning genuinely extreme?",
        "Valuation_model.compute_sectors / print_sectors_command / print_sector_command",
        ["python model.py sectors", "python model.py sectors all", "python model.py sector semis", "python model.py theme energy"],
        ["sector ETF history", "SPY history", "relative strength", "breakout", "valuation and breadth proxies"],
        ["Yahoo Finance"],
        ["leaderboard", "1M/3M/6M relative strength", "breakout", "sector condition", "narrative structure", "positioning", "candidate companies"],
        ["1M", "3M", "6M", "1Y"], "Live; omitted metrics stay unavailable", "Integrated research-system JSON when live refresh succeeds",
        "SUMMARY ONLY / PLACEHOLDER", "FULL when live; graceful unavailable", ["Dashboard signals", "Rotation module", "Sector research workspace"],
    ),
    engine(
        "risk_regime", "Risk Regime & Defensive Rotation", "ACTIVE / INTEGRATED",
        "Is weakness a healthy rotation, narrow-leadership unwind, broad risk-off move, or liquidity/inflation stress?",
        "risk_regime.py / Valuation_model.compute_risk_regime_report",
        ["python model.py risk-regime", "python model.py regime", "python model.py rotation", "python risk_regime.py"],
        ["SPY/RSP", "momentum proxies", "defensives", "cyclicals", "global equities", "credit", "VIX", "Treasuries", "gold", "USD"],
        ["Yahoo Finance"],
        ["regime", "confidence", "evidence matrix", "conflicts", "interpretation", "invalidation", "sector/company context", "unavailable evidence"],
        ["1D", "1W", "1M", "3M"], "Live; deterministic mock examples are test-only", "Integrated research-system JSON when live refresh succeeds",
        "SUMMARY ONLY", "FULL when live; test examples excluded from current claims", ["Dashboard", "Risk module", "Macro / US market structure"],
    ),
    engine(
        "inflation", "US Inflation Pressure", "ACTIVE / INTEGRATED",
        "Is inflation pressure rising or easing over 1–3M and 3–6M, and through which wage, shelter, services, energy, or goods mechanism?",
        "inflation_pressure.py",
        ["python model.py inflation", "python model.py cpi", "python model.py inflation-pressure", "python model.py inflation-debug"],
        ["27 registered public-data metrics", "freshness", "transformations", "thresholds"],
        ["FRED", "Atlanta Fed", "Zillow Research", "configured official endpoints"],
        ["coverage", "wages", "shelter and market rents", "services", "energy", "goods", "anchors", "1–3M/3–6M synthesis", "Fed tension", "watch conditions", "validation"],
        ["daily", "monthly", "quarterly", "1–3M", "3–6M"], "Live with fresh/stale last-known-good cache and per-series failure", "Native structured report integrated without TypeScript recalculation",
        "PLACEHOLDER", "FULL / progressive", ["Dashboard", "Inflation module", "Macro / United States / Inflation", "Evidence and source"],
    ),
    engine(
        "company_intelligence", "Company Intelligence Report", "ACTIVE / REPORT INTEGRATED",
        "Do fundamentals, valuation, narrative, and price behavior confirm one another?",
        "company_report.py / Valuation_model.print_company_command",
        ["python model.py company PLTR", "python model.py stock NVDA", "python model.py risk NVDA"],
        ["company statements", "price history", "relative strength", "valuation", "security type"],
        ["Yahoo Finance company, statement, and price data"],
        ["security resolution", "revenue", "margin", "FCF", "valuation", "decomposition", "narrative support", "chase risk", "strengthen/weaken conditions", "validation warnings"],
        ["TTM", "annual", "1M", "3M", "6M", "1Y"], "Live with explicit data-quality and non-operating-security routes", "Terminal report; selected facts normalized by Company Economics",
        "PARTIAL", "FULL report preserved; economics facts interactive", ["Company snapshot", "Full Report", "Evidence"],
    ),
    engine(
        "company_economics", "Company Economics", "ACTIVE / INTEGRATED",
        "What structurally drives growth, what constrains it, and how do those economics translate into financial outcomes?",
        "company_economics.py",
        ["python model.py economics PLTR", "python model.py company-economics NVDA --json", "python model.py economics TSM --fixture"],
        ["normalized company snapshot", "valuation report", "archetype registry", "overrides"],
        ["Existing structured financial provider", "deterministic fixtures"],
        ["classification", "growth architecture", "scaling", "constraint diagnosis", "falsification", "financial translation", "valuation review", "market expectations", "economic graph", "evidence ledger", "gaps", "validation"],
        ["TTM", "annual", "forecast assumptions"], "Live or explicit fixture", "Native complete JSON",
        "FULL", "FULL", ["Company snapshot", "Economic Map", "Thesis", "Financials", "Valuation bridge", "Evidence", "Report Mode"],
    ),
    engine(
        "intrinsic_valuation", "Intrinsic Valuation & Reverse DCF", "ACTIVE / PARTIAL UI",
        "What is the scenario value range, what does the market price imply, and do cash-flow identities reconcile?",
        "intrinsic_valuation.py",
        ["python model.py value MSFT", "python model.py valuation CRWD --json", "python model.py dcf MSFT --wacc 0.10 --terminal-growth 0.03"],
        ["financial statements", "shares", "price", "rates", "archetype-specific assumptions", "manual overrides"],
        ["Yahoo Finance", "FRED/rate inputs where configured"],
        ["framework routing", "FCFF reconciliation", "assumptions", "bear/base/bull DCF", "sensitivity", "reverse DCF", "cross-checks", "validation", "data provenance"],
        ["historical TTM/annual", "5–10Y forecast", "terminal"], "Live; JSON; blocks valuation when reconciliation fails", "Native JSON",
        "PARTIAL", "PARTIAL / report preserved; live valuation bridge remains a gap", ["Company Valuation", "Reverse DCF", "Assumption Trace", "Full Report"],
    ),
    engine(
        "central_bank_compass", "Central Bank Compass", "ACTIVE / INTEGRATED",
        "Do macro conditions support easing, holding, or tightening under each central bank's actual framework?",
        "Centralbank-Compass/central-bank-compass/model.py",
        ["--economy US/SG/EZ/JP", "--liquidity", "--allocation", "--backtest", "--narrative", "--energy-shock", "--real-yield", "--dollar-tide", "--treasury-demand", "--gold-drivers", "--motive-check"],
        ["inflation", "labor", "growth", "financial conditions", "FX", "policy rates", "real yields", "energy", "Treasury evidence"],
        ["FRED and normalized cache", "FX/FRED", "ECB/BOJ/MAS/SingStat/PBC/OECD adapters"],
        ["policy blocks", "indicator thresholds and contributions", "US probabilities", "BOJ normalization", "liquidity drivers", "global liquidity", "allocation", "narrative tests", "energy", "real yield", "dollar tide", "Treasury flows", "gold", "backtests"],
        ["current", "3M/6M policy horizons", "historical monthly backtests"], "Live when keys/sources work; normalized offline cache; missing indicators explicit", "Normalized macro-world JSON preserves engine-specific detail",
        "PARTIAL", "FULL for supported country-policy/liquidity blocks; advanced studies report-only", ["Macro World", "Country Policy", "Liquidity", "Central Bank workspace", "Evidence"],
        ["Backtest charts/CSV remain report-only", "Educational allocation remains report-only", "Motive checks stay report-only because hidden intent is not observable"],
    ),
    engine(
        "kospi", "KOSPI Multi-Factor Signal Monitor", "ACTIVE / INTEGRATED",
        "Which market proxies have descriptive candidate relationships with KOSPI returns, and what is the current volatility regime?",
        "KOSPI/KOSPI_Backend_v2.py",
        ["python KOSPI_Backend_v2.py", "python KOSPI_Backend_v2.py --json", "python KOSPI_Backend_v2.py --exports-json", "GET /health", "GET /exports", "POST /sweep"],
        ["KOSPI", "semiconductor leaders", "USD/KRW", "consumer basket", "K-pop agency basket", "optional foreign flows", "exports"],
        ["Yahoo Finance", "FRED", "pykrx", "MOTIR/MSIT", "KOCCA/MCST", "optional Korea Customs"],
        ["factor scores", "correlations", "adjusted Granger p-values", "OLS beta/R²", "wavelet SNR", "observed history", "GARCH volatility", "regime", "ranking", "exports", "source/period notes"],
        ["3M", "6M", "1Y", "2Y", "annual exports", "optional monthly customs"], "Live sweep; annual/mixed-period export fallback; factor failures isolated", "FastAPI and CLI JSON",
        "STRUCTURAL SUMMARY", "FULL when live; explicit fallback", ["Korea brief", "KOSPI workspace", "Factor monitor", "Exports", "Transmission evidence"],
        ["Granger and full-sample wavelet outputs are labeled descriptive, not causal or real-time signals"],
    ),
    engine(
        "macro_world", "Macro World Orchestrator", "ACTIVE / INTEGRATED",
        "What does CHAINSTOX currently know about each supported economy and cross-border mechanism?",
        "macro_world.py",
        ["python model.py macro-world --json", "python model.py macro-world SG --json"],
        ["Compass", "KOSPI", "coverage registry"],
        ["Audited child-engine outputs"],
        ["normalized region profiles", "coverage", "components", "evidence", "watch conditions", "engine-specific payloads", "transmission graph"],
        ["current/cached/structural"], "Cache-first orchestration; per-engine failure isolation", "Native JSON",
        "PARTIAL", "FULL / progressive", ["Macro World Map", "Country brief", "Engine workspace", "Transmission", "Evidence"],
    ),
    engine(
        "private_ai", "Archived Private AI Intelligence", "ARCHIVE / EXCLUDED",
        "Historical private-AI company evidence collection.",
        "archive/private_ai/private_ai_report.py",
        [], ["manually maintained JSON evidence"], ["archived static evidence"],
        ["company comparison report"], ["historical"], "Inactive and unsupported", "Archived JSON",
        "NOT EXPOSED", "NOT APPROPRIATE FOR UI", [],
        ["Explicitly archived; LLM-oriented feature conflicts with the no-new-LLM requirement and is absent from the active CLI"],
    ),
]


INFORMATION_SURFACE_REGISTRY = [
    {"output": "macro.liquidity.thresholds", "surface": "Macro / United States / Liquidity", "status": "interactive"},
    {"output": "macro.fragility.breadth", "surface": "Dashboard / Active Signals + Risk", "status": "interactive when live"},
    {"output": "inflation.metrics.*", "surface": "Inflation / Section workspace / Evidence", "status": "interactive"},
    {"output": "inflation.validation", "surface": "Inflation / Data Coverage", "status": "interactive"},
    {"output": "central_bank.blocks.*", "surface": "Macro / Country / Central Bank", "status": "interactive"},
    {"output": "central_bank.liquidity.drivers", "surface": "Macro / Country / Liquidity", "status": "interactive"},
    {"output": "kospi.results", "surface": "Korea / KOSPI Factors", "status": "interactive when live"},
    {"output": "kospi.volatility", "surface": "Korea / KOSPI Market", "status": "interactive when live"},
    {"output": "kospi.exports", "surface": "Korea / Export Structure", "status": "interactive"},
    {"output": "transmissions.*", "surface": "Macro / Transmission / Edge inspector", "status": "interactive"},
    {"output": "company.constraints", "surface": "Company / Economic Map / Inspector", "status": "interactive"},
    {"output": "company.evidence", "surface": "Company / Evidence / Source", "status": "interactive"},
    {"output": "valuation.reverse_dcf", "surface": "Company / Valuation / Reverse DCF", "status": "partial; full live bridge remaining"},
    {"output": "central_bank.backtests", "surface": "Terminal/CSV report", "status": "report_only"},
    {"output": "central_bank.allocation", "surface": "Terminal/CSV report", "status": "report_only"},
    {"output": "debug.*", "surface": "Not rendered", "status": "debug_only"},
]


COUNTRY_COVERAGE = {
    "US": {"policy": "AVAILABLE", "inflation": "AVAILABLE", "fx": "AVAILABLE", "liquidity": "AVAILABLE", "equity": "PARTIAL", "rates": "AVAILABLE"},
    "JP": {"policy": "PARTIAL", "inflation": "PARTIAL", "fx": "AVAILABLE", "liquidity": "PARTIAL", "equity": "UNAVAILABLE", "rates": "AVAILABLE"},
    "KR": {"policy": "UNAVAILABLE", "inflation": "UNAVAILABLE", "fx": "PARTIAL", "liquidity": "UNAVAILABLE", "equity": "PARTIAL", "rates": "UNAVAILABLE"},
    "EURO_AREA": {"policy": "AVAILABLE", "inflation": "AVAILABLE", "fx": "AVAILABLE", "liquidity": "PARTIAL", "equity": "UNAVAILABLE", "rates": "PARTIAL"},
}


TRANSMISSION_COVERAGE = [
    {"id": "jp-us-yen-carry", "required": ["BOJ stance", "JGB", "JPY", "US yields", "US risk", "VIX", "flow proxy"], "available": ["BOJ stance", "JGB", "JPY", "US financial conditions", "VIX"], "missing": ["direct carry positioning/flow proxy"], "status": "PARTIAL"},
    {"id": "us-jp-rate-fx", "required": ["Fed stance", "US yields", "USD/JPY", "BOJ pressure", "Japan inflation"], "available": ["Fed stance", "US yields", "USD/JPY", "BOJ pressure", "partial Japan inflation"], "missing": ["wages", "inflation expectations"], "status": "SUPPORTED_WITH_GAPS"},
    {"id": "us-eu-rate-fx", "required": ["Fed", "ECB", "US rates", "Euro rates", "EUR/USD", "regional stress"], "available": ["Fed", "ECB", "US rates", "EUR/USD", "sovereign spread proxy"], "missing": ["full euro credit/bank-lending stress"], "status": "SUPPORTED_WITH_GAPS"},
    {"id": "us-kr-dollar-kospi", "required": ["US rates", "USD", "USD/KRW", "KOSPI", "foreign flows", "exports"], "available": ["US rates", "USD context", "annual exports", "live-capable KOSPI/USD-KRW model"], "missing": ["persisted current sweep", "reliable current foreign flows"], "status": "PARTIAL"},
]


def capability_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "engines": ENGINE_INVENTORY,
        "country_coverage": COUNTRY_COVERAGE,
        "information_surfaces": INFORMATION_SURFACE_REGISTRY,
        "transmission_coverage": TRANSMISSION_COVERAGE,
    }
