"""Cache-aware research context and JSON bridge for the CHAINSTOX frontend."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from datetime import date, datetime
from pathlib import Path
import subprocess
import sys
import math
from typing import Any, Callable

from macro_world import apply_coverage, build_world
from research_capabilities import capability_payload
from signal_history import record_module
from environment import CARRY_EDGE_STATE, build_environment, fetch_boj_schedule, fetch_cftc_jpy
from sector_flow import all_sector_flow


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / ".cache" / "research"
FRONTEND_FIXTURE = ROOT / "frontend" / "lib" / "fixtures" / "research-system.json"
ENGINE_PYTHON = os.environ.get("CHAINSTOX_PYTHON_EXECUTABLE") or os.environ.get("CHAINSTOX_ENGINE_PYTHON") or sys.executable


def yield_return_to_bps(current_yield_percent: Any, fractional_return: Any) -> float | None:
    """Convert a provider price-style yield return into an absolute basis-point move."""
    if not isinstance(current_yield_percent, (int, float)) or not isinstance(fractional_return, (int, float)):
        return None
    if not math.isfinite(current_yield_percent) or not math.isfinite(fractional_return) or fractional_return <= -1:
        return None
    prior_yield = float(current_yield_percent) / (1 + float(fractional_return))
    return (float(current_yield_percent) - prior_yield) * 100


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
        return None
    return value


def cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


def save_cache(name: str, payload: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(name).write_text(json.dumps(json_safe(payload), indent=2) + "\n")


def load_cache(name: str) -> Any | None:
    path = cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def isolated(name: str, loader: Callable[[], Any], refresh: bool) -> dict[str, Any]:
    if refresh:
        try:
            payload = json_safe(loader())
            if name == "core-market" and not payload.get("sectors"):
                cached = load_cache(name)
                if cached and cached.get("sectors"):
                    return {"state": "STALE", "payload": cached, "error": "Refresh returned no sector measurements; preserving last-valid observations."}
            save_cache(name, payload)
            # Checklist 2.1: append the fresh observations to the signal history.
            history = record_module(name, payload, "LIVE")
            return {"state": "LIVE", "payload": payload, "error": None, "history": history}
        except Exception as exc:
            cached = load_cache(name)
            if cached is not None:
                return {"state": "STALE", "payload": cached, "error": f"{type(exc).__name__}: {exc}"}
            return {"state": "UNAVAILABLE", "payload": None, "error": f"{type(exc).__name__}: {exc}"}
    cached = load_cache(name)
    return {"state": "CACHED" if cached is not None else "UNAVAILABLE", "payload": cached, "error": None if cached is not None else "No last-valid research cache."}


def refresh_market(today: date | None = None, backup_dir: Path | None = None) -> dict[str, Any]:
    """Daily market prices only (owner-approved 2026-11-27): re-download the core-market module - sector and theme
    ETFs, Treasury yields, the dollar, VIX and credit spreads - and nothing else (inflation, KOSPI and the macro
    series stay cache-first). The day's first refresh keeps a copy of the previous snapshot; a refresh that returns
    no sector rows, or fails, keeps the last valid snapshot (see `isolated`)."""
    today = today or date.today()
    backup_dir = backup_dir or ROOT / ".cache" / "backups"
    previous = cache_path("core-market")
    if previous.exists():
        backup = backup_dir / f"research-core-market-{today.isoformat()}.json"
        if not backup.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(previous.read_bytes())
    result = isolated("core-market", build_core_market, refresh=True)
    payload = result.get("payload") or {}
    dates = sorted({str(row.get("as_of")) for row in payload.get("sectors") or [] if row.get("as_of")})
    # Korea's overnight call rate (monthly, FRED) rides along; a failure keeps the cached file.
    try:
        from macro_world import refresh_korea_call_rate
        korea_rate = refresh_korea_call_rate()
    except Exception as exc:  # noqa: BLE001 - never blocks the market refresh
        korea_rate = {"state": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
    return {"state": result["state"], "error": result["error"], "sector_rows": len(payload.get("sectors") or []),
            "as_of": dates[-1] if dates else None, "korea_call_rate": korea_rate}


def build_inflation() -> dict[str, Any]:
    import inflation_pressure
    return inflation_pressure.build_report(inflation_pressure.collect_inflation_data())


def build_core_market() -> dict[str, Any]:
    import Valuation_model as market
    with contextlib.redirect_stdout(io.StringIO()):
        macro = market.compute_macro()
        fragility = market.compute_macro_fragility(macro)
        catalysts = market.compute_macro_catalysts(macro)
        risk = market.compute_risk_regime_report()
        sectors = market.compute_sectors()
    macro_inputs = [
        macro.get(key)
        for key in ("tnx_level", "tyx_level", "dxy_level", "usdjpy_level", "vix_level", "m2_level", "hyg_ief")
    ]
    available_macro = sum(value is not None for value in macro_inputs)
    risk_coverage = float(risk.get("coverage") or 0.0)
    quality = {
        "state": "AVAILABLE" if available_macro >= 4 and risk_coverage >= 0.5 and sectors else "INSUFFICIENT",
        "available_macro_inputs": available_macro,
        "total_macro_inputs": len(macro_inputs),
        "risk_coverage": risk_coverage,
        "sector_rows": len(sectors or []),
        "rule": "Do not publish a regime label unless cross-asset coverage is at least 50%, four core macro inputs exist, and sector rankings are populated.",
    }
    return {
        "macro": macro,
        "fragility": fragility,
        "catalysts": catalysts,
        "risk": risk,
        "sectors": sectors,
        "data_quality": quality,
        "provider_diagnostics": market.market_provider_diagnostics(),
    }


def subprocess_json(command: list[str], cwd: Path, timeout: int = 120) -> Any:
    environment = dict(os.environ)
    environment.setdefault("MPLCONFIGDIR", "/private/tmp/chainstox-matplotlib")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False, env=environment)
    if result.returncode:
        message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else f"exit {result.returncode}"
        raise RuntimeError(message)
    output = result.stdout.strip()
    # Some third-party market libraries print an authentication/status notice before
    # the engine's JSON. Keep the engine CLI intact while making the bridge tolerant
    # of that non-payload preamble.
    starts = [position for position in (output.find("{"), output.find("[")) if position >= 0]
    if not starts:
        raise RuntimeError("Engine returned no JSON payload.")
    return json.loads(output[min(starts):])




def build_kospi() -> dict[str, Any]:
    sweep = subprocess_json([ENGINE_PYTHON, "-B", "KOSPI_Backend_v2.py", "--json"], ROOT / "KOSPI")
    exports = subprocess_json([ENGINE_PYTHON, "-B", "KOSPI_Backend_v2.py", "--exports-json"], ROOT / "KOSPI")
    return {"sweep": sweep, "exports": exports}


def company_research_index() -> list[dict[str, Any]]:
    rows = []
    cache_dir = ROOT / ".cache" / "company_economics"
    for path in cache_dir.glob("*.json"):
        if path.name == "index.json":
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        raw = payload.get("company_economics", {})
        company = raw.get("company", {})
        classification = raw.get("classification", {})
        constraint = raw.get("constraints", {}).get("primary_constraint", {})
        growth = raw.get("growth_sustainability", {})
        scaling = raw.get("scaling_economics", {})
        market = raw.get("market_expectations_comparison", {})
        metadata = payload.get("cache_metadata", {})
        rows.append({
            "ticker": company.get("ticker"),
            "name": company.get("name"),
            "as_of": company.get("as_of"),
            "last_analyzed": metadata.get("last_analyzed") or metadata.get("as_of"),
            "research_state": metadata.get("research_state", "AVAILABLE"),
            "archetype": classification.get("primary_archetype"),
            "classification_confidence": classification.get("classification_confidence"),
            "growth_direction": growth.get("constraint_direction"),
            "growth_confidence": growth.get("confidence"),
            "constraint": constraint.get("constraint"),
            "constraint_state": constraint.get("direction"),
            "scaling": scaling.get("interpretation"),
            "valuation_state": market.get("state"),
            "valuation_reason": market.get("reason"),
            "validation": raw.get("validation", {}).get("status"),
        })
    return sorted(rows, key=lambda item: item.get("last_analyzed") or "", reverse=True)


def inflation_watch_conditions(report: dict[str, Any] | None) -> list[dict[str, str]]:
    if not report:
        return []
    metrics = report.get("metrics", {})
    conditions = [
        ("Services persistence", "Services below 3.0% YoY on a sustained basis", metrics.get("services", {}).get("current")),
        ("Market-rent reacceleration", "Zillow rent growth above 4.0% YoY", metrics.get("zillow", {}).get("current")),
        ("Energy shock", "WTI holds above $90/bbl", metrics.get("wti", {}).get("current")),
        ("Producer pipeline", "PPI above 3.0% with positive momentum", metrics.get("ppi", {}).get("current")),
        ("Core PCE normalization", "Core PCE below 2.5% and falling", metrics.get("core_pce", {}).get("current")),
    ]
    return [
        {"module": "Inflation", "label": label, "threshold": threshold, "current": "Unavailable" if current is None else f"{current:.2f}", "state": "WATCH" if current is not None else "INSUFFICIENT", "href": "/macro/inflation"}
        for label, threshold, current in conditions
    ]


def first_evidence(profile: dict[str, Any], pattern: str) -> dict[str, Any] | None:
    pattern = pattern.lower()
    return next((item for item in profile.get("evidence", []) if pattern in item.get("label", "").lower()), None)


def typed_metric(
    key: str,
    label: str,
    raw_value: Any,
    unit: str,
    period: str | None,
    source: str,
    source_state: str,
    confidence: str = "MODERATE",
) -> dict[str, Any] | None:
    """Preserve numeric macro observations without parsing display prose."""
    if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
        return None
    value = float(raw_value)
    if not math.isfinite(value):
        return None
    if unit == "%":
        formatted = f"{value:.2f}%"
    elif unit in {"% YoY", "% 3M", "pp"}:
        formatted = f"{value:+.2f}{'%' if unit.startswith('%') else ' pp'}"
    elif unit == "score / 100":
        formatted = f"{value:.1f}"
    elif unit == "bp 3M":
        formatted = f"{value:+.2f} bp"
    elif unit == "USD billions":
        formatted = f"${value:,.1f}bn"
    else:
        formatted = f"{value:,.2f}"
    normalized_state = str(source_state or "UNKNOWN").upper()
    source_status = {
        "LIVE": "OBSERVED_LIVE",
        "CACHED": "OBSERVED_CACHED",
        "STALE": "OBSERVED_STALE",
    }.get(normalized_state, "HISTORICAL_REPORTED" if period else "OBSERVED_CACHED")
    return {
        "key": key,
        "label": label,
        "raw_value": value,
        "formatted_value": formatted,
        "unit": unit,
        "date": period,
        "source": source,
        "source_state": source_state,
        "confidence": confidence,
        "provider_status": "OK",
        "source_status": source_status,
        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observation_date": period,
        "validation_status": "VALID",
        "staleness_status": "STALE" if normalized_state == "STALE" else "CURRENT" if normalized_state == "LIVE" else "UNKNOWN",
        "limitation": "Observation date is unavailable from the upstream module." if not period else None,
    }


def coverage_state(available: list[str], missing: list[str], stale: list[str] | None = None) -> str:
    stale = stale or []
    if stale and not available:
        return "STALE"
    if available and not missing and not stale:
        return "FULL"
    if available:
        return "PARTIAL"
    return "UNAVAILABLE"


def build_market_transmission(
    world: dict[str, Any],
    core: dict[str, Any] | None,
    states: dict[str, str],
) -> dict[str, Any]:
    """Normalize existing market evidence for coverage-aware presentation.

    This is an adapter only. It does not change Compass, liquidity, risk, FX,
    rates, or transmission calculations.
    """
    core = core or {}
    macro = core.get("macro") or {}
    risk = core.get("risk") or {}
    us = world["regions"]["US"]
    jp = world["regions"]["JP"]
    euro = world["regions"]["EURO_AREA"]
    compass = us.get("engine_specific", {}).get("central_bank_compass", {})
    indicators = compass.get("indicator_values", {})
    compass_as_of = compass.get("latest") or us.get("as_of")
    source_state = world.get("data_state", "CACHED")

    def prefer(core_key: str, compass_key: str) -> tuple[Any, str, str, str | None]:
        if isinstance(macro.get(core_key), (int, float)):
            observed = {"tnx_level": "tnx_observed_at", "front_rate_level": "front_rate_observed_at"}.get(core_key)
            return macro[core_key], "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN"), macro.get(observed) if observed else None
        return indicators.get(compass_key), "Central Bank Compass", source_state, compass_as_of

    from treasury_semantics import treasury_curve, MATURITIES
    short_ticker = macro.get("front_rate_ticker")
    two_year_value, two_year_source, two_year_state, two_year_date = prefer("front_rate_level" if short_ticker == "2YY=F" else "_no_2y", "two_year_yield")
    ten_year_value, ten_year_source, ten_year_state, ten_year_date = prefer("tnx_level", "ten_year_yield")
    thirty_year_value = macro.get("tyx_level")
    curve = treasury_curve(macro.get("tnx_level"), macro.get("front_rate_level"), short_ticker,
                           macro.get("tnx_observed_at"), macro.get("front_rate_observed_at"), states.get("core_market", "UNKNOWN"))
    # Prefer the genuine Compass 10Y–2Y series over an alternative-maturity proxy.
    if (curve["value"] is None or curve["fallback"]) and isinstance(indicators.get("yield_curve"), (int, float)):
        curve = {**treasury_curve(None, None, "2YY=F", compass_as_of, compass_as_of, source_state),
                 "value": indicators["yield_curve"], "source": "Central Bank Compass"}
    curve_value, curve_source, curve_source_state, curve_date = curve["value"], curve["source"], curve["source_state"], curve["observation_timestamp"]
    curve_metric = typed_metric(f"us_10y_{str(curve['short_maturity']).lower()}", curve["label"], curve_value, "pp", curve_date, curve_source, curve_source_state)
    if curve_metric:
        curve_metric["maturity_metadata"] = curve
        curve_metric["note"] = f"{'Alternative maturity proxy. ' if curve['fallback'] else ''}Period alignment: {curve['period_alignment']}."
    liquidity = compass.get("liquidity", {})
    real_yield_driver = next((item for item in liquidity.get("drivers", []) if "real-yield" in str(item.get("name", "")).lower()), {})

    rate_metrics = [item for item in [
        typed_metric("us_2y", "US 2Y", two_year_value, "%", two_year_date, two_year_source, two_year_state),
        typed_metric("us_10y", "US 10Y", ten_year_value, "%", ten_year_date, ten_year_source, ten_year_state),
        typed_metric("us_30y", "US 30Y", thirty_year_value, "%", macro.get("tyx_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("us_10y_real", "US 10Y real yield", real_yield_driver.get("value"), "%", compass_as_of, "Central Bank Compass / Liquidity", source_state),
        curve_metric,
    ] if item]
    rate_moves = [item for item in [
        typed_metric(f"us_{MATURITIES.get(short_ticker, 'unknown').lower()}_3m", f"US {MATURITIES.get(short_ticker, 'unknown maturity')}", yield_return_to_bps(macro.get("front_rate_level"), macro.get("front_rate_3m")) if short_ticker in MATURITIES else None, "bp 3M", macro.get("front_rate_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("us_10y_3m", "US 10Y", yield_return_to_bps(macro.get("tnx_level"), macro.get("tnx_3m")), "bp 3M", macro.get("tnx_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("us_30y_3m", "US 30Y", yield_return_to_bps(thirty_year_value, macro.get("tyx_3m")), "bp 3M", None, "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
    ] if item]
    rate_missing = [
        label for key, label in (
            ("us_30y", "US 30Y current yield"),
            ("us_2y_3m", "US 2Y 3M move"),
            ("us_10y_3m", "US 10Y 3M move"),
            ("us_30y_3m", "US 30Y 3M move"),
            ("rates_history", "Treasury historical series"),
        ) if key not in {item["key"] for item in rate_metrics + rate_moves}
    ]

    regional_fx = [
        ("usd_jpy_yoy", "USD/JPY", jp, "usd_jpy_change_yoy"),
        ("eur_usd_yoy", "EUR/USD", euro, "currency_change_yoy"),
    ]
    fx_moves = []
    for key, label, region, indicator_key in regional_fx:
        regional_compass = region.get("engine_specific", {}).get("central_bank_compass", {})
        fx_metric = typed_metric(
            key, label, regional_compass.get("indicator_values", {}).get(indicator_key), "% YoY",
            regional_compass.get("latest") or region.get("as_of"), "Central Bank Compass", source_state,
            region.get("confidence", "MODERATE"),
        )
        if fx_metric:
            fx_moves.append(fx_metric)
    fx_metrics = [item for item in [
        typed_metric("dxy_level", "DXY", macro.get("dxy_level"), "index", macro.get("dxy_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("usd_jpy_level", "USD/JPY", macro.get("usdjpy_level"), "FX rate", macro.get("usdjpy_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("dxy_3m", "DXY", None if macro.get("dxy_3m") is None else macro["dxy_3m"] * 100, "% 3M", macro.get("dxy_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
        typed_metric("usd_jpy_3m", "USD/JPY", None if macro.get("usdjpy_3m") is None else macro["usdjpy_3m"] * 100, "% 3M", macro.get("usdjpy_observed_at"), "Core Market / Yahoo Finance", states.get("core_market", "UNKNOWN")),
    ] if item]
    for key, pair in (macro.get("fx_pairs") or {}).items():
        if not isinstance(pair, dict):
            continue
        for metric in (typed_metric(f"{key}_level", pair.get("label"), pair.get("level"), "FX rate", pair.get("observed_at"), f"Yahoo Finance ({pair.get('symbol')})", states.get("core_market", "UNKNOWN")),
                       typed_metric(f"{key}_3m", pair.get("label"), None if pair.get("change_3m") is None else pair["change_3m"] * 100, "% 3M", pair.get("observed_at"), f"Yahoo Finance ({pair.get('symbol')})", states.get("core_market", "UNKNOWN"))):
            if metric:
                fx_metrics.append(metric)
    fx_missing = [label for key, label in (
        ("dxy_level", "DXY current level"),
        ("dxy_3m", "DXY 3M move"),
        ("usd_jpy_level", "USD/JPY current level"),
        ("usd_jpy_3m", "USD/JPY 3M move"),
        ("fx_history", "Comparable FX historical series"),
    ) if key not in {item["key"] for item in fx_metrics}]

    liquidity_drivers = [
        {
            "key": str(item.get("name", "driver")).lower().replace(" ", "_"),
            "label": item.get("name"),
            "raw_value": item.get("value"),
            "formatted_value": "Unavailable" if item.get("value") is None else str(item.get("value")),
            "unit": item.get("value_kind"),
            "state": item.get("classification"),
            "contribution": item.get("score_effect"),
            "explanation": item.get("explanation"),
            "thresholds": item.get("thresholds", []),
            "date": compass_as_of,
            "source": "Central Bank Compass / Liquidity",
            "source_state": source_state,
        }
        for item in liquidity.get("drivers", [])
    ]
    available_liquidity = [item for item in liquidity_drivers if item["raw_value"] is not None]
    missing_liquidity = [str(item["label"]) for item in liquidity_drivers if item["raw_value"] is None]
    risk_missing = [str(row[0]) for row in risk.get("evidence", []) if len(row) > 1 and str(row[1]).lower() == "unavailable"]

    rates_available = [item["key"] for item in rate_metrics + rate_moves]
    fx_available = [item["key"] for item in fx_metrics + fx_moves]
    overall_available = rates_available + fx_available + [f"liquidity.{item['key']}" for item in available_liquidity]
    overall_missing = rate_missing + fx_missing + missing_liquidity + risk_missing
    curve_points = [item for item in rate_metrics if item["key"] in {"us_2y", "us_10y", "us_30y"}]
    curve_dates = {item["date"] for item in curve_points}
    if len(curve_dates) != 1 or None in curve_dates:
        curve_points = []
        rate_missing.append("Same-date Treasury curve (individual dated observations remain available)")
    return {
        "coverage": {
            "coverage_status": coverage_state(overall_available, overall_missing),
            "available_fields": overall_available,
            "missing_fields": overall_missing,
            "stale_fields": [],
            "last_valid_as_of": compass_as_of,
            "source_state": source_state,
            "reason": "The live cross-market feed did not pass coverage, so current regional Compass evidence and last-valid engine caches are shown separately from missing market history.",
        },
        "rates": {
            "coverage_status": coverage_state(rates_available, rate_missing),
            "metrics": rate_metrics,
            "current_curve": curve_points,
            "moves": rate_moves,
            "history": [],
            "missing_fields": rate_missing,
            "last_valid_as_of": compass_as_of,
            "source_state": source_state,
        },
        "fx": {
            "coverage_status": coverage_state(fx_available, fx_missing),
            "metrics": fx_metrics,
            "moves": fx_moves,
            "history": [],
            "missing_fields": fx_missing,
            "last_valid_as_of": max(filter(None, (jp.get("as_of"), euro.get("as_of")))),
            "source_state": source_state,
        },
        "liquidity": {
            "coverage_status": "FULL" if liquidity.get("available_drivers") == liquidity.get("expected_drivers") else "PARTIAL" if available_liquidity else "UNAVAILABLE",
            "state": liquidity.get("classification", "UNAVAILABLE"),
            "score": liquidity.get("score"),
            "available_drivers": liquidity.get("available_drivers", 0),
            "expected_drivers": liquidity.get("expected_drivers", 0),
            "drivers": liquidity_drivers,
            "missing_fields": missing_liquidity,
            "last_valid_as_of": compass_as_of,
            "source_state": source_state,
        },
        "risk": {
            "coverage_status": "INSUFFICIENT" if float(risk.get("coverage") or 0) < 0.5 else "FULL",
            "state": "INSUFFICIENT EVIDENCE" if float(risk.get("coverage") or 0) < 0.5 else risk.get("regime"),
            "confidence": "WITHHELD" if float(risk.get("coverage") or 0) < 0.5 else risk.get("confidence"),
            "coverage": float(risk.get("coverage") or 0),
            "missing_fields": risk_missing or list(risk.get("unavailable", [])),
            "summary": risk.get("summary", "Cross-asset risk inputs are unavailable."),
            "source_state": states.get("core_market", "UNAVAILABLE"),
        },
    }


def dashboard_from(world: dict[str, Any], inflation: dict[str, Any] | None, core: dict[str, Any] | None, states: dict[str, str], companies: list[dict[str, Any]]) -> dict[str, Any]:
    regions = world["regions"]
    us, jp, kr, euro = (regions[key] for key in ("US", "JP", "KR", "EURO_AREA"))
    core_macro = (core or {}).get("macro") or {}
    risk = (core or {}).get("risk") or {}
    sectors = (core or {}).get("sectors") or []
    core_quality = (core or {}).get("data_quality") or {}
    core_valid = core_quality.get("state") == "AVAILABLE"
    macro_state = risk.get("regime") if core_valid else us["brief"].split(".")[0]
    primary_tension = "US policy pressure, Japan FX pressure, and uneven regional growth require separate investigation."
    if core_macro.get("tyx_level") is not None:
        primary_tension = f"US 30Y yield is {core_macro['tyx_level']:.2f}% versus the 5.00% structural watch threshold."

    reads = [
        {"id": "us-policy", "label": "US Policy", "value": us["components"][0]["state"], "context": us["brief"], "state": us["confidence"], "href": "/macro/world?region=US&detail=policy"},
        {"id": "inflation", "label": "US Inflation 1–3M", "value": inflation.get("near_term", "Unavailable") if inflation else "Unavailable", "context": inflation.get("horizon_reason", "No current inflation report.") if inflation else "No current inflation report.", "state": "PARTIAL" if inflation and inflation.get("provisional") else "AVAILABLE" if inflation else "UNAVAILABLE", "href": "/macro/inflation"},
        {"id": "risk", "label": "Risk Regime", "value": risk.get("regime", "Unavailable") if core_valid else "Insufficient evidence", "context": risk.get("summary", "Live cross-asset risk context is not cached."), "state": states["core_market"] if core_valid else "INSUFFICIENT", "href": "/macro/risk"},
        {"id": "liquidity", "label": "US Liquidity", "value": next((item["state"] for item in us["components"] if item["id"] == "liquidity"), "Unavailable"), "context": next((item["summary"] for item in us["components"] if item["id"] == "liquidity"), "No liquidity block."), "state": us["freshness"], "href": "/macro/liquidity"},
        {"id": "japan", "label": "Japan / BOJ", "value": jp["components"][0]["state"], "context": jp["brief"], "state": jp["confidence"], "href": "/macro/world?region=JP&detail=policy"},
        {"id": "breadth", "label": "Sector Leadership", "value": sectors[0]["name"] if sectors and core_valid else "Insufficient evidence", "context": f"{sectors[0]['ticker']} leads this engine-ranked snapshot; observation {sectors[0].get('as_of') or 'date unavailable'}; source state {states['core_market']}. Relative strength does not establish crowding or breadth." if sectors and core_valid else "A sector ranking is withheld until the source coverage checks pass.", "state": states["core_market"] if core_valid else "INSUFFICIENT", "href": "/markets"},
    ]

    changed = []
    for label, profile, pattern in (("USD/JPY", jp, "USD/JPY YoY"), ("EUR/USD", euro, "EUR/USD YoY"), ("US credit", us, "Credit Spread Change")):
        evidence = first_evidence(profile, pattern)
        if evidence:
            changed.append({"label": label, "value": evidence["value"], "period": evidence["period"], "interpretation": evidence["classification"], "href": f"/macro/world?region={profile['id']}&detail=currency"})
    if core_macro:
        for label, key, href in (("US 30Y", "tyx_3m", "/macro/rates"), ("DXY", "dxy_3m", "/macro/fx")):
            value = core_macro.get(key)
            if key == "tyx_3m":
                value = yield_return_to_bps(core_macro.get("tyx_level"), value)
            if value is not None:
                formatted = f"{value:+.2f} bp 3M" if key == "tyx_3m" else f"{value * 100:+.2f}% 3M"
                changed.insert(0, {"label": label, "value": formatted, "period": "3-month change", "interpretation": "Observed market change", "href": href})

    priorities = []
    for profile in (us, jp, euro, kr):
        for watch in profile.get("watch_conditions", []):
            if watch["state"] in {"WATCH", "TRIGGERED"}:
                priorities.append({"rank": len(priorities) + 1, "module": profile["name"], **watch, "href": f"/macro/world?region={profile['id']}"})
            if len(priorities) >= 5:
                break
        if len(priorities) >= 5:
            break
    if inflation:
        priorities.insert(1, {"rank": 2, "module": "US Inflation", "label": f"1–3M pressure: {inflation['near_term']}", "threshold": "Open the five-driver synthesis", "current": f"{inflation['available']}/{inflation['total']} metrics", "state": "WATCH", "href": "/macro/inflation"})
    for index, item in enumerate(priorities[:5], 1):
        item["rank"] = index

    signals = [
        {"module": "United States", "signal": us["components"][0]["state"], "confidence": us["confidence"], "why": us["brief"], "href": "/macro/world?region=US"},
        {"module": "Japan", "signal": jp["components"][0]["state"], "confidence": jp["confidence"], "why": jp["brief"], "href": "/macro/world?region=JP"},
        {"module": "Euro Area", "signal": euro["components"][0]["state"], "confidence": euro["confidence"], "why": euro["brief"], "href": "/macro/world?region=EURO_AREA"},
        {"module": "Inflation", "signal": inflation.get("medium_term", "Unavailable") if inflation else "Unavailable", "confidence": "PROVISIONAL" if inflation and inflation.get("provisional") else "MODERATE", "why": inflation.get("horizon_reason", "No cached report") if inflation else "No cached report", "href": "/macro/inflation"},
    ]
    if risk and core_valid:
        signals.append({"module": "Risk", "signal": risk.get("regime"), "confidence": risk.get("confidence"), "why": risk.get("summary"), "href": "/macro/risk"})
    elif risk:
        signals.append({"module": "Risk", "signal": "Insufficient evidence", "confidence": "WITHHELD", "why": risk.get("summary"), "href": "/macro/risk"})

    freshness = [
        {"module": "Macro World / Compass", "state": world["data_state"], "as_of": max(filter(None, (item.get("as_of") for item in regions.values())))},
        {"module": "US Inflation", "state": states["inflation"], "as_of": inflation.get("latest_source") if inflation else None},
        {"module": "Market / Risk / Rotation", "state": states["core_market"], "as_of": max((row.get("as_of") or "" for row in sectors), default=None), "context": "Latest sector observation date; not the response-generation time or a date for every macro input."},
        {"module": "Korea KOSPI", "state": states["kospi"], "as_of": kr.get("as_of")},
        {"module": "Company Economics", "state": "CACHED" if companies else "NOT_ANALYZED", "as_of": max((item.get("last_analyzed") or "" for item in companies), default=None)},
    ]
    watches = inflation_watch_conditions(inflation)
    for profile in (jp, euro, kr):
        for watch in profile.get("watch_conditions", [])[:2]:
            watches.append({"module": profile["name"], **watch, "href": f"/macro/world?region={profile['id']}"})
    return {
        "headline": {"state": macro_state, "summary": primary_tension, "as_of": datetime.now().astimezone().isoformat(timespec="seconds")},
        "reads": reads,
        "what_changed": changed[:6],
        "signals": signals,
        "research_priority": priorities[:5],
        "global_regions": [{"id": item["id"], "name": item["name"], "state": item["components"][0]["state"], "confidence": item["confidence"], "availability": item["availability"], "href": f"/macro/world?region={item['id']}"} for item in regions.values()],
        "companies": companies,
        "valuation_flags": [{"ticker": item["ticker"], "state": item["valuation_state"], "reason": item["valuation_reason"], "href": f"/company/{item['ticker']}?view=valuation"} for item in companies],
        "freshness": freshness,
        "watch_conditions": watches,
    }


def with_two_liquidity_scores(dashboard: dict[str, Any], environment: dict[str, Any]) -> dict[str, Any]:
    """Checklist 3.5: wherever liquidity is shown, show policy and market liquidity together."""
    readings = environment["factors"]["liquidity"]["readings"]
    policy, market = readings["policy_liquidity"], readings["market_liquidity"]
    def score(item):
        return "unavailable" if item["score"] is None else f"{item['score']:.0f}/100"
    for read in dashboard.get("reads", []):
        if read.get("id") == "liquidity":
            read["value"] = f"Policy {policy['label'] or 'unavailable'} · Market {market['label'] or 'unavailable'}"
            read["context"] = (f"{policy['name']}: {policy['label'] or 'unavailable'}, {score(policy)}. "
                               f"{market['name']}: {market['label'] or 'unavailable'}, {score(market)}."
                               + (" The two disagree and are not merged." if readings.get("relation") in {"DIFFERENT", "OPPOSITE"} else ""))
            read["liquidity_relation"] = readings.get("relation")
    return dashboard


def kospi_edge_summary(kospi: dict[str, Any]) -> str:
    """Edge summary written from the current KOSPI sweep rather than a fixed sentence."""
    sweep = kospi.get("sweep") or {}
    factors = {item.get("key"): item for item in sweep.get("results") or []}
    macro, flow, tech = factors.get("macro") or {}, factors.get("foreign_flow") or {}, factors.get("tech") or {}
    parts = [f"KOSPI sweep {str(sweep.get('timestamp') or 'date unavailable')[:10]}"]
    if macro:
        parts.append(f"USD/KRW factor {macro.get('strength', 'unclassified')} (corr {macro.get('corr', 0):+.2f}, adjusted p {macro.get('pval', 1):.2f})")
    if tech:
        parts.append(f"semiconductor factor {tech.get('strength', 'unclassified')} (corr {tech.get('corr', 0):+.2f})")
    flow_obs = int((flow.get("detail") or {}).get("obs") or 0)
    parts.append("foreign-flow series unavailable" if not flow_obs else f"foreign-flow factor {flow.get('strength', 'unclassified')}")
    return "; ".join(parts) + "."


def build_research_system(refresh: bool = False) -> dict[str, Any]:
    world = build_world()
    inflation_result = isolated("inflation", build_inflation, refresh=refresh)
    core_result = isolated("core-market", build_core_market, refresh=refresh)
    kospi_result = isolated("kospi", build_kospi, refresh=refresh)
    if core_result["state"] != "STALE" and core_result["payload"] and core_result["payload"].get("data_quality", {}).get("state") != "AVAILABLE":
        core_result["state"] = "INSUFFICIENT"
    companies = company_research_index()
    states = {
        "inflation": inflation_result["state"],
        "core_market": core_result["state"],
        "kospi": kospi_result["state"],
    }
    if kospi_result["payload"]:
        kr = world["regions"]["KR"]
        kospi = kospi_result["payload"]
        kr["engine_specific"]["kospi_live"] = kospi
        sweep = kospi.get("sweep", {})
        interpretation = sweep.get("interpretation", {})
        volatility = sweep.get("volatility", {})
        kr["as_of"] = sweep.get("timestamp") or kr.get("as_of")
        kr["gaps"] = [gap for gap in kr["gaps"] if gap != "Current KOSPI sweep"]
        markets = next((item for item in kr["components"] if item["id"] == "markets"), None)
        if markets:
            markets.update({
                "state": interpretation.get("regime", {}).get("name", "Live descriptive sweep"),
                "summary": " ".join(interpretation.get("sentences", [])[:2]),
                "confidence": "MODERATE",
                "gaps": ["Reliable current foreign-flow series remains unavailable."],
            })
            markets.setdefault("evidence_ids", []).extend(["kr-kospi-sweep", "kr-kospi-volatility"])
        world["evidence_index"]["kr-kospi-sweep"] = {
            "id": "kr-kospi-sweep", "label": "Current KOSPI factor sweep",
            "value": interpretation.get("regime", {}).get("name", "UNAVAILABLE"),
            "classification": "DESCRIPTIVE", "evidence_type": "PROXY",
            "source": "KOSPI Multi-Factor Signal Monitor", "source_path": "KOSPI/KOSPI_Backend_v2.py",
            "period": sweep.get("timestamp"), "freshness": "CURRENT", "note": "Current descriptive factor sweep; statistical association is not causal proof.",
        }
        world["evidence_index"]["kr-kospi-volatility"] = {
            "id": "kr-kospi-volatility", "label": "KOSPI GARCH volatility state",
            "value": f"{volatility.get('current_vol', 0):.2f}% / {volatility.get('regime', 'Unavailable')}",
            "classification": volatility.get("regime", "UNAVAILABLE"), "evidence_type": "PROXY",
            "source": "KOSPI Multi-Factor Signal Monitor", "source_path": "KOSPI/KOSPI_Backend_v2.py",
            "period": sweep.get("timestamp"), "freshness": "CURRENT", "note": "GARCH state from the existing engine; not a forecast or causal claim.",
        }
        fx = next((item for item in kr["components"] if item["id"] == "fx"), None)
        if fx:
            macro_factor = next((item for item in sweep.get("results", []) if item.get("key") == "macro"), None)
            if macro_factor:
                fx.update({"state": macro_factor.get("strength", "No signal"), "summary": f"USD/KRW factor correlation {macro_factor.get('corr', 0):+.3f}; adjusted p={macro_factor.get('pval', 1):.3f}.", "confidence": "LOW", "gaps": []})
        for engine in kr["engines"]:
            if "KOSPI" in engine["name"]:
                engine["status"] = "AVAILABLE"
        kr["watch_conditions"].append({"label": "KOSPI volatility regime", "threshold": "GARCH regime remains High with clustering", "current": f"{volatility.get('current_vol', 0):.2f}% / {volatility.get('regime', 'Unavailable')}", "state": "WATCH" if volatility.get("regime") == "High" else "CLEAR"})
    if inflation_result["payload"]:
        world["regions"]["US"]["engine_specific"]["us_inflation"] = inflation_result["payload"]
    for region in world["regions"].values():   # coverage follows the merged engine outputs
        apply_coverage(region)
    for edge in world.get("transmissions", []):
        if edge.get("id") == "us-kr-dollar-kospi" and kospi_result["payload"]:
            edge.update({
                "current_state": "WATCH", "confidence": "MODERATE",
                "summary": kospi_edge_summary(kospi_result["payload"]),
                "evidence_ids": list(dict.fromkeys(edge.get("evidence_ids", []) + ["kr-kospi-sweep", "kr-kospi-volatility"])),
            })
    cftc_result = isolated("cftc", fetch_cftc_jpy, refresh=refresh)
    boj_result = isolated("boj", fetch_boj_schedule, refresh=refresh)   # checklist 10.6: BOJ meeting calendar
    from korea_chip_exports import fetch_korea_chip_exports
    exports_result = isolated("korea-exports", fetch_korea_chip_exports, refresh=refresh)   # checklist 10.7
    environment = build_environment(core_result["payload"], world, inflation_result["payload"], kospi_result["payload"], cftc_result["payload"],
                                    boj=boj_result["payload"], korea_exports=exports_result["payload"])
    carry = environment["factors"]["yen_carry"]
    for edge in world.get("transmissions", []):
        if edge.get("id") == "jp-us-yen-carry":
            readings = carry["readings"]
            usdjpy_3m = readings.get("usdjpy_3m")
            edge.update({
                "current_state": CARRY_EDGE_STATE[readings["carry_state"]],
                "summary": f"Yen carry: {carry['state']}. USD/JPY {'3-month change unavailable' if usdjpy_3m is None else f'{usdjpy_3m:+.1%} over three months'}, VIX {'unavailable' if readings.get('vix_level') is None else f"{readings['vix_level']:.1f}"}.",
            })
    market_transmission = build_market_transmission(world, core_result["payload"], states)
    world_history = record_module("world", world, "LIVE") if refresh else {"state": "SKIPPED", "written": 0, "error": None}
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "LIVE_REFRESH" if refresh else "CACHE_FIRST",
        "engine_states": states,
        "engine_errors": {"inflation": inflation_result["error"], "core_market": core_result["error"], "kospi": kospi_result["error"]},
        "history": {
            "inflation": inflation_result.get("history"), "core_market": core_result.get("history"),
            "kospi": kospi_result.get("history"), "world": world_history,
        },
        "dashboard": with_two_liquidity_scores(dashboard_from(world, inflation_result["payload"], core_result["payload"], states, companies), environment),
        "world": world,
        "market_transmission": market_transmission,
        "environment": environment,
        "sector_flow": all_sector_flow(),
        "modules": {
            "inflation": inflation_result,
            "core_market": core_result,
            "kospi": kospi_result,
            "companies": {"state": "CACHED" if companies else "NOT_ANALYZED", "payload": companies, "error": None},
        },
        "capabilities": capability_payload(),
        "disclaimer": "Deterministic research interface. No recommendations and no LLM-generated research output.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the complete CHAINSTOX research context.")
    parser.add_argument("command", choices=["full", "dashboard", "inventory"], nargs="?", default="full")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--live", action="store_true", help="Refresh live-capable market and KOSPI engines.")
    parser.add_argument("--write-frontend-fixture", type=Path)
    args = parser.parse_args(argv)
    if args.command == "inventory":
        payload = capability_payload()
    else:
        full = build_research_system(refresh=args.live)
        payload = full["dashboard"] if args.command == "dashboard" else full
    if args.write_frontend_fixture:
        args.write_frontend_fixture.parent.mkdir(parents=True, exist_ok=True)
        args.write_frontend_fixture.write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    if args.json or not args.write_frontend_fixture:
        print(json.dumps(json_safe(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
