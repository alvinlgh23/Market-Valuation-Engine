"""Issuer-scoped operational series; advisory only, never a valuation input."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
import math
from pathlib import Path

from evidence_contracts import EvidenceEnvelope, SourceStatus, StalenessStatus, ValidationStatus

REGISTRY = Path(__file__).parent / "data" / "operational_series.json"


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    issuer: str
    name: str
    definition: str
    category: str
    scope: str
    measurement: str
    unit: str
    currency: str | None
    version: str
    effective_from: str
    limitation: str
    mechanism: str
    effective_to: str | None = None


@dataclass(frozen=True)
class OperationalObservation:
    id: str
    metric_id: str
    issuer: str
    period: str
    period_basis: str
    period_start: str | None
    period_end: str
    definition_version: str
    scope: str
    measurement: str
    revision_status: str
    evidence: EvidenceEnvelope


def comparison_reasons(a: OperationalObservation, b: OperationalObservation) -> list[str]:
    reasons = []
    if any(not isinstance(o.evidence.value, (int, float)) or isinstance(o.evidence.value, bool) or not math.isfinite(o.evidence.value) for o in (a, b)):
        reasons.append("nonfinite measurement")
    for key in ("metric_id", "issuer", "period_basis", "definition_version", "scope", "measurement"):
        if getattr(a, key) != getattr(b, key):
            reasons.append(f"{key} mismatch")
    for key in ("unit", "currency"):
        if getattr(a.evidence, key) != getattr(b.evidence, key):
            reasons.append(f"{key} mismatch")
    if any(o.revision_status not in {"ORIGINAL", "RESTATED_COMPARABLE"} for o in (a, b)):
        reasons.append("unresolved revision")
    if any(o.evidence.validation_status != ValidationStatus.VALID for o in (a, b)):
        reasons.append("unverified observation")
    try:
        gap = (date.fromisoformat(b.period_end) - date.fromisoformat(a.period_end)).days
    except ValueError:
        return reasons + ["invalid period date"]
    bounds = {"FISCAL_ANNUAL": (350, 380), "FISCAL_QUARTER": (75, 105)}
    if a.period_basis not in bounds or not bounds[a.period_basis][0] <= gap <= bounds[a.period_basis][1]:
        reasons.append("missing or incompatible adjacent period")
    if a.measurement in {"FLOW", "PERIOD_POPULATION"}:
        if not a.period_start or not b.period_start:
            reasons.append("flow period start missing")
        else:
            try:
                durations = [(date.fromisoformat(o.period_end) - date.fromisoformat(o.period_start)).days for o in (a, b)]
            except ValueError:
                return reasons + ["invalid period start"]
            if any(d <= 0 for d in durations):
                reasons.append("invalid flow duration")
            if abs(durations[0] - durations[1]) > 8:
                reasons.append("flow duration mismatch")
    return reasons


def metric_change(a: OperationalObservation, b: OperationalObservation) -> dict:
    reasons = comparison_reasons(a, b)
    if reasons:
        return {"status": "INSUFFICIENT_EVIDENCE", "reasons": reasons, "absolute": None, "growth": None}
    before, after = a.evidence.value, b.evidence.value
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (before, after)):
        return {"status": "INSUFFICIENT_EVIDENCE", "reasons": ["nonfinite measurement"], "absolute": None, "growth": None}
    return {"status": "CALCULATED", "reasons": [], "absolute": after - before,
            "growth": (after / before - 1) if before > 0 and a.evidence.unit not in {"percentage points", "decimal share of wafer revenue", "ratio", "decimal share"} else None,
            "method": "Adjacent comparable reported observations; not causal attribution",
            "evidence_ids": [a.id, b.id]}


def revenue_bridge(revenue: tuple[OperationalObservation, OperationalObservation], customers: tuple[OperationalObservation, OperationalObservation]) -> dict:
    """Symmetric (Shapley) allocation of the interaction in R = N × R/N."""
    reasons = comparison_reasons(*revenue) + comparison_reasons(*customers)
    for r, c in zip(revenue, customers):
        if (r.issuer, r.scope, r.period_start, r.period_end, r.period_basis) != (c.issuer, c.scope, c.period_start, c.period_end, c.period_basis):
            reasons.append("revenue/customer population or period mismatch")
        if c.measurement != "PERIOD_POPULATION" or r.measurement != "FLOW":
            reasons.append("requires period population, not point-in-time customers")
    if reasons or any(o.evidence.value <= 0 for o in (*revenue, *customers)):
        return {"status": "INSUFFICIENT_EVIDENCE", "reasons": reasons or ["nonpositive denominator"]}
    r0, r1 = [o.evidence.value for o in revenue]
    n0, n1 = [o.evidence.value for o in customers]
    p0, p1 = r0 / n0, r1 / n1
    return {"status": "CALCULATED", "customer_contribution": (n1 - n0) * (p0 + p1) / 2,
            "revenue_per_customer_contribution": (p1 - p0) * (n0 + n1) / 2,
            "total_change": r1 - r0, "method": "Symmetric interaction allocation; accounting identity, not causality"}


def load_series(ticker: str, path: Path = REGISTRY) -> list[tuple[MetricDefinition, list[OperationalObservation]]]:
    data = json.loads(path.read_text())
    output = []
    for row in data["metrics"]:
        definition = MetricDefinition(**row["definition"])
        if definition.category not in {"ISSUER_DEFINED", "STANDARD_FINANCIAL", "DERIVED_OPERATIONAL", "PROXY", "ANALYST_HYPOTHESIS"}:
            raise ValueError("Unknown metric category")
        if definition.measurement not in {"FLOW", "STOCK", "PERIOD_POPULATION"}:
            raise ValueError("Unknown measurement basis")
        if definition.issuer != ticker.upper():
            continue
        observations = []
        for raw in row["observations"]:
            source = data["sources"][raw["source"]]
            end = raw["end"]
            if end < definition.effective_from or (definition.effective_to and end > definition.effective_to):
                raise ValueError("Observation outside definition effective period")
            if not math.isfinite(raw["value"]) or isinstance(raw["value"], bool):
                raise ValueError("Invalid operational value")
            for required in ("url", "title", "published", "retrieved_at"):
                if not source.get(required):
                    raise ValueError(f"Missing source {required}")
            if not source["url"].startswith("https://") or not raw.get("locator"):
                raise ValueError("Source URL and exact locator required")
            evidence = EvidenceEnvelope(source_id=raw["source"], source_name=source["title"], source_url=source["url"],
                source_type=source["type"], retrieved_at=source["retrieved_at"], observation_date=end,
                fiscal_period_start=raw.get("start"), fiscal_period_end=end, filing_date=source["published"],
                unit=definition.unit, currency=definition.currency, value=raw["value"], raw_concept=definition.name,
                normalized_concept=definition.id, transformation="No rescaling; manual source transcription",
                staleness_status=StalenessStatus.HISTORICAL, limitation=definition.limitation,
                entity_identifier=definition.issuer, source_status=SourceStatus.HISTORICAL_REPORTED,
                source_locator=raw["locator"], extraction_method="documentary_manual", definition_version=definition.version,
                revision_status=raw.get("revision", "ORIGINAL"))
            observations.append(OperationalObservation(f"{definition.id}:{end}", definition.id, definition.issuer,
                raw["period"], raw["basis"], raw.get("start"), end, definition.version, definition.scope,
                definition.measurement, raw.get("revision", "ORIGINAL"), evidence))
        dates = [o.period_end for o in observations]
        if len(set(dates)) != len(dates):
            raise ValueError("Duplicate observation period; resolve revision explicitly")
        output.append((definition, sorted(observations, key=lambda o: o.period_end)))
    return output


def build_operational_research(ticker: str, valuation_report: dict | None = None) -> dict:
    series = []
    for definition, observations in load_series(ticker):
        changes = [metric_change(a, b) for a, b in zip(observations, observations[1:])]
        series.append({"definition": asdict(definition), "observations": [asdict(o) for o in observations],
                       "changes": changes, "claim_type": "REPORTED_FACT",
                       "constraint_status": "STRUCTURAL_CANDIDATE", "direction_status": "DIRECTION_UNKNOWN",
                       "counterevidence": [], "falsification": "Obtain same-scope throughput, delivery, or utilization evidence; test demand and mix alternatives."})
    assumptions = {item["name"]: item["value"] for item in (valuation_report or {}).get("assumptions", {}).get("base", [])}
    tensions = [{"metric": row["definition"]["name"], "observation_period": row["observations"][-1]["period"],
                 "historical_growth": row["changes"][-1]["growth"] if row["changes"] else None,
                 "model_assumption": assumptions.get("year_1_revenue_growth"),
                 "state": "CONTEXT_ONLY" if assumptions else "INSUFFICIENT_EVIDENCE",
                 "limitation": "Historical metric movement and forward consolidated revenue growth have different horizons and may have different scopes; this is not a supported/unsupported forecast verdict.",
                 "action": "Review conversion, mix, price and persistence assumptions; do not mechanically extrapolate."} for row in series if row["definition"]["currency"] and row["definition"]["measurement"] == "FLOW"]
    return {"schema_version": "1.0", "coverage": "PARTIAL" if series else "MISSING",
            "series": series, "mutates_dcf_inputs": False,
            "assumption_tensions": tensions,
            "security_unit_evidence": {"ordinary_shares_per_ads": 5, "source_url": "https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm", "source_locator": "Item 6 / share ownership footnote (2)", "source_period": "FY2025", "ratio_effective_date": None, "limitation": "Ratio documented; current effective interval, total-share denominator and dated FX not reconciled. No per-ADR value emitted."} if ticker.upper() == "TSM" else None,
            "limitation": "Dated manual disclosures, not a live operational feed. No causal or forecast decomposition is implied.",
            "next_questions": ["Obtain current comparable operating disclosures.", "Test demand, pricing and mix alternatives before attributing growth to capacity."],
            "security_unit_status": "SECURITY_UNIT_AMBIGUITY" if ticker.upper() == "TSM" else "NOT_ASSESSED"}
