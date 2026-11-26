"use client";
import { StatusBadge } from "./StatusBadge";

import Link from "next/link";
import { useState } from "react";
import { ChartUnavailable, DivergingBarChart } from "../charts/AnalyticalCharts";
import type { InflationMetric, ResearchSystem } from "../../lib/research-system-types";
import type { QuantitativeDatum } from "../../lib/visualization-types";

function Badge({ state }: { state: string }) { return <StatusBadge value={state} />; }
function Value({ value }: { value: unknown }) { return <>{value === null || value === undefined || value === "" ? "Unavailable" : typeof value === "number" ? value.toFixed(2) : String(value)}</>; }

function humanizeCode(value: string | null | undefined) {
  if (!value) return "Unavailable";
  return value.toLowerCase().replaceAll("_", " ").replace(/^\w/, (ch) => ch.toUpperCase());
}

function Inflation({ system }: { system: ResearchSystem }) {
  const report = system.modules.inflation.payload;
  const [selectedKey, setSelectedKey] = useState("");
  if (!report) return <Unavailable title="US Inflation" state={system.modules.inflation.state} />;
  const moduleStale = system.modules.inflation.state === "STALE" || system.modules.inflation.state === "CACHED";
  const sections = Object.values(report.metrics).reduce<Record<string, InflationMetric[]>>((groups, metric) => {
    (groups[metric.section] ||= []).push(metric);
    return groups;
  }, {});
  const selected = report.metrics[selectedKey] || Object.values(report.metrics)[0];
  const freshnessLabel = selected.freshness === "CURRENT" && moduleStale
    ? "Cached snapshot (current at capture)"
    : humanizeCode(selected.freshness);
  const momentum: QuantitativeDatum[] = selected ? [
    ...(typeof selected.trend_3m === "number" ? [{ id: `${selected.key}-3m`, label: "3M momentum", value: selected.trend_3m, unit: "reported change", status: selected.pressure_label, context: selected.pressure_reason, scaleGroup: "inflation-momentum" }] : []),
    ...(typeof selected.trend_6m === "number" ? [{ id: `${selected.key}-6m`, label: "6M momentum", value: selected.trend_6m, unit: "reported change", status: selected.pressure_label, context: selected.pressure_reason, scaleGroup: "inflation-momentum" }] : []),
  ] : [];
  return <div className="engine-module">
    <header className="engine-module-header"><div><Link className="markets-back-link" href="/macro">← Macro story</Link><span>US INFLATION / 27-METRIC PIPELINE</span><h1>Inflation pressure</h1><p>{report.horizon_reason}</p></div><Badge state={system.modules.inflation.state} /></header>
    <section className="engine-kpis"><article><span>1–3 month</span><strong>{report.near_term}</strong></article><article><span>3–12 month</span><strong>{report.medium_term}</strong></article><article><span>Fed sensitivity</span><strong>{report.fed_sensitivity}</strong></article><article><span>Coverage</span><strong>{report.available} / {report.total}</strong></article><article><span>Common month</span><strong>{report.common_month}</strong></article></section>
    <section className="inflation-visual-workspace"><div className="inflation-category-matrix">{Object.entries(sections).map(([section, metrics]) => <section key={section}><header><div><span>{section.toUpperCase()}</span><strong>{report.states[section.toLowerCase()] || "Deterministic category"}</strong></div><small>{metrics.filter((metric) => metric.status === "AVAILABLE").length}/{metrics.length}</small></header><div>{metrics.map((metric) => <button type="button" key={metric.key} className={`inflation-cell state-${metric.status.toLowerCase().replaceAll("_", "-")} ${selected.key === metric.key ? "selected" : ""}`} onClick={() => setSelectedKey(metric.key)}><span>{metric.name}</span><b><Value value={metric.current} /></b><small>{metric.pressure_label}</small></button>)}</div></section>)}</div>
      <aside className="inflation-indicator-inspector"><header><div><span>INDICATOR / {selected.section.toUpperCase()}</span><h2>{selected.name}</h2></div><Badge state={selected.status} /></header><div className="indicator-primary"><strong><Value value={selected.current} /></strong><span>{selected.date || "No current observation"}</span></div><dl><div><dt>Forward role</dt><dd>{humanizeCode(selected.forward_role)}</dd></div><div><dt>Freshness</dt><dd>{freshnessLabel}</dd></div><div><dt>Validation</dt><dd>{humanizeCode(selected.validation_status)}</dd></div><div><dt>Source</dt><dd>{selected.source} · {selected.series || "No series ID"}</dd></div></dl><section><span>INTERPRETATION</span><strong>{selected.pressure_label}</strong><p>{selected.pressure_reason}</p></section><section><span>REFERENCE</span><p>{selected.reference}</p></section>{momentum.length ? <DivergingBarChart data={momentum} /> : <ChartUnavailable label="No comparable 3M/6M momentum observations are supplied for this indicator." />}<footer>The normalized engine payload supplies current level and momentum fields, but not a complete historical observation array for this indicator. No time-series line is fabricated.</footer></aside>
    </section>
  </div>;
}

function Risk({ system }: { system: ResearchSystem }) {
  const core = system.modules.core_market.payload as { risk?: { regime?: string; confidence?: string; coverage?: number; summary?: string; evidence?: unknown[][]; interpretation?: string[]; invalidation?: string[]; unavailable?: string[] }; data_quality?: Record<string, unknown> } | null;
  const risk = core?.risk;
  if (!risk) return <Unavailable title="Risk Regime" state={system.modules.core_market.state} />;
  const publishable = core?.data_quality?.state === "AVAILABLE";
  return <div className="engine-module"><header className="engine-module-header"><div><span>CROSS-ASSET RISK / COVERAGE GATED</span><h1>{publishable ? risk.regime : "Insufficient evidence"}</h1><p>{risk.summary}</p></div><Badge state={system.modules.core_market.state} /></header><section className="engine-kpis"><article><span>Published regime</span><strong>{publishable ? risk.regime : "WITHHELD"}</strong></article><article><span>Confidence</span><strong>{publishable ? risk.confidence : "WITHHELD"}</strong></article><article><span>Coverage</span><strong>{((risk.coverage || 0) * 100).toFixed(0)}%</strong></article><article><span>Quality rule</span><strong>≥ 50%</strong></article></section>{publishable ? <section className="engine-ledger"><header><h2>Cross-asset evidence</h2><span>Verified inputs</span></header>{risk.evidence?.map((row, index) => <article key={index}><strong>{String(row[0])}</strong><Badge state={String(row[1])} /><span>{String(row[2])}</span></article>)}</section> : <section className="risk-coverage-summary"><header><div><span>RISK COVERAGE</span><h2>Conclusion withheld</h2></div><Badge state="INSUFFICIENT" /></header><p>The configured risk regime needs at least half of its cross-asset inputs. The current cache contains no qualifying inputs, so the model does not publish a risk label.</p><details><summary>View missing inputs · {risk.evidence?.length || risk.unavailable?.length || 0}</summary>{risk.evidence?.map((row, index) => <span key={index}>— {String(row[0])}</span>)}</details></section>}<section className="engine-note"><span>Publication guardrail</span><p>{String(core?.data_quality?.rule)}</p></section></div>;
}

function Rotation({ system }: { system: ResearchSystem }) {
  const core = system.modules.core_market.payload as { sectors?: Record<string, unknown>[]; data_quality?: Record<string, unknown> } | null;
  const sectors = core?.sectors || [];
  return <div className="engine-module"><header className="engine-module-header"><div><span>SECTOR ROTATION / LIVE RANKING</span><h1>{sectors.length ? "Sector leadership" : "Insufficient evidence"}</h1><p>{sectors.length ? "Relative strength, breadth, and market structure by sector." : "The system withheld a sector leaderboard because the live input set did not pass coverage checks."}</p></div><Badge state={system.modules.core_market.state} /></header>{sectors.length ? <section className="engine-object-table">{sectors.map((sector, index) => <article key={index}>{Object.entries(sector).map(([key, value]) => <div key={key}><span>{key}</span><strong><Value value={value} /></strong></div>)}</article>)}</section> : <section className="workspace-empty-state"><span>ROTATION / COVERAGE GATE</span><h3>No publishable ranking</h3><p>Last refresh: {String(core?.data_quality?.available_macro_inputs || 0)} / {String(core?.data_quality?.total_macro_inputs || 0)} macro inputs, {String(core?.data_quality?.risk_coverage || 0)} risk coverage, and {String(core?.data_quality?.sector_rows || 0)} sector rows.</p></section>}</div>;
}

function Watches({ system }: { system: ResearchSystem }) { return <div className="engine-module"><header className="engine-module-header"><div><span>THRESHOLD LEDGER / SYSTEM-WIDE</span><h1>Research watches</h1><p>Observable conditions that could change the current interpretation. A watch is not a recommendation.</p></div><Badge state="CACHED" /></header><section className="engine-watch-table">{system.dashboard.watch_conditions.map((watch, index) => <article key={index}><div><span>{watch.module}</span><strong>{watch.label}</strong></div><p>{watch.threshold}</p><b>{watch.current}</b><Badge state={String(watch.state)} /></article>)}</section></div>; }

function Unavailable({ title, state }: { title: string; state: string }) { return <div className="engine-module"><header className="engine-module-header"><div><span>RESEARCH ENGINE</span><h1>{title}</h1><p>No last-valid normalized payload is available.</p></div><Badge state={state} /></header></div>; }

export function ResearchModule({ module, system }: { module: string; system: ResearchSystem }) {
  if (module === "inflation") return <Inflation system={system} />;
  if (module === "risk") return <Risk system={system} />;
  if (module === "rotation") return <Rotation system={system} />;
  return <Watches system={system} />;
}
