"use client";
import { StatusBadge } from "./StatusBadge";
import { MarketsOverview } from "../markets/MarketsOverview";

import Link from "next/link";
import { FedPathPanel } from "../macro/FedPathPanel";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { integrateSectorEngineRows, type SectorEngineRow, type SectorFlowRow, type SectorResearchObject } from "../../lib/market-research";
import { SectorPage } from "../markets/SectorPage";
import type { ResearchSystem } from "../../lib/research-system-types";
import { MacroOverviewSurface, MacroTransmissionDetail } from "../macro/MacroOverviewSurface";
import { ResearchModule } from "./ResearchModule";
import { ValuationSearch } from "../valuation/ValuationSearch";

function title(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function display(value: unknown) {
  if (value == null || value === "") return "Unavailable";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (Array.isArray(value)) return value.length ? value.map(String).join(" · ") : "None reported";
  if (typeof value === "object") return "Open evidence detail";
  return String(value);
}
function Badge({ value }: { value: string }) { return <StatusBadge value={value} />; }

export function ObjectHeader({ eyebrow, title: heading, summary }: { eyebrow: string; title: string; summary: string; state?: string }) {
  return <header className="engine-module-header object-page-header"><div><span>{eyebrow}</span><h1>{heading}</h1>{summary ? <p>{summary}</p> : null}</div></header>;
}

function RecordGrid({ record, limit }: { record: Record<string, unknown>; limit?: number }) {
  const entries = Object.entries(record).filter(([, value]) => typeof value !== "object" || value == null).slice(0, limit);
  return <section className="object-metric-grid">{entries.map(([key, value]) => <article key={key}><span>{title(key)}</span><strong>{display(value)}</strong></article>)}</section>;
}

export function MacroOverview({ system }: { system: ResearchSystem }) {
  return <MacroOverviewSurface system={system} />;
}

export function MacroResearch({ section, system }: { section: string; system: ResearchSystem }) {
  if (section === "inflation") return <ResearchModule module="inflation" system={system} />;
  if (section === "risk") return <ResearchModule module="risk" system={system} />;
  if (section === "rates" || section === "fx" || section === "liquidity") return <MacroTransmissionDetail section={section} system={system} />;
  const core = system.modules.core_market.payload ?? {};
  const macro = (core.macro ?? {}) as Record<string, unknown>;
  const US = system.world.regions.US;
  const component = US?.components.find((item) => item.id === section || (section === "central-banks" && item.id === "policy"));
  const keys: Record<string, string[]> = {
    rates: ["front_rate_level", "front_rate_3m", "tnx_level", "tnx_3m", "tyx_level", "tyx_3m", "yield_curve"],
    liquidity: ["liquidity_score", "m2_level", "m2_6m", "dxy_level", "dxy_3m", "tnx_level", "hyg_ief"],
    fx: ["dxy_level", "dxy_3m", "usdjpy_level", "usdjpy_3m"],
    "central-banks": []
  };
  const selected = Object.fromEntries((keys[section] ?? Object.keys(macro)).map((key) => [key, macro[key]]));
  const evidence = component ? US.evidence.filter((item) => component.evidence_ids.includes(item.id)) : [];
  return <div className="engine-module"><ObjectHeader eyebrow={`MACRO / ${section.toUpperCase()}`} title={section === "central-banks" ? "Central banks" : title(section)} summary={component?.summary ?? ""} state={system.modules.core_market.state} />
    {section === "central-banks" ? <FedPathPanel /> : null}
    {Object.keys(selected).length ? <RecordGrid record={selected} /> : null}
    <section className="object-section"><header><div><span>MECHANISM</span><h2>{component?.state ?? "Regional policy frameworks"}</h2></div><Link href="/macro/world?region=US">Open regional research →</Link></header><p className="object-narrative">{component?.summary ?? "Open an integrated economy to inspect its policy framework, model state, confidence, watch conditions, and source evidence."}</p></section>
    <section className="engine-ledger"><header><h2>Evidence and provenance</h2><span>{evidence.length || "Regional"} records</span></header>{evidence.map((item) => <article key={item.id}><strong>{item.label}</strong><Badge value={item.evidence_type} /><span>{item.value} · {item.source}</span></article>)}{!evidence.length ? Object.values(system.world.regions).map((region) => <article key={region.id}><strong>{region.name}</strong><Badge value={region.availability} /><span>{region.brief}</span></article>) : null}</section>
  </div>;
}

export function MarketsResearch({ system }: { section: string; system: ResearchSystem }) {
  const params = useSearchParams();
  const sectorParam = params.get("sector");
  const core = system.modules.core_market.payload ?? {};
  const sectorList = integrateSectorEngineRows((core.sectors ?? []) as SectorEngineRow[], system.modules.core_market.state, system.sector_flow);
  // Checklist 19.2: with no sector chosen, Markets is the whole-market overview.
  if (!sectorParam) return <MarketsOverview sectorList={sectorList} asOf={sectorList.map((item) => item.lastUpdated).filter((day) => /^\d{4}-/.test(day)).sort().pop()} />;
  return <MarketsRotationSurface sectorList={sectorList} selectedSector={sectorParam} flow={system.sector_flow} />;
}

export function SectorResearch({ sector, system }: { sector: string; system: ResearchSystem }) {
  const core = system.modules.core_market.payload ?? {};
  const sectorList = integrateSectorEngineRows((core.sectors ?? []) as SectorEngineRow[], system.modules.core_market.state, system.sector_flow);
  return <MarketsRotationSurface sectorList={sectorList} selectedSector={sector} flow={system.sector_flow} />;
}

const SECTOR_SLUG_ALIASES: Record<string, string> = {
  "information-technology": "technology",
  "health-care": "healthcare",
  "communication": "xlc",
  "communication-services": "xlc",
  "consumer-discretionary": "xly",
  "consumer-staples": "xlp",
  "materials": "xlb",
  "real-estate": "xlre",
  "financial": "financials",
  "industrial": "industrials",
};

/** One sector's page (rebuilt 2026-11-27). The old rotation map and 34-row table now live on the overview's Map view. */
function MarketsRotationSurface({ sectorList, selectedSector, flow }: { sectorList: SectorResearchObject[]; selectedSector?: string | null; flow?: Record<string, SectorFlowRow> }) {
  const rawSlug = (selectedSector || "").toLowerCase().replaceAll("_", "-");
  const normalized = SECTOR_SLUG_ALIASES[rawSlug] ?? rawSlug;
  const selected = sectorList.find((sector) => sector.slug === normalized || sector.name.toLowerCase() === normalized || sector.ticker.toLowerCase() === normalized);
  if (!selected) return <section className="valuation-framework-state"><h1>Sector unavailable</h1><p>No sector matches {selectedSector}.</p><Link href="/markets">Back to all sectors →</Link></section>;
  return <div className="engine-module markets-research-surface"><SectorPage sector={{ ...selected, flow: flow?.[selected.ticker] }} sectorList={sectorList} /></div>;
}

export function CompanyIndex() {
  const router = useRouter(); const [ticker, setTicker] = useState("");
  function submit(event: FormEvent) { event.preventDefault(); if (ticker.trim()) router.push(`/company/${ticker.trim().toUpperCase()}`); }
  return <div className="engine-module"><ObjectHeader eyebrow="COMPANIES / UNIVERSAL ENTRY" title="Company research" summary="Start with the company. Overview, economics, positioning, valuation, and evidence are views of one research object." /><form className="object-search-form" onSubmit={submit}><label htmlFor="company-ticker">Search ticker or company</label><div><input id="company-ticker" value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="AMD" /><button type="submit">Resolve company →</button></div><small>Enter any supported ticker. Previously analyzed companies are research history, not the supported universe.</small></form></div>;
}

export function ValuationIndex() {
  return <div className="engine-module valuation-index"><ObjectHeader eyebrow="VALUATION / ECONOMICS VS EXPECTATIONS" title="Intrinsic valuation" summary="Start with economic reality versus market expectations, then inspect assumptions, DCF mechanics, reverse DCF, sensitivity, validation, and evidence inside one valuation object." /><ValuationSearch /><section className="research-launch-grid">{[["MSFT", "Microsoft", "Dynamic benchmark"], ["GOOG", "Alphabet", "FCFF/SBC reconciliation benchmark"], ["PLTR", "Palantir", "No-solution market-implied state"], ["JPM", "JPMorgan", "Framework required"]].map(([symbol, name, note]) => <Link href={`/valuation/${symbol}`} key={symbol}><span>{symbol}</span><strong>{name}</strong><p>{note}</p><i>Open valuation →</i></Link>)}</section><section className="object-section"><header><div><span>VALUATION OBJECT MODEL</span><h2>Company economics → model assumptions → market-implied expectations</h2></div></header><div className="research-depth-row">{["Snapshot", "Economics vs Model", "DCF", "Reverse DCF", "Sensitivity", "Validation", "Evidence"].map((item, index) => <article key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong><small>Deep-linkable view</small></article>)}</div></section></div>;
}

export function LabsSurface({ section, system }: { section: string; system: ResearchSystem }) {
  return <div className="engine-module"><ObjectHeader eyebrow={`LABS / ${section.toUpperCase()}`} title={title(section)} summary="Access to cached and prior research states where currently available. Future history is not fabricated." state="PARTIAL" /><section className="engine-ledger"><header><h2>Available snapshots</h2><span>Last-valid cache</span></header>{system.dashboard.freshness.map((item, index) => <article key={index}><strong>{item.label ?? item.module ?? "Research engine"}</strong><Badge value={String(item.state ?? "CACHED")} /><span>{String(item.as_of ?? item.context ?? "Timestamp unavailable")}</span></article>)}</section></div>;
}

