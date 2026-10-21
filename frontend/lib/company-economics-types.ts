export type Confidence = "INSUFFICIENT" | "LOW" | "MODERATE" | "HIGH" | string;
export type ConstraintDirection = "EASING" | "TIGHTENING" | "MIXED" | "UNKNOWN" | "POSSIBLY_EASING" | string;
export type EvidenceType = "FACT" | "PROXY" | "INFERENCE" | string;

export interface RawEvidenceItem {
  id: string;
  type: EvidenceType;
  tier: string;
  metric: string;
  statement: string;
  value: string | number | null;
  unit: string;
  period: string;
  source: string;
  source_type: string;
  source_nature: string;
  direction: string;
  confidence: Confidence;
  related_driver?: string | null;
  related_constraint?: string | null;
  supporting_evidence_ids: string[];
}

export interface RawDataGap {
  missing_field: string;
  related_driver?: string | null;
  related_constraint?: string | null;
  why_it_matters: string;
  confidence_impact: string;
  fallback_proxy_used?: string | null;
}

export interface RawDriver {
  primitive: string;
  importance: string;
  observability: string;
  evidence_ids: string[];
  confidence: Confidence;
}

export interface RawConstraint {
  constraint: string;
  economic_mechanism: string;
  supporting_evidence_ids: string[];
  contrary_evidence_ids: string[];
  direction: ConstraintDirection;
  confidence: Confidence;
  data_gaps: RawDataGap[];
  inference: string;
  inference_evidence_ids: string[];
}

export interface RawCompanyEconomics {
  company: { name: string; ticker: string; as_of: string; security_type: string; market_price?: number | null; exchange?: string; currency?: string; country?: string; quote_type?: string; sector?: string; industry?: string };
  classification: {
    primary_archetype: string;
    secondary_archetypes: string[];
    classification_confidence: Confidence;
    routing_evidence: string[];
    routing_evidence_ids: string[];
    override_used?: boolean;
    override_required?: boolean;
    override_changes?: string[];
  };
  core_economic_question: string;
  growth_architecture: {
    primary_growth_equation: string;
    primary_driver: RawDriver;
    secondary_drivers: RawDriver[];
    direct_evidence_ids: string[];
    proxy_evidence_ids: string[];
    confidence: Confidence;
  };
  constraints: {
    primary_constraint: RawConstraint;
    secondary_constraints: RawConstraint[];
    candidate_constraints: string[];
    unknown_constraints: string[];
    constraint_interactions: string[];
  };
  scaling_economics: {
    metrics: Array<{
      name: string;
      value: number | null;
      unit: string;
      current_period: string;
      comparison_period?: string | null;
      interpretation: string;
      evidence_id?: string | null;
    }>;
    interpretation: string;
    confidence: Confidence;
  };
  growth_sustainability: {
    current_revenue_growth: number | null;
    primary_growth_engine: string;
    primary_constraint: string;
    constraint_direction: ConstraintDirection;
    scaling_structure: string;
    supporting_evidence_ids: string[];
    contrary_evidence_ids: string[];
    interpretation: string;
    confidence: Confidence;
  };
  falsification_conditions: Array<{
    condition: string;
    observable_metric: string;
    rationale: string;
    evidence_ids: string[];
  }>;
  financial_translation: Record<string, { state: string; reason: string; evidence_ids: string[] }>;
  valuation_assumption_review: {
    reviews: Array<{ assumption: string; dcf_value: number | string | null; state: string; reason: string; evidence_ids: string[] }>;
    mutates_dcf_inputs: boolean;
  };
  market_expectations_comparison: {
    state: string;
    market_implied_revenue_cagr: number | null;
    market_implied_fcff_margin: number | null;
    observed_economics: string;
    reason: string;
    evidence_ids: string[];
  };
  data_gaps: RawDataGap[];
  evidence_trace: RawEvidenceItem[];
  economic_graph: {
    nodes: Array<{ id: string; label: string; type: string }>;
    edges: Array<{ from: string; to: string; relationship: string }>;
  };
  validation: { status: string; checks: Record<string, boolean>; reasons: string[] };
  data_quality?: {
    classification: string;
    constraint_diagnosis: string;
    valuation: string;
    overall: string;
    evidence_coverage: { facts: number; proxies: number; inferences: number; gaps: number };
  };
  qualitative_research_needed?: boolean;
  qualitative_research_reason?: string;
  company_economics_schema_version: string;
}

export interface CompanyEconomicsPayload {
  company_economics: RawCompanyEconomics;
}

export interface CompanyEconomicsOntology {
  archetypes: Record<string, {
    display_name: string;
    revenue_model_description: string;
    economic_structure_steps: string[];
    driver_descriptions: string[];
  }>;
  constraints: Record<string, {
    display_name: string;
    economic_mechanism_steps: string[];
    why_it_matters: string;
    direct_kpis: string[];
  }>;
}

export interface EvidenceViewModel extends RawEvidenceItem {
  label: string;
  valueLabel: string;
  typeLabel: "Direct" | "Proxy" | "Inference";
  usedIn: string[];
}

export interface CompanyResearchViewModel {
  raw: RawCompanyEconomics;
  ticker: string;
  name: string;
  asOf: string;
  archetype: string;
  confidence: string;
  coreQuestion: string;
  growthEquation: string;
  growthDrivers: Array<RawDriver & { label: string; evidence: EvidenceViewModel[] }>;
  growthPath: string[];
  primaryConstraint: RawConstraint & { label: string; evidence: EvidenceViewModel[]; basis: string; directionLabel: string };
  secondaryConstraints: Array<RawConstraint & { label: string; evidence: EvidenceViewModel[]; basis: string; directionLabel: string }>;
  scalingMetrics: Array<RawCompanyEconomics["scaling_economics"]["metrics"][number] & { label: string; valueLabel: string }>;
  evidence: EvidenceViewModel[];
  evidenceById: Record<string, EvidenceViewModel>;
  evidenceCounts: { all: number; direct: number; proxy: number; inference: number; gaps: number };
  dataGaps: Array<RawDataGap & { label: string }>;
  availableMetrics: Set<string>;
}
