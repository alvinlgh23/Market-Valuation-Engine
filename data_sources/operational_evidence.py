"""Validated import for explicitly curated issuer operational evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence_contracts import (
    CoverageStatus,
    EvidenceEnvelope,
    ProviderStatus,
    SourceStatus,
    StalenessStatus,
    ValidationStatus,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "operational_evidence.json"
REQUIRED_FIELDS = {
    "id", "issuer", "metric", "metric_definition", "value", "unit",
    "reporting_period", "observation_date", "publication_date", "source_title",
    "source_url", "extraction_method", "verification_status",
}
ALLOWED_VERIFICATION_STATUSES = {
    "DOCUMENTARY_VERIFIED",
    "CURATED_UNVERIFIED",
    "MACHINE_EXTRACTED",
}


@dataclass(frozen=True)
class CuratedEvidenceEntry:
    id: str
    issuer: str
    metric: str
    metric_definition: str
    value: float | int | str
    unit: str
    reporting_period: str
    observation_date: str
    publication_date: str
    source_title: str
    source_url: str
    source_type: str
    extraction_method: str
    verification_status: str
    entity_identifier: str | None = None
    locator: str | None = None
    limitation: str | None = None

    def envelope(self) -> EvidenceEnvelope:
        return EvidenceEnvelope(
            source_id=self.id, source_name=self.source_title, source_url=self.source_url,
            source_type=self.source_type, provider_status=ProviderStatus.OK,
            observation_date=self.observation_date, fiscal_period_end=self.observation_date,
            filing_date=self.publication_date, unit=self.unit, value=self.value,
            raw_concept=self.metric_definition, normalized_concept=self.metric,
            transformation="manual transcription from cited issuer disclosure",
            coverage_status=CoverageStatus.COMPLETE,
            validation_status=ValidationStatus.VALID if self.verification_status == "DOCUMENTARY_VERIFIED" else ValidationStatus.UNVERIFIED,
            staleness_status=StalenessStatus.HISTORICAL, limitation=self.limitation,
            entity_identifier=self.entity_identifier or self.issuer,
            source_status=SourceStatus.HISTORICAL_REPORTED,
            source_locator=self.locator, extraction_method=self.extraction_method,
        )


def load_operational_evidence(ticker: str, path: Path = DEFAULT_REGISTRY) -> list[CuratedEvidenceEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("entries")
    if not isinstance(rows, list):
        raise ValueError("Operational evidence registry must contain an entries list.")
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Operational evidence entry {index} is not an object.")
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            raise ValueError(f"Operational evidence entry {row.get('id', index)} lacks: {', '.join(missing)}")
        if not row.get("source_url") or not str(row["source_url"]).startswith(("https://", "http://")):
            raise ValueError(f"Operational evidence entry {row['id']} needs a source URL.")
        if row.get("verification_status") not in ALLOWED_VERIFICATION_STATUSES:
            raise ValueError(f"Operational evidence entry {row['id']} has an unsupported verification status.")
        if row.get("value") is None or not row.get("unit") or not row.get("reporting_period"):
            raise ValueError(f"Operational evidence entry {row['id']} lacks value, unit, or period.")
        if str(row.get("issuer", "")).upper() == ticker.upper():
            result.append(CuratedEvidenceEntry(**row))
    return result


def enrich_snapshot(snapshot: Any, path: Path = DEFAULT_REGISTRY):
    """Mutate the normalized snapshot boundary, not downstream claim logic."""
    entries = load_operational_evidence(snapshot.ticker, path)
    envelopes = dict(getattr(snapshot, "evidence_envelopes", {}) or {})
    for entry in entries:
        snapshot.operational_metrics[entry.metric] = entry.value
        snapshot.periods[entry.metric] = entry.reporting_period
        snapshot.sources[entry.metric] = entry.source_title
        snapshot.source_nature[entry.metric] = "REPORTED"
        envelopes[entry.metric] = entry.envelope().to_dict()
    snapshot.evidence_envelopes = envelopes
    return snapshot
