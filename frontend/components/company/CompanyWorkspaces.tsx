"use client";

import { useEffect, useMemo, useState } from "react";
import type { CompanyResearchViewModel, EvidenceViewModel } from "../../lib/company-economics-types";
import { confidenceLabel, formatValue, humanize } from "../../lib/companyEconomicsAdapter";
import { EconomicMap, evidenceForEconomicNode } from "./EconomicMap";
import { OperationalResearch } from "./OperationalResearch";
import { ConfidenceLabel, EvidenceTypeBadge, Unavailable } from "./ResearchPrimitives";
import { InspectorRead, ResearchWorkspace, WorkspaceAction } from "../research/ResearchWorkspace";

export type CompanyWorkspaceKind = "economics" | "valuation" | "thesis" | "financials" | "evidence";
type GraphNode = CompanyResearchViewModel["raw"]["economic_graph"]["nodes"][number];

function useDepthEscape(onClose: () => void) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      onClose();
    };
    window.addEventListener("keydown", handler, true);
    return () => window.removeEventListener("keydown", handler, true);
  }, [onClose]);
}

function EvidenceList({ items, onSelect }: { items: EvidenceViewModel[]; onSelect: (item: EvidenceViewModel) => void }) {
  const uniqueItems = Array.from(new Map(items.map((item) => [item.id, item])).values());
  if (!uniqueItems.length) return <p className="workspace-empty">No connected evidence is available.</p>;
  return <div className="workspace-evidence-list">{uniqueItems.map((item) => <button key={item.id} type="button" onClick={() => onSelect(item)}><span>{item.id}</span><div><strong>{item.label}</strong><EvidenceTypeBadge type={item.typeLabel} /></div><b>{item.valueLabel}</b><i>→</i></button>)}</div>;
}

function evidenceByType(items: EvidenceViewModel[]) {
  return {
    direct: items.filter((item) => item.typeLabel === "Direct"),
    proxy: items.filter((item) => item.typeLabel === "Proxy"),
    inference: items.filter((item) => item.typeLabel === "Inference")
  };
}

function evidenceFromIds(company: CompanyResearchViewModel, ids: string[]) {
  return ids.map((id) => company.evidenceById[id]).filter(Boolean);
}

function relatedGaps(company: CompanyResearchViewModel, node: GraphNode) {
  const normalized = node.id.toLowerCase();
  return company.dataGaps.filter((gap) => [gap.related_driver, gap.related_constraint, gap.missing_field]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase() === normalized));
}

function NodeInspector({ company, node, onEvidence }: { company: CompanyResearchViewModel; node: GraphNode | null; onEvidence: (items: EvidenceViewModel[]) => void }) {
  if (!node) return <div className="inspector-empty"><span>SELECT NODE</span><h3>Investigate the economic system</h3><p>Select a driver, constraint, or financial outcome without leaving the map.</p></div>;
  const research = company.raw.operational_research;
  const operational = research?.series.find((series) => series.definition.id === node.id);
  if (research && operational) return <><OperationalResearch research={{ ...research, series: [operational] }} expanded /><WorkspaceAction onClick={() => onEvidence(evidenceForEconomicNode(node, company))}>Trace Evidence</WorkspaceAction></>;
  const evidence = evidenceForEconomicNode(node, company);
  const isConstraint = node.type === "constraint";
  const driver = company.growthDrivers.find((item) => item.primitive.toLowerCase() === node.id);
  const splitEvidence = evidenceByType(evidence);
  const contraryEvidence = isConstraint ? evidenceFromIds(company, company.primaryConstraint.contrary_evidence_ids) : [];
  const supportingEvidence = isConstraint ? evidenceFromIds(company, company.primaryConstraint.supporting_evidence_ids) : evidence;
  const inferenceEvidence = isConstraint ? evidenceFromIds(company, company.primaryConstraint.inference_evidence_ids) : splitEvidence.inference;
  const gaps = isConstraint ? company.primaryConstraint.data_gaps : relatedGaps(company, node);
  return <div className="node-inspector-content">
    <header><span>{humanize(node.type)} / {node.id}</span><h3>{node.label}</h3></header>
    {isConstraint ? <>
      <InspectorRead label="Economic mechanism"><p>{company.primaryConstraint.economic_mechanism}</p></InspectorRead>
      <div className="inspector-read-grid"><InspectorRead label="Binding status">{humanize(company.primaryConstraint.constraint_status || "EVIDENCE_INSUFFICIENT")}</InspectorRead><InspectorRead label="Directional status">{humanize(company.primaryConstraint.direction_status || company.primaryConstraint.direction)}</InspectorRead><InspectorRead label="Evidence basis">{company.primaryConstraint.basis}</InspectorRead></div>
      <InspectorRead label="Direct evidence">{evidenceByType(supportingEvidence).direct.length ? <EvidenceList items={evidenceByType(supportingEvidence).direct} onSelect={(item) => onEvidence([item])} /> : <p>No direct constraint evidence is exposed.</p>}</InspectorRead>
      <InspectorRead label="Proxy / inference evidence">{[...evidenceByType(supportingEvidence).proxy, ...inferenceEvidence].length ? <EvidenceList items={[...evidenceByType(supportingEvidence).proxy, ...inferenceEvidence]} onSelect={(item) => onEvidence([item])} /> : <p>No proxy or inference item is attached.</p>}</InspectorRead>
      <InspectorRead label="Counter evidence">{contraryEvidence.length ? <EvidenceList items={contraryEvidence} onSelect={(item) => onEvidence([item])} /> : <p>No contrary evidence recorded for this constraint.</p>}</InspectorRead>
      <InspectorRead label="Evidence limitations">{gaps.length ? gaps.map((gap) => <p key={gap.missing_field}>{humanize(gap.missing_field)}: {gap.why_it_matters}</p>) : <p>No constraint-specific limitation is recorded.</p>}</InspectorRead>
      <InspectorRead label="What would falsify this read">{company.raw.falsification_conditions.map((item) => <p key={item.condition}>{item.condition}</p>)}</InspectorRead>
      <InspectorRead label="Current inference"><p>{company.primaryConstraint.inference}</p></InspectorRead>
    </> : driver ? <>
      <div className="inspector-read-grid"><InspectorRead label="Direction">{evidence[0] ? humanize(evidence[0].direction) : "Unknown"}</InspectorRead><InspectorRead label="Contribution">Not directly isolated by current structured profile</InspectorRead><InspectorRead label="Confidence">{confidenceLabel(driver.confidence)}</InspectorRead></div>
      <InspectorRead label="Economic role"><p>{driver.importance === "PRIMARY" ? "Primary contributor" : "Secondary contributor"} within {company.growthEquation}.</p></InspectorRead>
      <InspectorRead label="Direct evidence">{splitEvidence.direct.length ? <EvidenceList items={splitEvidence.direct} onSelect={(item) => onEvidence([item])} /> : <p>No direct driver series is exposed.</p>}</InspectorRead>
      <InspectorRead label="Proxy / inference evidence">{[...splitEvidence.proxy, ...splitEvidence.inference].length ? <EvidenceList items={[...splitEvidence.proxy, ...splitEvidence.inference]} onSelect={(item) => onEvidence([item])} /> : <p>No proxy or inference item is attached.</p>}</InspectorRead>
      <InspectorRead label="Evidence limitations">{gaps.length ? gaps.map((gap) => <p key={gap.missing_field}>{humanize(gap.missing_field)}: {gap.why_it_matters}</p>) : <p>No driver-specific limitation is recorded.</p>}</InspectorRead>
    </> : <>
      <InspectorRead label="Economic role"><p>This node connects company economics to {humanize(node.type).toLowerCase()}.</p></InspectorRead>
      <InspectorRead label="Financial translation read">{evidence.length ? <p>{evidence.map((item) => item.statement).join(" ")}</p> : <p>Insufficient connected evidence.</p>}</InspectorRead>
      <InspectorRead label="Evidence nature">{evidence.length ? <p>{splitEvidence.direct.length} direct / {splitEvidence.proxy.length} proxy / {splitEvidence.inference.length} inference</p> : <p>No connected evidence classification.</p>}</InspectorRead>
    </>}
    <div className="inspector-evidence-preview"><span>CONNECTED EVIDENCE / {evidence.length}</span><EvidenceList items={evidence.slice(0, 4)} onSelect={(item) => onEvidence([item])} /></div>
    <WorkspaceAction onClick={() => onEvidence(evidence)}>Trace Evidence</WorkspaceAction>
  </div>;
}

function EvidenceWorkspace({ company, initialItems, onClose }: { company: CompanyResearchViewModel; initialItems?: EvidenceViewModel[]; onClose: () => void }) {
  const [filter, setFilter] = useState<"all" | "direct" | "proxy" | "inference" | "gaps">("all");
  const [selected, setSelected] = useState<EvidenceViewModel | null>(null);
  const [sourceOpen, setSourceOpen] = useState(false);
  const items = initialItems?.length ? initialItems : company.evidence;
  const filtered = useMemo(() => filter === "all" || filter === "gaps" ? items : items.filter((item) => item.typeLabel.toLowerCase() === filter), [filter, items]);
  return <>
    <ResearchWorkspace code="LEVEL 3 / EVIDENCE" title="Evidence Trace" ticker={company.ticker} depth={2} onClose={onClose} inspector={selected ? <EvidenceInspector item={selected} onSource={() => setSourceOpen(true)} /> : <div className="inspector-empty"><span>SELECT EVIDENCE</span><h3>Trace a metric</h3><p>Inspect classification, use, period, source nature, and confidence.</p></div>}>
      <div className="evidence-workspace-header"><div><strong>{items.length}</strong><span>Evidence items in current trace</span></div><nav>{(["all", "direct", "proxy", "inference", "gaps"] as const).map((key) => <button type="button" className={filter === key ? "active" : ""} key={key} onClick={() => setFilter(key)}>{key}</button>)}</nav></div>
      {filter === "gaps" ? <div className="workspace-gap-list">{company.dataGaps.map((gap) => <article key={`${gap.missing_field}-${gap.related_constraint}`}><span>DATA GAP</span><h3>{gap.label}</h3><p>{gap.why_it_matters}</p><small>{gap.confidence_impact}</small></article>)}</div> : <EvidenceList items={filtered} onSelect={(item) => { setSelected(item); setSourceOpen(false); }} />}
    </ResearchWorkspace>
    {selected && sourceOpen ? <SourceTrace item={selected} onClose={() => setSourceOpen(false)} /> : null}
  </>;
}

function EvidenceInspector({ item, onSource }: { item: EvidenceViewModel; onSource: () => void }) {
  return <div className="node-inspector-content evidence-inspector"><header><span>{item.id} / {item.typeLabel}</span><h3>{item.label}</h3><strong>{item.valueLabel}</strong></header><div className="inspector-read-grid"><InspectorRead label="Observation">{item.observation_date || item.period}</InspectorRead><InspectorRead label="Source status">{humanize(item.source_status || item.source_nature)}</InspectorRead><InspectorRead label="Freshness">{humanize(item.staleness_status || "UNKNOWN")}</InspectorRead></div><InspectorRead label="Supports">{item.usedIn.join(" · ")}</InspectorRead><InspectorRead label="Interpretation"><p>{item.statement}</p></InspectorRead>{item.limitation ? <InspectorRead label="Limitation"><p>{item.limitation}</p></InspectorRead> : null}<WorkspaceAction onClick={onSource}>View Source / Calculation</WorkspaceAction></div>;
}

function SourceTrace({ item, onClose }: { item: EvidenceViewModel; onClose: () => void }) {
  const calculated = ["CALCULATED", "DERIVED_PROXY"].includes(item.source_nature);
  useDepthEscape(onClose);
  return <ResearchWorkspace code="LEVEL 4 / PROVENANCE" title="Source & Calculation" depth={3} onClose={onClose}>
    {item.source_locator ? <div className="source-trace-sheet"><p>Source locator: {item.source_locator}</p><p>Extraction: {item.extraction_method} · Definition: {item.definition_version} · Revision: {item.revision_status}</p></div> : null}
    <div className="source-trace-sheet"><header><span>{item.id}</span><h3>{item.label}</h3><strong>{item.valueLabel}</strong></header><dl><div><dt>Source</dt><dd>{item.source || "Unavailable"}{item.source_url ? <> · <a href={item.source_url} target="_blank" rel="noreferrer">Open source</a></> : null}</dd></div><div><dt>Provider / source status</dt><dd>{humanize(item.provider_status || "UNKNOWN")} / {humanize(item.source_status || item.source_nature)}</dd></div><div><dt>Observed / retrieved</dt><dd>{item.observation_date || item.period} / {item.retrieved_at || "Not recorded"}</dd></div><div><dt>Fiscal period / filing</dt><dd>{item.fiscal_period_end || item.period} / {item.filing_date || "Not recorded"}</dd></div><div><dt>Unit / currency</dt><dd>{item.unit || "Unavailable"} / {item.currency || "Not applicable"}</dd></div><div><dt>Raw concept</dt><dd>{item.raw_concept || item.metric}</dd></div><div><dt>Normalized concept</dt><dd>{item.normalized_concept || item.metric}</dd></div><div><dt>Transformation</dt><dd>{item.transformation || "None recorded"}</dd></div><div><dt>Validation / freshness</dt><dd>{humanize(item.validation_status || "UNKNOWN")} / {humanize(item.staleness_status || "UNKNOWN")}</dd></div><div><dt>Evidence IDs</dt><dd>{[item.id, ...item.supporting_evidence_ids].join(", ")}</dd></div><div><dt>Conclusions using evidence</dt><dd>{item.usedIn.join(", ")}</dd></div></dl><section><span>{calculated ? "Calculation / Proxy Derivation" : "Reported Source"}</span><p>{calculated ? item.statement : "This item is treated as reported source evidence. CHAINSTOX does not derive or restate the value in this view."}</p>{item.limitation ? <small>Limitation: {item.limitation}</small> : null}{calculated && item.supporting_evidence_ids.length ? <small>Supporting inputs: {item.supporting_evidence_ids.join(", ")}</small> : null}{calculated && !item.supporting_evidence_ids.length ? <small>Raw calculation operands are not exposed separately by the current backend fixture.</small> : null}</section></div>
  </ResearchWorkspace>;
}

function ValuationWorkspace({ company, onClose, onEvidence }: { company: CompanyResearchViewModel; onClose: () => void; onEvidence: (items: EvidenceViewModel[]) => void }) {
  const [detail, setDetail] = useState<"reverse" | "assumptions" | "sensitivity" | null>(null);
  const market = company.raw.market_expectations_comparison;
  return <>
    <ResearchWorkspace code="LEVEL 1 / VALUATION" title="Valuation Workspace" ticker={company.ticker} onClose={onClose} inspector={<div className="valuation-workspace-read"><span>ECONOMIC READ</span><h3>{humanize(market.state)}</h3><p>{market.reason}</p><WorkspaceAction onClick={() => onEvidence(market.evidence_ids.map((id) => company.evidenceById[id]).filter(Boolean))}>Trace Valuation Evidence</WorkspaceAction></div>}>
      <div className="valuation-workspace-canvas">
        <section className="valuation-range-compact"><header><span>INTRINSIC RANGE</span><small>Scenario values unavailable in Company Economics fixture</small></header><div>{["Bear", "Base", "Bull", "Current Price"].map((label) => <div key={label}><span>{label}</span><Unavailable reason="Unavailable" /></div>)}</div></section>
        <section className="economics-dcf-bridge"><header><span>OBSERVED ECONOMICS</span><i>→</i><span>DCF ASSUMPTIONS</span></header>{company.raw.valuation_assumption_review.reviews.map((review) => { const observed = review.assumption === "revenue_growth" ? company.raw.growth_sustainability.current_revenue_growth : company.evidence.find((item) => item.metric === "fcf_margin")?.value; return <button type="button" key={review.assumption} onClick={() => setDetail("assumptions")}><div><small>Observed {humanize(review.assumption)}</small><strong>{formatValue(observed, "decimal")}</strong></div><i>→</i><div><small>{humanize(review.assumption)} assumption</small><strong>{formatValue(review.dcf_value, "decimal")}</strong></div><span>{humanize(review.state)}</span></button>; })}</section>
        <div className="valuation-workspace-actions"><WorkspaceAction onClick={() => setDetail("reverse")}>Open Reverse DCF</WorkspaceAction><WorkspaceAction onClick={() => setDetail("assumptions")} secondary>Open Assumptions</WorkspaceAction><WorkspaceAction onClick={() => setDetail("sensitivity")} secondary>Open Sensitivity</WorkspaceAction></div>
      </div>
    </ResearchWorkspace>
    {detail ? <ValuationDetail company={company} detail={detail} onClose={() => setDetail(null)} /> : null}
  </>;
}

function ValuationDetail({ company, detail, onClose }: { company: CompanyResearchViewModel; detail: "reverse" | "assumptions" | "sensitivity"; onClose: () => void }) {
  const market = company.raw.market_expectations_comparison;
  useDepthEscape(onClose);
  return <ResearchWorkspace code="LEVEL 2 / VALUATION TRACE" title={detail === "reverse" ? "Reverse DCF" : detail === "assumptions" ? "Assumption Trace" : "Sensitivity"} ticker={company.ticker} depth={2} onClose={onClose}>
    {detail === "reverse" ? <div className="valuation-detail-grid"><InspectorRead label="Current price"><Unavailable reason="Not exposed in fixture" /></InspectorRead><InspectorRead label="Market-implied 5Y growth">{formatValue(market.market_implied_revenue_cagr, "decimal")}</InspectorRead><InspectorRead label="Market-implied Year-5 FCFF margin">{formatValue(market.market_implied_fcff_margin, "decimal")}</InspectorRead><InspectorRead label="Solver status">{market.market_implied_revenue_cagr == null ? "NO ECONOMIC SOLUTION" : "CONVERGED"}</InspectorRead><InspectorRead label="Observed economics"><p>{market.observed_economics}</p></InspectorRead><InspectorRead label="Interpretation"><p>{market.reason}</p></InspectorRead></div> : detail === "assumptions" ? <div className="assumption-trace-list">{company.raw.valuation_assumption_review.reviews.map((review) => <article key={review.assumption}><span>{humanize(review.assumption)}</span><strong>{formatValue(review.dcf_value, "decimal")}</strong><dl><div><dt>Source</dt><dd>Intrinsic valuation base assumptions</dd></div><div><dt>Economic review</dt><dd>{humanize(review.state)}</dd></div><div><dt>Period</dt><dd>{review.assumption === "revenue_growth" ? "Forecast Year 1" : "Normalized Year 5"}</dd></div><div><dt>Mutates DCF input</dt><dd>{String(company.raw.valuation_assumption_review.mutates_dcf_inputs)}</dd></div></dl><p>{review.reason}</p></article>)}</div> : <div className="workspace-empty-state"><span>SENSITIVITY</span><h3>Data unavailable</h3><p>The Company Economics fixture does not expose valuation sensitivity matrices. No values have been manufactured.</p></div>}
  </ResearchWorkspace>;
}

function ThesisWorkspace({ company, onClose }: { company: CompanyResearchViewModel; onClose: () => void }) {
  const sustainability = company.raw.growth_sustainability;
  return <ResearchWorkspace code="LEVEL 1 / THESIS" title="Growth Sustainability" ticker={company.ticker} onClose={onClose}><div className="thesis-workspace"><header><span>CURRENT READ</span><h3>{company.raw.scaling_economics.interpretation}</h3><ConfidenceLabel value={sustainability.confidence} /></header><p>{sustainability.interpretation}</p><section><span>WHAT WOULD BREAK THIS VIEW?</span>{company.raw.falsification_conditions.map((item, index) => <article key={item.condition}><b>{String(index + 1).padStart(2, "0")}</b><div><strong>{item.condition}</strong><p>{item.rationale}</p></div></article>)}</section></div></ResearchWorkspace>;
}

function FinancialWorkspace({ company, onClose }: { company: CompanyResearchViewModel; onClose: () => void }) {
  return <ResearchWorkspace code="LEVEL 1 / FINANCIALS" title="Financial Translation" ticker={company.ticker} onClose={onClose}><div className="financial-workspace"><div className="financial-causal-chain">{["Economic Evidence", "Revenue Durability", "Margin Durability", "FCFF Conversion", "Valuation Assumptions"].map((item, index) => <div key={item}><span>{item}</span>{index < 4 ? <i>↓</i> : null}</div>)}</div><section>{Object.entries(company.raw.financial_translation).map(([key, item]) => <article key={key}><span>{humanize(key)}</span><strong>{humanize(item.state)}</strong><p>{item.reason}</p></article>)}</section></div></ResearchWorkspace>;
}

export function CompanyWorkspaces({ company, workspace, selectedNodeId, onNode, onClose, onEvidence }: { company: CompanyResearchViewModel; workspace: CompanyWorkspaceKind | null; selectedNodeId: string | null; onNode: (nodeId: string) => void; onClose: () => void; onEvidence: (items?: EvidenceViewModel[]) => void }) {
  const [evidenceItems, setEvidenceItems] = useState<EvidenceViewModel[] | undefined>();
  const selectedNode = company.raw.economic_graph.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const openEvidence = (items?: EvidenceViewModel[]) => { setEvidenceItems(items); onEvidence(items); };
  if (!workspace) return null;
  return <>
    {workspace === "economics" ? <ResearchWorkspace code="LEVEL 1 / COMPANY ECONOMICS" title="Economic Map" ticker={company.ticker} onClose={onClose} inspector={<NodeInspector company={company} node={selectedNode} onEvidence={openEvidence} />}><EconomicMap company={company} selectedNodeId={selectedNodeId} onSelectNode={(node) => onNode(node.id)} inlineInspector={false} /></ResearchWorkspace> : null}
    {workspace === "valuation" ? <ValuationWorkspace company={company} onClose={onClose} onEvidence={openEvidence} /> : null}
    {workspace === "thesis" ? <ThesisWorkspace company={company} onClose={onClose} /> : null}
    {workspace === "financials" ? <FinancialWorkspace company={company} onClose={onClose} /> : null}
    {workspace === "evidence" ? <EvidenceWorkspace company={company} initialItems={evidenceItems} onClose={onClose} /> : null}
  </>;
}
