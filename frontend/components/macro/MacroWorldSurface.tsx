"use client";
import { StatusBadge } from "../research/StatusBadge";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { MacroEvidence, MacroRegion, MacroTransmission, MacroWorld } from "../../lib/macro-types";
import { MacroWorldMap } from "./MacroWorldMap";
import { MacroEngineDetails } from "./MacroEngineDetails";
import { CoverageBar, CoverageDetail } from "./CoverageBar";
import { ChannelsView } from "./ChannelsView";
import { FedPathPanel } from "./FedPathPanel";
import { CHANNEL_CHAIN, exposureLine, factorsLine, REGION_FACTORS } from "../../lib/channel-exposure";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";

const REGION_ORDER = ["US", "JP", "KR", "EURO_AREA"];
const SERIES_PLAIN: Record<string, string> = { cpi_ex_fresh_food: "CPI", unemployment: "unemployment rate", pmi: "business survey (PMI)" };
const REGION_ADJ: Record<string, string> = { US: "US", JP: "Japan", KR: "Korea", EURO_AREA: "Euro area" };
export type FxPair = { label?: string; level?: number | null; change_3m?: number | null; observed_at?: string | null };

/** "Japan CPI (FRED series stopped in 2021)" instead of "cpi_ex_fresh_food (JPNCPIALLMINMEI, last 2021-06-01)". */
function coverageGaps(region: MacroRegion): string[] {
  const c = region.coverage;
  if (!c) return [];
  const stopped = (c.stale_inputs ?? []).map((item) => `${REGION_ADJ[region.id] ?? region.name} ${SERIES_PLAIN[item.key] ?? item.key.replace(/_/g, " ")} (FRED series stopped in ${String(item.last).slice(0, 4)})`);
  const missing = c.areas.flatMap((area) => area.missing.map((m) => `${area.label}: ${m} (not collected)`));
  return [...stopped, ...missing];
}
const REGION_CODE: Record<string, string> = { EURO_AREA: "EA" };
const code = (id: string) => REGION_CODE[id] ?? id;
function sentence(value: string) { const t = String(value ?? "").replace(/_/g, " ").toLowerCase(); return t.charAt(0).toUpperCase() + t.slice(1); }
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

const EMPTY_STATES = new Set(["NOT AVAILABLE", "INSUFFICIENT"]);
const POLICY_BANK: Record<string, string> = { US: "Fed", JP: "Bank of Japan", EURO_AREA: "ECB" };

/** Up to three plain facts per economy card, from stored readings only. */
function economyFacts(id: string, region: MacroRegion, fx: Record<string, FxPair>): string[] {
  const state = (key: string) => region.components.find((c) => c.id === key)?.state;
  const usable = (v?: string) => v && !["NOT AVAILABLE", "INSUFFICIENT", "No Signal"].includes(v);
  const out: string[] = [];
  const policy = state("policy");
  if (POLICY_BANK[id] && usable(policy)) out.push(`${POLICY_BANK[id]}: ${sentence(policy!).toLowerCase()}`);
  if (id === "KR") {
    const krw = fx.usdkrw;
    if (typeof krw?.level === "number") {
      const ch = krw.change_3m;
      out.push(`₩${Math.round(krw.level).toLocaleString("en-US")} per $${typeof ch === "number" ? ` · won ${ch <= 0 ? "up" : "down"} ${Math.abs(ch * 100).toFixed(1)}% in 3 months` : ""}`);
    }
    const exp = (region.engine_specific as { kospi?: { export_snapshot?: { total_exports_usd_b?: number; semiconductors_usd_b?: number; period?: string } } } | undefined)?.kospi?.export_snapshot;
    if (exp?.total_exports_usd_b && exp.semiconductors_usd_b) out.push(`Chips ${Math.round((exp.semiconductors_usd_b / exp.total_exports_usd_b) * 100)}% of exports (${exp.period ?? "latest year"})`);
    if (/tech/i.test(state("markets") ?? "")) out.push("KOSPI moves most with chip stocks");
    return out;
  }
  if (id === "EURO_AREA" && typeof fx.eurusd?.change_3m === "number") out.push(`Euro ${fx.eurusd.change_3m >= 0 ? "up" : "down"} ${Math.abs(fx.eurusd.change_3m * 100).toFixed(1)}% vs $ in 3 months`);
  for (const key of ["inflation", "growth"]) { const v = state(key); if (usable(v) && out.length < 3) out.push(`${key === "inflation" ? "Inflation" : "Growth"}: ${sentence(v!).toLowerCase()}`); }
  return out.slice(0, 3);
}

function RegionInspector({ region, selectedDetail, onDetail, onClose, drivers }: { region: MacroRegion; selectedDetail: string; onDetail: (id: string) => void; onClose: () => void; drivers: DriverRow[] | null }) {
  const component = region.components.find((item) => item.id === selectedDetail);
  const [openEvidence, setOpenEvidence] = useState<string>("");
  const evidence = component ? region.evidence.filter((item) => component.evidence_ids.includes(item.id)) : [];
  const empty = region.components.filter((item) => EMPTY_STATES.has(item.state));
  const gaps = [...empty.map((item) => `${item.label}: ${item.summary}`), ...coverageGaps(region)];
  const watches = region.watch_conditions.filter((watch) => !EMPTY_STATES.has(String(watch.state).toUpperCase()));
  return <aside className="macro-region-inspector" aria-label={`${region.name} macro profile`}>
    <header><div><span>REGION / {code(region.id)}</span><h2>{region.name}</h2></div><button type="button" onClick={onClose}>Close · ESC</button></header>
    <p className="mri-lead">{region.brief}</p>
    <section className="mri-holdings"><span>Your holdings it moved · 3 months</span><p>{factorsLine(REGION_FACTORS[region.id] ?? [], drivers).replace(/^Your holdings, 3 months: /, "")}</p></section>
    <nav className="macro-component-nav" aria-label={`${region.name} macro components`}>
      {region.components.filter((item) => !EMPTY_STATES.has(item.state)).map((item) => <button type="button" key={item.id} className={component?.id === item.id ? "active" : ""} onClick={() => onDetail(item.id)}><span>{item.label}</span><strong>{sentence(item.state)}</strong></button>)}
    </nav>
    {component ? <section className="macro-component-detail">
      <header><span>{component.label.toUpperCase()}</span><Status value={component.confidence} /></header><h3>{sentence(component.state)}</h3><p>{component.summary}</p>
      <div className="macro-detail-heading"><span>Evidence</span><b>{evidence.length} records</b></div>
      {evidence.length ? evidence.map((item) => <EvidenceRow key={item.id} evidence={item} expanded={openEvidence === item.id} onToggle={() => setOpenEvidence(openEvidence === item.id ? "" : item.id)} />) : <div className="macro-no-evidence">No measured evidence for this reading.</div>}
      {component.gaps.length ? <div className="macro-gap-block"><span>Known gaps</span>{component.gaps.map((gap) => <p key={gap}>— {gap}</p>)}</div> : null}
    </section> : <p className="mri-prompt">Pick a reading above to see its evidence.</p>}
    {region.id === "US" ? <div className="macro-region-actions"><Link href="/macro/inflation">Inflation →</Link><Link href="/macro/conditions#rates">Rates →</Link><Link href="/macro/conditions#fx">Dollar →</Link><Link href="/macro/conditions#regime">Risk mood →</Link></div> : null}
    {watches.length ? <section className="macro-region-watches"><header><span>What we&apos;re watching</span><small>{watches.length}</small></header>{watches.map((watch) => <article key={watch.label}><strong>{watch.label}</strong><Status value={watch.state} /><span>{watch.threshold}</span><b>{watch.current}</b></article>)}</section> : null}
    <MacroEngineDetails engineSpecific={region.engine_specific} />
    <details className="mri-coverage"><summary>Data coverage &amp; gaps{region.coverage ? ` · ${region.coverage.available} of ${region.coverage.expected} inputs` : ""}</summary>
      <CoverageDetail coverage={region.coverage} />
      {gaps.length ? <ul className="mri-gaps">{gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul> : null}
      <dl><div><dt>Framework</dt><dd>{region.framework}</dd></div><div><dt>Confidence</dt><dd>{region.confidence}</dd></div></dl>
      <footer><span>Engines</span>{region.engines.map((engine) => <div key={engine.name}><strong>{engine.name}</strong><small>{engine.role}</small><Status value={engine.status} /></div>)}</footer>
    </details>
  </aside>;
}

function EdgeInspector({ edge, evidence, onClose }: { edge: MacroTransmission; evidence: MacroEvidence[]; onClose: () => void }) {
  const chain = CHANNEL_CHAIN[edge.id] || [`${edge.source} policy / market state`, edge.label, `${edge.target} financial conditions`];
  return <aside className="macro-edge-inspector" aria-label={`${edge.label} transmission detail`}><header><span>TRANSMISSION / {edge.source} → {edge.target}</span><button type="button" onClick={onClose}>Close · ESC</button></header><h2>{edge.label}</h2><div className="edge-status"><div><span>Structural</span><Status value={edge.structural_state} /></div><div><span>Current</span><Status value={edge.current_state} /></div><div><span>Confidence</span><Status value={edge.confidence} /></div></div><section><span>Mechanism</span><p>{edge.mechanism}</p></section><section className="transmission-chain"><span>Structural chain</span><div>{chain.map((item, index) => <span key={item}><b>{item}</b>{index < chain.length - 1 ? <i>↓</i> : null}</span>)}</div></section><section><span>Current read</span><p>{edge.summary}</p></section><section className="edge-caveat"><span>Interpretive limit</span><p>{edge.caveat}</p></section><div className="macro-detail-heading"><span>Evidence</span><b>{evidence.length} linked records</b></div>{evidence.map((item) => <div className="edge-evidence" key={item.id}><span>{item.evidence_type}</span><strong>{item.label}</strong><b>{item.value}</b><small>{item.period}</small></div>)}</aside>;
}

export type WorldQuery = { mode?: string; region?: string; detail?: string; edge?: string };

// The server passes the URL query in, so the first client render matches the server render (no hydration mismatch).
export function MacroWorldSurface({ world, initial = {}, fxPairs = {} }: { world: MacroWorld; initial?: WorldQuery; fxPairs?: Record<string, FxPair> }) {
  const [mode, setMode] = useState(initial.mode || "regions");
  const [regionId, setRegionId] = useState(initial.region || "");
  const [detailId, setDetailId] = useState(initial.detail || "");
  const [edgeId, setEdgeId] = useState(initial.edge || "");
  const [notice, setNotice] = useState("");
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); }); return () => { active = false; }; }, []);
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
  function selectRegion(id: string) { setRegionId(id); setDetailId(""); setEdgeId(""); setNotice(""); push({ mode: "regions", region: id, detail: "", edge: "" }); }
  function selectDetail(id: string) { setDetailId(id); push({ mode: "regions", region: regionId, detail: id, edge: "" }); }
  function selectEdgeInline(id: string) { setEdgeId(id); setRegionId(""); setDetailId(""); push({ mode: "regions", region: "", detail: "", edge: id }); }
  function changeMode(next: string) { setMode(next); setRegionId(""); setDetailId(""); setEdgeId(""); push({ mode: next, region: "", detail: "", edge: "" }); }

  useEffect(() => {
    const sync = () => { const query = readQuery(); setMode(query.mode); setRegionId(query.region); setDetailId(query.detail); setEdgeId(query.edge); };
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
  const activeCount = world.transmissions.filter((t) => t.current_state === "ACTIVE").length;
  const hasRegionsInspector = Boolean(region || edge);

  return (
    <div className="macro-world-surface macro-world-upgraded">
      <header className="macro-world-header">
        <div>
          <Link className="markets-back-link" href="/macro">← Market story</Link>
          <h1>World Macro Map</h1>
          <p>What the world&apos;s big central banks are doing, how it travels into US stocks, and which of your holdings it reached.</p>
        </div>
        <div className="macro-mode-switch" role="tablist">
          <button role="tab" aria-selected={mode === "regions"} onClick={() => changeMode("regions")}>World &amp; Channels</button>
          <button role="tab" aria-selected={mode === "transmission"} onClick={() => changeMode("transmission")}>Channels → holdings</button>
        </div>
      </header>

      <div className="macro-world-summary-bar">
        <span className="mws-pill active">
          <i />
          <b>{activeCount} active cross-border {activeCount === 1 ? "pressure" : "pressures"}</b>
        </span>
        <span className="mws-text">
          {world.transmissions
            .filter((t) => t.current_state === "ACTIVE")
            .map((t) => t.label)
            .join(" · ") || "No elevated cross-border transmission triggers."}
        </span>
        <span className="mws-meta">US · Japan · South Korea · Euro Area</span>
      </div>

      {mode === "regions" ? <div id="central-banks" className="macro-central-banks"><FedPathPanel /></div> : null}

      {mode === "regions" ? (
        <div className={`macro-region-layout ${hasRegionsInspector ? "has-inspector" : ""}`}>
          <div className="macro-world-main">
            <div className="macro-world-map-wrap">
              <MacroWorldMap
                regions={world.regions}
                transmissions={world.transmissions}
                selected={regionId}
                selectedEdge={edgeId}
                onSelect={selectRegion}
                onSelectEdge={selectEdgeInline}
                onUnavailable={(label) => setNotice(`${label.toUpperCase()} / NOT AVAILABLE — no verified macro profile is integrated.`)}
                onHover={(id) => { setHoverRegionId(id); setHoverUnavailable(""); }}
                onHoverUnavailable={(label) => { setHoverUnavailable(label); setHoverRegionId(""); }}
                onLeave={() => { setHoverRegionId(""); setHoverUnavailable(""); }}
              />
              {hoverRegion ? (
                <aside className="macro-map-tooltip" aria-live="polite">
                  <header><strong>{hoverRegion.name.toUpperCase()}</strong><CoverageBar coverage={hoverRegion.coverage} /></header>
                  <p>{hoverRegion.brief}</p>
                  {hoverRegion.components.filter((c) => c.state !== "NOT AVAILABLE").slice(0, 4).map((item) => (
                    <div key={item.id}><b>{item.label}</b><small>{item.state}</small></div>
                  ))}
                  <small>Click card to inspect {hoverRegion.name} mechanisms &amp; evidence →</small>
                </aside>
              ) : null}
              {hoverUnavailable ? (
                <aside className="macro-map-tooltip unavailable" aria-live="polite">
                  <header><strong>{hoverUnavailable.toUpperCase()}</strong><Status value="NOT AVAILABLE" /></header>
                  <p>No verified CHAINSTOX macro engine currently covers this economy.</p>
                </aside>
              ) : null}
            </div>

            {notice ? (
              <div className="macro-unavailable-notice" role="status">
                <strong>NOT AVAILABLE</strong>
                <span>{notice}</span>
                <button onClick={() => setNotice("")} type="button">Dismiss</button>
              </div>
            ) : null}

            {/* Live Cross-Border Transmission Channels visible immediately on first load */}
            <section className="macro-live-channels" aria-label="Cross-border transmission channels">
              <header>
                <div>
                  <h2>How policy abroad reaches your stocks</h2>
                </div>
                <small>Click a channel for its evidence</small>
              </header>
              <div className="macro-channel-grid">
                {world.transmissions.map((item) => {
                  const isActive = item.current_state === "ACTIVE";
                  return (
                    <button
                      type="button"
                      key={item.id}
                      className={`macro-channel-card ${isActive ? "is-active" : "is-watch"}${edgeId === item.id ? " selected" : ""}`}
                      onClick={() => selectEdgeInline(item.id)}
                    >
                      <div className="mcc-top">
                        <span className="mcc-route">{code(item.source)} → {code(item.target)}</span>
                        <span className={`mcc-state ${isActive ? "on" : ""}`}>{isActive ? "Active" : item.current_state === "WATCH" ? "Watching" : sentence(item.current_state)}</span>
                      </div>
                      <strong>{item.label}</strong>
                      <small className="mcc-equity">{exposureLine(item.id, drivers)}</small>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* 4 Supported Economy Cards (preserving .macro-region-index > button contract) */}
            <section className="macro-region-index macro-economy-cards">
              <header>
                <div>
                  <h2>Economies we model</h2>
                </div>
                <small>Click one for its policy and data</small>
              </header>
              {REGION_ORDER.map((id) => {
                const item = world.regions[id];
                if (!item) return null;
                const facts = economyFacts(id, item, fxPairs);
                return (
                  <button
                    type="button"
                    key={id}
                    className={`macro-econ-card${regionId === id ? " selected" : ""}`}
                    onClick={() => selectRegion(id)}
                  >
                    <div className="mec-head">
                      <div className="mec-title">
                        <b>{code(id)}</b>
                        <strong>{item.name}</strong>
                      </div>
                    </div>
                    <p className="mec-lead">{factorsLine(REGION_FACTORS[id] ?? [], drivers)}</p>
                    <div className="mec-pills">{facts.map((fact) => <span key={fact}>{fact}</span>)}</div>
                    {id === "KR" ? <small className="mec-note">Bank of Korea rate and Korean inflation aren&apos;t stored yet.</small> : null}
                    <small className="mec-cta">Open {item.name} →</small>
                  </button>
                );
              })}
            </section>
          </div>

          {region ? (
            <RegionInspector
              region={region}
              selectedDetail={detailId}
              onDetail={selectDetail}
              onClose={() => { setRegionId(""); setDetailId(""); push({ region: "", detail: "" }); }}
              drivers={drivers}
            />
          ) : edge ? (
            <EdgeInspector
              edge={edge}
              evidence={evidence}
              onClose={() => { setEdgeId(""); push({ edge: "" }); }}
            />
          ) : null}
        </div>
      ) : (
        <ChannelsView world={world} drivers={drivers} />
      )}

      <footer className="macro-world-footer">
        <span>{world.disclaimer}</span>
        <span>Generated {timestamp(world.generated_at)}</span>
      </footer>
    </div>
  );
}
