import type {
  CompanyEconomicsPayload,
  CompanyResearchViewModel,
  Confidence,
  ConstraintDirection,
  EvidenceViewModel,
  RawCompanyEconomics,
  RawConstraint,
  RawEvidenceItem
} from "./company-economics-types";
import ontologyFixture from "./fixtures/company-economics/ontology.json";
import type { CompanyEconomicsOntology } from "./company-economics-types";

const ontology = ontologyFixture as CompanyEconomicsOntology;

const ACRONYMS: Record<string, string> = { adr: "ADR", ai: "AI", asp: "ASP", dcf: "DCF", eps: "EPS", erp: "ERP", etf: "ETF", ev: "EV", fcf: "FCFF", fcff: "FCFF", kpi: "KPI", ocf: "OCF", roe: "ROE", saas: "SaaS", sbc: "SBC", wacc: "WACC" };

// Gap scan 2026-11-27: engine states such as INSUFFICIENT_EVIDENCE read as jargon on every section. Readers see
// "Not enough data"; the internal state stays in the data.
const NOT_ENOUGH = new Set(["INSUFFICIENT", "INSUFFICIENT_EVIDENCE", "EVIDENCE_INSUFFICIENT", "INSUFFICIENT_DATA"]);

export function humanize(value?: string | null): string {
  if (!value) return "Unavailable";
  if (NOT_ENOUGH.has(value.toUpperCase().replaceAll(" ", "_"))) return "Not enough data";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => ACRONYMS[part] ?? `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function confidenceLabel(value: Confidence): string {
  return value === "INSUFFICIENT" ? "Not enough data" : humanize(value);
}

export function directionLabel(value: ConstraintDirection): string {
  const labels: Record<string, string> = {
    EASING: "Easing",
    TIGHTENING: "Tightening",
    MIXED: "Mixed",
    UNKNOWN: "No Direction Confirmed",
    POSSIBLY_EASING: "Possibly Easing",
    POSSIBLY_TIGHTENING: "Possibly Tightening",
    OBSERVED_EASING: "Observed Easing",
    OBSERVED_TIGHTENING: "Observed Tightening",
    DIRECTION_UNKNOWN: "No Direction Confirmed"
  };
  return labels[value] ?? humanize(value);
}

export function formatValue(value: unknown, unit = ""): string {
  if (value === null || value === undefined || value === "" || (typeof value === "number" && !Number.isFinite(value))) return "—";
  if (typeof value === "string") return value;
  if (typeof value !== "number") return "—";
  if (unit === "decimal") return `${(value * 100).toFixed(1)}%`;
  if (unit === "multiple") return `${value.toFixed(2)}×`;
  if (unit === "currency/employee") return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} currency units/employee`;
  if (unit === "currency") return `$${value.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function usedInMap(raw: RawCompanyEconomics): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  const add = (ids: Array<string | null | undefined>, section: string) => {
    ids.filter(Boolean).forEach((id) => {
      const key = id as string;
      result[key] = Array.from(new Set([...(result[key] ?? []), section]));
    });
  };
  add([...raw.growth_architecture.direct_evidence_ids, ...raw.growth_architecture.proxy_evidence_ids], "Growth Engine");
  add([...raw.constraints.primary_constraint.supporting_evidence_ids, ...raw.constraints.primary_constraint.contrary_evidence_ids], "Constraint Diagnosis");
  add(raw.scaling_economics.metrics.map((metric) => metric.evidence_id), "Scaling Economics");
  add([...raw.growth_sustainability.supporting_evidence_ids, ...raw.growth_sustainability.contrary_evidence_ids], "Growth Sustainability");
  raw.valuation_assumption_review.reviews.forEach((review) => add(review.evidence_ids, "Valuation Connection"));
  return result;
}

function evidenceType(item: RawEvidenceItem): EvidenceViewModel["typeLabel"] {
  if (item.source_status === "FIXTURE" || item.type === "FIXTURE") return "Fixture";
  if (item.type === "INFERENCE") return "Inference";
  if (item.type === "PROXY" || item.tier !== "DIRECT") return "Proxy";
  return "Direct";
}

function constraintBasis(constraint: RawConstraint, evidenceById: Record<string, EvidenceViewModel>): string {
  const cited = [...constraint.supporting_evidence_ids, ...constraint.contrary_evidence_ids].map((id) => evidenceById[id]).filter(Boolean);
  return cited.some((item) => item.typeLabel === "Direct") ? "Direct operating evidence" : cited.length ? "Proxy-based" : "Unconfirmed";
}

export function adaptCompanyEconomics(payload: CompanyEconomicsPayload): CompanyResearchViewModel {
  const raw = payload.company_economics;
  const usage = usedInMap(raw);
  const evidence = raw.evidence_trace.map<EvidenceViewModel>((item) => ({
    ...item,
    label: humanize(item.metric),
    valueLabel: formatValue(item.value, item.unit),
    typeLabel: evidenceType(item),
    usedIn: usage[item.id] ?? ["Supporting Context"]
  }));
  const evidenceById = Object.fromEntries(evidence.map((item) => [item.id, item]));
  const archetypeMetadata = ontology.archetypes[raw.classification.primary_archetype];
  const drivers = [raw.growth_architecture.primary_driver, ...raw.growth_architecture.secondary_drivers].map((driver, index) => ({
    ...driver,
    label: archetypeMetadata?.driver_descriptions[index] ?? humanize(driver.primitive),
    evidence: driver.evidence_ids.map((id) => evidenceById[id]).filter(Boolean)
  }));
  const decorateConstraint = (constraint: RawConstraint) => ({
    ...constraint,
    label: ontology.constraints[constraint.constraint]?.display_name ?? humanize(constraint.constraint),
    evidence: Array.from(new Set([...constraint.supporting_evidence_ids, ...constraint.contrary_evidence_ids])).map((id) => evidenceById[id]).filter(Boolean),
    basis: constraintBasis(constraint, evidenceById),
    directionLabel: directionLabel(constraint.direction)
  });
  const graphDrivers = raw.economic_graph.nodes.filter((node) => node.type === "growth_driver").map((node) => node.label);
  const growthPath = archetypeMetadata?.economic_structure_steps ?? [...graphDrivers, "Revenue"];
  const contraryIds = new Set([
    ...raw.constraints.primary_constraint.contrary_evidence_ids,
    ...raw.constraints.secondary_constraints.flatMap((item) => item.contrary_evidence_ids),
    ...(raw.constraints.candidate_assessments ?? []).flatMap((item) => item.contrary_evidence_ids)
  ]);
  return {
    raw,
    ticker: raw.company.ticker,
    name: raw.company.name,
    asOf: raw.company.as_of,
    archetype: archetypeMetadata?.display_name ?? humanize(raw.classification.primary_archetype),
    confidence: confidenceLabel(raw.growth_sustainability.confidence),
    coreQuestion: raw.core_economic_question,
    growthEquation: raw.growth_architecture.primary_growth_equation,
    growthDrivers: drivers,
    growthPath,
    primaryConstraint: decorateConstraint(raw.constraints.primary_constraint),
    secondaryConstraints: raw.constraints.secondary_constraints.map(decorateConstraint),
    scalingMetrics: raw.scaling_economics.metrics.map((metric) => ({ ...metric, label: humanize(metric.name), valueLabel: formatValue(metric.value, metric.unit) })),
    evidence,
    evidenceById,
    evidenceCounts: {
      all: evidence.length,
      direct: evidence.filter((item) => item.typeLabel === "Direct").length,
      proxy: evidence.filter((item) => item.typeLabel === "Proxy").length,
      inference: evidence.filter((item) => item.typeLabel === "Inference").length,
      observed: evidence.filter((item) => item.typeLabel === "Direct").length,
      unverified: evidence.filter((item) => item.validation_status && item.validation_status !== "VALID").length,
      counter: evidence.filter((item) => contraryIds.has(item.id)).length,
      stale: evidence.filter((item) => item.staleness_status === "STALE").length,
      gaps: raw.data_gaps.length
    },
    dataGaps: raw.data_gaps.map((gap) => ({ ...gap, label: humanize(gap.missing_field) })),
    availableMetrics: new Set(evidence.map((item) => item.metric))
  };
}


/** Gap scan 2026-11-27: evidence rows carry no freshness status, so the page printed "/ Unknown" on every row. Show the
 * profile's own data date instead, so the reader sees how old the figures are. */
export function freshnessLabel(staleness: string | null | undefined, asOf: string | null | undefined): string {
  if (staleness && staleness !== "UNKNOWN") return humanize(staleness);
  return asOf ? `data as of ${asOf}` : "date of data not recorded";
}
