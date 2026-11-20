"""Compact data-provenance and research-claim contracts for CHAINSTOX.

The module deliberately separates acquisition state, observation freshness,
measurement validity, and claim sufficiency.  It has no network dependency and
does not mutate valuation inputs.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


EVIDENCE_SCHEMA_VERSION = "1.0"
CLASSIFICATION_VERSION = "phase7-rules-v1"


class SourceStatus(str, Enum):
    OBSERVED_LIVE = "OBSERVED_LIVE"
    OBSERVED_CACHED = "OBSERVED_CACHED"
    OBSERVED_STALE = "OBSERVED_STALE"
    HISTORICAL_REPORTED = "HISTORICAL_REPORTED"
    CALCULATED = "CALCULATED"
    PROXY = "PROXY"
    FIXTURE = "FIXTURE"
    MISSING = "MISSING"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"
    CONFLICTING = "CONFLICTING"


class ProviderStatus(str, Enum):
    OK = "OK"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    UNSUPPORTED_SYMBOL = "UNSUPPORTED_SYMBOL"
    MISSING_CONCEPT = "MISSING_CONCEPT"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    UNSUPPORTED_FRAMEWORK = "UNSUPPORTED_FRAMEWORK"
    INVALID = "INVALID"


class CoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNSUPPORTED = "UNSUPPORTED"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"


class StalenessStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class ClaimType(str, Enum):
    REPORTED_FACT = "REPORTED_FACT"
    DERIVED_MEASUREMENT = "DERIVED_MEASUREMENT"
    INDIRECT_PROXY = "INDIRECT_PROXY"
    STRUCTURAL_HYPOTHESIS = "STRUCTURAL_HYPOTHESIS"
    ECONOMIC_INFERENCE = "ECONOMIC_INFERENCE"
    VALIDATED_CONCLUSION = "VALIDATED_CONCLUSION"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


class Directness(str, Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    STRUCTURAL = "STRUCTURAL"
    UNKNOWN = "UNKNOWN"


class ConstraintStatus(str, Enum):
    STRUCTURAL_CANDIDATE = "STRUCTURAL_CANDIDATE"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    POTENTIALLY_BINDING = "POTENTIALLY_BINDING"
    OBSERVED_BINDING = "OBSERVED_BINDING"
    OBSERVED_NON_BINDING = "OBSERVED_NON_BINDING"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class DirectionStatus(str, Enum):
    DIRECTION_UNKNOWN = "DIRECTION_UNKNOWN"
    POSSIBLY_TIGHTENING = "POSSIBLY_TIGHTENING"
    OBSERVED_TIGHTENING = "OBSERVED_TIGHTENING"
    POSSIBLY_EASING = "POSSIBLY_EASING"
    OBSERVED_EASING = "OBSERVED_EASING"
    MIXED = "MIXED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CausalStatus(str, Enum):
    NOT_ASSESSED = "NOT_ASSESSED"
    ASSOCIATION_ONLY = "ASSOCIATION_ONLY"
    STRUCTURALLY_PLAUSIBLE = "STRUCTURALLY_PLAUSIBLE"
    CAUSALLY_VALIDATED = "CAUSALLY_VALIDATED"


def _iso(value: dt.datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.astimezone(dt.timezone.utc).isoformat()
    return str(value)


def _date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def classify_staleness(
    observation_date: str | None,
    *,
    as_of: dt.date | None = None,
    max_age_days: int | None = None,
    historical: bool = False,
) -> StalenessStatus:
    if historical:
        return StalenessStatus.HISTORICAL
    observed = _date(observation_date)
    if observed is None or max_age_days is None:
        return StalenessStatus.UNKNOWN
    age = ((as_of or dt.datetime.now(dt.timezone.utc).date()) - observed).days
    return StalenessStatus.CURRENT if age <= max_age_days else StalenessStatus.STALE


@dataclass(frozen=True)
class EvidenceEnvelope:
    source_id: str
    source_name: str
    source_url: str | None = None
    source_type: str = "structured_data"
    provider_status: ProviderStatus = ProviderStatus.OK
    retrieved_at: str | None = None
    observation_date: str | None = None
    fiscal_period_start: str | None = None
    fiscal_period_end: str | None = None
    fiscal_year: int | str | None = None
    filing_date: str | None = None
    unit: str | None = None
    currency: str | None = None
    value: Any = None
    raw_concept: str | None = None
    normalized_concept: str | None = None
    transformation: str | None = None
    coverage_status: CoverageStatus = CoverageStatus.COMPLETE
    validation_status: ValidationStatus = ValidationStatus.VALID
    staleness_status: StalenessStatus = StalenessStatus.UNKNOWN
    limitation: str | None = None
    entity_identifier: str | None = None
    source_status: SourceStatus = SourceStatus.HISTORICAL_REPORTED
    schema_version: str = EVIDENCE_SCHEMA_VERSION
    source_locator: str | None = None
    extraction_method: str | None = None
    definition_version: str | None = None
    revision_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value.value if isinstance(value, Enum) else value for key, value in payload.items()}


@dataclass(frozen=True)
class ResearchClaim:
    claim_id: str
    entity_identifier: str
    mechanism: str
    relationship: str
    claim_type: ClaimType
    direct_evidence_ids: tuple[str, ...] = ()
    proxy_evidence_ids: tuple[str, ...] = ()
    counterevidence_ids: tuple[str, ...] = ()
    unresolved_evidence: tuple[str, ...] = ()
    source_references: tuple[str, ...] = ()
    reporting_period: str | None = None
    as_of: str | None = None
    source_reliability: ValidationStatus = ValidationStatus.UNVERIFIED
    measurement_directness: Directness = Directness.UNKNOWN
    temporal_relevance: ValidationStatus = ValidationStatus.UNVERIFIED
    entity_specificity: ValidationStatus = ValidationStatus.UNVERIFIED
    consistency: ValidationStatus = ValidationStatus.UNVERIFIED
    constraint_status: ConstraintStatus = ConstraintStatus.EVIDENCE_INSUFFICIENT
    direction_status: DirectionStatus = DirectionStatus.DIRECTION_UNKNOWN
    causal_status: CausalStatus = CausalStatus.NOT_ASSESSED
    limitations: tuple[str, ...] = ()
    falsification_conditions: tuple[str, ...] = ()
    methodological_notes: tuple[str, ...] = ()
    classification_version: str = CLASSIFICATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {
            key: value.value if isinstance(value, Enum) else list(value) if isinstance(value, tuple) else value
            for key, value in payload.items()
        }


def validate_numeric_observation(envelope: EvidenceEnvelope) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not isinstance(envelope.value, (int, float)) or isinstance(envelope.value, bool) or not math.isfinite(envelope.value):
        reasons.append("value is not a finite number")
    if not envelope.unit:
        reasons.append("unit is missing")
    if not envelope.observation_date and not envelope.fiscal_period_end:
        reasons.append("observation period is missing")
    if envelope.provider_status != ProviderStatus.OK:
        reasons.append(f"provider status is {envelope.provider_status.value}")
    return not reasons, reasons


def validate_comparable_observations(
    observations: list[EvidenceEnvelope],
    *,
    require_same_currency: bool = True,
    require_same_period: bool = True,
) -> tuple[ValidationStatus, list[str]]:
    present = [item for item in observations if item.value is not None]
    if len(present) != len(observations):
        return ValidationStatus.PARTIAL, ["one or more required observations are missing"]
    reasons: list[str] = []
    units = {item.unit for item in present}
    currencies = {item.currency for item in present if item.currency}
    periods = {item.fiscal_period_end or item.observation_date for item in present}
    if len(units) > 1:
        reasons.append("unit mismatch")
    if require_same_currency and len(currencies) > 1:
        reasons.append("currency mismatch")
    if require_same_period and len(periods) > 1:
        reasons.append("period mismatch")
    return (ValidationStatus.VALID if not reasons else ValidationStatus.CONFLICTING), reasons


def assess_constraint_claim(
    *,
    claim_id: str,
    entity_identifier: str,
    mechanism: str,
    direct_ids: list[str],
    proxy_ids: list[str],
    counter_ids: list[str],
    direct_direction: str | None = None,
    proxy_direction: str | None = None,
    evidence_current: bool = True,
    explicitly_binding: bool | None = None,
) -> ResearchClaim:
    """Apply conservative deterministic sufficiency rules.

    A proxy can qualify direction as possible, but can never establish observed
    binding.  Direct evidence can establish a direction while binding remains a
    separate question unless the source explicitly addresses binding status.
    """
    limitations: list[str] = []
    if not evidence_current and (direct_ids or proxy_ids):
        limitations.append("Evidence is historical or stale for a current-state claim.")
    if direct_ids and counter_ids:
        constraint_status = ConstraintStatus.CONFLICTING_EVIDENCE
        direction_status = DirectionStatus.MIXED
    elif explicitly_binding is True and direct_ids and evidence_current:
        constraint_status = ConstraintStatus.OBSERVED_BINDING
        direction_status = _direction_status(direct_direction, observed=True)
    elif explicitly_binding is False and direct_ids and evidence_current:
        constraint_status = ConstraintStatus.OBSERVED_NON_BINDING
        direction_status = _direction_status(direct_direction, observed=True)
    elif direct_ids and evidence_current:
        constraint_status = ConstraintStatus.POTENTIALLY_BINDING
        direction_status = _direction_status(direct_direction, observed=True)
        limitations.append("Direct measurements do not by themselves establish that the mechanism is binding.")
    elif proxy_ids:
        constraint_status = ConstraintStatus.EVIDENCE_INSUFFICIENT
        direction_status = _direction_status(proxy_direction, observed=False) if evidence_current else DirectionStatus.DIRECTION_UNKNOWN
        limitations.append("Proxy evidence is not a direct observation of the proposed constraint.")
    else:
        constraint_status = ConstraintStatus.STRUCTURAL_CANDIDATE
        direction_status = DirectionStatus.DIRECTION_UNKNOWN
        limitations.append("The mechanism is structurally plausible but lacks current entity-specific measurement.")
    if counter_ids and not direct_ids:
        constraint_status = ConstraintStatus.CONFLICTING_EVIDENCE
        direction_status = DirectionStatus.MIXED
    claim_type = (
        ClaimType.CONTRADICTED if constraint_status == ConstraintStatus.CONFLICTING_EVIDENCE
        else ClaimType.ECONOMIC_INFERENCE if direct_ids or proxy_ids
        else ClaimType.STRUCTURAL_HYPOTHESIS
    )
    return ResearchClaim(
        claim_id=claim_id,
        entity_identifier=entity_identifier,
        mechanism=mechanism,
        relationship=f"Whether {mechanism.lower()} is currently binding",
        claim_type=claim_type,
        direct_evidence_ids=tuple(direct_ids),
        proxy_evidence_ids=tuple(proxy_ids),
        counterevidence_ids=tuple(counter_ids),
        source_reliability=ValidationStatus.VALID if direct_ids or proxy_ids or counter_ids else ValidationStatus.UNVERIFIED,
        measurement_directness=Directness.DIRECT if direct_ids else Directness.INDIRECT if proxy_ids else Directness.STRUCTURAL,
        temporal_relevance=ValidationStatus.VALID if evidence_current else ValidationStatus.INVALID,
        entity_specificity=ValidationStatus.VALID if direct_ids or proxy_ids else ValidationStatus.UNVERIFIED,
        consistency=ValidationStatus.CONFLICTING if counter_ids else ValidationStatus.VALID if direct_ids or proxy_ids else ValidationStatus.UNVERIFIED,
        constraint_status=constraint_status,
        direction_status=direction_status,
        causal_status=CausalStatus.ASSOCIATION_ONLY if direct_ids or proxy_ids else CausalStatus.STRUCTURALLY_PLAUSIBLE,
        limitations=tuple(limitations),
        falsification_conditions=("Obtain a direct, entity-specific throughput or utilization measure for the same period.",),
        methodological_notes=("Constraint binding, direction, and structural importance are assessed separately.",),
    )


def _direction_status(value: str | None, *, observed: bool) -> DirectionStatus:
    normalized = (value or "").upper()
    if normalized in {"EASING", "IMPROVING", "OBSERVED_EASING"}:
        return DirectionStatus.OBSERVED_EASING if observed else DirectionStatus.POSSIBLY_EASING
    if normalized in {"TIGHTENING", "DETERIORATING", "OBSERVED_TIGHTENING"}:
        return DirectionStatus.OBSERVED_TIGHTENING if observed else DirectionStatus.POSSIBLY_TIGHTENING
    if normalized in {"MIXED", "CONFLICTING"}:
        return DirectionStatus.MIXED
    return DirectionStatus.DIRECTION_UNKNOWN
