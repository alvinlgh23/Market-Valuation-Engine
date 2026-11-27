import { integrateSectorEngineRows, percent, type SectorEngineRow } from "./market-research";
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

function measuredSectors(system: ResearchSystem) {
  const rows = system.modules.core_market.payload?.sectors as SectorEngineRow[] | undefined;
  const order = new Map((Array.isArray(rows) ? rows : []).map((row, index) => [row.ticker, index]));
  return integrateSectorEngineRows(rows, system.modules.core_market.state, system.sector_flow).sort((a, b) => (order.get(a.ticker) ?? Infinity) - (order.get(b.ticker) ?? Infinity));
}

export function dashboardStateStrip(system: ResearchSystem): DashboardLink[] {
  const inflation = findRead(system, "inflation");
  const risk = findRead(system, "risk");
  const liquidity = findRead(system, "liquidity");
  const macro = findRead(system, "us-policy");
  const leadership = measuredSectors(system).find(s => s.rel6m != null);
  const valuation = system.dashboard.valuation_flags.find((flag) => flag.state);
  return [
    { label: "Macro", state: value(macro), detail: detail(macro), href: href(macro, "/macro/world?region=US&detail=policy") },
    { label: "Inflation", state: value(inflation), detail: detail(inflation), href: href(inflation, "/macro/inflation") },
    { label: "Liquidity", state: value(liquidity), detail: detail(liquidity), href: href(liquidity, "/macro/conditions#liquidity") },
    { label: "Risk", state: value(risk), detail: detail(risk), href: href(risk, "/macro/conditions#regime") },
    { label: "Leadership", state: leadership?.name || "Unavailable", detail: leadership ? `${percent(leadership.rel6m)} 6M RS · ${leadership.lastUpdated} · ${leadership.sourceState}. Breadth and crowding unavailable.` : "No validated relative-strength observations in this snapshot.", href: leadership ? `/markets?sector=${leadership.slug}` : "/markets" },
    { label: "Valuation", state: valuation ? humanize(valuation.state) : "No aggregate flag", detail: valuation ? String(valuation.reason) : "Only recent company valuation flags are shown.", href: valuation?.ticker ? `/valuation/${valuation.ticker}` : href(valuation, "/valuation") }
  ];
}

export function dashboardChanges(system: ResearchSystem): DashboardPriority[] {
  return system.dashboard.what_changed.slice(0, 5).map((item, index) => ({
    rank: index + 1,
    object: String(item.label || "Research object"),
    label: String(item.value || "Observed change"),
    current: String(item.period || ""),
    why: item.interpretation && item.interpretation !== "Observed market change" ? String(item.interpretation) : "",
    href: href(item, "/macro"),
    state: String(item.interpretation || "OBSERVED")
  }));
}

export function dashboardPriorities(system: ResearchSystem): DashboardPriority[] {
  const semis = measuredSectors(system).find(s => s.ticker === "SMH")!;
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
      label: "Inspect dated relative strength; positioning unverified",
      current: `${percent(semis.rel6m)} 6M RS · ${semis.lastUpdated}`,
      why: "Relative strength does not establish breadth or crowding. Open the same cached sector observation.",
      href: "/markets?sector=semiconductors&view=positioning",
      state: "WATCH"
    },
    {
      rank: base.length + 2,
      object: "Risk Coverage",
      label: "Risk conclusion withheld",
      current: value(findRead(system, "risk")),
      why: "Missing breadth, momentum leadership, defensive, and credit coverage is itself a research priority.",
      href: "/macro/conditions#regime",
      state: "INSUFFICIENT"
    }
  ].slice(0, 6);
}

export function dashboardTensions(system: ResearchSystem): ResearchTension[] {
  const macro = findRead(system, "us-policy");
  const risk = findRead(system, "risk");
  const semis = measuredSectors(system).find(s => s.ticker === "SMH")!;
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
      interpretation: "Dated relative strength is separate from breadth and crowding; missing measurements cannot establish positive leadership or positioning.",
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
      href: "/macro/conditions#regime"
    }
  ];
}

export function marketLeadershipSummary(system: ResearchSystem) {
  return measuredSectors(system).filter(s => s.rel6m != null).slice(0, 4).map((sector) => ({
    ticker: sector.ticker,
    name: sector.name,
    rel6m: percent(sector.rel6m),
    rel6mValue: typeof sector.rel6m === "number" ? sector.rel6m : null,
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

/** Today page: sectors by one-month relative strength (the signal the scorecard kept), strongest and weakest. */
export function sectorLeadershipBars(system: ResearchSystem, each = 5) {
  const rows = measuredSectors(system)
    .filter((sector) => typeof sector.rel1m === "number" && Number.isFinite(sector.rel1m))
    .map((sector) => ({ ticker: sector.ticker, name: sector.name, value: sector.rel1m as number, href: `/markets?sector=${sector.slug}` }))
    .sort((a, b) => b.value - a.value);
  if (rows.length <= each * 2) return rows;
  return [...rows.slice(0, each), ...rows.slice(-each)];
}

export type MarketMove = { label: string; value: number; unit: string; text: string; note: string; href: string };

/** Today page: observed changes as numbers grouped by unit (%, bp, other), so bars share a scale only within a unit. */
export function marketMoves(system: ResearchSystem): MarketMove[] {
  return system.dashboard.what_changed.slice(0, 8).flatMap((item) => {
    const text = String(item.value ?? "");
    const match = text.match(/[-+−]?\d+(?:\.\d+)?/);
    if (!match) return [];
    const value = Number(match[0].replace("−", "-"));
    if (!Number.isFinite(value)) return [];
    const unit = /bp/i.test(text) ? "bp" : /%/.test(text) ? "%" : "level";
    const note = [item.period, item.interpretation && item.interpretation !== "Observed market change" ? item.interpretation : null].filter(Boolean).join(" · ");
    return [{ label: String(item.label ?? ""), value, unit, text, note, href: String(item.href || "/macro") }];
  });
}
