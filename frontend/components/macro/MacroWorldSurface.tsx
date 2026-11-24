"use client";
import { StatusBadge } from "../research/StatusBadge";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { MacroComponent, MacroEvidence, MacroRegion, MacroTransmission, MacroWorld } from "../../lib/macro-types";
import { MacroWorldMap } from "./MacroWorldMap";
import { MacroEngineDetails } from "./MacroEngineDetails";
import { CoverageBar, CoverageDetail } from "./CoverageBar";
import { TransmissionGraph } from "../charts/AnalyticalCharts";
import { normalizeTransmissions } from "../../lib/research-visualization-adapter";

const REGION_ORDER = ["US", "JP", "KR", "EURO_AREA"];
// Checklist 18.8: short codes for display; EURO_AREA is an internal key.
const REGION_CODE: Record<string, string> = { EURO_AREA: "EA" };
const code = (id: string) => REGION_CODE[id] ?? id;
function timestamp(value: string) { return value.replace("T", " ").replace(/([+-]\d\d:\d\d|Z)$/, " UTC"); }

function readQuery() {
  if (typeof window === "undefined") return { mode: "regions", region: "", detail: "", edge: "" };
  const query = new URLSearchParams(window.location.search);
  return { mode: query.get("mode") ?? "regions", region: query.get("region") ?? "", detail: query.get("detail") ?? "", edge: query.get("edge") ?? "" };
}

function Status({ value }: { value: string }) {
  return <StatusBadge value={value} variant="macro" />;
}

function EvidenceRow({ evidence, expanded, onToggle }: { evidence: MacroEvidence; expanded: boolean; onToggle: () => void }) {
  return <article className="macro-evidence-row">
    <button type="button" aria-expanded={expanded} onClick={onToggle}><span className={`evidence-kind evidence-kind-${evidence.evidence_type.toLowerCase()}`}>{evidence.evidence_type}</span><strong>{evidence.label}</strong><b>{evidence.value}</b><i>{expanded ? "−" : "+"}</i></button>
    {expanded ? <div className="macro-evidence-detail"><dl><div><dt>Classification</dt><dd>{evidence.classification}</dd></div><div><dt>Period</dt><dd>{evidence.period ?? "Unavailable"}</dd></div><div><dt>Freshness</dt><dd>{evidence.freshness}</dd></div><div><dt>Source</dt><dd>{evidence.source}</dd></div></dl><p>{evidence.note}</p><code>{evidence.source_path}</code></div> : null}
  </article>;
}

function mechanismOrder(region: MacroRegion) {
  const preferred: Record<string, string[]> = {
    JP: ["inflation", "policy", "financial", "currency", "liquidity"],
    SG: ["inflation", "currency", "policy", "liquidity"],
    KR: ["markets", "fx", "transmission"],
    US: ["inflation", "policy", "financial", "currency", "liquidity"],
    EURO_AREA: ["inflation", "policy", "growth", "financial", "currency", "liquidity"],
  };
  const ordered = (preferred[region.id] || region.components.map((item) => item.id))
    .map((id) => region.components.find((component) => component.id === id))
    .filter((component): component is MacroComponent => Boolean(component));
  const remaining = region.components.filter((component) => !ordered.some((item) => item.id === component.id));
  return [...ordered, ...remaining];
}

function CountryMechanismCanvas({ region, onDetail }: { region: MacroRegion; onDetail: (id: string) => void }) {
  const components = mechanismOrder(region);
  const evidenceCount = components.reduce((count, component) => count + component.evidence_ids.length, 0);
  return <section className="country-mechanism-canvas" aria-label={`${region.name} macro mechanism map`}>
    <header>
      <div><span>MECHANISM MAP / {code(region.id)}</span><h3>{region.name} transmission structure</h3></div>
      <CoverageBar coverage={region.coverage} />
    </header>
    <p>{region.framework}</p>
    <div className="country-mechanism-path">
      {components.map((component, index) => <button type="button" key={component.id} onClick={() => onDetail(component.id)} className={`mechanism-node mechanism-node-${component.confidence.toLowerCase().replaceAll(" ", "-")}`}>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <strong>{component.label}</strong>
        <b>{component.state}</b>
        <small>{component.evidence_ids.length} evidence · {component.confidence}</small>
      </button>)}
    </div>
    <div className="mechanism-map-footer">
      <article><span>Evidence coverage</span><strong>{evidenceCount} linked records</strong><small>Click any node to inspect source evidence.</small></article>
      <article><span>Known data gaps</span><strong>{region.gaps.length || components.flatMap((item) => item.gaps).length}</strong><small>Missing data remains part of the result.</small></article>
    </div>
  </section>;
}

function RegionInspector({ region, selectedDetail, onDetail, onClose }: { region: MacroRegion; selectedDetail: string; onDetail: (id: string) => void; onClose: () => void }) {
  const component = region.components.find((item) => item.id === selectedDetail);
  const [openEvidence, setOpenEvidence] = useState<string>("");
  const evidence = component ? region.evidence.filter((item) => component.evidence_ids.includes(item.id)) : [];
  const exploringMechanism = selectedDetail === "mechanism";
  return <aside className="macro-region-inspector" aria-label={`${region.name} macro profile`}>
    <header><div><span>REGION / {code(region.id)}</span><h2>{region.name}</h2></div><button type="button" onClick={onClose}>Close · ESC</button></header>
    <div className="macro-region-brief"><CoverageDetail coverage={region.coverage} /><p>{region.brief}</p><dl><div><dt>Framework</dt><dd>{region.framework}</dd></div><div><dt>Confidence</dt><dd>{region.confidence}</dd></div></dl></div>
    <div className="macro-region-actions"><button type="button" className="primary-action" onClick={() => onDetail("mechanism")}>Explore {region.name}</button>{region.id === "KR" ? <button type="button" onClick={() => onDetail("markets")}>Open KOSPI</button> : null}<button type="button" onClick={() => onDetail("policy")}>Open Policy</button>{region.components.some((item) => item.id === "liquidity") ? <button type="button" onClick={() => onDetail("liquidity")}>Open Liquidity</button> : null}<button type="button" onClick={() => onDetail(region.components.find((item) => item.id === "financial" || item.id === "markets")?.id || region.components[0]?.id)}>Open Assets</button>{region.id === "US" ? <><Link href="/macro/inflation">Open Inflation</Link><Link href="/macro/rates">Open Rates</Link><Link href="/macro/risk">Open Risk</Link><Link href="/macro/fx">Open FX</Link></> : null}<button type="button" onClick={() => onDetail(component?.id || region.components[0]?.id)}>Evidence</button></div>
    <nav className="macro-component-nav" aria-label={`${region.name} macro components`}>
      {region.components.map((item) => <button type="button" key={item.id} className={component?.id === item.id ? "active" : ""} onClick={() => onDetail(item.id)}><span>{item.label}</span><strong>{item.state}</strong></button>)}
    </nav>
    {exploringMechanism ? <CountryMechanismCanvas region={region} onDetail={onDetail} /> : component ? <section className="macro-component-detail">
      <header><span>COMPONENT / {component.label.toUpperCase()}</span><Status value={component.confidence} /></header><h3>{component.state}</h3><p>{component.summary}</p>
      <div className="macro-detail-heading"><span>Evidence trace</span><b>{evidence.length} records</b></div>
      {evidence.length ? evidence.map((item) => <EvidenceRow key={item.id} evidence={item} expanded={openEvidence === item.id} onToggle={() => setOpenEvidence(openEvidence === item.id ? "" : item.id)} />) : <div className="macro-no-evidence">NO VERIFIED EVIDENCE AVAILABLE FOR THIS COMPONENT</div>}
      {component.gaps.length ? <div className="macro-gap-block"><span>Known gaps</span>{component.gaps.map((gap) => <p key={gap}>— {gap}</p>)}</div> : null}
    </section> : <div className="macro-inspector-prompt"><span>SELECT A COMPONENT</span><p>Move from the regional brief into one mechanism, then trace its evidence and source.</p></div>}
    <MacroEngineDetails engineSpecific={region.engine_specific} />
    <section className="macro-region-watches"><header><span>Watch conditions</span><small>{region.watch_conditions.length}</small></header>{region.watch_conditions.map((watch) => <article key={watch.label}><strong>{watch.label}</strong><Status value={watch.state} /><span>{watch.threshold}</span><b>{watch.current}</b></article>)}</section>
    <footer><span>Engines</span>{region.engines.map((engine) => <div key={engine.name}><strong>{engine.name}</strong><small>{engine.role}</small><Status value={engine.status} /></div>)}</footer>
  </aside>;
}

function EdgeInspector({ edge, evidence, onClose }: { edge: MacroTransmission; evidence: MacroEvidence[]; onClose: () => void }) {
  const chains: Record<string, string[]> = {
    "jp-us-yen-carry": ["BOJ policy", "Japanese rates", "JPY funding conditions", "Carry economics", "Global risk liquidity", "US risk assets"],
    "us-jp-rate-fx": ["Fed policy", "US rates", "Rate differential", "USD/JPY", "Japanese financial conditions"],
    "us-eu-rate-fx": ["Fed / ECB policy", "Rate differential", "EUR/USD", "Euro-area financial conditions"],
    "us-kr-dollar-kospi": ["US rates / dollar", "Capital conditions", "USD/KRW", "KOSPI / exporters"],
  };
  const chain = chains[edge.id] || [`${edge.source} policy / market state`, edge.label, `${edge.target} financial conditions`];
  return <aside className="macro-edge-inspector" aria-label={`${edge.label} transmission detail`}><header><span>TRANSMISSION / {edge.source} → {edge.target}</span><button type="button" onClick={onClose}>Close · ESC</button></header><h2>{edge.label}</h2><div className="edge-status"><div><span>Structural</span><Status value={edge.structural_state} /></div><div><span>Current</span><Status value={edge.current_state} /></div><div><span>Confidence</span><Status value={edge.confidence} /></div></div><section><span>Mechanism</span><p>{edge.mechanism}</p></section><section className="transmission-chain"><span>Structural chain</span><div>{chain.map((item, index) => <span key={item}><b>{item}</b>{index < chain.length - 1 ? <i>↓</i> : null}</span>)}</div></section><section><span>Current read</span><p>{edge.summary}</p></section><section className="edge-caveat"><span>Interpretive limit</span><p>{edge.caveat}</p></section><section><span>Counter evidence</span><p>No separately normalized counter-evidence series is supplied for this relationship.</p></section><section><span>Missing evidence</span><p>{edge.current_state === "INSUFFICIENT" ? edge.caveat : "No additional missing-field list is supplied beyond the stated interpretive limit."}</p></section><section><span>Activation / weakening</span><p>No numeric activation threshold is supplied. The current state changes only through the existing deterministic regional evidence and coverage rules.</p></section><div className="macro-detail-heading"><span>Evidence</span><b>{evidence.length} linked records</b></div>{evidence.map((item) => <div className="edge-evidence" key={item.id}><span>{item.evidence_type}</span><strong>{item.label}</strong><b>{item.value}</b><small>{item.period}</small></div>)}</aside>;
}

export function MacroWorldSurface({ world }: { world: MacroWorld }) {
  const [mode, setMode] = useState("regions");
  const [regionId, setRegionId] = useState("");
  const [detailId, setDetailId] = useState("");
  const [edgeId, setEdgeId] = useState("");
  const [notice, setNotice] = useState("");
  const [hoverRegionId, setHoverRegionId] = useState("");
  const [hoverUnavailable, setHoverUnavailable] = useState("");
  const region = world.regions[regionId];
  const hoverRegion = world.regions[hoverRegionId];
  const edge = world.transmissions.find((item) => item.id === edgeId);

  function push(next: { mode?: string; region?: string; detail?: string; edge?: string }) {
    const url = new URL(window.location.href);
    const values = { mode, region: regionId, detail: detailId, edge: edgeId, ...next };
    ["mode", "region", "detail", "edge"].forEach((key) => { const value = values[key as keyof typeof values]; if (value) url.searchParams.set(key, value); else url.searchParams.delete(key); });
    window.history.pushState({}, "", url);
  }
  function selectRegion(id: string) { setRegionId(id); setDetailId(""); setNotice(""); push({ mode: "regions", region: id, detail: "", edge: "" }); }
  function selectDetail(id: string) { setDetailId(id); push({ mode: "regions", region: regionId, detail: id, edge: "" }); }
  function selectEdge(id: string) { setEdgeId(id); push({ mode: "transmission", region: "", detail: "", edge: id }); }
  function changeMode(next: string) { setMode(next); setRegionId(""); setDetailId(""); setEdgeId(""); push({ mode: next, region: "", detail: "", edge: "" }); }

  useEffect(() => {
    const sync = () => { const query = readQuery(); setMode(query.mode); setRegionId(query.region); setDetailId(query.detail); setEdgeId(query.edge); };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  useEffect(() => {
    const closeDeepest = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (detailId) { setDetailId(""); push({ detail: "" }); }
      else if (regionId) { setRegionId(""); push({ region: "" }); }
      else if (edgeId) { setEdgeId(""); push({ edge: "" }); }
    };
    window.addEventListener("keydown", closeDeepest);
    return () => window.removeEventListener("keydown", closeDeepest);
  });
  const evidence = useMemo(() => edge ? edge.evidence_ids.map((id) => world.evidence_index[id]).filter(Boolean) : [], [edge, world]);
  const transmission = useMemo(() => normalizeTransmissions(world), [world]);

  return <div className="macro-world-surface">
    <header className="macro-world-header"><div><Link className="markets-back-link" href="/macro">← Macro story</Link><span>MACRO / WORLD RESEARCH SYSTEM</span><h1>World Macro Map</h1><p>Start with the world. Open one economy, one mechanism, and only then the evidence beneath it.</p></div><div className="macro-mode-switch" role="tablist"><button role="tab" aria-selected={mode === "regions"} onClick={() => changeMode("regions")}>Regions</button><button role="tab" aria-selected={mode === "transmission"} onClick={() => changeMode("transmission")}>Transmission</button></div></header>
    <div className="macro-coverage-strip"><span>Coverage / 04 economies</span><span>State / cached research</span><span>Facts · proxies · inference</span><span>No recommendations</span></div>
    {mode === "regions" ? <div className={`macro-region-layout ${region ? "has-inspector" : ""}`}><div className="macro-world-main">
      <div className="macro-world-map-wrap"><MacroWorldMap regions={world.regions} selected={regionId} onSelect={selectRegion} onUnavailable={(label) => setNotice(`${label.toUpperCase()} / NOT AVAILABLE — no verified macro profile is integrated.`)} onHover={(id) => { setHoverRegionId(id); setHoverUnavailable(""); }} onHoverUnavailable={(label) => { setHoverUnavailable(label); setHoverRegionId(""); }} onLeave={() => { setHoverRegionId(""); setHoverUnavailable(""); }} />
      {hoverRegion ? <aside className="macro-map-tooltip" aria-live="polite"><header><strong>{hoverRegion.name.toUpperCase()}</strong><CoverageBar coverage={hoverRegion.coverage} /></header><span>Research coverage</span>{hoverRegion.components.slice(0, 5).map((item) => <div key={item.id}><b>{item.label}</b><small>{item.confidence}</small></div>)}<p>{hoverRegion.brief}</p><small>Click marker to open {hoverRegion.name}.</small></aside> : null}
      {hoverUnavailable ? <aside className="macro-map-tooltip unavailable" aria-live="polite"><header><strong>{hoverUnavailable.toUpperCase()}</strong><Status value="NOT AVAILABLE" /></header><p>No verified CHAINSTOX macro engine currently covers this economy.</p></aside> : null}</div>
      {notice ? <div className="macro-unavailable-notice" role="status"><strong>NOT AVAILABLE</strong><span>{notice}</span><button onClick={() => setNotice("")} type="button">Dismiss</button></div> : null}
      <section className="macro-region-index"><header><span>Supported economy index</span><small className="cov-legend"><i className="cov-seg cov-full" />all data <i className="cov-seg cov-partial" />some missing <i className="cov-seg cov-stale" />out of date <i className="cov-seg cov-missing" />none <i className="cov-seg cov-not_covered" />not modelled</small></header>{REGION_ORDER.map((id) => { const item = world.regions[id]; return <button type="button" key={id} onClick={() => selectRegion(id)}><b>{code(id)}</b><span><strong>{item.name}</strong><small>{item.framework}</small></span><CoverageBar coverage={item.coverage} /><i>→</i></button>; })}</section>
    </div>{region ? <RegionInspector region={region} selectedDetail={detailId} onDetail={selectDetail} onClose={() => { setRegionId(""); setDetailId(""); push({ region: "", detail: "" }); }} /> : null}</div> : <div className={`macro-transmission-layout ${edge ? "has-inspector" : ""}`}><div className="macro-world-main"><header className="transmission-header"><span>MECHANISM NETWORK</span><h2>Cross-border transmission</h2><p>Solid, dashed, and dotted edges distinguish fact, proxy, and inference. No coefficient or causal strength is invented.</p></header><TransmissionGraph nodes={transmission.nodes} edges={transmission.edges} selected={edgeId} onSelect={(item) => selectEdge(item.id)} /><div className="transmission-edge-list">{world.transmissions.map((item) => <button type="button" key={item.id} className={edgeId === item.id ? "active" : ""} onClick={() => selectEdge(item.id)}><span>{item.source} → {item.target}</span><strong>{item.label}</strong><Status value={item.current_state} /></button>)}</div></div>{edge ? <EdgeInspector edge={edge} evidence={evidence} onClose={() => { setEdgeId(""); push({ edge: "" }); }} /> : null}</div>}
    <footer className="macro-world-footer"><span>{world.disclaimer}</span><span>Generated {timestamp(world.generated_at)}</span></footer>
  </div>;
}
