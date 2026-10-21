import { sectorBySlug, sectors, percent } from "./market-research";
import type { ResearchRow, ResearchSystem } from "./research-system-types";

export type DashboardLink = {
  label: string;
  state: string;
  detail: string;
  href: string;
};

export type DashboardPriority = {
  rank: number;
  object: string;
  label: string;
  current: string;
  why: string;
  href: string;
  state: string;
};

export type ResearchTension = {
  id: string;
  objects: string;
  stateA: string;
  stateB: string;
  interpretation: string;
  confidence: string;
  href: string;
};

function value(row?: ResearchRow, fallback = "Unavailable") {
  return String(row?.value || row?.current || row?.state || row?.signal || fallback);
}

function detail(row?: ResearchRow, fallback = "No detail supplied.") {
  return String(row?.context || row?.why || row?.threshold || row?.reason || fallback);
}

function href(row?: ResearchRow, fallback = "/") {
  return String(row?.href || fallback);
}

function humanize(value: unknown, fallback = "Unavailable") {
  return String(value || fallback).replaceAll("_", " ");
}

function findRead(system: ResearchSystem, id: string) {
  return system.dashboard.reads.find((read) => read.id === id);
}

export function dashboardStateStrip(system: ResearchSystem): DashboardLink[] {
  const inflation = findRead(system, "inflation");
  const risk = findRead(system, "risk");
  const liquidity = findRead(system, "liquidity");
  const macro = findRead(system, "us-policy");
  const leadership = sectorBySlug("semiconductors");
  const valuation = system.dashboard.valuation_flags.find((flag) => flag.state);
  return [
    { label: "Macro", state: value(macro), detail: detail(macro), href: href(macro, "/macro/world?region=US&detail=policy") },
    { label: "Inflation", state: value(inflation), detail: detail(inflation), href: href(inflation, "/macro/inflation") },
    { label: "Liquidity", state: value(liquidity), detail: detail(liquidity), href: href(liquidity, "/macro/liquidity") },
    { label: "Risk", state: value(risk), detail: detail(risk), href: href(risk, "/macro/risk") },
    { label: "Leadership", state: leadership.name, detail: `${percent(leadership.rel6m)} 6M RS; ${leadership.breadth} breadth; ${leadership.crowding}.`, href: `/markets?sector=${leadership.slug}` },
    { label: "Valuation", state: valuation ? humanize(valuation.state) : "No aggregate flag", detail: valuation ? String(valuation.reason) : "Only recent company valuation flags are shown.", href: valuation?.ticker ? `/valuation/${valuation.ticker}` : href(valuation, "/valuation") }
  ];
}

export function dashboardChanges(system: ResearchSystem): DashboardPriority[] {
  return system.dashboard.what_changed.slice(0, 5).map((item, index) => ({
    rank: index + 1,
    object: String(item.label || "Research object"),
    label: String(item.value || "Observed change"),
    current: String(item.period || system.generated_at),
    why: `Observed ${item.label || "research"} change classified ${item.interpretation || "available"} by the source module.`,
    href: href(item, "/macro"),
    state: String(item.interpretation || "OBSERVED")
  }));
}

export function dashboardPriorities(system: ResearchSystem): DashboardPriority[] {
  const base = system.dashboard.research_priority.slice(0, 4).map((item, index) => ({
    rank: Number(item.rank || index + 1),
    object: String(item.module || "Research"),
    label: String(item.label || "Research priority"),
    current: String(item.current || "Open detail"),
    why: String(item.threshold || item.reason || "Current watch condition requires inspection."),
    href: href(item, "/"),
    state: String(item.state || "WATCH")
  }));
  return [
    ...base,
    {
      rank: base.length + 1,
      object: "Semiconductors",
      label: "Leadership strong; crowding proxy elevated",
      current: `${percent(sectorBySlug("semiconductors").rel6m)} 6M RS`,
      why: "Phase 3 market bridge exposes leadership, breadth, and crowding as a direct sector research object.",
      href: "/markets?sector=semiconductors&view=positioning",
      state: "WATCH"
    },
    {
      rank: base.length + 2,
      object: "Risk Coverage",
      label: "Risk conclusion withheld",
      current: value(findRead(system, "risk")),
      why: "Missing breadth, momentum leadership, defensive, and credit coverage is itself a research priority.",
      href: "/macro/risk",
      state: "INSUFFICIENT"
    }
  ].slice(0, 6);
}

export function dashboardTensions(system: ResearchSystem): ResearchTension[] {
  const macro = findRead(system, "us-policy");
  const risk = findRead(system, "risk");
  const semis = sectorBySlug("semiconductors");
  const inflation = findRead(system, "inflation");
  return [
    {
      id: "policy-leadership",
      objects: "Macro × Markets",
      stateA: `US policy ${value(macro)}`,
      stateB: `${semis.name} ${percent(semis.rel6m)} vs SPY`,
      interpretation: "Risk assets can show sector leadership even while discount-rate pressure remains a separate macro constraint.",
      confidence: String(macro?.state || "CACHED"),
      href: "/markets?sector=semiconductors"
    },
    {
      id: "leadership-crowding",
      objects: "Markets × Breadth",
      stateA: semis.breadth,
      stateB: semis.crowding,
      interpretation: "Leadership remains positive, but breadth and crowding must be inspected separately rather than averaged into one read.",
      confidence: semis.sourceState,
      href: "/markets?sector=semiconductors&view=breadth"
    },
    {
      id: "inflation-policy",
      objects: "Inflation × Policy",
      stateA: value(inflation),
      stateB: value(macro),
      interpretation: "Near-term inflation pressure and policy stance should be read together before interpreting rates transmission.",
      confidence: String(inflation?.state || "AVAILABLE"),
      href: "/macro/inflation"
    },
    {
      id: "risk-coverage",
      objects: "Risk × Data Coverage",
      stateA: value(risk),
      stateB: "Coverage withheld",
      interpretation: "The system should route to missing evidence rather than publish a false neutral risk state.",
      confidence: String(risk?.state || "INSUFFICIENT"),
      href: "/macro/risk"
    }
  ];
}

export function marketLeadershipSummary() {
  return sectors.slice(0, 4).map((sector) => ({
    ticker: sector.ticker,
    name: sector.name,
    rel6m: percent(sector.rel6m),
    breadth: sector.breadth,
    crowding: sector.crowding,
    href: `/markets?sector=${sector.slug}`
  }));
}

export function recentCompanyRows(system: ResearchSystem) {
  return system.dashboard.companies
    .filter((company) => Boolean(company.research_state))
    .slice(0, 5)
    .map((company) => ({
      ticker: String(company.ticker || ""),
      name: String(company.name || company.ticker || "Unavailable"),
      state: String(company.research_state || "CACHED"),
      constraint: String(company.constraint || "UNKNOWN").replaceAll("_", " "),
      valuation: String(company.valuation_state || "INSUFFICIENT_EVIDENCE").replaceAll("_", " "),
      href: `/company/${company.ticker}`
    }));
}
