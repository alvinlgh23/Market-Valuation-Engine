"""Normalized, evidence-backed world macro integration for CHAINSTOX.

The adapters in this module wrap the copied research engines without changing
their calculations. Missing coverage is represented explicitly; it is never
filled with synthetic values.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
COMPASS_DIR = ROOT / "Centralbank-Compass" / "central-bank-compass"
# FRED observations live in this repo, not in the nested Compass repo (refresh approved 2026-11-22).
# scripts/refresh_compass_data.py seeds it from the Compass cache once and refreshes it online.
COMPASS_CACHE_DIR = ROOT / ".cache" / "compass_fred"
KOSPI_FILE = ROOT / "KOSPI" / "KOSPI_Backend_v2.py"
SUPPORTED_REGIONS = ("US", "JP", "KR", "EURO_AREA")   # Singapore removed 2026-11-22 (global audience)
ALIASES = {"USA": "US", "JAPAN": "JP", "KOREA": "KR", "EU": "EURO_AREA", "EZ": "EURO_AREA", "EUROZONE": "EURO_AREA"}


@dataclass
class MacroEvidence:
    id: str
    label: str
    value: str
    classification: str
    evidence_type: str
    source: str
    source_path: str
    period: str | None = None
    freshness: str = "UNKNOWN"
    note: str = ""


@dataclass
class MacroComponent:
    id: str
    label: str
    state: str
    summary: str
    confidence: str
    evidence_ids: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class MacroRegionProfile:
    id: str
    name: str
    available: bool
    availability: str
    framework: str
    brief: str
    as_of: str | None
    freshness: str
    confidence: str
    components: list[MacroComponent] = field(default_factory=list)
    evidence: list[MacroEvidence] = field(default_factory=list)
    engines: list[dict[str, str]] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    watch_conditions: list[dict[str, str]] = field(default_factory=list)
    engine_specific: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransmissionEdge:
    id: str
    source: str
    target: str
    label: str
    mechanism: str
    structural_state: str
    current_state: str
    summary: str
    confidence: str
    evidence_ids: list[str]
    caveat: str


COVERAGE_REGISTRY: dict[str, dict[str, Any]] = {
    "US": {"name": "United States", "engines": ["Central Bank Compass", "US Inflation Pressure"]},
    "JP": {"name": "Japan", "engines": ["Central Bank Compass"]},
    "KR": {"name": "South Korea", "engines": ["KOSPI Multi-Factor Signal Monitor"]},
    "EURO_AREA": {"name": "Euro Area", "engines": ["Central Bank Compass"]},
}


def canonical_region(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return ALIASES.get(normalized, normalized)


def freshness_for(period: str | None, today: date | None = None) -> str:
    if not period:
        return "UNKNOWN"
    today = today or date.today()
    try:
        observed = datetime.fromisoformat(period[:10]).date()
    except ValueError:
        return "UNKNOWN"
    age = (today - observed).days
    if age <= 45:
        return "CURRENT"
    if age <= 120:
        return "AGING"
    return "STALE"


def period_alignment(periods: list[str | None]) -> str:
    """Classify whether evidence periods can support a current joint inference."""
    parsed = []
    for period in periods:
        if not period:
            return "INSUFFICIENT"
        try:
            parsed.append(datetime.fromisoformat(period[:10]).date())
        except ValueError:
            return "INSUFFICIENT"
    if not parsed:
        return "INSUFFICIENT"
    spread = (max(parsed) - min(parsed)).days
    return "ALIGNED" if spread <= 45 else "MISMATCH"


def confidence_label(score: int | float | None) -> str:
    if score is None:
        return "INSUFFICIENT"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"


# Which research area each Compass data input feeds. The Compass config does not record this.
INPUT_AREA = {
    "core_pce": "inflation", "cpi": "inflation", "cpi_ex_fresh_food": "inflation", "hicp": "inflation", "core_hicp": "inflation",
    "mas_core_inflation": "inflation", "import_inflation_pressure": "inflation", "inflation_expectations": "inflation",
    "unemployment": "labor", "payrolls": "labor", "initial_claims": "labor", "wage_growth": "labor",
    "real_gdp": "growth", "pmi": "growth", "external_demand": "growth",
    "ten_year_yield": "markets", "two_year_yield": "markets", "credit_spread": "markets", "vix": "markets", "sovereign_spreads": "markets",
    "usd_jpy": "fx", "eur_usd": "fx", "broad_dollar": "fx",
}
# Days after which an input counts as out of date, by publication frequency (allows normal release lags).
STALE_AFTER = {"daily/weekly": 45, "monthly": 150, "quarterly": 270, "annual": 550}


def input_record(key: str, series_id: str | None, series: Any, today: date | None = None) -> dict[str, Any] | None:
    """Latest date, inferred frequency and staleness of one model input (None when it has no data)."""
    try:
        index = series.dropna().index
    except AttributeError:
        return None
    if len(index) == 0:
        return None
    last = index[-1].date()
    gaps = sorted((index[i] - index[i - 1]).days for i in range(max(1, len(index) - 6), len(index)))
    median_gap = gaps[len(gaps) // 2] if gaps else 365
    frequency = "daily/weekly" if median_gap <= 10 else "monthly" if median_gap <= 40 else "quarterly" if median_gap <= 100 else "annual"
    age = ((today or date.today()) - last).days
    return {"key": key, "series_id": series_id, "area": INPUT_AREA.get(key), "last": last.isoformat(),
            "frequency": frequency, "age_days": age, "stale": age > STALE_AFTER[frequency]}



def _read_cached_money_trends(liquidity: Any, fred: Any) -> None:
    """Data-access fix (2026-11-27): Compass's fred_yoy() returns nothing without a FRED_API_KEY, even offline, so the
    cached M2 and Fed balance-sheet series were scored as "missing" (0 points) although they are stored. Read them
    through the same offline cache reader every other Compass input uses; Compass's own scoring rule is unchanged."""
    if getattr(liquidity, "_chainstox_cached_yoy", False):
        return
    original = liquidity.fred_yoy

    def fred_yoy(config: dict[str, Any], economy_code: str, key: str, periods: int) -> float | None:
        series_id = config.get("liquidity", {}).get("fred_series", {}).get(economy_code, {}).get(key)
        if not series_id or os.getenv("FRED_API_KEY"):
            return original(config, economy_code, key, periods)
        series = fred.fetch_series(series_id, config)
        if series is None or series.empty:
            return None
        return liquidity.yoy(series, periods)

    liquidity.fred_yoy = fred_yoy
    liquidity._chainstox_cached_yoy = True

class CentralBankCompassAdapter:
    """Calls the copied Central Bank Compass modules in offline/cache mode."""

    CODE_MAP = {"US": "US", "JP": "JP", "EURO_AREA": "EZ"}

    def __init__(self, project_dir: Path = COMPASS_DIR, cache_dir: Path = COMPASS_CACHE_DIR):
        self.project_dir = project_dir
        self.cache_dir = cache_dir

    def _modules(self) -> dict[str, Any]:
        path = str(self.project_dir)
        if path not in sys.path:
            sys.path.insert(0, path)
        os.environ.setdefault("CBC_FRED_OFFLINE", "1")
        fred = importlib.import_module("src.data_sources.fred")
        if self.cache_dir.is_dir() and any(self.cache_dir.glob("*.csv")):
            fred.CACHE_DIR = self.cache_dir    # read and write here; the nested repo's cache stays untouched
        liquidity = importlib.import_module("src.liquidity")
        _read_cached_money_trends(liquidity, fred)
        return {
            "fred": fred,
            "config": importlib.import_module("app"),
            "profiles": importlib.import_module("src.country_profiles"),
            "data": importlib.import_module("src.data_sources"),
            "indicators": importlib.import_module("src.indicators"),
            "policy": importlib.import_module("src.policy_signal"),
            "probability": importlib.import_module("src.probability_model"),
            "japan": importlib.import_module("src.japan_pressure"),
            "liquidity": liquidity,
        }

    def load(self, region: str) -> dict[str, Any]:
        if region not in self.CODE_MAP:
            return {"available": False, "reason": "No Central Bank Compass economy profile."}
        modules = self._modules()
        code = self.CODE_MAP[region]
        config = modules["config"].load_config(self.project_dir / "config.yaml")
        data, warnings = modules["data"].fetch_economy_data(config, code)
        indicators = modules["indicators"].build_indicators(code, data)
        profile = modules["profiles"].get_profile(code)
        placeholders = modules["data"].configured_placeholders(config, code)
        signal = modules["policy"].build_policy_signal(indicators, profile, config, warnings, placeholders)
        latest = indicators.latest_observation.date().isoformat() if indicators.latest_observation is not None else None
        economy = config.get("economies", {}).get(code, {})
        input_map = economy.get("indicator_map", economy.get("fred_series", {}))
        inputs = [record for key, series in data.items()
                  if (record := input_record(key, input_map.get(key) if isinstance(input_map.get(key), str) else (input_map.get(key) or {}).get("series_id"), series))]
        blocks = {}
        evidence = []
        for block_id in ("inflation", "labor", "growth", "financial", "currency"):
            block = getattr(signal, block_id)
            blocks[block_id] = {
                "state": block.label,
                "score": round(float(block.score), 1),
                "coverage": f"{block.available}/{block.expected}",
                "policy_meaning": block.policy_meaning,
                "notes": list(block.notes),
                "evidence": [
                    {
                        "name": item.name,
                        "value": item.value,
                        "value_kind": item.value_kind,
                        "thresholds": list(item.thresholds),
                        "classification": item.classification,
                        "score_contribution": item.score_contribution,
                        "explanation": item.explanation,
                    }
                    for item in block.evidence
                ],
            }
            for index, item in enumerate(block.evidence):
                if item.value is None:
                    continue
                evidence.append({
                    "id": f"{region.lower()}-{block_id}-{index}",
                    "label": item.name,
                    "value": format_value(item.value, item.value_kind),
                    "classification": item.classification,
                    "type": "FACT" if "proxy" not in item.name.lower() else "PROXY",
                    "period": latest,
                    "note": item.explanation,
                })
        result = {
            "available": True,
            "code": code,
            "latest": latest,
            "signal": signal.signal,
            "bias": signal.policy_bias,
            "model_view": signal.model_view,
            "confidence": signal.confidence,
            "policy_tool": profile.policy_tool,
            "blocks": blocks,
            "evidence": evidence,
            "warnings": signal.warnings,
            "placeholders": placeholders,
            "inputs": inputs,
            "policy_score": round(float(signal.policy_score), 2),
            "block_scores": {key: round(float(value), 2) for key, value in signal.block_scores.items()},
            "decision_rules": list(signal.decision_rules),
            "indicator_values": {key: value for key, value in signal.indicators.values.items()},
            "missing_indicators": [
                {
                    "block": item.block,
                    "indicator": item.indicator_name,
                    "expected_source": item.expected_source,
                    "reason": item.reason,
                    "confidence_reduced": item.confidence_reduced,
                }
                for item in signal.missing_indicators
            ],
        }
        liquidity_drivers = modules["liquidity"].policy_drivers(code, signal)
        liquidity_drivers.extend(modules["liquidity"].market_liquidity_drivers(code, indicators, config))
        liquidity_score = modules["liquidity"].clamp(50 + sum(item.score_effect for item in liquidity_drivers), 0, 100)
        result["liquidity"] = {
            "score": round(float(liquidity_score), 2),
            "classification": modules["liquidity"].classify_liquidity(liquidity_score),
            "available_drivers": sum(item.value is not None for item in liquidity_drivers),
            "expected_drivers": len(liquidity_drivers),
            "drivers": [
                {
                    "name": item.name,
                    "value": item.value,
                    "value_kind": item.value_kind,
                    "thresholds": list(item.thresholds),
                    "classification": item.classification,
                    "score_effect": item.score_effect,
                    "explanation": item.explanation,
                }
                for item in liquidity_drivers
            ],
        }
        if region == "US":
            special = modules["probability"].build_us_probability_signal(config)
            result["special"] = {
                "label": "US policy probability model",
                "state": special.signal,
                "bias": special.policy_bias,
                "confidence": special.confidence,
                "coverage": special.data_coverage,
                "quality": special.model_quality,
                "probabilities_3m": special.probabilities_3m,
                "probabilities_6m": special.probabilities_6m,
                "pipeline_failure": special.pipeline_failure,
                "block_coverage": special.block_coverage,
                "features": [
                    {
                        "key": item.key,
                        "name": item.name,
                        "value": item.value,
                        "percentile": item.percentile,
                        "zscore": item.z_score,
                        "trend": item.trend,
                        "block": item.block,
                        "value_kind": item.value_kind,
                        "policy_effect": item.pressure,
                        "contribution": item.contribution,
                    }
                    for item in special.features
                ],
            }
        elif region == "JP":
            special = modules["japan"].build_japan_policy_pressure(config)
            result["special"] = {
                "label": "BOJ normalization pressure",
                "state": special.stance,
                "bias": special.policy_bias,
                "confidence": special.confidence,
                "inflation_character": special.inflation_character,
                "coverage": {key: f"{value[0]}/{value[1]}" for key, value in special.coverage.items()},
                "probabilities": {"easing": special.easing, "hold": special.hold, "normalization": special.normalization},
                "features": [
                    {
                        "name": item.name,
                        "value": item.value,
                        "kind": item.kind,
                        "percentile": item.percentile,
                        "pressure_effect": item.pressure_effect,
                        "why": item.why,
                    }
                    for item in special.features
                ],
            }
        return result


class KospiAdapter:
    """Reads the KOSPI engine's last output; export figures are never hard-coded (checklist 3.7)."""

    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or ROOT / ".cache" / "research" / "kospi.json"

    def load(self) -> dict[str, Any]:
        base = {
            "benchmark": "^KS11 KOSPI Composite",
            "market_factors": ["Semiconductor leaders", "USD/KRW", "Cultural exports", "Consumption", "Foreign flows"],
            "methods": ["Granger tests", "OLS", "Wavelet", "GARCH"],
            "warning": "The econometric outputs are descriptive candidates, not causal proof.",
        }
        try:
            payload = json.loads(self.cache_path.read_text())
        except (OSError, json.JSONDecodeError):
            return {**base, "available": False, "current_sweep": False, "export_snapshot": None}
        exports = payload.get("exports") or {}
        items = {item.get("key"): item for item in exports.get("items") or []}
        semis = items.get("semiconductors") or {}
        return {
            **base,
            "available": True,
            "current_sweep": bool((payload.get("sweep") or {}).get("results")),
            "sweep_timestamp": (payload.get("sweep") or {}).get("timestamp"),
            "has_fx_factor": any(item.get("key") == "macro" for item in (payload.get("sweep") or {}).get("results") or []),
            "has_volatility": bool((payload.get("sweep") or {}).get("volatility")),
            "export_snapshot": {
                "total_exports_usd_b": exports.get("total_exports_b"),
                "semiconductors_usd_b": semis.get("value_b"),
                "period": str(exports.get("year")) if exports.get("year") else None,
                "semiconductor_source": semis.get("source"),
                "note": exports.get("as_of"),
            } if exports else None,
        }


def format_value(value: Any, kind: str) -> str:
    if not isinstance(value, (int, float)):
        return str(value)
    if kind in {"pct", "percent"}:
        return f"{value:.2f}%"
    if kind == "index":
        return f"{value:.2f}"
    return f"{value:.2f}"


class MacroRegionEngine:
    def __init__(self, compass: CentralBankCompassAdapter | None = None):
        self.compass = compass or CentralBankCompassAdapter()
        self.kospi = KospiAdapter()

    def unsupported(self, region: str) -> MacroRegionProfile:
        return MacroRegionProfile(
            id=region,
            name=region.replace("_", " ").title(),
            available=False,
            availability="NOT_AVAILABLE",
            framework="No integrated research engine",
            brief="No verified macro profile is available for this economy.",
            as_of=None,
            freshness="UNKNOWN",
            confidence="INSUFFICIENT",
            gaps=["This economy is outside the initial world-map coverage registry."],
        )

    def build(self, requested: str) -> MacroRegionProfile:
        region = canonical_region(requested)
        if region not in COVERAGE_REGISTRY:
            return self.unsupported(region)
        profile = self._build_korea() if region == "KR" else self._build_compass_region(region, self.compass.load(region))
        return attach_coverage(profile)

    def _build_compass_region(self, region: str, raw: dict[str, Any]) -> MacroRegionProfile:
        coverage = COVERAGE_REGISTRY[region]
        evidence = [
            MacroEvidence(
                id=item["id"], label=item["label"], value=item["value"], classification=item["classification"],
                evidence_type=item["type"], source="Central Bank Compass", source_path="Centralbank-Compass/central-bank-compass",
                period=item["period"], freshness=freshness_for(item["period"]), note=item["note"],
            ) for item in raw["evidence"]
        ]
        components = []
        for key, label in (("inflation", "Inflation"), ("labor", "Labor"), ("growth", "Growth"), ("financial", "Markets & Financial Conditions"), ("currency", "FX")):
            block = raw["blocks"][key]
            ids = [item.id for item in evidence if f"-{key}-" in item.id]
            components.append(MacroComponent(
                id=key, label=label, state=block["state"], summary=block["policy_meaning"],
                confidence="MODERATE" if ids else "INSUFFICIENT", evidence_ids=ids,
                gaps=[] if ids else [f"No usable {label.lower()} observation in the cached engine output."],
            ))
        policy_state = raw.get("special", {}).get("state", raw["signal"])
        policy_confidence = raw.get("special", {}).get("confidence", raw["confidence"])
        policy_evidence = [item.id for item in evidence]
        components.insert(0, MacroComponent(
            id="policy", label="Policy", state=policy_state,
            summary=raw.get("special", {}).get("label", raw["model_view"]),
            confidence=confidence_label(policy_confidence), evidence_ids=policy_evidence,
        ))
        liquidity = raw["liquidity"]
        liquidity_ids = []
        for index, driver in enumerate(liquidity["drivers"]):
            if driver["value"] is None:
                continue
            evidence_id = f"{region.lower()}-liquidity-{index}"
            liquidity_ids.append(evidence_id)
            evidence.append(MacroEvidence(
                id=evidence_id,
                label=driver["name"],
                value=format_value(driver["value"], driver["value_kind"]),
                classification=driver["classification"],
                evidence_type="PROXY" if "proxy" in driver["name"].lower() else "FACT",
                source="Central Bank Compass / Liquidity",
                source_path="Centralbank-Compass/central-bank-compass/src/liquidity.py",
                period=raw["latest"],
                freshness=freshness_for(raw["latest"]),
                note=driver["explanation"],
            ))
        components.append(MacroComponent(
            id="liquidity", label="Liquidity", state=liquidity["classification"],
            summary=f"{liquidity['available_drivers']}/{liquidity['expected_drivers']} configured drivers are available; score {liquidity['score']:.0f}/100.",
            confidence="MODERATE" if liquidity_ids else "INSUFFICIENT", evidence_ids=liquidity_ids,
            gaps=[driver["name"] for driver in liquidity["drivers"] if driver["value"] is None],
        ))
        gaps = list(raw["placeholders"])
        brief = f"{raw['policy_tool']}: {policy_state}. {raw.get('special', {}).get('bias', raw['bias'])} bias with {confidence_label(policy_confidence).lower()} model confidence."
        engines = [{"name": "Central Bank Compass", "role": "Policy, inflation, growth, financial and FX blocks", "status": "CACHED"}]
        return MacroRegionProfile(
            id=region, name=coverage["name"], available=True, availability="PENDING",
            framework=raw["policy_tool"], brief=brief, as_of=raw["latest"], freshness=freshness_for(raw["latest"]),
            confidence=confidence_label(policy_confidence), components=components, evidence=evidence, engines=engines,
            gaps=dedupe(gaps),
            watch_conditions=build_region_watches(region, raw),
            engine_specific={"central_bank_compass": raw},
        )

    def _build_korea(self) -> MacroRegionProfile:
        raw = self.kospi.load()
        swept = bool(raw.get("current_sweep"))
        snapshot = raw.get("export_snapshot") or {}
        period = snapshot.get("period")
        evidence = []
        if snapshot.get("total_exports_usd_b") is not None:
            evidence.append(MacroEvidence("kr-export-total", "Total exports", f"${snapshot['total_exports_usd_b']:,.1f}B", f"{period} ANNUAL", "FACT", "Annual exports via KOSPI monitor", str(KOSPI_FILE.relative_to(ROOT)), f"{period}-12-31" if period else None, "STRUCTURAL", "Annual snapshot from the KOSPI engine; not a current market sweep."))
        if snapshot.get("semiconductors_usd_b") is not None:
            evidence.append(MacroEvidence("kr-semi-export", "Semiconductor exports", f"${snapshot['semiconductors_usd_b']:,.1f}B", f"{period} ANNUAL", "FACT", snapshot.get("semiconductor_source") or "KOSPI monitor", str(KOSPI_FILE.relative_to(ROOT)), f"{period}-12-31" if period else None, "STRUCTURAL", "Annual figure; monthly customs data needs a data.go.kr service key that is not configured."))
        call = read_korea_call_rate()
        month = move = ""
        if call:
            month = date.fromisoformat(call["date"]).strftime("%b %Y")
            move = "" if call["change_12m"] is None else f", {call['change_12m']:+.2f} points over 12 months"
            evidence.append(MacroEvidence("kr-call-rate", "Overnight call rate (tracks the Bank of Korea base rate)", f"{call['value']:.2f}%", f"{month} MONTHLY AVERAGE", "FACT",
                                          f"FRED {KR_CALL_RATE_SERIES} (OECD)", f".cache/compass_fred/{KR_CALL_RATE_SERIES}.csv", call["date"], "CACHED",
                                          f"Monthly average of the interbank call rate{move}. The Bank of Korea steers this rate onto its base rate; it is not the announced base rate."))
        return MacroRegionProfile(
            id="KR", name="South Korea", available=True, availability="PENDING",
            framework="KOSPI market, export and USD/KRW factor monitor",
            brief=("A cached KOSPI factor sweep and annual exports are available; Bank of Korea policy and Korean inflation are not modelled." if swept
                   else "Export and market transmission structure is mapped, but no current KOSPI sweep is persisted. Active pressure is therefore not classified."),
            as_of=f"{period}-12-31" if period else None, freshness="STRUCTURAL", confidence="LOW",
            components=[
                (MacroComponent("policy", "Policy", f"CALL RATE {call['value']:.2f}%", f"Overnight call rate {call['value']:.2f}% ({month} average){move}. A reading, not a Bank of Korea policy model.", "LOW", ["kr-call-rate"], ["BOK policy model"])
                 if call else MacroComponent("policy", "Policy", "NOT AVAILABLE", "No Bank of Korea policy model is integrated.", "INSUFFICIENT", gaps=["BOK policy model"])),
                MacroComponent("inflation", "Inflation", "NOT AVAILABLE", "No Korean inflation engine is integrated.", "INSUFFICIENT", gaps=["Korean CPI and inflation framework"]),
                MacroComponent("fx", "FX", "FRAMEWORK ONLY", "USD/KRW is a configured KOSPI factor; no current sweep is persisted.", "LOW", gaps=["Current USD/KRW factor result"]) if not raw.get("has_fx_factor")
                else MacroComponent("fx", "FX", "SWEEP CACHED", "USD/KRW factor result is in the cached KOSPI sweep.", "LOW"),
                MacroComponent("markets", "Markets", "STRUCTURAL", "KOSPI, semiconductor leaders, cultural exports, consumption and foreign flows are modeled.", "LOW", ["kr-export-total", "kr-semi-export"], ["Current econometric sweep", "Current foreign-flow series"]),
                MacroComponent("transmission", "Transmission", "INSUFFICIENT", "US rate and USD channels are structurally plausible but not classified as active.", "INSUFFICIENT", gaps=["Aligned current US/KR market observations"]),
            ],
            evidence=evidence,
            engines=[{"name": "KOSPI Multi-Factor Signal Monitor", "role": "Market, export, FX and flow relationships", "status": "STRUCTURAL_ONLY"}],
            gaps=["Bank of Korea policy", "Korean inflation"] + ([] if swept else ["Current KOSPI sweep"]),
            watch_conditions=[
                {"label": "Current KOSPI factor sweep", "threshold": "Current benchmark and factor history available", "current": "Unavailable", "state": "INSUFFICIENT"},
                {"label": "Foreign-flow confirmation", "threshold": "Current pykrx series available", "current": "Unavailable", "state": "INSUFFICIENT"},
            ],
            engine_specific={"kospi": raw},
        )


# Korea's overnight call rate (owner-approved 2026-11-27). The Bank of Korea steers the call rate onto its base rate,
# so it is shown as "call rate (tracks the BOK base rate)", never as the base rate itself. FRED's OECD base-rate
# series (IRSTCB01KRM156N) no longer exists; this monthly average is the closest public series.
KR_CALL_RATE_SERIES = "IRSTCI01KRM156N"


def refresh_korea_call_rate(fetch: Any = None, cache_dir: Path = COMPASS_CACHE_DIR) -> dict[str, Any]:
    """Download the series into the FRED cache. A failed or empty download keeps the existing file."""
    if fetch is None:
        from Valuation_model import fetch_fred_series as fetch
    rows = [(d, v) for d, v in (fetch(KR_CALL_RATE_SERIES) or []) if d and v is not None]
    if not rows:
        return {"state": "KEPT_CACHE", "rows": 0}
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{KR_CALL_RATE_SERIES}.csv"
    temporary = target.with_suffix(".csv.tmp")
    temporary.write_text("date,value\n" + "".join(f"{d},{v}\n" for d, v in rows))
    temporary.replace(target)
    return {"state": "OK", "rows": len(rows), "last": rows[-1][0]}


def read_korea_call_rate(cache_dir: Path = COMPASS_CACHE_DIR) -> dict[str, Any] | None:
    """Latest monthly value and its change over 12 months, from the cached file only (missing stays None)."""
    path = cache_dir / f"{KR_CALL_RATE_SERIES}.csv"
    if not path.exists():
        return None
    rows = []
    for line in path.read_text().strip().splitlines()[1:]:
        date, _, value = line.partition(",")
        try:
            rows.append((date, float(value)))
        except ValueError:
            continue
    if not rows:
        return None
    date, value = rows[-1]
    year_ago = next((v for d, v in reversed(rows) if d <= f"{int(date[:4]) - 1}{date[4:]}"), None)
    return {"date": date, "value": value, "change_12m": None if year_ago is None else round(value - year_ago, 3)}


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


# --- Coverage is calculated from the data, not typed in (fix 2026-11-22) -----------------------
COVERAGE_AREAS = (("policy", "Policy"), ("inflation", "Inflation"), ("labor", "Labor"), ("growth", "Growth"),
                  ("markets", "Markets"), ("fx", "FX"), ("liquidity", "Liquidity"))
COMPASS_BLOCK_AREA = {"inflation": "inflation", "labor": "labor", "growth": "growth", "financial": "markets", "currency": "fx"}
# Topics the engines do not try to measure at all. They are listed separately so that they are not
# confused with configured indicators whose data is missing.
NOT_MODELLED = {"JP": ["BOJ balance-sheet trend"], "EURO_AREA": ["Services inflation", "Wage growth"],
                "KR": ["Bank of Korea policy", "Korean inflation", "Labour market", "Liquidity"]}


def dedupe_ci(values: list[str]) -> list[str]:
    seen, out = set(), []
    for value in values:
        key = (value or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _area(area_id: str, label: str, items: list[tuple[str, bool, str | None]]) -> dict[str, Any]:
    """items: (indicator name, has data, observation date)."""
    available = sum(1 for _, ok, _ in items if ok)
    expected = len(items)
    dates = sorted(d[:10] for _, ok, d in items if ok and d)
    state = "NOT_COVERED" if expected == 0 else "FULL" if available == expected else "MISSING" if available == 0 else "PARTIAL"
    return {"id": area_id, "label": label, "state": state, "available": available, "expected": expected,
            "missing": [name for name, ok, _ in items if not ok], "as_of": dates[0] if dates else None,
            "newest": dates[-1] if dates else None}


def region_coverage(region: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Count configured indicators per research area from the engine outputs themselves."""
    specific = region.get("engine_specific") or {}
    items: dict[str, list[tuple[str, bool, str | None]]] = {area_id: [] for area_id, _ in COVERAGE_AREAS}
    compass = specific.get("central_bank_compass") or {}
    if compass.get("available"):
        latest = compass.get("latest")
        items["policy"].append(("Policy signal", bool(compass.get("signal")), latest))
        placeholders = set(compass.get("placeholders") or [])
        for block_id, block in (compass.get("blocks") or {}).items():
            area = COMPASS_BLOCK_AREA.get(block_id)
            if area:
                items[area].extend((ev["name"], ev.get("value") is not None, latest) for ev in block.get("evidence") or [])
        for missing in compass.get("missing_indicators") or []:
            area = COMPASS_BLOCK_AREA.get(missing.get("block"))
            if area and missing.get("indicator") in placeholders:
                items[area].append((missing["indicator"], False, None))
        items["liquidity"].extend((d["name"], d.get("value") is not None, latest) for d in (compass.get("liquidity") or {}).get("drivers") or [])
    kospi = specific.get("kospi") or {}
    live = specific.get("kospi_live") or {}
    if live.get("sweep"):
        sweep = live["sweep"]
        kospi = {**kospi, "current_sweep": bool(sweep.get("results")), "sweep_timestamp": sweep.get("timestamp"),
                 "has_fx_factor": any(item.get("key") == "macro" for item in sweep.get("results") or []),
                 "has_volatility": bool(sweep.get("volatility"))}
    if kospi:
        swept = kospi.get("sweep_timestamp")
        snapshot = kospi.get("export_snapshot") or {}
        export_date = f"{snapshot['period']}-12-31" if snapshot.get("period") else None
        items["growth"].extend([("Total exports (annual)", snapshot.get("total_exports_usd_b") is not None, export_date),
                                ("Semiconductor exports (annual)", snapshot.get("semiconductors_usd_b") is not None, export_date)])
        items["markets"].extend([("KOSPI factor sweep", bool(kospi.get("current_sweep")), swept),
                                 ("KOSPI volatility (GARCH)", bool(kospi.get("has_volatility")), swept),
                                 ("Foreign investor flows", False, None)])
        items["fx"].append(("USD/KRW factor", bool(kospi.get("has_fx_factor")), swept))
    areas = [_area(area_id, label, items[area_id]) for area_id, label in COVERAGE_AREAS]
    stale_inputs = [item for item in (compass.get("inputs") or []) if item.get("stale")] if compass.get("available") else []
    for area in areas:
        area["stale"] = [f"{item['key']} ({item['series_id']}, last {item['last']})" for item in stale_inputs if item.get("area") == area["id"]]
        if area["stale"] and area["state"] in {"FULL", "PARTIAL"}:
            area["state"] = "STALE"
    available = sum(a["available"] for a in areas)
    expected = sum(a["expected"] for a in areas)
    oldest = min((a["as_of"] for a in areas if a["as_of"]), default=None)
    newest = max((a["newest"] for a in areas if a["newest"]), default=None)
    if available == 0:
        availability = "NOT_AVAILABLE"
    elif all(a["state"] == "FULL" for a in areas):   # STALE areas also keep a region PARTIAL
        availability = "AVAILABLE"
    else:
        availability = "PARTIAL"
    return {
        "availability": availability,
        "available": available,
        "expected": expected,
        "areas_full": sum(1 for a in areas if a["state"] == "FULL"),
        "areas_covered": sum(1 for a in areas if a["state"] != "NOT_COVERED"),
        "areas": areas,
        "as_of": oldest,
        "newest": newest,
        "freshness": freshness_for(oldest, today),
        "missing": dedupe_ci([name for a in areas for name in a["missing"]]),
        "stale_inputs": [{"key": item["key"], "series_id": item["series_id"], "area": item.get("area"), "last": item["last"],
                          "frequency": item["frequency"], "age_days": item["age_days"]} for item in stale_inputs],
        "not_modelled": NOT_MODELLED.get(region.get("id", ""), []),
        "rule": "AVAILABLE only when every research area has all of its configured indicators and none is out of date; the date is the earliest of each source's latest observation.",
    }


def apply_coverage(region: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Recalculate a serialised region in place (run again after live engine payloads are merged)."""
    if not region.get("available"):
        return region
    coverage = region_coverage(region, today)
    region["coverage"] = coverage
    region["availability"] = coverage["availability"]
    region["gaps"] = dedupe_ci(coverage["missing"] + [gap for gap in region.get("gaps") or [] if gap not in coverage["not_modelled"]])
    return region


def attach_coverage(profile: MacroRegionProfile) -> MacroRegionProfile:
    if not profile.available:
        return profile
    serialised = apply_coverage(asdict(profile))
    profile.coverage = serialised["coverage"]
    profile.availability = serialised["availability"]
    profile.gaps = serialised["gaps"]
    return profile


def build_region_watches(region: str, raw: dict[str, Any]) -> list[dict[str, str]]:
    watches = []
    for block_id, block in raw["blocks"].items():
        if block["state"] in {"HIGH", "STICKY"}:
            watches.append({
                "label": f"{block_id.title()} pressure",
                "threshold": "Engine block remains HIGH or STICKY",
                "current": block["state"],
                "state": "WATCH",
            })
    for driver in raw["liquidity"]["drivers"]:
        if driver["classification"] in {"MISSING DATA", "RESTRICTIVE", "STRESS"}:
            watches.append({
                "label": driver["name"],
                "threshold": "Configured liquidity driver becomes available or changes state",
                "current": driver["classification"],
                "state": "INSUFFICIENT" if driver["classification"] == "MISSING DATA" else "WATCH",
            })
    return watches


class MacroTransmissionEngine:
    """Deterministic relationship templates separated from current-state claims."""

    def build(self, profiles: dict[str, MacroRegionProfile]) -> list[TransmissionEdge]:
        us = profiles["US"]
        jp = profiles["JP"]
        eu = profiles["EURO_AREA"]
        kr = profiles["KR"]
        return [
            TransmissionEdge("jp-us-yen-carry", "JP", "US", "Yen carry → US risk assets", "JPY funding conditions and Japanese yields can alter leveraged global risk appetite.", "ESTABLISHED", "INSUFFICIENT", "Current state comes from the environment layer's single yen-carry definition when USD/JPY and VIX observations are available.", "LOW" if jp.confidence == "LOW" else "MODERATE", self._ids(jp, ["currency", "financial"]) + self._ids(us, ["financial"]), "A transmission channel is not proof that it caused an observed market move."),
            TransmissionEdge("us-jp-rate-fx", "US", "JP", "US rates → USD/JPY → BOJ pressure", "US/Japan rate conditions transmit through USD/JPY and imported inflation pressure.", "ESTABLISHED", self._paired_state(us, jp), "The Compass explicitly models US rates, USD/JPY and BOJ normalization pressure.", "MODERATE", self._ids(us, ["policy", "financial"]) + self._ids(jp, ["currency", "policy"]), "Direction is model context, not a forecast of the exchange rate."),
            TransmissionEdge("us-eu-rate-fx", "US", "EURO_AREA", "Fed/ECB divergence → EUR/USD", "Relative policy and growth conditions can transmit through EUR/USD and regional financial conditions.", "ESTABLISHED", self._paired_state(us, eu), "Both policy frameworks are integrated; several Euro Area financial subcomponents remain missing.", "MODERATE", self._ids(us, ["policy"]) + self._ids(eu, ["policy", "currency"]), "The Euro Area is a monetary union; this does not represent every EU member's fiscal conditions."),
            TransmissionEdge("us-kr-dollar-kospi", "US", "KR", "US rates/USD → KRW and KOSPI", "Dollar and funding conditions can affect USD/KRW, foreign flows and export-sensitive Korean equities.", "ESTABLISHED", "INSUFFICIENT", "The KOSPI monitor defines the channel, but its current sweep and foreign-flow data are not persisted.", "LOW", self._ids(us, ["policy", "financial"]) + ["kr-export-total", "kr-semi-export"], "Structural plausibility is not an active-signal claim and Granger tests are not causal proof."),
        ]

    @staticmethod
    def _ids(profile: MacroRegionProfile, component_ids: list[str]) -> list[str]:
        return dedupe([evidence_id for component in profile.components if component.id in component_ids for evidence_id in component.evidence_ids])

    @staticmethod
    def _paired_state(first: MacroRegionProfile, second: MacroRegionProfile) -> str:
        if first.confidence == "INSUFFICIENT" or second.confidence == "INSUFFICIENT":
            return "INSUFFICIENT"
        if first.freshness == "STALE" or second.freshness == "STALE":
            return "WATCH"
        return "WATCH" if first.confidence == "LOW" or second.confidence == "LOW" else "ACTIVE"


def build_world(regions: list[str] | None = None) -> dict[str, Any]:
    region_engine = MacroRegionEngine()
    selected = [canonical_region(item) for item in regions] if regions else list(SUPPORTED_REGIONS)
    profiles = {region: region_engine.build(region) for region in selected}
    transmissions = MacroTransmissionEngine().build(profiles) if all(region in profiles for region in SUPPORTED_REGIONS) else []
    evidence_index = {item.id: asdict(item) for profile in profiles.values() for item in profile.evidence}
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data_state": "CACHED",
        "supported_regions": list(SUPPORTED_REGIONS),
        "coverage": COVERAGE_REGISTRY,
        "regions": {key: asdict(value) for key, value in profiles.items()},
        "transmissions": [asdict(item) for item in transmissions],
        "evidence_index": evidence_index,
        "disclaimer": "Deterministic research context only. No recommendations. Facts, proxies and inferences are labeled separately.",
    }


def run_macro_world_cli(args: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="model.py macro-world", description="Build the normalized CHAINSTOX world macro profile.")
    parser.add_argument("region", nargs="?", help="Optional region code or alias.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--write-frontend-fixture", type=Path, help="Write the full world output to a JSON fixture path.")
    options = parser.parse_args(args)
    world = build_world([options.region] if options.region else None)
    if options.write_frontend_fixture:
        options.write_frontend_fixture.parent.mkdir(parents=True, exist_ok=True)
        options.write_frontend_fixture.write_text(json.dumps(world, indent=2) + "\n")
    if options.json or not options.write_frontend_fixture:
        print(json.dumps(world, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_macro_world_cli(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
