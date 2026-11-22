"use client";
import { StatusBadge } from "../research/StatusBadge";

import { useState } from "react";
import { DivergingBarChart, RankedBarChart, TimeSeriesChart } from "../charts/AnalyticalCharts";
import { normalizeKospiFactors, normalizeKospiHistory, normalizeKospiVolatility } from "../../lib/research-visualization-adapter";
import type { QuantitativeDatum, RankedResearchItem } from "../../lib/visualization-types";

type Json = Record<string, unknown>;

function Status({ value }: { value: unknown }) { return <StatusBadge value={value ?? "UNAVAILABLE"} variant="macro" />; }
function show(value: unknown) { return value === null || value === undefined ? "Unavailable" : typeof value === "number" ? value.toFixed(3) : String(value); }

function SpecialModel({ payload }: { payload: Json }) {
  const special = payload.special as Json | undefined;
  if (!special) return null;
  const features = (special.features || []) as Json[];
  return <section className="macro-special-model"><header><div><span>SPECIALIZED POLICY MODEL</span><h4>{show(special.label)}</h4></div><Status value={special.state} /></header><dl><div><dt>Bias</dt><dd>{show(special.bias)}</dd></div><div><dt>Confidence</dt><dd>{show(special.confidence)}</dd></div><div><dt>Coverage</dt><dd>{typeof special.coverage === "object" ? Object.values(special.coverage as Json).join(" · ") : show(special.coverage)}</dd></div><div><dt>Quality</dt><dd>{show(special.quality)}</dd></div></dl>{features.length ? <div className="macro-special-features">{features.map((feature, index) => <article key={String(feature.key || feature.name || index)}><strong>{show(feature.name)}</strong><span>{show(feature.value)}</span><small>{show(feature.policy_effect || feature.pressure_effect)}</small><p>{show(feature.why || feature.trend)}</p></article>)}</div> : null}</section>;
}

function Compass({ payload }: { payload: Json }) {
  const blocks = (payload.blocks || {}) as Record<string, Json>;
  const liquidity = (payload.liquidity || {}) as Json;
  const [selectedBlock, setSelectedBlock] = useState(Object.keys(blocks)[0] || "");
  const blockItems: RankedResearchItem[] = Object.entries(blocks).sort(([, a], [, b]) => Number(b.score || 0) - Number(a.score || 0)).map(([key, block], index) => ({ id: key, rank: index + 1, label: key.toUpperCase(), group: "Policy pressure block", status: String(block.state), current: `${show(block.score)} / 100`, magnitude: Number(block.score || 0), unit: "score / 100", reason: String(block.policy_meaning || ""), threshold: String(block.coverage || "") }));
  const selected = blocks[selectedBlock];
  const liquidityData: QuantitativeDatum[] = ((liquidity.drivers || []) as Json[]).map((driver, index) => ({ id: `liquidity-${index}`, label: String(driver.name), value: Number(driver.score_effect || 0), unit: "score contribution", status: String(driver.classification), context: String(driver.explanation), scaleGroup: "liquidity-contribution" }));
  return <details className="macro-engine-detail"><summary><span>CENTRAL BANK COMPASS</span><strong>{show(payload.signal)} / {show(payload.bias)}</strong><i>+</i></summary><div className="macro-engine-body">
    <section className="macro-engine-kpis"><article><span>Policy score</span><strong>{show(payload.policy_score)}</strong></article><article><span>Model view</span><strong>{show(payload.model_view)}</strong></article><article><span>Confidence</span><strong>{show(payload.confidence)}</strong></article><article><span>Policy tool</span><strong>{show(payload.policy_tool)}</strong></article></section>
    <SpecialModel payload={payload} />
    <section className="macro-engine-visual"><header><span>Policy pressure comparison</span><small>Existing block scores / 100</small></header><RankedBarChart items={blockItems} onSelect={(item) => setSelectedBlock(item.id)} />{selected ? <div className="engine-evidence-drill"><header><strong>{selectedBlock.toUpperCase()} EVIDENCE</strong><Status value={selected.state} /></header>{((selected.evidence || []) as Json[]).map((evidence, index) => <article key={index}><span>{show(evidence.name)}</span><b>{show(evidence.value)}</b><small>{show(evidence.classification)} · {show(evidence.score_contribution)} pts</small><p>{show(evidence.explanation)}</p></article>)}</div> : null}</section>
    <section className="macro-engine-visual"><header><span>Liquidity driver contributions</span><small>{show(liquidity.score)} / 100 · {show(liquidity.classification)}</small></header><DivergingBarChart data={liquidityData} /></section>
    <section className="macro-engine-rules"><span>Decision rules</span>{((payload.decision_rules || []) as unknown[]).map((rule, index) => <p key={index}>— {show(rule)}</p>)}</section>
  </div></details>;
}

function Kospi({ payload }: { payload: Json }) {
  const sweep = (payload.sweep || {}) as Json;
  const interpretation = (sweep.interpretation || {}) as Json;
  const volatility = (sweep.volatility || {}) as Json;
  const exports = (payload.exports || {}) as Json;
  const factorData = normalizeKospiFactors(payload);
  const [factorKey, setFactorKey] = useState(factorData[0]?.id || "tech");
  const factorItems: RankedResearchItem[] = [...factorData].sort((a, b) => b.value - a.value).map((factor, index) => ({ id: factor.id, rank: index + 1, label: factor.label, group: "KOSPI factor study", status: factor.status || "UNAVAILABLE", current: `${factor.value.toFixed(3)} / 10`, magnitude: factor.value, unit: factor.unit, reason: factor.context, threshold: factor.confidence }));
  const factorHistory = normalizeKospiHistory(payload, factorKey);
  const exportItems: RankedResearchItem[] = [...((exports.items || []) as Json[])].sort((a, b) => Number(b.value_b || 0) - Number(a.value_b || 0)).map((item, index) => ({ id: String(item.key), rank: index + 1, label: String(item.label), group: String(item.period), status: "OBSERVED", current: `$${Number(item.value_b || 0).toFixed(2)}bn`, magnitude: Number(item.value_b || 0), unit: "USD bn", reason: `${item.note} Source: ${item.source}`, threshold: `${item.share_of_total_exports}% of total exports` }));
  const volatilityItems = normalizeKospiVolatility(payload);
  return <details className="macro-engine-detail" id="kospi-workspace"><summary><span>KOSPI RESEARCH ENGINE</span><strong>{show(((interpretation.regime || {}) as Json).name)}</strong><i>+</i></summary><div className="macro-engine-body">
    <section className="macro-engine-kpis"><article><span>Primary driver</span><strong>{show(interpretation.primary_driver)}</strong></article><article><span>Vol regime</span><strong>{show(volatility.regime)}</strong></article><article><span>GARCH daily</span><strong>{show(volatility.current_vol)}%</strong></article><article><span>Persistence</span><strong>{show(volatility.persistence)}</strong></article></section>
    <section className="macro-engine-visual"><header><span>Comparison / factor study scores</span><small>Descriptive relationships; click a factor to inspect observed history</small></header><RankedBarChart items={factorItems} onSelect={(item) => setFactorKey(item.id)} />{factorHistory ? <TimeSeriesChart series={factorHistory} maxPoints={120} /> : null}</section>
    <section className="macro-engine-visual"><header><span>Volatility / GARCH state</span><small>Current daily volatility compared with the engine&apos;s sample average</small></header><RankedBarChart items={volatilityItems} /></section>
    <section className="macro-engine-visual"><header><span>Comparison / export structure</span><small>Independent published or explicitly estimated category values</small></header><RankedBarChart items={exportItems} /></section>
    <section className="macro-engine-rules"><span>Interpretation</span>{((interpretation.sentences || []) as unknown[]).map((sentence, index) => <p key={index}>— {show(sentence)}</p>)}<p>Preserved analytical output is descriptive research only. Portfolio-positioning sentences from the legacy engine are intentionally not surfaced.</p></section>
  </div></details>;
}

export function MacroEngineDetails({ engineSpecific }: { engineSpecific: Record<string, unknown> }) {
  const compass = engineSpecific.central_bank_compass as Json | undefined;
  const kospi = engineSpecific.kospi_live as Json | undefined;
  if (!compass && !kospi) return null;
  return <section className="macro-specialist-engines"><header><span>Specialist engine output</span><small>Open verified detail</small></header>{compass ? <Compass payload={compass} /> : null}{kospi ? <Kospi payload={kospi} /> : null}</section>;
}
