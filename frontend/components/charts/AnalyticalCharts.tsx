"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { CoverageItem, HeatmapCell, QuantitativeDatum, RankedResearchItem, TimeSeriesDefinition, TransmissionEdge, TransmissionNode } from "../../lib/visualization-types";
import { coveragePercent, groupDivergingData, normalizeTimeSeriesPoints } from "../../lib/chart-normalization-core";

function stateClass(value: string) { return value.toLowerCase().replaceAll(" ", "-").replaceAll("/", "-").replaceAll("_", "-"); }
function exact(value: number, unit: string) { return `${value > 0 ? "+" : ""}${value.toFixed(Math.abs(value) < 1 ? 3 : 2)}${unit.startsWith("%") ? "%" : unit.startsWith("pp") ? " pp" : ""}`; }

export function RankedBarChart({ items, onSelect }: { items: RankedResearchItem[]; onSelect?: (item: RankedResearchItem) => void }) {
  const [selected, setSelected] = useState(items[0]?.id || "");
  const current = items.find((item) => item.id === selected);
  const max = Math.max(...items.map((item) => item.magnitude || 0), 0);
  return <div className="ranked-chart"><div className="ranked-chart-list">{items.map((item) => <button type="button" key={item.id} className={selected === item.id ? "selected" : ""} onClick={() => { setSelected(item.id); onSelect?.(item); }} aria-label={`Inspect priority ${item.rank}: ${item.label}`}><b>{String(item.rank).padStart(2, "0")}</b><span className={`ranked-track${item.magnitude === undefined ? " ordinal" : ""}`} aria-hidden="true"><i className={`state-${stateClass(item.status)}`} style={item.magnitude !== undefined && max > 0 ? { width: `${Math.max(2, item.magnitude / max * 100)}%` } : undefined} /></span><div><small>{item.group}</small><strong>{item.label}</strong></div><em>{item.current}</em><span className={`visual-state state-${stateClass(item.status)}`}>{item.status}</span></button>)}</div>{current ? <aside className="chart-drilldown" aria-live="polite"><header><span>RANK {String(current.rank).padStart(2, "0")}</span><b>{current.status}</b></header><h4>{current.group} / {current.label}</h4><dl><div><dt>Current</dt><dd>{current.current}</dd></div><div><dt>{current.magnitude === undefined ? "Trigger" : "Measure"}</dt><dd>{current.magnitude === undefined ? current.threshold : `${current.magnitude} ${current.unit || ""}`}</dd></div></dl><p>{current.reason}</p>{current.href ? <Link href={current.href}>Open underlying evidence →</Link> : null}</aside> : null}</div>;
}

export function DivergingBarChart({ data, onSelect }: { data: QuantitativeDatum[]; onSelect?: (item: QuantitativeDatum) => void }) {
  const [selected, setSelected] = useState(data[0]?.id || "");
  const groups = useMemo(() => groupDivergingData(data), [data]);
  const current = data.find((item) => item.id === selected);
  if (!data.length) return <ChartUnavailable label="No observed numeric moves" />;
  return <div className="diverging-chart"><div>{groups.map((group) => { const max = Math.max(...group.map((item) => Math.abs(item.value)), 0.0001); return <section key={group[0].scaleGroup || group[0].unit}><header><span>{group[0].unit}</span>{" "}<small>Independent zero-centred scale</small></header>{group.map((item) => { const width = Math.abs(item.value) / max * 48; return <button type="button" key={item.id} onClick={() => { setSelected(item.id); onSelect?.(item); }} className={selected === item.id ? "selected" : ""}><strong>{item.label}</strong><span className="diverging-axis" aria-hidden="true"><i className={item.value < 0 ? "negative" : "positive"} style={{ width: `${width}%`, left: item.value < 0 ? `${50 - width}%` : "50%" }} /><b /></span><em>{exact(item.value, item.unit)}</em></button>; })}</section>; })}</div>{current ? <aside className="chart-drilldown"><header><span>{current.date || "NO DATE"}</span><b>{current.status}</b></header><h4>{current.label}: {exact(current.value, current.unit)}</h4><p>{current.context}</p><small>{current.evidenceId ? `Evidence ${current.evidenceId}` : "Observed engine value"}</small></aside> : null}</div>;
}

function linePath(points: Array<{ x: number; y: number }>) { return points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" "); }

export function TimeSeriesChart({ series, maxPoints = 180 }: { series: TimeSeriesDefinition; maxPoints?: number }) {
  const valid = normalizeTimeSeriesPoints(series.points);
  if (!valid.length) return <ChartUnavailable label={`${series.label}: no historical observations`} />;
  const sampled = valid.length <= maxPoints ? valid : valid.filter((_, index) => index % Math.ceil(valid.length / maxPoints) === 0 || index === valid.length - 1);
  const values = sampled.flatMap((point) => [point.value, point.comparison]).filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  const low = Math.min(...values), high = Math.max(...values); const spread = high - low || Math.max(Math.abs(high), 1) * .05;
  const coords = sampled.map((point, index) => ({ x: sampled.length === 1 ? 50 : 4 + index / (sampled.length - 1) * 92, y: 92 - ((Number(point.value) - low) / spread) * 80 }));
  const comparison = sampled.flatMap((point, index) => point.comparison === null || point.comparison === undefined ? [] : [{ x: sampled.length === 1 ? 50 : 4 + index / (sampled.length - 1) * 92, y: 92 - ((point.comparison - low) / spread) * 80 }]);
  const latest = sampled.at(-1)!;
  return <figure className="time-series-chart"><figcaption><div><span>{series.label}</span><strong>{Number(latest.value).toFixed(3)} {series.unit}</strong></div><div><small>{sampled[0].date}</small><small>{latest.date}</small></div></figcaption><svg viewBox="0 0 100 100" role="img" aria-label={`${series.label} from ${sampled[0].date} to ${latest.date}`} preserveAspectRatio="none"><path className="chart-grid" d="M4 12H96M4 52H96M4 92H96" />{comparison.length ? <path className="comparison-line" d={linePath(comparison)} /> : null}<path className="primary-line" d={linePath(coords)} />{coords.length === 1 ? <circle className="single-point" cx={coords[0].x} cy={coords[0].y} r="2" /> : null}</svg><footer><span>LOW {low.toFixed(3)}</span><span className="line-key primary">Observed</span>{comparison.length ? <span className="line-key comparison">{series.comparisonLabel}</span> : null}<span>HIGH {high.toFixed(3)}</span></footer>{series.source ? <small className="chart-source">{series.source}</small> : null}</figure>;
}

export function ResearchHeatmap({ rows, columns, cells, onSelect }: { rows: string[]; columns: string[]; cells: HeatmapCell[]; onSelect?: (cell: HeatmapCell) => void }) {
  const [selected, setSelected] = useState(cells[0]?.id || "");
  const current = cells.find((cell) => cell.id === selected);
  function choose(cell: HeatmapCell) { setSelected(cell.id); onSelect?.(cell); }
  return <div className="research-heatmap"><div className="heatmap-grid" style={{ gridTemplateColumns: `minmax(118px, 1.2fr) repeat(${columns.length}, minmax(90px, 1fr))` }}><span className="heatmap-corner">ECONOMY / DIMENSION</span>{columns.map((column) => <b key={column}>{column}</b>)}{rows.flatMap((row) => [<strong key={`${row}-label`}>{row}</strong>, ...columns.map((column) => { const cell = cells.find((item) => item.row === row && item.column === column)!; return <button type="button" key={cell.id} className={`heatmap-cell state-${stateClass(cell.state)} ${selected === cell.id ? "selected" : ""}`} onClick={() => choose(cell)}><span>{cell.state}</span><small>{cell.confidence}</small></button>; })])}</div>{current ? <aside className="heatmap-inspector"><div><span>{current.row} / {current.column}</span><b>{current.confidence}</b></div><strong>{current.state}</strong><small>{current.coverage}</small>{current.href ? <Link href={current.href}>Inspect evidence →</Link> : null}</aside> : null}</div>;
}

export function CoverageChart({ items }: { items: CoverageItem[] }) {
  const [selected, setSelected] = useState(items[0]?.id || "");
  const current = items.find((item) => item.id === selected);
  return <div className="coverage-chart"><div>{items.map((item) => { const width = coveragePercent(item.available, item.total); const hasRatio = width !== null; return <button type="button" key={item.id} onClick={() => setSelected(item.id)} className={selected === item.id ? "selected" : ""}><header><strong>{item.label}</strong><span className={`visual-state state-${stateClass(item.state)}`}>{item.state}</span></header><div className={`coverage-track${hasRatio ? "" : " categorical"}`}><i style={hasRatio ? { width: `${width}%` } : undefined} /></div><footer><span>{hasRatio ? `${item.available}/${item.total}` : "Categorical state"}</span><small>{item.asOf || "No verified as-of date"}</small></footer></button>; })}</div>{current ? <aside className="chart-drilldown"><header><span>COVERAGE / {current.label}</span><b>{current.state}</b></header><p>{current.detail}</p><small>{current.asOf || "No verified as-of date"}</small></aside> : null}</div>;
}

export function YieldCurveChart({ points, asOf, source }: { points: Array<{ label: string; tenorYears: number; value: number }>; asOf?: string | null; source?: string }) {
  const valid = points.filter((point) => Number.isFinite(point.tenorYears) && Number.isFinite(point.value)).sort((a, b) => a.tenorYears - b.tenorYears);
  if (valid.length < 2) return <ChartUnavailable label="At least two verified Treasury tenors are required for a current curve." />;
  const values = valid.map((point) => point.value);
  const low = Math.min(...values), high = Math.max(...values), spread = high - low || .25;
  const minTenor = valid[0].tenorYears, maxTenor = valid.at(-1)!.tenorYears;
  const coords = valid.map((point) => ({
    ...point,
    x: maxTenor === minTenor ? 50 : 8 + (point.tenorYears - minTenor) / (maxTenor - minTenor) * 84,
    y: 48 - (point.value - low) / spread * 34,
  }));
  return <figure className="yield-curve-chart"><figcaption><div><span>Current Treasury curve</span><strong>{valid.map((point) => `${point.label} ${point.value.toFixed(2)}%`).join(" · ")}</strong></div><small>{asOf || "No verified as-of date"}</small></figcaption><svg viewBox="0 0 100 58" role="img" aria-label={`Treasury curve with ${valid.map((point) => point.label).join(", ")}`}><path className="chart-grid" d="M8 14H92M8 31H92M8 48H92" /><path className="primary-line" d={linePath(coords)} />{coords.map((point) => <g key={point.label}><circle cx={point.x} cy={point.y} r="1.3" /><text x={point.x} y="54">{point.label}</text><text className="curve-value" x={point.x} y={Math.max(7, point.y - 3)}>{point.value.toFixed(2)}%</text></g>)}</svg>{source ? <small className="chart-source">{source}</small> : null}</figure>;
}

export function TransmissionGraph({ nodes, edges, selected, onSelect }: { nodes: TransmissionNode[]; edges: TransmissionEdge[]; selected?: string; onSelect: (edge: TransmissionEdge) => void }) {
  const nodeMap = Object.fromEntries(nodes.map((node) => [node.id, node]));
  return <div className="transmission-graph"><svg viewBox="0 0 100 100" role="img" aria-label="Evidence-backed macro transmission graph"><defs><marker id="viz-arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto"><path d="M0 0L5 2.5L0 5z" /></marker></defs>{edges.map((edge) => { const from = nodeMap[edge.source], to = nodeMap[edge.target]; if (!from || !to) return null; return <g key={edge.id} role="button" tabIndex={0} aria-label={`${edge.source} to ${edge.target}: ${edge.label}`} onClick={() => onSelect(edge)} onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onSelect(edge)}><line className={`transmission-edge edge-${stateClass(edge.evidenceType)} ${selected === edge.id ? "selected" : ""}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} markerEnd="url(#viz-arrow)" /><text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 2}>{edge.evidenceType}</text></g>; })}{nodes.map((node) => <g className="transmission-viz-node" key={node.id}><circle cx={node.x} cy={node.y} r="5" /><text x={node.x} y={node.y + 1.2}>{node.label}</text></g>)}</svg><div className="transmission-legend"><span className="fact">FACT / SOLID</span><span className="proxy">PROXY / DASHED</span><span className="inference">INFERENCE / DOTTED</span></div></div>;
}

export function ChartUnavailable({ label }: { label: string }) { return <div className="chart-unavailable"><span>INSUFFICIENT EVIDENCE</span><p>{label}</p></div>; }
