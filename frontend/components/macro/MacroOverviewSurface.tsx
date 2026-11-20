"use client";
import { StatusBadge } from "../research/StatusBadge";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { MacroCoverageState, MacroLiquidityDriver, MacroTypedMetric, ResearchSystem } from "../../lib/research-system-types";
import type { QuantitativeDatum } from "../../lib/visualization-types";
import { DivergingBarChart, YieldCurveChart } from "../charts/AnalyticalCharts";
import { MacroWorldMap } from "./MacroWorldMap";

function Status({ value }: { value: string }) { return <StatusBadge value={value} variant="macro" />; }
function SectionHeader({ code, title, note, href, action }: { code: string; title: string; note: string; href?: string; action?: string }) {
  return <header className="macro-overview-section-header"><div><span>{code}</span><h2>{title}</h2>{note ? <p>{note}</p> : null}</div>{href ? <Link href={href}>{action || "Investigate →"}</Link> : null}</header>;
}
function CoverageFallback({ title, coverage, reason }: { title: string; coverage: MacroCoverageState; reason: string }) {
  return <div className="macro-coverage-fallback"><header><span>{title}</span><Status value={coverage.coverage_status} /></header><p>{reason}</p>{coverage.missing_fields.length ? <details><summary>View missing coverage · {coverage.missing_fields.length}</summary>{coverage.missing_fields.map((field) => <span key={field}>— {field}</span>)}</details> : null}<footer><span>{coverage.last_valid_as_of || "No last-valid date"}</span></footer></div>;
}
function metricDatum(metric: MacroTypedMetric, scaleGroup: string): QuantitativeDatum {
  return { id: metric.key, label: metric.label, value: metric.raw_value, unit: metric.unit, status: metric.confidence, context: `${metric.source} · ${metric.date || "period unavailable"}`, date: metric.date || undefined, scaleGroup };
}
function driverDatum(driver: MacroLiquidityDriver): QuantitativeDatum | null {
  if (!Number.isFinite(driver.contribution)) return null;
  return { id: driver.key, label: driver.label, value: driver.contribution, unit: "score contribution", status: driver.state, context: driver.explanation, date: driver.date || undefined, scaleGroup: "liquidity-contribution" };
}

export function MacroOverviewSurface({ system }: { system: ResearchSystem }) {
  const router = useRouter();
  const transmission = system.market_transmission;
  const [hoveredRegion, setHoveredRegion] = useState("");
  const [unavailable, setUnavailable] = useState("");
  const hover = system.world.regions[hoveredRegion];
  const curve = transmission.rates.current_curve.flatMap((metric) => {
    const tenor = metric.key === "us_2y" ? 2 : metric.key === "us_10y" ? 10 : metric.key === "us_30y" ? 30 : null;
    return tenor === null ? [] : [{ label: metric.label.replace("US ", ""), tenorYears: tenor, value: metric.raw_value }];
  });
  const fxMoves = transmission.fx.moves.map((metric) => metricDatum(metric, metric.unit));
  const liquidityMoves = transmission.liquidity.drivers.flatMap((driver) => { const datum = driverDatum(driver); return datum ? [datum] : []; });
  const coreReads = system.dashboard.reads.filter((read) => ["us-policy", "inflation", "liquidity", "risk"].includes(String(read.id)));

  return <div className="engine-module macro-overview-surface">
    <header className="engine-module-header object-page-header"><div><span>MACRO / GLOBAL STATE</span><h1>Macro overview</h1><p>Policy, inflation, rates, liquidity, FX and risk across the US, Japan, Korea, Singapore and the Euro Area.</p></div></header>

    <section className="macro-global-state"><div><span>GLOBAL MACRO STATE</span></div><h2>{system.dashboard.headline.state}</h2><p>{system.dashboard.headline.summary}</p></section>
    <section className="macro-state-strip">{coreReads.map((read) => <Link href={String(read.href || "/macro")} key={String(read.id)}><span>{read.label}</span><strong>{read.value}</strong><small>{read.state}</small></Link>)}</section>

    <section className="macro-overview-section macro-market-transmission" aria-label="Market Transmission">
      <SectionHeader code="MARKET TRANSMISSION" title="Rates, dollar, liquidity, and risk" note="" href="/macro/world?mode=transmission" action="Open transmission graph →" />
      <div className="macro-transmission-summary">
        <article className="macro-viz-card rates-card"><header><div><span>RATES / CURRENT CURVE</span><h3>US Treasury structure</h3></div><Status value={transmission.rates.coverage_status} /></header>{curve.length >= 2 ? <YieldCurveChart points={curve} asOf={transmission.rates.last_valid_as_of} source={transmission.rates.current_curve[0]?.source} /> : <CoverageFallback title="Rates" coverage={transmission.rates} reason="No verified multi-tenor curve is available." />}<div className="macro-compact-metrics">{transmission.rates.metrics.filter((metric) => !["us_2y", "us_10y", "us_30y"].includes(metric.key)).map((metric) => <div key={metric.key} title={`${metric.source} · ${metric.date || "date unavailable"}`}><span>{metric.label}</span><strong>{metric.formatted_value}</strong></div>)}</div><Link href="/macro/rates">Open rates coverage →</Link></article>
        <article className="macro-viz-card fx-card"><header><div><span>FX / COMPARABLE MOVES</span><h3>Regional dollar channels</h3></div><Status value={transmission.fx.coverage_status} /></header>{fxMoves.length ? <DivergingBarChart data={fxMoves} /> : <CoverageFallback title="Dollar / FX" coverage={transmission.fx} reason="No comparable verified FX changes are available." />}<Link href="/macro/fx">Open FX coverage →</Link></article>
        <article className="macro-viz-card liquidity-card"><header><div><span>LIQUIDITY / DRIVER CONTRIBUTION</span><h3>{transmission.liquidity.state} · {transmission.liquidity.score ?? "—"}/100</h3></div><Status value={transmission.liquidity.coverage_status} /></header><p>{transmission.liquidity.available_drivers}/{transmission.liquidity.expected_drivers} configured drivers available.</p>{liquidityMoves.length ? <DivergingBarChart data={liquidityMoves} /> : <CoverageFallback title="Liquidity" coverage={transmission.liquidity} reason="No verified liquidity-driver contributions are available." />}<Link href="/macro/liquidity">Open driver evidence →</Link></article>
        <article className="macro-viz-card risk-card"><header><div><span>RISK / PUBLICATION GATE</span><h3>{transmission.risk.state}</h3></div><Status value={transmission.risk.coverage_status} /></header><strong>{(transmission.risk.coverage * 100).toFixed(0)}% cross-asset coverage</strong><p>{transmission.risk.summary}</p><div className="macro-missing-list">{transmission.risk.missing_fields.slice(0, 5).map((field) => <span key={field}>— {field}</span>)}</div><Link href="/macro/risk">Open risk coverage →</Link></article>
      </div>
    </section>

    <section className="macro-overview-section macro-overview-world">
      <SectionHeader code="REGIONAL MACRO MAP" title="World research coverage" note="" href="/macro/world" action="Open full world workspace →" />
      <div className="macro-overview-map-wrap"><MacroWorldMap regions={system.world.regions} onSelect={(id) => router.push(`/macro/world?region=${id}`)} onUnavailable={(label) => setUnavailable(label)} onHover={(id) => { setHoveredRegion(id); setUnavailable(""); }} onHoverUnavailable={(label) => { setUnavailable(label); setHoveredRegion(""); }} onLeave={() => { setHoveredRegion(""); setUnavailable(""); }} />{hover ? <aside className="macro-map-tooltip" aria-live="polite"><header><strong>{hover.name.toUpperCase()}</strong><Status value={hover.availability} /></header><span>Research coverage</span>{hover.components.slice(0, 5).map((component) => <div key={component.id}><b>{component.label}</b><small>{component.confidence}</small></div>)}<p>{hover.brief}</p><Link href={`/macro/world?region=${hover.id}`}>Open {hover.name} →</Link></aside> : null}{unavailable ? <aside className="macro-map-tooltip unavailable"><header><strong>{unavailable.toUpperCase()}</strong><Status value="NOT AVAILABLE" /></header><p>No verified CHAINSTOX macro engine currently covers this economy.</p><button type="button" onClick={() => setUnavailable("")}>Dismiss</button></aside> : null}</div>
    </section>

    <section className="macro-overview-section macro-channel-overview">
      <SectionHeader code="CROSS-BORDER CHANNELS" title="Structural mechanisms and current state" note="Whether each channel is active now is shown separately from whether it exists." href="/macro/world?mode=transmission" action="Open mechanism network →" />
      <div>{system.world.transmissions.map((edge) => <Link href={`/macro/world?mode=transmission&edge=${edge.id}`} key={edge.id}><span>{edge.source} → {edge.target}</span><strong>{edge.label}</strong><small>Structural · {edge.structural_state}</small><Status value={edge.current_state} /><i>{edge.confidence}</i></Link>)}</div>
    </section>

    <details className="macro-overview-section macro-data-coverage">
      <summary>Data coverage · {transmission.coverage.missing_fields.length} fields unavailable</summary>
      <div>{[
        ["Rates", transmission.rates], ["FX", transmission.fx], ["Liquidity", transmission.liquidity], ["Risk", transmission.risk],
        ["US Inflation", { coverage_status: system.modules.inflation.state, source_state: system.modules.inflation.state, last_valid_as_of: system.modules.inflation.payload?.latest_source, missing_fields: [] }],
        ["Singapore NEER", { coverage_status: system.modules.neer.state, source_state: system.modules.neer.state, last_valid_as_of: system.world.regions.SG.as_of, missing_fields: [] }],
        ["South Korea KOSPI", { coverage_status: system.modules.kospi.state, source_state: system.modules.kospi.state, last_valid_as_of: system.world.regions.KR.as_of, missing_fields: [] }],
      ].map(([label, coverage]) => { const item = coverage as MacroCoverageState; return <article key={String(label)}><span>{String(label)}</span><Status value={item.coverage_status} /><small>{item.last_valid_as_of || "No verified date"}</small></article>; })}</div>
      <p>{transmission.coverage.reason}</p><div className="macro-coverage-columns"><section><strong>Available fields</strong>{transmission.coverage.available_fields?.map((field) => <span key={field}>— {field}</span>)}</section><section><strong>Unavailable fields</strong>{transmission.coverage.missing_fields.map((field) => <span key={field}>— {field}</span>)}</section></div>
    </details>
  </div>;
}

export function MacroTransmissionDetail({ section, system }: { section: "rates" | "fx" | "liquidity"; system: ResearchSystem }) {
  const transmission = system.market_transmission;
  const curve = transmission.rates.current_curve.flatMap((metric) => {
    const tenor = metric.key === "us_2y" ? 2 : metric.key === "us_10y" ? 10 : metric.key === "us_30y" ? 30 : null;
    return tenor === null ? [] : [{ label: metric.label.replace("US ", ""), tenorYears: tenor, value: metric.raw_value }];
  });
  const fx = transmission.fx.moves.map((metric) => metricDatum(metric, metric.unit));
  const liquidity = transmission.liquidity.drivers.flatMap((driver) => { const datum = driverDatum(driver); return datum ? [datum] : []; });
  const labels = { rates: "Rates", fx: "Dollar / FX", liquidity: "Liquidity" };
  const coverage = transmission[section];
  return <div className="engine-module macro-transmission-detail"><header className="engine-module-header object-page-header"><div><span>MACRO / MARKET TRANSMISSION</span><h1>{labels[section]}</h1></div></header>
    {section === "rates" ? <section className="macro-detail-visual"><SectionHeader code="RATES" title="Current Treasury curve" note="" />{curve.length >= 2 ? <YieldCurveChart points={curve} asOf={transmission.rates.last_valid_as_of} source={transmission.rates.current_curve[0]?.source} /> : <CoverageFallback title="Rates" coverage={transmission.rates} reason="No verified multi-tenor curve is available." />}<div className="macro-metric-ledger">{transmission.rates.metrics.map((metric) => <article key={metric.key} title={metric.source}><span>{metric.label}</span><strong>{metric.formatted_value}</strong><small>{metric.unit}</small><b>{metric.date || "date unavailable"}</b></article>)}</div></section> : null}
    {section === "fx" ? <section className="macro-detail-visual"><SectionHeader code="FX MARKET MOVES" title="Comparable regional currency changes" note="Year-over-year change against the US dollar." />{fx.length ? <DivergingBarChart data={fx} /> : <CoverageFallback title="FX" coverage={transmission.fx} reason="No comparable verified FX changes are available." />}</section> : null}
    {section === "liquidity" ? <section className="macro-detail-visual"><SectionHeader code="LIQUIDITY DRIVERS" title={`${transmission.liquidity.state} · ${transmission.liquidity.available_drivers}/${transmission.liquidity.expected_drivers} drivers`} note="Each driver's push on the Central Bank Compass liquidity score." />{liquidity.length ? <DivergingBarChart data={liquidity} /> : <CoverageFallback title="Liquidity" coverage={transmission.liquidity} reason="No verified liquidity contributions are available." />}<div className="macro-driver-ledger">{transmission.liquidity.drivers.map((driver) => <details key={driver.key}><summary><span>{driver.label}</span><Status value={driver.state} /><strong>{driver.contribution > 0 ? "+" : ""}{driver.contribution}</strong></summary><p>{driver.explanation}</p><small>{driver.source} · {driver.date || "date unavailable"}</small>{driver.thresholds.map((threshold) => <b key={threshold}>— {threshold}</b>)}</details>)}</div></section> : null}
    <CoverageFallback title={`${labels[section]} data coverage`} coverage={coverage} reason={transmission.coverage.reason || "Coverage is incomplete."} />
  </div>;
}
