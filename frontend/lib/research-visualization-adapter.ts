import type { MacroComponent, MacroRegion, MacroWorld } from "./macro-types";
import type { ResearchSystem } from "./research-system-types";
import type { CompanyMatrixRow, CoverageItem, HeatmapCell, QuantitativeDatum, RankedResearchItem, TimeSeriesDefinition, TransmissionEdge, TransmissionNode } from "./visualization-types";

type Json = Record<string, unknown>;

function json(value: unknown): Json { return (value && typeof value === "object" ? value : {}) as Json; }
function number(value: unknown): number | null { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function human(value: string | undefined | null) { return value ? value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Unavailable"; }

export function normalizeObservedMoves(system: ResearchSystem): QuantitativeDatum[] {
  const configs = [
    ["JP", "usd_jpy_change_yoy", "USD/JPY", "% YoY", "fx-yoy"],
    ["EURO_AREA", "currency_change_yoy", "EUR/USD", "% YoY", "fx-yoy"],
    ["US", "credit_spread_change", "US credit spread", "pp / 6M", "credit-pp"],
  ] as const;
  return configs.flatMap(([regionId, key, label, unit, scaleGroup]) => {
    const region = system.world.regions[regionId];
    const compass = json(region?.engine_specific.central_bank_compass);
    const raw = number(json(compass.indicator_values)[key]);
    if (raw === null) return [];
    const evidence = ((compass.evidence || []) as Json[]).find((item) => String(item.label || "").toLowerCase().includes(label === "US credit spread" ? "credit spread change" : label.toLowerCase().replace("eur/usd", "broad euro").replace("usd/sgd", "usd/sgd").replace("usd/jpy", "usd/jpy")));
    return [{ id: `${regionId}-${key}`, label, value: raw, unit, date: String(evidence?.period || compass.latest || region.as_of || ""), status: String(evidence?.classification || "OBSERVED"), evidenceId: String(evidence?.id || ""), context: String(evidence?.note || "Observed engine value."), scaleGroup }];
  });
}

export function normalizePriorities(system: ResearchSystem): RankedResearchItem[] {
  return system.dashboard.research_priority.map((item, index) => ({
    id: `${item.module}-${item.label}`,
    rank: Number(item.rank || index + 1),
    label: String(item.label || "Research watch"),
    group: String(item.module || "Research"),
    status: String(item.state || "WATCH"),
    current: String(item.current || "Unavailable"),
    threshold: String(item.threshold || "No threshold supplied"),
    reason: String(item.reason || item.threshold || "Open the linked evidence."),
    href: String(item.href || "/"),
  }));
}

const DIMENSIONS: Array<[string, string, string[]]> = [
  ["Policy", "policy", ["policy"]],
  ["Inflation", "inflation", ["inflation"]],
  ["Growth", "growth", ["growth"]],
  ["Liquidity", "liquidity", ["liquidity"]],
  ["FX", "currency", ["currency", "fx"]],
  ["Market / risk", "markets", ["markets", "financial", "transmission"]],
];

function findComponent(region: MacroRegion, candidates: string[]): MacroComponent | undefined {
  return region.components.find((component) => candidates.includes(component.id));
}

export function normalizeRegimeMatrix(world: MacroWorld): { rows: string[]; columns: string[]; cells: HeatmapCell[] } {
  const order = ["US", "JP", "KR", "EURO_AREA"];
  const cells = order.flatMap((regionId) => DIMENSIONS.map(([column, detail, candidates]) => {
    const region = world.regions[regionId];
    const component = findComponent(region, candidates);
    return {
      id: `${regionId}-${detail}`,
      row: region.name,
      column,
      state: component?.state || "NOT AVAILABLE",
      confidence: component?.confidence || "INSUFFICIENT",
      coverage: component ? `${component.evidence_ids.length} evidence` : "0 evidence",
      href: `/macro?mode=regions&region=${regionId}&detail=${component?.id || detail}`,
      evidenceIds: component?.evidence_ids || [],
    };
  }));
  return { rows: order.map((id) => world.regions[id].name), columns: DIMENSIONS.map(([label]) => label), cells };
}

export function normalizeCoverage(system: ResearchSystem): CoverageItem[] {
  const inflation = system.modules.inflation.payload;
  const core = json(system.modules.core_market.payload);
  const quality = json(core.data_quality);
  const kospi = json(system.modules.kospi.payload);
  const kospiResults = (json(kospi.sweep).results || []) as Json[];
  const validKospi = kospiResults.filter((result) => Number(json(result.detail).obs || 0) > 0).length;
  const analyzedCompanies = system.dashboard.companies.filter((company) => Boolean(company.research_state));
  return [
    { id: "compass", label: "Macro World / Compass", state: system.world.data_state, asOf: system.dashboard.freshness[0]?.as_of, detail: "Four policy models across five country profiles; unsupported dimensions remain explicit." },
    { id: "inflation", label: "US Inflation", state: system.modules.inflation.state, asOf: inflation?.latest_source, available: inflation?.available, total: inflation?.total, detail: `${inflation?.available || 0}/${inflation?.total || 0} registered indicators available.` },
    { id: "core", label: "Market / Risk / Rotation", state: system.modules.core_market.state, asOf: system.dashboard.freshness[2]?.as_of, available: Number(quality.available_macro_inputs || 0), total: Number(quality.total_macro_inputs || 0), detail: `${Number(quality.risk_coverage || 0) * 100}% risk coverage; ${Number(quality.sector_rows || 0)} sector rows.` },
    { id: "kospi", label: "South Korea KOSPI", state: system.modules.kospi.state, asOf: String(json(kospi.sweep).timestamp || ""), available: validKospi, total: kospiResults.length || 5, detail: `${validKospi}/${kospiResults.length || 5} factor studies have observations; foreign-flow availability is isolated.` },
    { id: "companies", label: "Company Economics", state: analyzedCompanies.length ? system.modules.companies.state : "NOT_ANALYZED", asOf: analyzedCompanies.length ? system.dashboard.freshness[5]?.as_of : null, detail: `${analyzedCompanies.length} previously analyzed company profiles. This is recent research, not a supported-universe count.` },
  ];
}

export function normalizeCompanies(system: ResearchSystem): CompanyMatrixRow[] {
  return system.dashboard.companies.filter((company) => Boolean(company.research_state)).map((company) => ({
    ticker: String(company.ticker || ""),
    name: String(company.name || company.ticker || "Unavailable"),
    archetype: human(String(company.archetype || "")),
    growthDirection: human(String(company.growth_direction || "UNKNOWN")),
    growthConfidence: String(company.growth_confidence || company.classification_confidence || "INSUFFICIENT"),
    constraint: human(String(company.constraint || "UNKNOWN")),
    constraintDirection: human(String(company.constraint_state || "UNKNOWN")),
    scaling: String(company.scaling || "Open the profile for structured scaling evidence."),
    valuation: human(String(company.valuation_state || "INSUFFICIENT_EVIDENCE")),
    confidence: String(company.validation || company.research_state || "PARTIAL"),
    href: `/company/${company.ticker}`,
  }));
}

export function normalizeKospiFactors(payload: Json): QuantitativeDatum[] {
  const results = (json(payload.sweep).results || []) as Json[];
  return results.map((factor) => ({ id: String(factor.key), label: String(factor.label), value: Number(factor.score || 0), unit: "score / 10", status: String(factor.strength || "UNAVAILABLE"), confidence: Number(json(factor.detail).obs || 0) > 0 ? "OBSERVED" : "INSUFFICIENT", context: `r=${factor.corr}; adjusted p=${factor.pval}; ${Number(json(factor.detail).obs || 0)} observations.`, scaleGroup: "kospi-factor" }));
}

export function normalizeKospiHistory(payload: Json, factorKey: string): TimeSeriesDefinition | null {
  const factor = ((json(payload.sweep).results || []) as Json[]).find((item) => item.key === factorKey);
  if (!factor) return null;
  const history = (json(factor.detail).history || []) as Json[];
  return { id: `kospi-${factorKey}`, label: `${factor.label} proxy vs KOSPI`, unit: "normalized index", comparisonLabel: "KOSPI", source: String(factor.data_source || ""), points: history.map((point) => ({ date: String(point.t), value: number(point.signal), comparison: number(point.benchmark) })) };
}

export function normalizeKospiVolatility(payload: Json): RankedResearchItem[] {
  const volatility = json(json(payload.sweep).volatility);
  const current = number(volatility.current_vol);
  const average = number(volatility.avg_vol);
  return [
    ...(current === null ? [] : [{ id: "current", rank: 1, label: "Current GARCH volatility", group: "GARCH(1,1) daily volatility", status: String(volatility.regime || "OBSERVED"), current: `${current.toFixed(3)}%`, magnitude: current, unit: "% / day", reason: `Clustering: ${volatility.clustering}; persistence ${volatility.persistence}`, threshold: "Compare with sample average" }]),
    ...(average === null ? [] : [{ id: "average", rank: 2, label: "Average volatility", group: "Sample reference", status: "REFERENCE", current: `${average.toFixed(3)}%`, magnitude: average, unit: "% / day", reason: "Existing engine sample average; not a forecast.", threshold: "Reference" }]),
  ];
}

export function normalizeTransmissions(world: MacroWorld): { nodes: TransmissionNode[]; edges: TransmissionEdge[] } {
  const positions: Record<string, [number, number]> = { US: [16, 55], EURO_AREA: [47, 25], JP: [84, 35], KR: [78, 63], SG: [65, 84] };
  return {
    nodes: Object.entries(positions).map(([id, [x, y]]) => ({ id, label: id === "EURO_AREA" ? "EURO" : id, x, y })),
    edges: world.transmissions.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, label: edge.label, state: edge.current_state, evidenceType: edge.evidence_ids.some((id) => world.evidence_index[id]?.evidence_type === "FACT") ? "FACT" : edge.evidence_ids.some((id) => world.evidence_index[id]?.evidence_type === "PROXY") ? "PROXY" : "INFERENCE", confidence: edge.confidence, evidenceIds: edge.evidence_ids })),
  };
}
