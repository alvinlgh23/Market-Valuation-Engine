"use client";
import { StatusBadge } from "./StatusBadge";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { integrateSectorEngineRows, rotationAxis, percent, type SectorEngineRow, type SectorResearchObject, type SectorStructureNode } from "../../lib/market-research";
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
  return <header className="engine-module-header object-page-header"><div><span>{eyebrow}</span><h1>{heading}</h1><p>{summary}</p></div></header>;
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
  return <div className="engine-module"><ObjectHeader eyebrow={`MACRO / ${section.toUpperCase()}`} title={section === "central-banks" ? "Central banks" : title(section)} summary={component?.summary ?? `A focused view of available ${section.replaceAll("-", " ")} observations. Missing coverage remains explicit.`} state={system.modules.core_market.state} />
    {Object.keys(selected).length ? <RecordGrid record={selected} /> : null}
    <section className="object-section"><header><div><span>MECHANISM</span><h2>{component?.state ?? "Regional policy frameworks"}</h2></div><Link href="/macro/world?region=US">Open regional research →</Link></header><p className="object-narrative">{component?.summary ?? "Open an integrated economy to inspect its policy framework, model state, confidence, watch conditions, and source evidence."}</p></section>
    <section className="engine-ledger"><header><h2>Evidence and provenance</h2><span>{evidence.length || "Regional"} records</span></header>{evidence.map((item) => <article key={item.id}><strong>{item.label}</strong><Badge value={item.evidence_type} /><span>{item.value} · {item.source}</span></article>)}{!evidence.length ? Object.values(system.world.regions).map((region) => <article key={region.id}><strong>{region.name}</strong><Badge value={region.availability} /><span>{region.brief}</span></article>) : null}</section>
  </div>;
}

export function MarketsResearch({ section, system }: { section: string; system: ResearchSystem }) {
  const params = useSearchParams();
  const sectorParam = params.get("sector");
  const view = params.get("view");
  const node = params.get("node");
  const core = system.modules.core_market.payload ?? {};
  const sectorList = integrateSectorEngineRows((core.sectors ?? []) as SectorEngineRow[], system.modules.core_market.state);
  if (section === "rotation") return <MarketsRotationSurface sectorList={sectorList} selectedSector={sectorParam} view={view} selectedNodeId={node} />;
  const fragility = (core.fragility ?? {}) as Record<string, unknown>;
  const risk = (core.risk ?? {}) as Record<string, unknown>;
  if (section === "defensive-rotation") return <DefensiveRotationSurface risk={risk} state={system.modules.core_market.state} />;
  if (section === "breadth") return <MarketsRotationSurface sectorList={sectorList} selectedSector="semiconductors" view="breadth" selectedNodeId={null} />;
  if (section === "crowding") return <MarketsRotationSurface sectorList={sectorList} selectedSector="semiconductors" view="positioning" selectedNodeId={null} />;
  return <div className="engine-module"><ObjectHeader eyebrow={`MARKETS / ${section.toUpperCase().replaceAll("-", " ")}`} title={title(section)} summary="Cross-asset market structure with coverage-gated conclusions." state={system.modules.core_market.state} /><RecordGrid record={fragility} /></div>;
}

export function SectorResearch({ sector, system }: { sector: string; system: ResearchSystem }) {
  const params = useSearchParams();
  const core = system.modules.core_market.payload ?? {};
  const sectorList = integrateSectorEngineRows((core.sectors ?? []) as SectorEngineRow[], system.modules.core_market.state);
  return <MarketsRotationSurface sectorList={sectorList} selectedSector={sector} view={params.get("view") ?? "snapshot" } selectedNodeId={params.get("node") ?? null} />;
}

function sectorHref(sector: SectorResearchObject, view = "snapshot", node?: string) {
  const query = new URLSearchParams({ sector: sector.slug, view });
  if (node) query.set("node", node);
  return `/markets?${query.toString()}`;
}

function SectorMetricStrip({ sector }: { sector: SectorResearchObject }) {
  return <section className="market-state-strip" aria-label={`${sector.name} current market state`}>
    <article><span>6M Relative Strength</span><strong>{percent(sector.rel6m)}</strong><small>vs SPY</small></article>
    <article><span>Breadth</span><strong>{sector.breadth}</strong><small>{sector.breadthRatio == null ? "coverage unavailable" : `${Math.round(sector.breadthRatio * 100)}% participating`}</small></article>
    <article><span>Crowding</span><strong>{sector.crowding}</strong><small>separate from momentum</small></article>
    <article><span>Stage</span><strong>{sector.stage}</strong><small>{sector.momentum}</small></article>
    <article><span>Theme</span><strong>{sector.primaryTheme}</strong></article>
  </section>;
}

function RotationMap({ selected, sectorList }: { selected: SectorResearchObject; sectorList: SectorResearchObject[] }) {
  const max = Math.max(...sectorList.map((sector) => Math.abs(sector.rel6m ?? 0)), 0.25);
  const crowdingY = (sector: SectorResearchObject) => sector.crowding.toLowerCase().includes("elevated") ? 24 : sector.crowding.toLowerCase().includes("moderate") ? 50 : 74;
  return <section className="rotation-map-panel">
    <header><div><span>ROTATION MAP</span><h2>Leadership vs positioning risk</h2></div><small>{rotationAxis.x} / {rotationAxis.y}</small></header>
    {!sectorList.some(sector => sector.rel6m != null && sector.crowding !== "Unavailable") ? <p role="status">Positioning plane unavailable: crowding measurements are missing. Dated relative strength is shown in the table; no crowding coordinate is invented.</p> : null}
    <div className="rotation-plane" role="img" aria-label="Sector rotation positioning plane">
      <span className="axis axis-x">Leadership / relative strength →</span><span className="axis axis-y">Crowding / extension ↑</span>
      {sectorList.filter(sector => sector.rel6m != null && sector.crowding !== "Unavailable").map((sector) => {
        const x = 50 + ((sector.rel6m ?? 0) / max) * 42;
        return <Link key={sector.slug} className={`sector-dot${sector.slug === selected.slug ? " selected" : ""}`} href={sectorHref(sector, "snapshot")} style={{ left: `${Math.max(8, Math.min(92, x))}%`, top: `${crowdingY(sector)}%` }}><strong>{sector.ticker}</strong><span>{sector.name}</span></Link>;
      })}
    </div>
    <p>{rotationAxis.reason} Sectors without both measurements are omitted from the plane; available relative strength and structural links remain in the table.</p>
  </section>;
}

function RotationTable({ sectorList }: { sectorList: SectorResearchObject[] }) {
  return <section className="sector-research-table" aria-label="Sector rotation table">
    <header><span>Sector</span><span>1M</span><span>3M</span><span>6M RS</span><span>Breadth</span><span>Crowding</span><span>Stage</span><span>Theme</span></header>
    {sectorList.map((sector) => <Link key={sector.slug} href={sectorHref(sector, "snapshot")} title={`${sector.measurementSource} · ${sector.measurementReason}`}><strong>{sector.name}<small>{sector.ticker}</small></strong><span>{percent(sector.rel1m)}</span><span>{percent(sector.rel3m)}</span><span>{percent(sector.rel6m)}</span><span>{sector.breadth}</span><span>{sector.crowding}</span><span>{sector.stage}</span><span>{sector.primaryTheme}</span></Link>)}
  </section>;
}

function SectorSnapshot({ sector }: { sector: SectorResearchObject }) {
  return <section className="sector-snapshot-surface">
    <header><span>MARKETS / SECTOR SNAPSHOT</span><h1>{sector.name}</h1><p>{sector.currentRead}</p></header>
    {sector.rel6m == null ? <p>{sector.measurementReason}</p> : null}
    <SectorMetricStrip sector={sector} />
    <nav className="sector-actions">
      <Link className="primary" href={sectorHref(sector, "structure")}>Explore Sector Structure →</Link>
      <Link href={sectorHref(sector, "leadership")}>Leadership</Link>
      <Link href={sectorHref(sector, "breadth")}>Breadth</Link>
      <Link href={sectorHref(sector, "positioning")}>Crowding / Positioning</Link>
      <Link href={sectorHref(sector, "report")}>Full Report</Link>
    </nav>
  </section>;
}

function SectorStructureMap({ sector, selectedNodeId }: { sector: SectorResearchObject; selectedNodeId: string | null }) {
  const selected = sector.structure.nodes.find((item) => item.id === selectedNodeId) ?? sector.structure.nodes[0];
  if (!selected) return <section><h2>Structure unavailable</h2><p>No curated structural model for {sector.ticker}; its reported measurements remain available above.</p></section>;
  return <section className="sector-structure-workspace">
    <div className="sector-map-canvas">
      <header><div><span>STRUCTURAL SECTOR MAP</span><h2>{sector.structure.template}</h2></div><small>{sector.structure.status}</small></header>
      <p>{sector.structure.summary}</p>
      <div className="sector-structure-grid">
        {sector.structure.nodes.map((node) => <Link key={node.id} className={`sector-structure-node${selected.id === node.id ? " selected" : ""}`} href={sectorHref(sector, "structure", node.id)}><span>{node.role}</span><strong>{node.title}</strong><small>{node.currentState}</small><b>{node.companies.slice(0, 4).join(" / ")}</b></Link>)}
      </div>
      <div className="sector-edge-ledger">{sector.structure.edges.map((edge) => <span key={`${edge.from}-${edge.to}`}>{nodeTitle(sector, edge.from)}<i>{edge.relationship}</i>{nodeTitle(sector, edge.to)}</span>)}</div>
    </div>
    <SectorNodeInspector sector={sector} node={selected} />
  </section>;
}

function nodeTitle(sector: SectorResearchObject, id: string) {
  return sector.structure.nodes.find((node) => node.id === id)?.title ?? id;
}

function SectorNodeInspector({ sector, node }: { sector: SectorResearchObject; node: SectorStructureNode }) {
  const evidence = node.evidenceIds.map((id) => sector.evidence.find((item) => item.id === id)).filter(Boolean);
  return <aside className="sector-node-inspector">
    <header><span>INSPECTOR / {node.role}</span><h3>{node.title}</h3></header>
    <dl><div><dt>Current State</dt><dd>{node.currentState}</dd></div><div><dt>Role</dt><dd>{node.role}</dd></div></dl>
    <section><span>Why it matters</span><p>{node.description}</p></section>
    <section><span>Evidence</span>{evidence.map((item) => item ? <article key={item.id}><b>{item.type}</b><strong>{item.label}</strong><small>{item.value} · {item.source}</small><p>{item.note}</p></article> : null)}</section>
    <section><span>Associated Companies</span><div className="sector-company-links">{node.companies.map((ticker) => <Link key={ticker} href={`/company/${ticker}?from=markets&sector=${sector.slug}`}>{ticker}</Link>)}</div></section>
    <section><span>Data Gaps</span>{node.dataGaps.length ? node.dataGaps.map((gap) => <p key={gap}>{gap}</p>) : <p>No node-specific gap recorded.</p>}</section>
  </aside>;
}

function SectorLeadership({ sector }: { sector: SectorResearchObject }) {
  const max = Math.max(...sector.leaders.map((item) => Math.abs(item.relativeStrength ?? 0)), 0.01);
  return <section className="sector-detail-panel"><header><span>LEADERSHIP</span><h2>Companies expressing the sector structure</h2></header><div className="sector-leadership-bars">{sector.leaders.map((leader) => <Link href={`/company/${leader.ticker}?from=markets&sector=${sector.slug}`} key={leader.ticker}><strong>{leader.ticker}<small>{leader.role}</small></strong><span>{leader.relativeStrength != null && Number.isFinite(leader.relativeStrength) ? <i style={{ width: `${Math.abs(leader.relativeStrength / max) * 100}%` }} /> : null}</span><b>{percent(leader.relativeStrength)}</b><em>{leader.condition}</em></Link>)}</div></section>;
}

function SectorEvidenceView({ sector, kind }: { sector: SectorResearchObject; kind: "breadth" | "positioning" }) {
  const titleText = kind === "breadth" ? "Breadth" : "Crowding / Positioning";
  const state = kind === "breadth" ? sector.breadth : sector.crowding;
  const detail = kind === "breadth" ? `${sector.breadthRatio == null ? "Coverage unavailable" : `${Math.round(sector.breadthRatio * 100)}% participating`} using backend breadth-label semantics.` : sector.crowdingBasis;
  return <section className="sector-detail-panel"><header><span>{titleText.toUpperCase()}</span><h2>{state}</h2></header><p>{detail}</p><div className="sector-evidence-ledger">{sector.evidence.map((item) => <article key={item.id}><span>{item.type}</span><strong>{item.label}</strong><b>{item.value}</b><p>{item.note}</p><small>{item.source} · {item.period}</small></article>)}</div><div className="sector-gap-strip">{sector.dataGaps.map((gap) => <span key={gap}>{gap}</span>)}</div></section>;
}

function SectorReport({ sector }: { sector: SectorResearchObject }) {
  return <section className="sector-report-mode"><header><span>FULL SECTOR REPORT</span><h2>{sector.name}</h2><Link href={sectorHref(sector, "snapshot")}>Close report →</Link></header>{["Snapshot", "Rotation Metrics", "Structure", "Leadership", "Breadth", "Crowding", "Evidence", "Data Gaps", "CLI Mapping"].map((heading) => <article key={heading}><h3>{heading}</h3><pre>{JSON.stringify(reportPayload(sector, heading), null, 2)}</pre></article>)}</section>;
}

function reportPayload(sector: SectorResearchObject, heading: string) {
  if (heading === "Snapshot") return { currentRead: sector.currentRead, stage: sector.stage, sourceState: sector.sourceState };
  if (heading === "Rotation Metrics") return { rel_1m: sector.rel1m, rel_3m: sector.rel3m, rel_6m: sector.rel6m, breadth: sector.breadth, crowding: sector.crowding, momentum: sector.momentum };
  if (heading === "Structure") return sector.structure;
  if (heading === "Leadership") return sector.leaders;
  if (heading === "Breadth") return { breadth: sector.breadth, breadthRatio: sector.breadthRatio };
  if (heading === "Crowding") return { crowding: sector.crowding, basis: sector.crowdingBasis, heat: sector.heat };
  if (heading === "Evidence") return sector.evidence;
  if (heading === "Data Gaps") return sector.dataGaps;
  return sector.reportNotes;
}

function MarketsRotationSurface({ sectorList, selectedSector, view, selectedNodeId }: { sectorList: SectorResearchObject[]; selectedSector?: string | null; view?: string | null; selectedNodeId?: string | null }) {
  const normalized = (selectedSector || "semiconductors").toLowerCase().replaceAll("_", "-");
  const selected = sectorList.find((sector) => sector.slug === normalized || sector.name.toLowerCase() === normalized || sector.ticker.toLowerCase() === normalized);
  if (!selected) return <section className="valuation-framework-state"><h1>Sector unavailable</h1><p>No structural research object matches {selectedSector}.</p><Link href="/markets">Return to sector overview →</Link></section>;
  if (view === "report") return <div className="engine-module"><SectorReport sector={selected} /></div>;
  return <div className="engine-module markets-research-surface">
    <ObjectHeader eyebrow="MARKETS / SECTOR ROTATION" title="Where leadership is moving" summary="Sector Rotation is the bridge between macro regime and company research: compare leadership, then open a sector, structure node, evidence, or company." state={selected.sourceState} />
    <div className="markets-topology">
      <RotationMap selected={selected} sectorList={sectorList} />
      <RotationTable sectorList={sectorList} />
    </div>
    <SectorSnapshot sector={selected} />
    {view === "structure" || selectedNodeId ? <SectorStructureMap sector={selected} selectedNodeId={selectedNodeId ?? null} /> : null}
    {view === "leadership" ? <SectorLeadership sector={selected} /> : null}
    {view === "breadth" ? <SectorEvidenceView sector={selected} kind="breadth" /> : null}
    {view === "positioning" ? <SectorEvidenceView sector={selected} kind="positioning" /> : null}
  </div>;
}

function DefensiveRotationSurface({ risk, state }: { risk: Record<string, unknown>; state: string }) {
  const evidence = (risk.evidence ?? {}) as Record<string, { label?: string; detail?: string }>;
  return <div className="engine-module"><ObjectHeader eyebrow="MARKETS / DEFENSIVE ROTATION" title="Risk regime in market context" summary="This view reuses the existing risk-regime engine output as a market-rotation lens. No duplicate computation." state={state} /><section className="defensive-rotation-grid">{Object.entries(evidence).map(([key, item]) => <article key={key}><span>{title(key)}</span><strong>{item?.label ?? "Unavailable"}</strong><p>{item?.detail ?? "No detail available from current risk-regime payload."}</p></article>)}</section><section className="object-section"><header><div><span>CONTEXT BRIDGE</span><h2>Macro risk → market defensives</h2></div><Link href="/macro/risk">Open Macro Risk Regime →</Link></header><p className="object-narrative">{String(risk.sector_context ?? "Sector weakness should be compared against defensive rotation and breadth before calling it broad risk-off.")}</p></section></div>;
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
  const historical = section === "historical";
  const fragility = (system.modules.core_market.payload?.fragility ?? {}) as Record<string, unknown>;
  return <div className="engine-module"><ObjectHeader eyebrow={`LABS / ${section.toUpperCase()}`} title={title(section)} summary={historical ? "Access to cached and prior research states where currently available. Future history is not fabricated." : "Experimental macro fragility research, shown at its actual coverage level."} state={historical ? "PARTIAL" : system.modules.core_market.state} />{historical ? <section className="engine-ledger"><header><h2>Available snapshots</h2><span>Last-valid cache</span></header>{system.dashboard.freshness.map((item, index) => <article key={index}><strong>{item.label ?? item.module ?? "Research engine"}</strong><Badge value={String(item.state ?? "CACHED")} /><span>{String(item.as_of ?? item.context ?? "Timestamp unavailable")}</span></article>)}</section> : <RecordGrid record={fragility} />}</div>;
}

export function FullMarketBrief({ system }: { system: ResearchSystem }) {
  const sections = [
    ["Global macro and liquidity", system.modules.core_market.payload?.macro],
    ["Macro fragility", system.modules.core_market.payload?.fragility],
    ["Macro catalysts", system.modules.core_market.payload?.catalysts],
    ["Risk regime and defensive rotation", system.modules.core_market.payload?.risk],
    ["Sector rotation", system.modules.core_market.payload?.sectors],
    ["Inflation pressure", system.modules.inflation.payload],
  ] as const;
  return <div className="engine-module full-market-brief"><ObjectHeader eyebrow="DASHBOARD / REPORT MODE" title="Full market brief" summary="A deliberate long-form view of the same normalized research snapshot used across the interactive workspaces." state="CACHED" />
    <div className="report-mode-notice"><strong>REPORT MODE</strong><span>Interactive investigation remains available through Macro, Markets, Companies, and Valuation.</span><Link href="/">Return to dashboard →</Link></div>
    {sections.map(([heading, payload], index) => <section className="object-section report-data-section" key={heading}><header><div><span>SECTION {String(index + 1).padStart(2, "0")}</span><h2>{heading}</h2></div></header><pre>{JSON.stringify(payload ?? { state: "UNAVAILABLE" }, null, 2)}</pre></section>)}
  </div>;
}
