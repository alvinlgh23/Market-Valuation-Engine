"""Deterministic, evidence-traceable company economic intelligence.

This module bridges normalized company fundamentals and valuation review.  It
does not mutate valuation assumptions and has no LLM or network dependency in
its domain layer.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from company_economics_overrides import COMPANY_ECONOMICS_OVERRIDES
from company_economics_registry import (
    ARCHETYPE_REGISTRY,
    CONSTRAINT_REGISTRY,
    Archetype,
    ConstraintType,
    GrowthPrimitive,
)
from evidence_contracts import assess_constraint_claim


COMPANY_ECONOMICS_SCHEMA_VERSION = "1.1"


class EvidenceType(str, Enum):
    FIXTURE = "FIXTURE"
    FACT = "FACT"
    PROXY = "PROXY"
    INFERENCE = "INFERENCE"


class EvidenceTier(str, Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    QUALITATIVE = "QUALITATIVE"


class SourceNature(str, Enum):
    REPORTED = "REPORTED"
    CALCULATED = "CALCULATED"
    DERIVED_PROXY = "DERIVED_PROXY"
    INFERRED = "INFERRED"


class Direction(str, Enum):
    ACCELERATING = "ACCELERATING"
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECELERATING = "DECELERATING"
    DETERIORATING = "DETERIORATING"
    UNKNOWN = "UNKNOWN"


class ConstraintDirection(str, Enum):
    EASING = "EASING"
    TIGHTENING = "TIGHTENING"
    STABLE = "STABLE"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class ImplicationState(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ValuationReviewState(str, Enum):
    SUPPORTED = "SUPPORTED"
    TOO_AGGRESSIVE = "TOO_AGGRESSIVE"
    TOO_CONSERVATIVE = "TOO_CONSERVATIVE"
    MIXED = "MIXED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class MarketExpectationState(str, Enum):
    ABOVE_SUPPORTED_ECONOMICS = "ABOVE_SUPPORTED_ECONOMICS"
    ROUGHLY_CONSISTENT = "ROUGHLY_CONSISTENT"
    BELOW_SUPPORTED_ECONOMICS = "BELOW_SUPPORTED_ECONOMICS"
    MIXED = "MIXED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _growth(current, prior):
    return current / prior - 1 if _number(current) and _number(prior) and prior != 0 else None


def _safe_delta_ratio(current_num, prior_num, current_den, prior_den):
    delta_den = current_den - prior_den if _number(current_den) and _number(prior_den) else None
    delta_num = current_num - prior_num if _number(current_num) and _number(prior_num) else None
    if not _number(delta_den) or not _number(delta_num) or delta_den <= 0:
        return None
    return delta_num / delta_den


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {str(_jsonable(k)): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


@dataclass
class CompanySnapshot:
    ticker: str
    company_name: str
    as_of: str
    sector: str = ""
    industry: str = ""
    business_description: str = ""
    security_type: str = "OPERATING_COMPANY"
    exchange: str = ""
    currency: str = ""
    country: str = ""
    quote_type: str = ""
    metrics: dict[str, float | None] = field(default_factory=dict)
    histories: dict[str, list[float]] = field(default_factory=dict)
    operational_metrics: dict[str, float | str | None] = field(default_factory=dict)
    periods: dict[str, str] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    source_nature: dict[str, SourceNature | str] = field(default_factory=dict)
    segments: list[dict] = field(default_factory=list)
    evidence_envelopes: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class EvidenceItem:
    id: str
    type: EvidenceType
    tier: EvidenceTier
    metric: str
    statement: str
    value: Any = None
    unit: str = ""
    period: str = "Unavailable"
    source: str = ""
    source_type: str = ""
    source_nature: SourceNature = SourceNature.REPORTED
    direction: Direction = Direction.UNKNOWN
    confidence: Confidence = Confidence.LOW
    related_driver: str | None = None
    related_constraint: str | None = None
    supporting_evidence_ids: list[str] = field(default_factory=list)
    source_id: str | None = None
    source_url: str | None = None
    provider_status: str = "OK"
    retrieved_at: str | None = None
    observation_date: str | None = None
    fiscal_period_start: str | None = None
    fiscal_period_end: str | None = None
    fiscal_year: int | str | None = None
    filing_date: str | None = None
    currency: str | None = None
    raw_concept: str | None = None
    normalized_concept: str | None = None
    transformation: str | None = None
    coverage_status: str = "COMPLETE"
    validation_status: str = "VALID"
    staleness_status: str = "UNKNOWN"
    limitation: str | None = None
    entity_identifier: str | None = None
    source_status: str = "HISTORICAL_REPORTED"
    source_locator: str | None = None
    extraction_method: str | None = None
    definition_version: str | None = None
    revision_status: str | None = None


@dataclass
class DataGap:
    missing_field: str
    related_driver: str | None
    related_constraint: str | None
    why_it_matters: str
    confidence_impact: str
    fallback_proxy_used: str | None = None


@dataclass
class BusinessModelClassification:
    primary_archetype: Archetype
    secondary_archetypes: list[Archetype]
    classification_confidence: Confidence
    routing_evidence: list[str]
    routing_evidence_ids: list[str] = field(default_factory=list)
    override_used: bool = False
    override_required: bool = False
    override_changes: list[str] = field(default_factory=list)


@dataclass
class GrowthDriver:
    primitive: GrowthPrimitive
    importance: str
    observability: EvidenceTier
    evidence_ids: list[str]
    confidence: Confidence


@dataclass
class GrowthArchitecture:
    primary_growth_equation: str
    primary_driver: GrowthDriver
    secondary_drivers: list[GrowthDriver]
    direct_evidence_ids: list[str]
    proxy_evidence_ids: list[str]
    confidence: Confidence


@dataclass
class ScalingMetric:
    name: str
    value: float | None
    unit: str
    current_period: str
    comparison_period: str | None
    interpretation: str
    evidence_id: str | None = None


@dataclass
class ScalingEconomics:
    metrics: list[ScalingMetric]
    interpretation: str
    confidence: Confidence


@dataclass
class ConstraintEvidence:
    constraint: ConstraintType
    supporting_evidence_ids: list[str]
    contrary_evidence_ids: list[str]
    data_gaps: list[DataGap]


@dataclass
class ConstraintDiagnosis:
    constraint: ConstraintType
    economic_mechanism: str
    supporting_evidence_ids: list[str]
    contrary_evidence_ids: list[str]
    direction: ConstraintDirection
    confidence: Confidence
    data_gaps: list[DataGap]
    inference: str
    inference_evidence_ids: list[str]
    constraint_status: str = "EVIDENCE_INSUFFICIENT"
    direction_status: str = "DIRECTION_UNKNOWN"


@dataclass
class ConstraintSet:
    primary_constraint: ConstraintDiagnosis
    secondary_constraints: list[ConstraintDiagnosis]
    candidate_constraints: list[ConstraintType]
    unknown_constraints: list[ConstraintType]
    constraint_interactions: list[str] = field(default_factory=list)
    previous_primary_constraint: str = "UNAVAILABLE"
    current_primary_constraint: str = "UNKNOWN"
    constraint_transition: str = "UNAVAILABLE"
    transition_confidence: Confidence = Confidence.INSUFFICIENT
    transition_evidence_ids: list[str] = field(default_factory=list)
    candidate_assessments: list[ConstraintDiagnosis] = field(default_factory=list)


@dataclass
class GrowthSustainability:
    current_revenue_growth: float | None
    primary_growth_engine: str
    primary_constraint: str
    constraint_direction: ConstraintDirection
    scaling_structure: str
    supporting_evidence_ids: list[str]
    contrary_evidence_ids: list[str]
    interpretation: str
    confidence: Confidence


@dataclass
class FalsificationCondition:
    condition: str
    observable_metric: str
    rationale: str
    evidence_ids: list[str]


@dataclass
class FinancialImplication:
    state: ImplicationState
    reason: str
    evidence_ids: list[str]


@dataclass
class FinancialTranslation:
    revenue_forecast: FinancialImplication
    margin: FinancialImplication
    capital_intensity: FinancialImplication
    fcff_conversion: FinancialImplication


@dataclass
class AssumptionReview:
    assumption: str
    dcf_value: float | str | None
    state: ValuationReviewState
    reason: str
    evidence_ids: list[str]


@dataclass
class ValuationAssumptionReview:
    reviews: list[AssumptionReview]
    mutates_dcf_inputs: bool = False


@dataclass
class MarketExpectationComparison:
    state: MarketExpectationState
    market_implied_revenue_cagr: float | None
    market_implied_fcff_margin: float | None
    observed_economics: str
    reason: str
    evidence_ids: list[str]


@dataclass
class ValidationResult:
    status: str
    checks: dict[str, bool]
    reasons: list[str]


@dataclass
class CompanyEconomicsProfile:
    company: dict[str, Any]
    classification: BusinessModelClassification
    core_economic_question: str
    growth_architecture: GrowthArchitecture
    constraints: ConstraintSet
    scaling_economics: ScalingEconomics
    growth_sustainability: GrowthSustainability
    falsification_conditions: list[FalsificationCondition]
    financial_translation: FinancialTranslation
    valuation_assumption_review: ValuationAssumptionReview
    market_expectations_comparison: MarketExpectationComparison
    data_gaps: list[DataGap]
    evidence_trace: list[EvidenceItem]
    economic_graph: dict[str, list[dict]]
    validation: ValidationResult
    data_quality: dict[str, Any] = field(default_factory=dict)
    qualitative_research_needed: bool = False
    qualitative_research_reason: str = ""
    company_economics_schema_version: str = COMPANY_ECONOMICS_SCHEMA_VERSION
    research_claims: list[dict[str, Any]] = field(default_factory=list)
    evidence_registry: dict[str, dict[str, Any]] = field(default_factory=dict)
    classification_version: str = "phase8.1-evidence-authority-v2"
    operational_research: dict[str, Any] = field(default_factory=dict)
    segments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        payload = _jsonable(self)
        if not payload.get("segments"):
            payload.pop("segments", None)
        return {"company_economics": payload}


class StructuredFinancialEvidenceProvider(ABC):
    @abstractmethod
    def collect(self, ticker: str) -> CompanySnapshot:
        raise NotImplementedError


class StructuredOperationalEvidenceProvider(ABC):
    @abstractmethod
    def enrich(self, snapshot: CompanySnapshot) -> CompanySnapshot:
        raise NotImplementedError


class QualitativeEvidenceProvider(ABC):
    @abstractmethod
    def collect(self, snapshot: CompanySnapshot) -> list[EvidenceItem]:
        raise NotImplementedError


class QualitativeCompanyEconomicsExtractor(QualitativeEvidenceProvider):
    """Gemini-backed filing extraction boundary; strictly optional and human-reviewed."""

    def __init__(self, candidate_store_path: Path | None = None):
        from qualitative_evidence import CANDIDATE_REGISTRY

        self.candidate_store_path = candidate_store_path or CANDIDATE_REGISTRY

    def collect(self, snapshot: CompanySnapshot) -> list[EvidenceItem]:
        if any("fixture" in str(src).lower() for src in snapshot.sources.values()):
            return []
        if not self.candidate_store_path.exists():
            return []
        try:
            payload = json.loads(self.candidate_store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        items: list[EvidenceItem] = []
        for idx, row in enumerate(payload.get("candidates") or [], start=1):
            if str(row.get("issuer", "")).upper() != snapshot.ticker.upper():
                continue
            if row.get("review_state") != "PENDING_REVIEW":
                continue
            items.append(
                EvidenceItem(
                    id=f"QE{idx}",
                    type=EvidenceType.FACT,
                    tier=EvidenceTier.QUALITATIVE,
                    metric=str(row.get("metric") or "unknown"),
                    statement=f"Machine-extracted {row.get('metric')} is {row.get('value')} ({row.get('unit')}); awaits documentary review.",
                    value=row.get("value"),
                    unit=str(row.get("unit") or ""),
                    period=str(row.get("reporting_period") or "Unavailable"),
                    source=str(row.get("source_title") or "SEC filing"),
                    source_type=str(row.get("source_type") or "issuer_sec_filing"),
                    source_nature=SourceNature.REPORTED,
                    confidence=Confidence.LOW,
                    source_id=str(row.get("id") or f"QE{idx}"),
                    source_url=row.get("source_url"),
                    observation_date=row.get("observation_date"),
                    fiscal_period_end=row.get("observation_date"),
                    filing_date=row.get("publication_date"),
                    validation_status="UNVERIFIED",
                    staleness_status="HISTORICAL",
                    limitation=row.get("limitation"),
                    entity_identifier=snapshot.ticker,
                    source_status="HISTORICAL_REPORTED",
                    source_locator=row.get("locator"),
                    extraction_method=row.get("extraction_method"),
                )
            )
        return items

    def extract(self, ticker: str | None = None, **kwargs):
        from qualitative_evidence import api_key_from_env, extract_live_for_ticker

        if not ticker:
            return {"status": "UNAVAILABLE", "reason": "A ticker symbol is required for filing extraction."}
        if not api_key_from_env():
            return {"status": "API_KEY_MISSING", "reason": "Set GEMINI_API_KEY (or GOOGLE_API_KEY) to run live Gemini filing extraction."}
        return extract_live_for_ticker(ticker, **kwargs)


class ExistingStructuredFinancialProvider(StructuredFinancialEvidenceProvider):
    """Adapter over the existing valuation collector; collection happens once."""

    def collect(self, ticker: str) -> CompanySnapshot:
        from intrinsic_valuation import collect_valuation_data

        return snapshot_from_valuation_data(collect_valuation_data(ticker))


class NoOpOperationalProvider(StructuredOperationalEvidenceProvider):
    def enrich(self, snapshot: CompanySnapshot) -> CompanySnapshot:
        return snapshot



def sec_bank_balances(ticker: str, facts: dict | None = None) -> dict[str, float]:
    """Deposits, loans and their growth from a year earlier, from SEC company facts (the same reading as the card's
    operating signals). Returns only what the filings report."""
    try:
        import operating_metrics as om
        if facts is None:
            from growth_inputs import sec_facts
            facts = sec_facts(ticker)
        signals = {item["key"]: item for item in om.operating_signals(facts, "BANK").get("signals") or []}
        out: dict[str, float] = {}
        for key in ("deposits", "loans"):
            rows, _ = om._rows(facts, om.METRICS[key][1])
            if rows and key in signals:
                latest = max(rows, key=lambda row: (row["end"], row.get("filed", "")))
                out[key] = float(latest["val"])
                out[f"{key[:-1]}_growth"] = float(signals[key]["change"])
        return out
    except Exception:  # noqa: BLE001 - missing SEC data stays missing
        return {}

def snapshot_from_valuation_data(data: dict) -> CompanySnapshot:
    info = data.get("info") or {}
    revenue = data.get("revenue_history") or []
    op_income = data.get("operating_income_history") or []
    income, cashflow, balance = data.get("income"), data.get("cashflow"), data.get("balance")

    def values(frame, *names):
        if frame is None or getattr(frame, "empty", False):
            return []
        for name in names:
            if name in frame.index:
                return [float(item) for item in frame.loc[name].tolist() if _number(item)]
        return []

    def latest_and_growth(frame, *names):
        history = values(frame, *names)
        return (history[0] if history else None, _growth(history[0], history[1]) if len(history) > 1 else None, history)

    fcf = values(cashflow, "Free Cash Flow")
    ocf = values(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex_history = [abs(item) for item in values(cashflow, "Capital Expenditure", "Capital Expenditures")]
    inventory, inventory_growth, inventory_history = latest_and_growth(balance, "Inventory")
    assets, asset_growth, asset_history = latest_and_growth(balance, "Total Assets")
    deposits, deposit_growth, deposit_history = latest_and_growth(balance, "Total Deposits")
    loans, loan_growth, loan_history = latest_and_growth(balance, "Net Loans", "Loans Receivable")
    current_fcf = data.get("latest_fcf")
    provider_growth = info.get("revenueGrowth")
    provider_margin = info.get("operatingMargins")
    metrics = {
        "revenue": data.get("latest_revenue"),
        "revenue_growth": provider_growth if _number(provider_growth) else (_growth(revenue[0], revenue[1]) if len(revenue) > 1 else None),
        "gross_margin": info.get("grossMargins"),
        "operating_income": data.get("latest_operating_income"),
        "operating_margin": provider_margin if _number(provider_margin) else (data.get("latest_operating_income") / data.get("latest_revenue") if _number(data.get("latest_operating_income")) and _number(data.get("latest_revenue")) and data["latest_revenue"] else None),
        "fcf": current_fcf,
        "fcf_margin": current_fcf / data.get("latest_revenue") if _number(current_fcf) and _number(data.get("latest_revenue")) and data["latest_revenue"] else None,
        "capex": data.get("latest_capex"),
        "capex_growth": _growth(capex_history[0], capex_history[1]) if len(capex_history) > 1 else None,
        "operating_cash_flow": data.get("latest_ocf"),
        "net_income": data.get("latest_net_income"),
        "sbc": data.get("sbc"),
        "cash": data.get("cash"),
        "debt": data.get("debt"),
        "shares": data.get("shares"),
        "beta": data.get("beta"),
        "enterprise_value": info.get("enterpriseValue"),
        "employees": info.get("fullTimeEmployees"),
        "inventory": inventory if _number(inventory) else info.get("inventory"),
        "inventory_growth": inventory_growth,
        "assets": assets if _number(assets) else info.get("totalAssets"),
        "asset_growth": asset_growth,
        "deposits": deposits,
        "deposit_growth": deposit_growth,
        "loans": loans,
        "loan_growth": loan_growth,
        "net_interest_margin": info.get("netInterestMargin"),
        "market_cap": data.get("market_cap"),
    }
    if not fcf and _number(current_fcf):
        fcf.append(current_fcf)
    histories = {
        "revenue": revenue,
        "operating_income": op_income,
        "fcf": fcf,
        "operating_cash_flow": ocf,
        "capex": capex_history,
        "inventory": inventory_history,
        "assets": asset_history,
        "deposits": deposit_history,
        "loans": loan_history,
    }
    source = str(data.get("provider") or "Yahoo Finance financial statement via yfinance")
    sources = {key: source for key in metrics}
    # Gap scan 2026-11-27: Yahoo has no deposit or loan rows for banks such as JPM, so loan and deposit growth showed as
    # unavailable. The SEC figures the judgment card already reads fill them; when the SEC has none either, they stay missing.
    if data.get("security_type") in ("FINANCIAL_INSTITUTION", "BANK") and not _number(metrics.get("deposits")) and not _number(metrics.get("loans")):
        sec = sec_bank_balances(str(data.get("ticker") or ""))
        for key, value in sec.items():
            metrics[key] = value
            sources[key] = "SEC company facts (10-K/10-Q)"
    return CompanySnapshot(
        ticker=data.get("ticker", "").upper(), company_name=data.get("company") or data.get("ticker", ""), as_of=data.get("as_of") or dt.datetime.now().astimezone().isoformat(),
        sector=str(info.get("sector") or ""), industry=str(info.get("industry") or ""), business_description=str(info.get("longBusinessSummary") or ""), security_type=data.get("security_type", "OPERATING_COMPANY"),
        exchange=str(info.get("fullExchangeName") or info.get("exchange") or ""), currency=str(data.get("currency") or info.get("currency") or ""),
        country=str(info.get("country") or ""), quote_type=str(info.get("quoteType") or ""),
        metrics=metrics, histories=histories, periods=data.get("periods") or {},
        sources=sources,
        source_nature={
            "revenue_growth": SourceNature.REPORTED if _number(provider_growth) else SourceNature.CALCULATED,
            "operating_margin": SourceNature.REPORTED if _number(provider_margin) else SourceNature.CALCULATED,
            "fcf_margin": SourceNature.CALCULATED,
        },
        segments=list(data.get("segments") or []),
        evidence_envelopes=data.get("evidence_envelopes") or {},
    )


def snapshot_from_resolved_security(resolved: dict) -> CompanySnapshot:
    """Normalize the security object already collected by the legacy CLI."""
    info = resolved.get("info") or {}
    income, cashflow = resolved.get("income"), resolved.get("cashflow")

    def values(frame, *names):
        if frame is None:
            return []
        for name in names:
            if name in frame.index:
                return [float(x) for x in frame.loc[name].tolist() if _number(x)]
        return []

    revenue = values(income, "Total Revenue", "Operating Revenue")
    operating = values(income, "Operating Income", "Pretax Income")
    fcf = values(cashflow, "Free Cash Flow")
    capex = values(cashflow, "Capital Expenditure", "Capital Expenditures")
    current_revenue = revenue[0] if revenue else info.get("totalRevenue")
    current_operating = operating[0] if operating else None
    current_fcf = fcf[0] if fcf else info.get("freeCashflow")
    metrics = {
        "revenue": current_revenue,
        "revenue_growth": info.get("revenueGrowth") if _number(info.get("revenueGrowth")) else (_growth(revenue[0], revenue[1]) if len(revenue) > 1 else None),
        "gross_margin": info.get("grossMargins"), "operating_income": current_operating,
        "operating_margin": info.get("operatingMargins"), "fcf": current_fcf,
        "fcf_margin": current_fcf / current_revenue if _number(current_fcf) and _number(current_revenue) and current_revenue else None,
        "capex": abs(capex[0]) if capex else None, "employees": info.get("fullTimeEmployees"),
        "inventory": info.get("inventory"), "assets": info.get("totalAssets"), "market_cap": info.get("marketCap"),
    }
    return CompanySnapshot(
        resolved.get("ticker", "").upper(), resolved.get("name") or info.get("longName") or resolved.get("ticker", ""), resolved.get("as_of") or dt.datetime.now().astimezone().isoformat(),
        str(info.get("sector") or ""), str(info.get("industry") or ""), str(info.get("longBusinessSummary") or ""),
        security_type=str(resolved.get("security_type") or "OPERATING_COMPANY"), exchange=str(resolved.get("exchange") or info.get("fullExchangeName") or info.get("exchange") or ""),
        currency=str(resolved.get("currency") or info.get("currency") or ""), country=str(info.get("country") or ""), quote_type=str(info.get("quoteType") or ""),
        metrics=metrics, histories={"revenue": revenue, "operating_income": operating, "fcf": fcf},
        periods={"revenue": "Latest provider statement periods", "operating_income": "Latest provider statement periods", "fcf": "Latest provider statement periods"},
        sources={key: resolved.get("provider", "structured financial provider") for key in metrics},
        source_nature={
            "revenue_growth": SourceNature.REPORTED if _number(info.get("revenueGrowth")) else SourceNature.CALCULATED,
            "fcf_margin": SourceNature.CALCULATED,
        },
    )


class BusinessModelClassifier:
    # Patterns are economic metadata, never ticker identities.  Industry matches
    # receive more weight than broad prose matches so generic words such as
    # "platform" or "cloud" cannot determine a route on their own.
    RULES = {
        Archetype.ENTERPRISE_AI_SOFTWARE: (("artificial intelligence platform", "enterprise data platform", "data analytics platform"), ("software - infrastructure",)),
        Archetype.TRADITIONAL_SAAS: (("software as a service", "subscription software", "customer relationship management", "enterprise application software"), ("software - application", "software - infrastructure", "prepackaged software")),
        Archetype.FABLESS_SEMICONDUCTOR: (("fabless", "designs processors", "designs and develops semiconductor", "microprocessor", "graphics processor", "accelerator"), ("semiconductors",)),
        Archetype.SEMICONDUCTOR_FOUNDRY: (("semiconductor foundry", "wafer fabrication", "contract semiconductor manufacturing", "integrated device manufacturing"), ()),
        # Checklist 9.3: equipment makers sell to fabs; they are not foundries.
        Archetype.SEMICONDUCTOR_EQUIPMENT: (("wafer fabrication equipment", "semiconductor equipment", "manufacturing equipment, services and software", "deposition", "etch", "lithography", "process control"), ("semiconductor equipment & materials",)),
        Archetype.HYPERSCALER_CLOUD_PLATFORM: (("cloud computing platform", "cloud infrastructure", "hyperscale", "data center platform"), ("internet services & infrastructure",)),
        Archetype.CONSUMER_PLATFORM: (("social network", "social media", "digital advertising", "family of apps", "consumer platform"), ("internet content & information",)),
        Archetype.RETAIL_PHYSICAL_NETWORK: (("warehouse club", "retail stores", "retail locations", "supercenter", "grocery stores"), ("discount stores", "department stores", "grocery stores", "retail-variety stores")),
        # Checklist 11.1: consumer lenders (personal / student / home loans, deposit accounts) are banks, not payment networks.
        Archetype.BANK: (("bank holding company", "banking services", "deposits and lending", "commercial banking", "checking and savings accounts", "personal loans", "student loans", "home loans"), ("banks - diversified", "banks - regional", "national commercial banks", "state commercial banks")),
        Archetype.INDUSTRIAL: (("industrial machinery", "heavy machinery", "construction equipment", "aerospace systems", "manufacturing company"), ("farm & heavy construction machinery", "specialty industrial machinery", "aerospace & defense", "construction machinery", "industrial machinery", "auto manufacturers", "motor vehicles")),
        Archetype.PHARMA_BIOTECH: (("pharmaceutical", "biopharmaceutical", "biotechnology", "drug portfolio", "therapeutic"), ("drug manufacturers", "biotechnology", "pharmaceutical preparations")),
        Archetype.COMMODITY_PRODUCER: (("oil and gas", "exploration and production", "integrated energy", "mining company", "commodity producer"), ("oil & gas integrated", "oil & gas e&p", "gold", "copper", "petroleum refining", "crude petroleum")),
        Archetype.PAYMENT_NETWORK: (("payment network", "payments technology", "transaction processing network", "digital payments"), ("credit services",)),
        Archetype.MARKETPLACE_PLATFORM: (("marketplace", "ride sharing", "ridesharing", "delivery platform", "two-sided platform", "mobility platform"), ("internet retail",)),
        Archetype.UTILITY_INFRASTRUCTURE: (("regulated utility", "electric utility", "gas utility", "infrastructure operator", "rate base"), ("utilities - regulated electric", "utilities - diversified")),
    }

    NEEDS_METADATA_MATCH = {Archetype.RETAIL_PHYSICAL_NETWORK}

    SECTOR_SIGNALS = {
        Archetype.BANK: ("financial services",),
        Archetype.PHARMA_BIOTECH: ("healthcare",),
        Archetype.COMMODITY_PRODUCER: ("energy", "basic materials"),
        Archetype.INDUSTRIAL: ("industrials",),
        Archetype.UTILITY_INFRASTRUCTURE: ("utilities",),
        Archetype.RETAIL_PHYSICAL_NETWORK: ("consumer defensive", "consumer cyclical"),
    }

    def classify(self, snapshot: CompanySnapshot) -> BusinessModelClassification:
        description = snapshot.business_description.lower()
        industry = snapshot.industry.lower()
        sector = snapshot.sector.lower()
        scores: dict[Archetype, int] = {a: 0 for a in Archetype}
        evidence: dict[Archetype, list[str]] = {a: [] for a in Archetype}
        for archetype, (description_patterns, industry_patterns) in self.RULES.items():
            for pattern in description_patterns:
                if pattern in description:
                    scores[archetype] += 2
                    evidence[archetype].append(f"business description contains '{pattern}'")
            for pattern in industry_patterns:
                if pattern in industry:
                    scores[archetype] += 3
                    evidence[archetype].append(f"industry matches '{pattern}'")
        # Checklist 11.1: the consumer sectors span car makers, restaurants, apparel and retailers, so for
        # retail the sector only reinforces a description or industry match; alone it routed Tesla to warehouse retail.
        for archetype, patterns in self.SECTOR_SIGNALS.items():
            if archetype in self.NEEDS_METADATA_MATCH and scores[archetype] == 0:
                continue
            if any(pattern in sector for pattern in patterns):
                scores[archetype] += 1
                evidence[archetype].append(f"sector '{snapshot.sector}' is consistent with the archetype")
        margin = snapshot.metrics.get("gross_margin")
        capex = snapshot.metrics.get("capex")
        revenue = snapshot.metrics.get("revenue")
        if _number(margin) and margin >= 0.65:
            for archetype in (Archetype.ENTERPRISE_AI_SOFTWARE, Archetype.TRADITIONAL_SAAS, Archetype.PAYMENT_NETWORK):
                if scores[archetype] > 0:
                    scores[archetype] += 1
                    evidence[archetype].append("high gross margin reinforces the metadata route's asset-light economics")
        if _number(capex) and _number(revenue) and revenue and capex / revenue >= 0.15:
            for archetype in (Archetype.SEMICONDUCTOR_FOUNDRY, Archetype.HYPERSCALER_CLOUD_PLATFORM, Archetype.UTILITY_INFRASTRUCTURE, Archetype.COMMODITY_PRODUCER):
                if scores[archetype] > 0:
                    scores[archetype] += 1
                    evidence[archetype].append("capex intensity reinforces the metadata route's physical capacity economics")
        if "semiconductor" in industry and "equipment" not in industry:
            capex_intensity = capex / revenue if _number(capex) and _number(revenue) and revenue else None
            foundry_language = any(word in description for word in ("foundry", "wafer fabrication", "manufactures semiconductors"))
            if foundry_language or (_number(capex_intensity) and capex_intensity >= 0.20):
                scores[Archetype.SEMICONDUCTOR_FOUNDRY] += 3
                evidence[Archetype.SEMICONDUCTOR_FOUNDRY].append("semiconductor manufacturing language or high capex intensity indicates owned fabrication")
            else:
                scores[Archetype.FABLESS_SEMICONDUCTOR] += 2
                evidence[Archetype.FABLESS_SEMICONDUCTOR].append("semiconductor industry with no owned-foundry signal is consistent with design economics")
        natural_ranked = sorted(scores, key=lambda key: scores[key], reverse=True)
        natural_primary = natural_ranked[0] if scores[natural_ranked[0]] > 0 else Archetype.GENERIC_OPERATING_COMPANY
        override = COMPANY_ECONOMICS_OVERRIDES.get(snapshot.ticker, {})
        preferred = override.get("preferred_archetype")
        override_changes = []
        override_required = False
        if preferred:
            candidate = Archetype(preferred)
            before = natural_primary
            scores[candidate] += 4
            evidence[candidate].append("declarative company routing preference")
            override_changes.append(f"preferred_archetype: {before.value} -> {candidate.value}")
            override_required = before != candidate
        if override.get("constraint_priority"):
            override_changes.append("constraint_priority: " + ", ".join(override["constraint_priority"]))
        # Checklist 11.7: a declared preference wins ties. MSFT's Yahoo industry ("Software - Infrastructure")
        # tied enterprise AI software with its hyperscaler preference, and enum order picked the wrong one.
        preferred_archetype = Archetype(preferred) if preferred else None
        ranked = sorted(scores, key=lambda key: (scores[key], key == preferred_archetype), reverse=True)
        primary = ranked[0] if scores[ranked[0]] > 0 else Archetype.GENERIC_OPERATING_COMPANY
        explicit_secondary = [Archetype(item) for item in override.get("secondary_archetypes", [])]
        if explicit_secondary:
            override_changes.append("secondary_archetypes: " + ", ".join(item.value for item in explicit_secondary))
        secondary = list(dict.fromkeys(explicit_secondary + [item for item in ranked[1:4] if scores[item] >= 4 and scores[item] >= scores[primary] - 3]))
        route = evidence[primary] or ["insufficient evidence for a narrower archetype; generic fallback used"]
        confidence = Confidence.HIGH if scores[primary] >= 7 and len(route) >= 2 else Confidence.MODERATE if scores[primary] >= 3 else Confidence.LOW
        return BusinessModelClassification(primary, secondary, confidence, route, override_used=bool(override), override_required=override_required, override_changes=override_changes)


class EvidenceLedger:
    def __init__(self):
        self.items: list[EvidenceItem] = []

    def add(self, **kwargs) -> EvidenceItem:
        item = EvidenceItem(id=f"E{len(self.items) + 1}", **kwargs)
        self.items.append(item)
        return item

    def ids_for(self, metric_names: tuple[str, ...] | list[str], types=None):
        allowed = set(types) if types else None
        return [item.id for item in self.items if item.metric in metric_names and (allowed is None or item.type in allowed)]


def _metric_direction(name, value):
    if not _number(value):
        return Direction.UNKNOWN
    if "growth" in name or "change" in name:
        return Direction.IMPROVING if value > 0.01 else Direction.DETERIORATING if value < -0.01 else Direction.STABLE
    if "retention" in name:
        return Direction.IMPROVING if value > 1.0 else Direction.DETERIORATING if value < 0.95 else Direction.STABLE
    return Direction.UNKNOWN


def collect_base_evidence(snapshot: CompanySnapshot, ledger: EvidenceLedger):
    identity = {"ticker": snapshot.ticker, "company_name": snapshot.company_name, "sector": snapshot.sector or None, "industry": snapshot.industry or None, "business_description": snapshot.business_description or None}
    from operational_research import load_series
    series_ids = {definition.id for definition, _ in load_series(snapshot.ticker)}
    aliases = {"customers": "pltr_customers", "wafer_volume": "tsm_shipments", "advanced_node_mix": "tsm_node_mix"}
    for name, value in {**identity, **snapshot.metrics, **snapshot.operational_metrics}.items():
        if value is None:
            continue
        if aliases.get(name) in series_ids:
            continue
        operational = name in snapshot.operational_metrics
        unit = "decimal" if any(word in name for word in ("growth", "margin", "rate", "yield", "utilization", "mix")) else "count" if name in {"employees", "customers", "users", "members", "store_count"} else "currency"
        nature = snapshot.source_nature.get(name, SourceNature.REPORTED)
        nature = nature if isinstance(nature, SourceNature) else SourceNature(nature)
        envelope = snapshot.evidence_envelopes.get(name, {})
        unit = envelope.get("unit") or ("text" if isinstance(value, str) else "shares" if name == "shares" else "employees" if name in {"employees", "deployment_headcount"} else "units" if name == "units" else "unknown" if name in {"wafer_volume", "fab_capacity"} else unit)
        fixture = envelope.get("source_status") == "FIXTURE" or "fixture" in snapshot.sources.get(name, "").lower()
        ledger.add(
            type=EvidenceType.FIXTURE if fixture else EvidenceType.FACT, tier=EvidenceTier.INDIRECT if fixture else EvidenceTier.DIRECT, metric=name,
            statement=f"{name.replace('_', ' ').title()} {'is a synthetic fixture value of' if fixture else 'is reported as'} {value}.", value=value, unit=unit,
            period=snapshot.periods.get(name, snapshot.periods.get("revenue", "Latest available period")),
            source=snapshot.sources.get(name, "structured operational fixture" if operational else "security resolution / structured financial provider"),
            source_type=envelope.get("source_type", "fixture" if "fixture" in snapshot.sources.get(name, "") else "structured_data"),
            source_nature=nature, direction=_metric_direction(name, value), confidence=Confidence.HIGH,
            source_id=envelope.get("source_id"), source_url=envelope.get("source_url"),
            provider_status=envelope.get("provider_status", "OK"), retrieved_at=envelope.get("retrieved_at"),
            observation_date=envelope.get("observation_date"), fiscal_period_start=envelope.get("fiscal_period_start"),
            fiscal_period_end=envelope.get("fiscal_period_end"), fiscal_year=envelope.get("fiscal_year"),
            filing_date=envelope.get("filing_date"), currency=envelope.get("currency") or snapshot.currency or None,
            raw_concept=envelope.get("raw_concept"), normalized_concept=envelope.get("normalized_concept") or name,
            transformation=envelope.get("transformation"), coverage_status=envelope.get("coverage_status", "COMPLETE"),
            validation_status=envelope.get("validation_status", "VALID"), staleness_status=envelope.get("staleness_status", "UNKNOWN"),
            limitation=envelope.get("limitation"), entity_identifier=envelope.get("entity_identifier") or snapshot.ticker,
            source_status=envelope.get("source_status", "FIXTURE" if "fixture" in snapshot.sources.get(name, "") else "HISTORICAL_REPORTED"),
        )
    for seg in snapshot.segments or []:
        seg_id = seg.get("segment_id") or "segment"
        seg_name = seg.get("segment_name") or seg_id
        rev = seg.get("revenue")
        if _number(rev):
            growth = seg.get("revenue_growth")
            ledger.add(
                type=EvidenceType.FACT,
                tier=EvidenceTier.DIRECT,
                metric=f"segment:{seg_id}:revenue",
                statement=f"Segment '{seg_name}' revenue is reported as {rev}.",
                value=rev,
                unit="currency",
                period=str(seg.get("period_end") or snapshot.periods.get("revenue", "Latest available period")),
                source=f"SEC {seg.get('form', '10-K')} XBRL segment disclosure",
                source_type="structured_regulatory_data",
                source_nature=SourceNature.REPORTED,
                direction=_metric_direction("revenue_growth", growth) if _number(growth) else Direction.UNKNOWN,
                confidence=Confidence.HIGH,
                source_id=f"sec-seg:{snapshot.ticker}:{seg.get('accession_number', '')}:{seg_id}:revenue",
                source_url=seg.get("source_url"),
                observation_date=seg.get("period_end"),
                fiscal_period_start=seg.get("period_start"),
                fiscal_period_end=seg.get("period_end"),
                filing_date=seg.get("filing_date"),
                currency=seg.get("currency") or snapshot.currency or None,
                raw_concept=seg.get("revenue_concept"),
                normalized_concept=f"segment_revenue:{seg_id}",
                transformation="Single-axis StatementBusinessSegmentsAxis/SegmentsAxis annual fact",
                entity_identifier=snapshot.ticker,
                source_status="HISTORICAL_REPORTED",
                source_locator=seg.get("xbrl_member"),
                extraction_method="deterministic_xbrl_segment_axis",
            )


class GrowthArchitectureBuilder:
    DRIVER_KPIS = {
        GrowthPrimitive.CUSTOMERS: ("customers", "customer_growth", "pltr_customers"), GrowthPrimitive.USERS: ("users", "user_growth"), GrowthPrimitive.SUBSCRIBERS: ("subscribers", "subscriber_growth"),
        GrowthPrimitive.SEATS: ("seats", "seat_growth"), GrowthPrimitive.ARPU: ("arpu", "arpu_growth"), GrowthPrimitive.REVENUE_PER_CUSTOMER: ("revenue_per_customer",),
        GrowthPrimitive.PRICING: ("pricing", "same_store_sales"), GrowthPrimitive.VOLUME: ("volume", "volume_growth"), GrowthPrimitive.UNITS: ("units", "unit_growth"),
        GrowthPrimitive.ASP: ("asp", "asp_growth"), GrowthPrimitive.PRODUCT_MIX: ("product_mix", "advanced_node_mix"), GrowthPrimitive.STORE_COUNT: ("store_count", "store_growth"),
        GrowthPrimitive.SAME_STORE_SALES: ("same_store_sales",), GrowthPrimitive.MEMBERSHIP: ("members", "membership_growth"), GrowthPrimitive.WORKLOADS: ("workloads", "cloud_growth"),
        GrowthPrimitive.CLOUD_SPEND: ("cloud_spend", "cloud_growth"), GrowthPrimitive.TRANSACTION_VOLUME: ("payment_volume", "transaction_growth"), GrowthPrimitive.TAKE_RATE: ("take_rate",),
        GrowthPrimitive.ASSETS: ("assets", "asset_growth"), GrowthPrimitive.NET_INTEREST_SPREAD: ("net_interest_margin",), GrowthPrimitive.FEES: ("fees", "fee_growth"),
        GrowthPrimitive.WAFER_VOLUME: ("wafer_volume",), GrowthPrimitive.NODE_MIX: ("advanced_node_mix",), GrowthPrimitive.CAPACITY: ("capacity", "capacity_growth"),
        GrowthPrimitive.UTILIZATION: ("utilization",), GrowthPrimitive.BACKLOG: ("backlog", "backlog_growth"), GrowthPrimitive.PATIENTS: ("patients", "patient_growth"),
        GrowthPrimitive.DRUG_PORTFOLIO: ("pipeline_milestones", "drug_portfolio"), GrowthPrimitive.PRODUCTION_VOLUME: ("production_volume",), GrowthPrimitive.COMMODITY_PRICE: ("realized_price",),
        GrowthPrimitive.ENGAGEMENT: ("engagement",), GrowthPrimitive.AD_INVENTORY: ("ad_inventory",), GrowthPrimitive.GROSS_BOOKINGS: ("gross_bookings", "bookings_growth"),
        GrowthPrimitive.CUSTOMER_CAPEX: ("wfe_spend", "customer_capex"), GrowthPrimitive.INSTALLED_BASE: ("installed_base", "services_revenue"),
    }

    def build(self, classification, ledger, gaps):
        definition = ARCHETYPE_REGISTRY[classification.primary_archetype]
        drivers = []
        for index, primitive in enumerate(definition.growth_engines):
            ids = ledger.ids_for(self.DRIVER_KPIS.get(primitive, ()), [EvidenceType.FACT])
            if not ids:
                gaps.append(DataGap(self.DRIVER_KPIS.get(primitive, (primitive.value.lower(),))[0], primitive.value, None, "Direct observation would confirm the growth equation component.", "Driver confidence remains LOW.", "revenue growth" if ledger.ids_for(("revenue_growth",)) else None))
            drivers.append(GrowthDriver(primitive, "PRIMARY" if index == 0 else "SECONDARY", EvidenceTier.DIRECT if ids else EvidenceTier.INDIRECT, ids, Confidence.HIGH if len(ids) >= 2 else Confidence.MODERATE if ids else Confidence.LOW))
        if not drivers:
            drivers = [GrowthDriver(GrowthPrimitive.VOLUME, "PRIMARY", EvidenceTier.INDIRECT, [], Confidence.INSUFFICIENT)]
        direct = [item for driver in drivers for item in driver.evidence_ids]
        proxies = ledger.ids_for(("revenue_growth",), [EvidenceType.FACT, EvidenceType.PROXY])
        confidence = Confidence.MODERATE if direct else Confidence.LOW if proxies else Confidence.INSUFFICIENT
        return GrowthArchitecture(definition.equation, drivers[0], drivers[1:], direct, proxies, confidence)


class ScalingEconomicsAnalyzer:
    def analyze(self, snapshot, classification, ledger, gaps):
        m, h, p = snapshot.metrics, snapshot.histories, snapshot.periods
        calculations: dict[str, tuple[float | None, str, str]] = {}
        revenue, employees, capex, assets, fcf = m.get("revenue"), m.get("employees"), m.get("capex"), m.get("assets"), m.get("fcf")
        calculations["revenue_per_employee"] = (revenue / employees if _number(revenue) and _number(employees) and employees > 0 else None, "currency/employee", "Revenue generated per employee")
        calculations["fcf_per_employee"] = (fcf / employees if _number(fcf) and _number(employees) and employees > 0 else None, "currency/employee", "Free cash flow generated per employee")
        calculations["revenue_per_capex"] = (revenue / capex if _number(revenue) and _number(capex) and capex > 0 else None, "multiple", "Revenue supported per unit of current capex")
        calculations["revenue_per_assets"] = (revenue / assets if _number(revenue) and _number(assets) and assets > 0 else None, "multiple", "Asset turnover")
        revenues, operating, fcfs = h.get("revenue", []), h.get("operating_income", []), h.get("fcf", [])
        calculations["incremental_operating_margin"] = (_safe_delta_ratio(operating[0], operating[1], revenues[0], revenues[1]) if len(operating) > 1 and len(revenues) > 1 else None, "decimal", "Change in operating income divided by positive change in revenue")
        calculations["incremental_fcf_margin"] = (_safe_delta_ratio(fcfs[0], fcfs[1], revenues[0], revenues[1]) if len(fcfs) > 1 and len(revenues) > 1 else None, "decimal", "Change in FCF divided by positive change in revenue")
        for growth_name, base_name in (("employee_growth", "employees"), ("capex_growth", "capex"), ("inventory_growth", "inventory"), ("asset_growth", "assets")):
            gap_name = f"revenue_growth_minus_{growth_name}"
            calculations[gap_name] = (m.get("revenue_growth") - m.get(growth_name) if _number(m.get("revenue_growth")) and _number(m.get(growth_name)) else None, "decimal", f"Revenue growth less {base_name} growth")
        definition = ARCHETYPE_REGISTRY[classification.primary_archetype]
        relevant = set(definition.scaling_metrics)
        relevant.update({name for name in calculations if name in definition.proxy_kpis})
        output = []
        for name in sorted(relevant):
            value, unit, interpretation = calculations.get(name, (m.get(name), "decimal", name.replace("_", " ").title()))
            evidence_id = None
            if _number(value):
                nature = SourceNature.DERIVED_PROXY if "_minus_" in name else SourceNature.CALCULATED
                evidence = ledger.add(type=EvidenceType.PROXY, tier=EvidenceTier.INDIRECT, metric=name, statement=f"{name.replace('_', ' ').title()} is {value:.4f}.", value=value, unit=unit, period=p.get("revenue", "Latest available period"), source="calculated from normalized company snapshot", source_type="calculation", source_nature=nature, direction=_metric_direction(name, value), confidence=Confidence.MODERATE)
                if any("fixture" in source.lower() for source in snapshot.sources.values()):
                    evidence.source_status = "FIXTURE"
                    evidence.limitation = "Calculated from synthetic fixture financials; not an observed company fact."
                evidence_id = evidence.id
            else:
                gaps.append(DataGap(name, None, None, "Required to evaluate archetype-specific scaling economics.", "Scaling confidence is reduced.", None))
            output.append(ScalingMetric(name, value, unit, p.get("revenue", "Latest available period"), "Prior comparable period" if len(revenues) > 1 else None, interpretation, evidence_id))
        available = [item for item in output if _number(item.value)]
        if any("fixture" in source.lower() for source in snapshot.sources.values()):
            text, confidence = "Synthetic fixture scaling metrics are illustrative, not observed company economics.", Confidence.INSUFFICIENT
        elif not available:
            text, confidence = "Relevant scaling metrics are unavailable; no scaling conclusion is forced.", Confidence.INSUFFICIENT
        else:
            positive = [item for item in available if ("minus" in item.name or "incremental" in item.name) and item.value > 0]
            text = "Available archetype-relevant metrics indicate improving scaling." if positive else "Available scaling evidence is mixed or level-only; operating leverage needs confirmation."
            confidence = Confidence.MODERATE if len(available) >= 2 else Confidence.LOW
        return ScalingEconomics(output, text, confidence)


class ConstraintEvidenceCollector:
    def collect(self, constraint, ledger):
        definition = CONSTRAINT_REGISTRY[constraint]
        supporting, contrary = [], []
        ids = ledger.ids_for(definition.direct_kpis + definition.proxy_kpis)
        for evidence_id in ids:
            item = next(x for x in ledger.items if x.id == evidence_id)
            if item.source_status == "FIXTURE" or item.type == EvidenceType.FIXTURE:
                continue
            if item.direction == Direction.DETERIORATING:
                contrary.append(evidence_id)
            else:
                supporting.append(evidence_id)
        gaps = []
        if not ledger.ids_for(definition.direct_kpis):
            field_name = definition.direct_kpis[0] if definition.direct_kpis else f"direct_{constraint.value.lower()}_kpi"
            fallback = definition.proxy_kpis[0] if ledger.ids_for(definition.proxy_kpis) else None
            gaps.append(DataGap(field_name, None, constraint.value, "A direct KPI would distinguish the limiting mechanism from correlated financial outcomes.", "Constraint confidence cannot be HIGH.", fallback))
        return ConstraintEvidence(constraint, supporting, contrary, gaps)


class ConstraintClassifier:
    def candidates(self, snapshot, classification):
        definition = ARCHETYPE_REGISTRY[classification.primary_archetype]
        ordered = [ConstraintType(item) for item in COMPANY_ECONOMICS_OVERRIDES.get(snapshot.ticker, {}).get("constraint_priority", [])]
        for item in definition.primary_constraints + definition.secondary_constraints:
            if item not in ordered:
                ordered.append(item)
        return ordered or [ConstraintType.UNKNOWN]


class ConstraintDiagnosisEngine:
    def __init__(self):
        self.collector = ConstraintEvidenceCollector()

    def _direction(self, evidence, ledger):
        items = [next(x for x in ledger.items if x.id == eid) for eid in evidence.supporting_evidence_ids + evidence.contrary_evidence_ids]
        explicit = [x.value for x in items if x.metric.endswith("constraint_direction") and isinstance(x.value, str)]
        if explicit:
            try: return ConstraintDirection(explicit[0])
            except ValueError: pass
        # Metric movement is not bottleneck movement. No demand/capacity
        # sufficiency rule has been approved; retain unknown instead.
        return ConstraintDirection.UNKNOWN

    def diagnose(self, candidates, ledger):
        diagnoses = []
        for constraint in candidates:
            evidence = self.collector.collect(constraint, ledger)
            direction = self._direction(evidence, ledger)
            count = len(evidence.supporting_evidence_ids) + len(evidence.contrary_evidence_ids)
            direct_count = len(ledger.ids_for(CONSTRAINT_REGISTRY[constraint].direct_kpis))
            confidence = Confidence.HIGH if direct_count >= 2 and count >= 3 else Confidence.MODERATE if direct_count and count >= 2 else Confidence.LOW if count else Confidence.INSUFFICIENT
            refs = evidence.supporting_evidence_ids + evidence.contrary_evidence_ids
            direct_ids = [eid for eid in ledger.ids_for(CONSTRAINT_REGISTRY[constraint].direct_kpis) if any(x.id == eid and x.type == EvidenceType.FACT and x.source_status != "FIXTURE" for x in ledger.items)]
            proxy_ids = [item for item in evidence.supporting_evidence_ids if item not in direct_ids]
            direct_items = [next(item for item in ledger.items if item.id == evidence_id) for evidence_id in direct_ids]
            proxy_items = [next(item for item in ledger.items if item.id == evidence_id) for evidence_id in proxy_ids]
            evidence_current = not any(item.staleness_status == "STALE" for item in direct_items + proxy_items)
            direct_verified = any(item.validation_status == "VALID" for item in direct_items) if direct_items else True
            direct_direction = None
            proxy_direction = None
            claim = assess_constraint_claim(
                claim_id=f"{constraint.value.lower()}-assessment", entity_identifier=next((item.entity_identifier for item in direct_items + proxy_items if item.entity_identifier), "UNKNOWN"),
                mechanism=CONSTRAINT_REGISTRY[constraint].display_name, direct_ids=direct_ids, proxy_ids=proxy_ids,
                counter_ids=evidence.contrary_evidence_ids, direct_direction=direct_direction,
                proxy_direction=proxy_direction, evidence_current=evidence_current,
                direct_verified=direct_verified,
            )
            if direct_ids:
                inference = f"{constraint.value.replace('_', ' ').title()} has direct measurements, but binding status is {claim.constraint_status.value.lower().replace('_', ' ')} and direction is {claim.direction_status.value.lower().replace('_', ' ')}."
            elif proxy_ids:
                inference = f"{constraint.value.replace('_', ' ').title()} remains unverified; cited proxies support only {claim.direction_status.value.lower().replace('_', ' ')}."
            else:
                inference = f"There is insufficient evidence to diagnose {constraint.value.replace('_', ' ').lower()}."
            if refs:
                ledger.add(type=EvidenceType.INFERENCE, tier=EvidenceTier.INDIRECT, metric=f"{constraint.value.lower()}_diagnosis", statement=inference, period="Current assessment", source="Company Economics deterministic diagnosis", source_type="model", source_nature=SourceNature.INFERRED, direction=Direction.UNKNOWN, confidence=confidence, related_constraint=constraint.value, supporting_evidence_ids=refs)
            diagnoses.append(ConstraintDiagnosis(constraint, CONSTRAINT_REGISTRY[constraint].mechanism, evidence.supporting_evidence_ids, evidence.contrary_evidence_ids, direction, confidence, evidence.data_gaps, inference, refs, claim.constraint_status.value, claim.direction_status.value))
        # A financial proxy can rank candidate constraints, but cannot by itself
        # establish the primary bottleneck.  This keeps arbitrary companies at
        # UNKNOWN until a constraint-specific structured KPI is available.
        supported = []
        for item in diagnoses:
            direct_ids = ledger.ids_for(CONSTRAINT_REGISTRY[item.constraint].direct_kpis)
            direct_items = [next(entry for entry in ledger.items if entry.id == evidence_id) for evidence_id in direct_ids]
            if item.direction_status in {"OBSERVED_EASING", "OBSERVED_TIGHTENING"} and any(entry.source_status != "FIXTURE" for entry in direct_items):
                supported.append(item)
        if supported:
            primary, secondary = supported[0], supported[1:3]
            candidate_only = [item.constraint for item in diagnoses if item not in supported]
        else:
            primary = ConstraintDiagnosis(ConstraintType.UNKNOWN, CONSTRAINT_REGISTRY[ConstraintType.UNKNOWN].mechanism, [], [], ConstraintDirection.UNKNOWN, Confidence.INSUFFICIENT, [gap for d in diagnoses for gap in d.data_gaps], "Available evidence does not support a primary constraint.", [], "STRUCTURAL_CANDIDATE", "DIRECTION_UNKNOWN")
            secondary, candidate_only = [], [item.constraint for item in diagnoses if item.constraint != ConstraintType.UNKNOWN]
        interactions = []
        if len(supported) >= 2:
            interactions.append(f"{supported[0].constraint.value} and {supported[1].constraint.value} may jointly limit conversion of demand into revenue; interaction evidence is currently indirect.")
        candidate_assessments = [item for item in diagnoses if item.constraint in candidate_only]
        return ConstraintSet(primary, secondary, candidate_only, [], interactions, current_primary_constraint=primary.constraint.value, candidate_assessments=candidate_assessments)


class GrowthSustainabilityInterpreter:
    def interpret(self, snapshot, architecture, constraints, scaling):
        growth = snapshot.metrics.get("revenue_growth")
        ids = list(dict.fromkeys(architecture.direct_evidence_ids + architecture.proxy_evidence_ids + constraints.primary_constraint.supporting_evidence_ids + [m.evidence_id for m in scaling.metrics if m.evidence_id]))
        ids = [item for item in ids if item]
        contrary = constraints.primary_constraint.contrary_evidence_ids
        if not _number(growth) or constraints.primary_constraint.constraint == ConstraintType.UNKNOWN:
            text = "Growth sustainability remains uncertain because current growth or the primary scaling constraint is not defensibly observed."
            confidence = Confidence.INSUFFICIENT if not ids else Confidence.LOW
        elif growth > 0 and constraints.primary_constraint.direction in {ConstraintDirection.EASING, ConstraintDirection.STABLE}:
            text = "Current evidence supports continued growth because the observed growth engine remains active and the identified constraint is not tightening; maintaining the rate still requires the cited drivers to persist."
            confidence = Confidence.MODERATE
        elif constraints.primary_constraint.direction == ConstraintDirection.TIGHTENING:
            text = "Growth remains positive, but a tightening primary constraint makes continuation of the current rate less secure."
            confidence = Confidence.MODERATE
        else:
            text = "Current growth evidence and constraint direction are mixed; no durable-growth conclusion is forced."
            confidence = Confidence.LOW
        return GrowthSustainability(growth, architecture.primary_driver.primitive.value, constraints.primary_constraint.constraint.value, constraints.primary_constraint.direction, scaling.interpretation, ids, contrary, text, confidence)


class FalsificationEngine:
    def build(self, classification, architecture, constraints, scaling):
        definition = ARCHETYPE_REGISTRY[classification.primary_archetype]
        evidence_ids = list(dict.fromkeys(architecture.direct_evidence_ids + constraints.primary_constraint.supporting_evidence_ids + [m.evidence_id for m in scaling.metrics if m.evidence_id]))
        conditions = []
        for pattern in definition.falsification_patterns[:4]:
            metric = pattern.split()[0].replace("-", "_")
            conditions.append(FalsificationCondition(pattern[0].upper() + pattern[1:], metric, f"This would weaken the {definition.equation} growth mechanism or its cash conversion.", evidence_ids[:4]))
        return conditions


class FinancialTranslationEngine:
    def translate(self, snapshot, sustainability, constraints, scaling):
        ids = sustainability.supporting_evidence_ids
        if any("fixture" in source.lower() for source in snapshot.sources.values()):
            return FinancialTranslation(*[FinancialImplication(ImplicationState.INSUFFICIENT_EVIDENCE, "Synthetic fixture financials cannot substantiate a financial implication.", []) for _ in range(4)])
        if sustainability.confidence == Confidence.INSUFFICIENT:
            revenue_state = ImplicationState.INSUFFICIENT_EVIDENCE
        elif _number(sustainability.current_revenue_growth) and sustainability.current_revenue_growth > 0 and constraints.primary_constraint.direction != ConstraintDirection.TIGHTENING:
            revenue_state = ImplicationState.POSITIVE
        elif constraints.primary_constraint.direction == ConstraintDirection.TIGHTENING:
            revenue_state = ImplicationState.MIXED
        else:
            revenue_state = ImplicationState.NEUTRAL
        incremental = next((m for m in scaling.metrics if m.name == "incremental_operating_margin" and _number(m.value)), None)
        margin_state = ImplicationState.POSITIVE if incremental and incremental.value > 0 else ImplicationState.MIXED if incremental else ImplicationState.INSUFFICIENT_EVIDENCE
        capex_gap = next((m for m in scaling.metrics if m.name == "revenue_growth_minus_capex_growth" and _number(m.value)), None)
        capital_state = ImplicationState.POSITIVE if capex_gap and capex_gap.value > 0 else ImplicationState.NEGATIVE if capex_gap and capex_gap.value < 0 else ImplicationState.INSUFFICIENT_EVIDENCE
        fcf_metric = next((m for m in scaling.metrics if m.name == "incremental_fcf_margin" and _number(m.value)), None)
        fcf_state = ImplicationState.POSITIVE if fcf_metric and fcf_metric.value > 0 else ImplicationState.MIXED if fcf_metric else ImplicationState.INSUFFICIENT_EVIDENCE
        return FinancialTranslation(
            FinancialImplication(revenue_state, sustainability.interpretation, ids),
            FinancialImplication(margin_state, incremental.interpretation if incremental else "Incremental operating margin is unavailable.", [incremental.evidence_id] if incremental else []),
            FinancialImplication(capital_state, capex_gap.interpretation if capex_gap else "Comparable capex growth is unavailable.", [capex_gap.evidence_id] if capex_gap else []),
            FinancialImplication(fcf_state, fcf_metric.interpretation if fcf_metric else "Incremental FCF margin is unavailable.", [fcf_metric.evidence_id] if fcf_metric else []),
        )


class ValuationAssumptionReviewer:
    def review(self, valuation_report, snapshot, translation, evidence_ids):
        if not valuation_report or not valuation_report.get("assumptions", {}).get("base"):
            return ValuationAssumptionReview([AssumptionReview("revenue_growth", None, ValuationReviewState.INSUFFICIENT_EVIDENCE, "A comparable DCF assumption is unavailable; no adjustment is made.", []), AssumptionReview("fcff_margin", None, ValuationReviewState.INSUFFICIENT_EVIDENCE, "A comparable DCF assumption is unavailable; no adjustment is made.", [])])
        base = {item["name"]: item["value"] for item in valuation_report["assumptions"]["base"]}
        observed = snapshot.metrics.get("revenue_growth")
        assumed = base.get("year_1_revenue_growth")
        if _number(observed) and _number(assumed):
            state = ValuationReviewState.SUPPORTED if abs(assumed - observed) <= 0.05 else ValuationReviewState.TOO_AGGRESSIVE if assumed > observed else ValuationReviewState.TOO_CONSERVATIVE
            reason = f"DCF Year-1 growth of {assumed:.1%} is compared with observed growth of {observed:.1%}; Company Economics does not change it."
        else:
            state, reason = ValuationReviewState.INSUFFICIENT_EVIDENCE, "Observed and assumed revenue growth are not both available."
        fcf_assumed = base.get("year_5_fcff_margin")
        fcf_observed = snapshot.metrics.get("fcf_margin")
        if _number(fcf_assumed) and _number(fcf_observed):
            fcf_state = ValuationReviewState.SUPPORTED if abs(fcf_assumed - fcf_observed) <= 0.05 else ValuationReviewState.TOO_AGGRESSIVE if fcf_assumed > fcf_observed else ValuationReviewState.TOO_CONSERVATIVE
            fcf_reason = f"DCF normalized FCFF margin of {fcf_assumed:.1%} is compared with observed FCFF margin of {fcf_observed:.1%}; no mutation occurs."
        else:
            fcf_state, fcf_reason = ValuationReviewState.INSUFFICIENT_EVIDENCE, "Observed and assumed FCFF margins are not both available."
        return ValuationAssumptionReview([AssumptionReview("revenue_growth", assumed, state, reason, evidence_ids[:4]), AssumptionReview("fcff_margin", fcf_assumed, fcf_state, fcf_reason, evidence_ids[:4])])


class MarketExpectationsComparator:
    def compare(self, valuation_report, snapshot, sustainability):
        reverse = (valuation_report or {}).get("reverse_dcf") or {}
        implied_growth = reverse.get("required_5y_revenue_cagr") if reverse.get("converged") else None
        implied_margin = reverse.get("required_year_5_fcff_margin") if reverse.get("converged") else None
        observed = snapshot.metrics.get("revenue_growth")
        if not (_number(implied_growth) and _number(observed)):
            return MarketExpectationComparison(MarketExpectationState.INSUFFICIENT_EVIDENCE, implied_growth, implied_margin, sustainability.interpretation, "A converged reverse DCF and comparable observed growth are required.", sustainability.supporting_evidence_ids[:4])
        difference = implied_growth - observed
        state = MarketExpectationState.ROUGHLY_CONSISTENT if abs(difference) <= 0.05 else MarketExpectationState.ABOVE_SUPPORTED_ECONOMICS if difference > 0 else MarketExpectationState.BELOW_SUPPORTED_ECONOMICS
        return MarketExpectationComparison(state, implied_growth, implied_margin, sustainability.interpretation, f"Market-implied five-year growth of {implied_growth:.1%} is compared with observed growth of {observed:.1%} and the diagnosed scaling structure.", sustainability.supporting_evidence_ids[:4])


def build_economic_graph(profile_parts):
    architecture, constraints, translation = profile_parts
    nodes = [{"id": "revenue", "label": "Revenue", "type": "revenue"}]
    edges = []
    for driver in [architecture.primary_driver] + architecture.secondary_drivers:
        node_id = driver.primitive.value.lower()
        nodes.append({"id": node_id, "label": driver.primitive.value.replace("_", " ").title(), "type": "growth_driver"})
        edges.append({"from": node_id, "to": "revenue", "relationship": "drives"})
    if constraints.primary_constraint.constraint != ConstraintType.UNKNOWN:
        node_id = constraints.primary_constraint.constraint.value.lower()
        nodes.append({"id": node_id, "label": constraints.primary_constraint.constraint.value.replace("_", " ").title(), "type": "constraint"})
        edges.append({"from": node_id, "to": "revenue", "relationship": "limits"})
    nodes.extend([{"id": "margin", "label": "Margin", "type": "margin"}, {"id": "cash_flow", "label": "Cash Flow", "type": "cash_flow"}, {"id": "valuation", "label": "Valuation Review", "type": "valuation"}])
    edges.extend([{"from": "revenue", "to": "margin", "relationship": "supports"}, {"from": "margin", "to": "cash_flow", "relationship": "converts_to"}, {"from": "cash_flow", "to": "valuation", "relationship": "supports"}])
    return {"nodes": nodes, "edges": edges}


class CompanyEconomicsValidation:
    VALID_NODE_TYPES = {"growth_driver", "constraint", "resource", "revenue", "margin", "cash_flow", "valuation", "risk"}
    VALID_RELATIONSHIPS = {"drives", "limits", "supports", "pressures", "converts_to", "depends_on", "structural_exposure_not_causal_attribution"}

    def validate(self, profile):
        evidence_ids = [item.id for item in profile.evidence_trace]
        node_ids = {item["id"] for item in profile.economic_graph["nodes"]}
        inference_refs_valid = all(item.supporting_evidence_ids and set(item.supporting_evidence_ids) <= set(evidence_ids) for item in profile.evidence_trace if item.type == EvidenceType.INFERENCE)
        checks = {
            "company_identity_valid": bool(profile.company.get("ticker") and profile.company.get("name")),
            "archetype_valid": profile.classification.primary_archetype in ARCHETYPE_REGISTRY,
            "classification_evidence_exists": bool(profile.classification.routing_evidence),
            "growth_equation_exists": bool(profile.growth_architecture.primary_growth_equation),
            "growth_drivers_exist": bool(profile.growth_architecture.primary_driver),
            "primary_constraint_supported_or_unknown": profile.constraints.primary_constraint.constraint == ConstraintType.UNKNOWN or bool(profile.constraints.primary_constraint.inference_evidence_ids),
            "evidence_ids_unique": len(evidence_ids) == len(set(evidence_ids)),
            "facts_have_sources": all(item.source for item in profile.evidence_trace if item.type == EvidenceType.FACT),
            "facts_have_periods": all(item.period for item in profile.evidence_trace if item.type == EvidenceType.FACT),
            "facts_have_values": all(item.value is not None for item in profile.evidence_trace if item.type == EvidenceType.FACT),
            "proxies_labeled": all(item.source_nature in {SourceNature.CALCULATED, SourceNature.DERIVED_PROXY} for item in profile.evidence_trace if item.type == EvidenceType.PROXY),
            "inferences_cite_evidence": inference_refs_valid,
            "classification_evidence_references_exist": bool(profile.classification.routing_evidence_ids) and set(profile.classification.routing_evidence_ids) <= set(evidence_ids),
            "high_confidence_is_justified": all(item.confidence != Confidence.HIGH or len(item.supporting_evidence_ids) >= 2 for item in profile.evidence_trace if item.type == EvidenceType.INFERENCE),
            "data_gaps_explicit": isinstance(profile.data_gaps, list),
            "scaling_metrics_valid": all(item.value is None or _number(item.value) for item in profile.scaling_economics.metrics),
            "falsification_conditions_exist": bool(profile.falsification_conditions),
            "valuation_review_does_not_mutate": not profile.valuation_assumption_review.mutates_dcf_inputs,
            "ticker_overrides_are_declarative": all(not callable(value) for override in COMPANY_ECONOMICS_OVERRIDES.values() for value in override.values()),
            "json_serializable": True,
            "graph_node_types_valid": all(item["type"] in self.VALID_NODE_TYPES for item in profile.economic_graph["nodes"]),
            "graph_edges_valid": all(item["relationship"] in self.VALID_RELATIONSHIPS and item["from"] in node_ids and item["to"] in node_ids for item in profile.economic_graph["edges"]),
        }
        try:
            json.dumps(profile.to_dict())
        except (TypeError, ValueError):
            checks["json_serializable"] = False
        failed = [name for name, passed in checks.items() if not passed]
        critical = {"company_identity_valid", "archetype_valid", "evidence_ids_unique", "inferences_cite_evidence", "json_serializable", "graph_edges_valid", "valuation_review_does_not_mutate"}
        status = "FAILED" if critical.intersection(failed) else "PROVISIONAL" if failed or profile.constraints.primary_constraint.constraint == ConstraintType.UNKNOWN or profile.data_gaps else "PASSED"
        return ValidationResult(status, checks, [name.replace("_", " ") for name in failed] + (["Data gaps or UNKNOWN conclusions remain explicit."] if status == "PROVISIONAL" and not failed else []))


def build_company_economics(snapshot: CompanySnapshot, valuation_report: dict | None = None) -> CompanyEconomicsProfile:
    # Keep illustrative financial inputs out of authoritative model comparisons.
    if any("fixture" in source.lower() for source in snapshot.sources.values()):
        valuation_report = None
    ledger, gaps = EvidenceLedger(), []
    collect_base_evidence(snapshot, ledger)
    from operational_research import build_operational_research
    operational_data = build_operational_research(snapshot.ticker, valuation_report)
    for series in operational_data["series"]:
        for observation in series["observations"]:
            envelope = observation["evidence"]
            item = ledger.add(type=EvidenceType.FACT, tier=EvidenceTier.DIRECT,
                metric=series["definition"]["id"], statement=series["definition"]["definition"],
                value=envelope["value"], unit=envelope["unit"], period=observation["period"],
                source=envelope["source_name"], source_type=envelope["source_type"],
                confidence=Confidence.HIGH, source_nature=SourceNature.REPORTED,
                **{key: envelope[key] for key in ("source_id", "source_url", "retrieved_at", "observation_date", "fiscal_period_start", "fiscal_period_end", "filing_date", "currency", "raw_concept", "normalized_concept", "transformation", "limitation", "entity_identifier", "source_status", "validation_status", "staleness_status", "source_locator", "extraction_method", "definition_version", "revision_status")})
            observation["ledger_id"] = item.id
    classification = BusinessModelClassifier().classify(snapshot)
    classification_refs = ledger.ids_for(("sector", "industry", "business_description", "gross_margin", "capex", "revenue"))
    classification.routing_evidence_ids = classification_refs
    if classification_refs:
        ledger.add(
            type=EvidenceType.INFERENCE, tier=EvidenceTier.INDIRECT, metric="business_model_classification",
            statement=f"The supported primary business-model archetype is {classification.primary_archetype.value}.",
            period="Current structural profile", source="Company Economics deterministic classifier", source_type="model",
            source_nature=SourceNature.INFERRED, confidence=classification.classification_confidence,
            supporting_evidence_ids=classification_refs,
        )
    architecture = GrowthArchitectureBuilder().build(classification, ledger, gaps)
    scaling = ScalingEconomicsAnalyzer().analyze(snapshot, classification, ledger, gaps)
    candidates = ConstraintClassifier().candidates(snapshot, classification)
    constraints = ConstraintDiagnosisEngine().diagnose(candidates, ledger)
    gaps.extend(gap for diagnosis in [constraints.primary_constraint] + constraints.secondary_constraints for gap in diagnosis.data_gaps)
    sustainability = GrowthSustainabilityInterpreter().interpret(snapshot, architecture, constraints, scaling)
    falsification = FalsificationEngine().build(classification, architecture, constraints, scaling)
    translation = FinancialTranslationEngine().translate(snapshot, sustainability, constraints, scaling)
    valuation_review = ValuationAssumptionReviewer().review(valuation_report, snapshot, translation, sustainability.supporting_evidence_ids)
    market = MarketExpectationsComparator().compare(valuation_report, snapshot, sustainability)
    graph = build_economic_graph((architecture, constraints, translation))
    valuation_available = any(item.state != ValuationReviewState.INSUFFICIENT_EVIDENCE for item in valuation_review.reviews)
    overall_state = "AVAILABLE"
    if classification.primary_archetype == Archetype.GENERIC_OPERATING_COMPANY or constraints.primary_constraint.constraint == ConstraintType.UNKNOWN or gaps:
        overall_state = "PARTIAL"
    if not any(_number(value) for value in snapshot.metrics.values()):
        overall_state = "INSUFFICIENT_DATA"
    data_quality = {
        "classification": classification.classification_confidence.value,
        "constraint_diagnosis": constraints.primary_constraint.confidence.value,
        "valuation": "AVAILABLE" if valuation_available else "INSUFFICIENT",
        "overall": overall_state,
        "evidence_coverage": {
            "facts": sum(item.type == EvidenceType.FACT for item in ledger.items),
            "proxies": sum(item.type == EvidenceType.PROXY for item in ledger.items),
            "inferences": sum(item.type == EvidenceType.INFERENCE for item in ledger.items),
            "gaps": len(_deduplicate_gaps(gaps)),
        },
    }
    qualitative_needed = constraints.primary_constraint.constraint == ConstraintType.UNKNOWN or any(
        gap.related_constraint for gap in gaps
    )
    qualitative_reason = (
        "Direct operational evidence is unavailable from the current structured data pipeline; candidate constraints remain structural until verified."
        if qualitative_needed else "Current structured evidence supports the reported deterministic diagnosis."
    )
    if constraints.primary_constraint.constraint == ConstraintType.UNKNOWN:
        driver = architecture.primary_driver.primitive.value.replace("_", " ").lower()
        core_question = f"What determines whether {snapshot.company_name} can convert {driver} into sustainable revenue growth without a candidate operating constraint becoming binding?"
    else:
        core_question = ARCHETYPE_REGISTRY[classification.primary_archetype].core_economic_question_template.format(company=snapshot.company_name)
    profile = CompanyEconomicsProfile(
        {"name": snapshot.company_name, "ticker": snapshot.ticker, "as_of": snapshot.as_of, "security_type": snapshot.security_type,
         "exchange": snapshot.exchange, "currency": snapshot.currency, "country": snapshot.country, "quote_type": snapshot.quote_type,
         "sector": snapshot.sector, "industry": snapshot.industry}, classification,
        core_question,
        architecture, constraints, scaling, sustainability, falsification, translation, valuation_review, market,
        _deduplicate_gaps(gaps), ledger.items, graph, ValidationResult("PENDING", {}, []), data_quality,
        qualitative_needed, qualitative_reason,
        segments=list(snapshot.segments or []),
    )
    all_diagnoses = [constraints.primary_constraint, *constraints.secondary_constraints, *constraints.candidate_assessments]
    profile.research_claims = [
        {
            "claim_id": f"{item.constraint.value.lower()}-assessment",
            "entity_identifier": snapshot.ticker,
            "mechanism": item.constraint.value,
            "relationship": item.inference,
            "claim_type": "STRUCTURAL_HYPOTHESIS" if item.constraint_status == "STRUCTURAL_CANDIDATE" else "CONTRADICTED" if item.constraint_status == "CONFLICTING_EVIDENCE" else "ECONOMIC_INFERENCE",
            "direct_evidence_ids": ledger.ids_for(CONSTRAINT_REGISTRY[item.constraint].direct_kpis) if item.constraint in CONSTRAINT_REGISTRY else [],
            "proxy_evidence_ids": [evidence_id for evidence_id in item.supporting_evidence_ids if evidence_id not in ledger.ids_for(CONSTRAINT_REGISTRY[item.constraint].direct_kpis)] if item.constraint in CONSTRAINT_REGISTRY else [],
            "counterevidence_ids": item.contrary_evidence_ids,
            "constraint_status": item.constraint_status,
            "direction_status": item.direction_status,
            "causal_status": "ASSOCIATION_ONLY" if item.supporting_evidence_ids else "STRUCTURALLY_PLAUSIBLE",
            "limitations": [gap.why_it_matters for gap in item.data_gaps],
            "classification_version": "phase8.1-evidence-authority-v2",
        }
        for item in all_diagnoses
        if item.constraint != ConstraintType.UNKNOWN
    ]
    profile.operational_research = operational_data
    profile.data_quality["evidence_coverage"]["facts"] = sum(item.type == EvidenceType.FACT for item in ledger.items)
    profile.evidence_registry = {
        item.id: next((o["evidence"] for series in profile.operational_research["series"] for o in series["observations"] if o["ledger_id"] == item.id), None) or snapshot.evidence_envelopes.get(item.metric, {
            "source_id": item.source_id or item.id, "source_name": item.source, "source_url": item.source_url,
            "source_type": item.source_type, "provider_status": item.provider_status,
            "retrieved_at": item.retrieved_at, "observation_date": item.observation_date,
            "fiscal_period_start": item.fiscal_period_start, "fiscal_period_end": item.fiscal_period_end,
            "fiscal_year": item.fiscal_year, "filing_date": item.filing_date, "unit": item.unit,
            "currency": item.currency, "value": item.value, "raw_concept": item.raw_concept,
            "normalized_concept": item.normalized_concept or item.metric, "transformation": item.transformation,
            "coverage_status": item.coverage_status, "validation_status": item.validation_status,
            "staleness_status": item.staleness_status, "limitation": item.limitation,
            "entity_identifier": item.entity_identifier or snapshot.ticker, "source_status": item.source_status,
        })
        for item in ledger.items
    }
    for series in profile.operational_research["series"]:
        definition = series["definition"]
        alias_nodes = {"pltr_customers": "customers", "tsm_shipments": "wafer_volume", "tsm_node_mix": "node_mix"}
        old_id = alias_nodes.get(definition["id"])
        if old_id:
            graph["nodes"][:] = [node for node in graph["nodes"] if node["id"] != old_id]
            for edge in graph["edges"]:
                if edge["from"] == old_id:
                    edge["from"] = definition["id"]
                if edge["to"] == old_id:
                    edge["to"] = definition["id"]
        graph["nodes"].append({"id": definition["id"], "label": definition["name"] + " (reported)", "type": "growth_driver"})
        graph["edges"].append({"from": definition["id"], "to": "revenue", "relationship": "structural_exposure_not_causal_attribution"})
    profile.validation = CompanyEconomicsValidation().validate(profile)
    return profile


def _deduplicate_gaps(gaps):
    output, seen = [], set()
    for gap in gaps:
        key = (gap.missing_field, gap.related_driver, gap.related_constraint)
        if key not in seen:
            seen.add(key); output.append(gap)
    return output


def build_live_company_economics(ticker: str, include_valuation=True):
    from intrinsic_valuation import build_valuation_report, collect_valuation_data
    from data_sources.operational_evidence import enrich_snapshot

    data = collect_valuation_data(ticker)
    snapshot = enrich_snapshot(snapshot_from_valuation_data(data))
    valuation = build_valuation_report(ticker, data=data) if include_valuation else None
    return build_company_economics(snapshot, valuation)


def cache_structural_profile(profile, cache_dir=".cache/company_economics"):
    path = Path(cache_dir) / f"{profile.company['ticker']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = profile.to_dict()
    payload["cache_metadata"] = {"ticker": profile.company["ticker"], "company_name": profile.company["name"], "as_of": profile.company["as_of"], "schema_version": COMPANY_ECONOMICS_SCHEMA_VERSION, "data_version": "structured-v1", "excludes_live_market_price": True}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _fmt_value(value, unit=""):
    if not _number(value): return "Unavailable"
    if unit == "decimal": return f"{value:.1%}"
    if unit == "multiple": return f"{value:.2f}x"
    return f"{value:,.2f}"


def print_company_economics(profile: CompanyEconomicsProfile):
    from company_economics_report import print_company_economics_report

    print_company_economics_report(profile)


def run_company_economics(ticker: str, json_output=False, use_fixture=False, force_refresh=False):
    if use_fixture:
        from company_economics_fixtures import benchmark_snapshot, benchmark_valuation_report
        profile = build_company_economics(benchmark_snapshot(ticker), benchmark_valuation_report(ticker))
    elif json_output:
        from company_research import analyze_company_economics
        result = analyze_company_economics(ticker, force_refresh=force_refresh)
        payload = result.get("profile")
        print(json.dumps(payload if payload is not None else result, indent=2))
        return payload
    else:
        profile = build_live_company_economics(ticker)
    if json_output:
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        print_company_economics(profile)
    return profile
