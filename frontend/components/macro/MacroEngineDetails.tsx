"use client";
import { StatusBadge } from "../research/StatusBadge";

import { useState } from "react";
import { DivergingBarChart, RankedBarChart, TimeSeriesChart } from "../charts/AnalyticalCharts";
import { normalizeKospiFactors, normalizeKospiHistory, normalizeKospiVolatility, normalizeNeerContributions, normalizeNeerHistory } from "../../lib/research-visualization-adapter";
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

function Neer({ payload }: { payload: Json }) {
  const current = (payload.current || {}) as Json;
  const assumptions = (payload.policy_assumptions || {}) as Json;
  const history = normalizeNeerHistory(payload);
  const contributions = normalizeNeerContributions(payload);
  const components = (payload.fx_components || []) as Json[];
  const coverage = (payload.coverage || {}) as Json;
  const [currency, setCurrency] = useState(String(components[0]?.currency || ""));
  const selected = components.find((item) => item.currency === currency);
  return <details className="macro-engine-detail" id="neer-workspace"><summary><span>SHADOW S$NEER</span><strong>{show(current.band_state)}</strong><i>+</i></summary><div className="macro-engine-body">
    <section className="macro-engine-kpis"><article><span>Index</span><strong>{show(current.index)}</strong></article><article><span>Est. centre</span><strong>{show(current.estimated_center)}</strong></article><article><span>Deviation</span><strong>{show(current.deviation_pct)}%</strong></article><article><span>21D volatility</span><strong>{show(current.volatility_21d_ann_pct)}%</strong></article></section>
    <section className="macro-engine-visual"><header><span>Time / shadow proxy history</span><small>Observed proxy vs estimated centre</small></header><TimeSeriesChart series={history} /></section>
    <section className="macro-engine-visual"><header><span>Comparison / 63D basket contributions</span><small>Which FX components contribute most to current basket movement?</small></header><DivergingBarChart data={contributions} onSelect={(item) => setCurrency(item.id)} />{selected ? <aside className="neer-currency-inspector"><header><div><span>CURRENCY COMPONENT</span><h4>{show(selected.currency)}</h4></div><Status value={Number(selected.contribution_63d_pct || 0) >= 0 ? "POSITIVE" : "NEGATIVE"} /></header><dl><div><dt>Weight</dt><dd>{(Number(selected.weight || 0) * 100).toFixed(1)}%</dd></div><div><dt>Latest cross</dt><dd>{show(selected.latest_cross)}</dd></div><div><dt>21D move</dt><dd>{show(selected.change_21d_pct)}%</dd></div><div><dt>63D move</dt><dd>{show(selected.change_63d_pct)}%</dd></div><div><dt>63D contribution</dt><dd>{show(selected.contribution_63d_pct)}%</dd></div><div><dt>Filled gap</dt><dd>{show(selected.forward_filled_gap_pct)}%</dd></div></dl><p>Component-level historical arrays are not exposed by the normalized engine; the verified current windows and contribution are shown without synthesizing a line series.</p><small>{show(payload.source)} · {show(payload.as_of)}</small></aside> : null}<div className="neer-component-table-scroll"><div className="neer-component-table"><header><span>Currency</span><span>Weight</span><span>21D move</span><span>63D move</span><span>Contribution</span></header>{components.map((item) => <button type="button" key={String(item.currency)} onClick={() => setCurrency(String(item.currency))} className={currency === item.currency ? "selected" : ""}><strong>{show(item.currency)}</strong><span>{(Number(item.weight || 0) * 100).toFixed(1)}%</span><span>{show(item.change_21d_pct)}%</span><span>{show(item.change_63d_pct)}%</span><span>{show(item.contribution_63d_pct)}%</span></button>)}</div></div></section>
    <section className="macro-engine-rules"><span>Transparent proxy assumptions</span><p>Estimated band ±{show(assumptions.estimated_band_half_width_pct)}%; slope {show(assumptions.slope_before_pct_pa)}% before and {show(assumptions.slope_after_pct_pa)}% after {show(assumptions.policy_change)}. This is not the official MAS basket or band.</p>{Object.entries(coverage).map(([key, value]) => <p key={key}>— {key.replaceAll("_", " ")}: {show(value)}</p>)}{((payload.warnings || []) as unknown[]).map((warning, index) => <p key={index}>— {show(warning)}</p>)}<p>Source: {show(payload.source)} · As of {show(payload.as_of)}</p></section>
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
  const neer = engineSpecific.shadow_neer_live as Json | undefined;
  const kospi = engineSpecific.kospi_live as Json | undefined;
  if (!compass && !neer && !kospi) return null;
  return <section className="macro-specialist-engines"><header><span>Specialist engine output</span><small>Open verified detail</small></header>{compass ? <Compass payload={compass} /> : null}{neer ? <Neer payload={neer} /> : null}{kospi ? <Kospi payload={kospi} /> : null}</section>;
}
