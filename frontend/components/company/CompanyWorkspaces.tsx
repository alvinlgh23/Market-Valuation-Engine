"use client";

import { useEffect, useMemo, useState } from "react";
import type { CompanyResearchViewModel, EvidenceViewModel } from "../../lib/company-economics-types";
import { formatValue, freshnessLabel, humanize } from "../../lib/companyEconomicsAdapter";
import { loadCachedCompanyCard, loadCompanyCard } from "../../lib/company-card";
import { EngineChainView, FinancialStatements } from "./EngineTabs";
import { MarketView } from "./MarketView";
import type { Operating } from "./StoredProfileReads";
import { OperationalResearch } from "./OperationalResearch";
import type { Attribution, PriceReading } from "./PriceDrivers";
import { EvidenceTypeBadge, Unavailable } from "./ResearchPrimitives";
import { InspectorRead, ResearchWorkspace, WorkspaceAction } from "../research/ResearchWorkspace";

export type CompanyWorkspaceKind = "economics" | "valuation" | "thesis" | "financials" | "evidence";

type LiveCardSnapshot = {
  axes?: Record<string, { state?: string; confidence?: string; evidence?: string[]; detail?: Record<string, unknown> }>;
  attribution?: Attribution;
  price_reading?: PriceReading;
  operating?: Operating | null;
  next_catalysts?: { last_earnings?: string | null };
};

function useLiveCardSnapshot(ticker: string): LiveCardSnapshot | null {
  const [card, setCard] = useState<LiveCardSnapshot | null>(null);
  useEffect(() => {
    let active = true;
    loadCachedCompanyCard(ticker).then((res) => {
      if (active && res.card) setCard((prev) => prev ?? (res.card as unknown as LiveCardSnapshot));
    });
    loadCompanyCard(ticker).then((res) => {
      if (active && res.card) setCard(res.card as unknown as LiveCardSnapshot);
    });
    return () => { active = false; };
  }, [ticker]);
  return card;
}

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

function EvidenceList({ items, selectedId, onSelect }: { items: EvidenceViewModel[]; selectedId?: string | null; onSelect: (item: EvidenceViewModel) => void }) {
  const uniqueItems = Array.from(new Map(items.map((item) => [item.id, item])).values());
  if (!uniqueItems.length) return <p className="workspace-empty">No connected evidence is available.</p>;
  return (
    <div className="workspace-evidence-list">
      {uniqueItems.map((item) => (
        <button key={item.id} type="button" className={selectedId === item.id ? "selected" : ""} onClick={() => onSelect(item)}>
          <span>{item.id}</span>
          <div><strong>{item.label}</strong><EvidenceTypeBadge type={item.typeLabel} /></div>
          <b>{item.valueLabel}</b>
          <i>→</i>
        </button>
      ))}
    </div>
  );
}

function EvidenceWorkspace({ company, initialItems, onClose, onResetFilter, inline = false }: { company: CompanyResearchViewModel; initialItems?: EvidenceViewModel[]; onClose: () => void; onResetFilter?: () => void; inline?: boolean }) {
  const [filter, setFilter] = useState<"all" | "direct" | "proxy" | "inference" | "gaps">("all");
  const items = initialItems?.length ? initialItems : company.evidence;
  const filtered = useMemo(() => filter === "all" || filter === "gaps" ? items : items.filter((item) => item.typeLabel.toLowerCase() === filter), [filter, items]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sourceOpen, setSourceOpen] = useState(false);
  const selected = filtered.find((i) => i.id === selectedId) ?? filtered[0] ?? null;

  return <>
    <ResearchWorkspace
      code="EVIDENCE & PROVENANCE"
      title="Evidence Trace"
      ticker={company.ticker}
      depth={inline ? 1 : 2}
      inline={inline}
      onClose={onClose}
      inspector={selected ? <EvidenceInspector item={selected} onSource={() => setSourceOpen(true)} /> : <div className="inspector-empty"><span>SELECT EVIDENCE</span><h3>Trace a metric</h3><p>Inspect classification, use, period, source nature, and confidence.</p></div>}
    >
      <div className="evidence-workspace-header">
        <div>
          <strong>{items.length}</strong>
          <span>{initialItems?.length ? "Filtered node evidence items" : "Verified evidence items"}</span>
          {initialItems?.length && onResetFilter ? <button type="button" className="ev-reset-btn" onClick={onResetFilter}>Show all {company.evidence.length} items</button> : null}
        </div>
        <nav>{(["all", "direct", "proxy", "inference", "gaps"] as const).map((key) => <button type="button" className={filter === key ? "active" : ""} key={key} onClick={() => setFilter(key)}>{key}</button>)}</nav>
      </div>
      {company.raw.operational_research?.series.length && !initialItems?.length ? <details className="ev-operational"><summary>Company operating disclosures · source detail</summary><OperationalResearch research={company.raw.operational_research} /></details> : null}
      {filter === "gaps" ? <div className="workspace-gap-list">{company.dataGaps.map((gap) => <article key={`${gap.missing_field}-${gap.related_constraint}`}><span>DATA GAP</span><h3>{gap.label}</h3><p>{gap.why_it_matters}</p><small>{gap.confidence_impact}</small></article>)}</div> : <EvidenceList items={filtered} selectedId={selected?.id} onSelect={(item) => { setSelectedId(item.id); setSourceOpen(false); }} />}
    </ResearchWorkspace>
    {selected && sourceOpen ? <SourceTrace item={selected} asOf={company.asOf} onClose={() => setSourceOpen(false)} /> : null}
  </>;
}

function EvidenceInspector({ item, onSource }: { item: EvidenceViewModel; onSource: () => void }) {
  return <div className="node-inspector-content evidence-inspector"><header><span>{item.id} / {item.typeLabel}</span><h3>{item.label}</h3><strong>{item.valueLabel}</strong></header><div className="inspector-read-grid"><InspectorRead label="Observation">{item.observation_date || item.period}</InspectorRead><InspectorRead label="Source status">{humanize(item.source_status || item.source_nature)}</InspectorRead><InspectorRead label="Freshness">{humanize(item.staleness_status || "UNKNOWN")}</InspectorRead></div><InspectorRead label="Supports">{item.usedIn.join(" · ")}</InspectorRead><InspectorRead label="Interpretation"><p>{item.statement}</p></InspectorRead>{item.limitation ? <InspectorRead label="Limitation"><p>{item.limitation}</p></InspectorRead> : null}<WorkspaceAction onClick={onSource}>View Source / Calculation</WorkspaceAction></div>;
}

function SourceTrace({ item, asOf, onClose }: { item: EvidenceViewModel; asOf?: string | null; onClose: () => void }) {
  const calculated = ["CALCULATED", "DERIVED_PROXY"].includes(item.source_nature);
  useDepthEscape(onClose);
  return <ResearchWorkspace code="LEVEL 4 / PROVENANCE" title="Source & Calculation" depth={3} onClose={onClose}>
    {item.source_locator ? <div className="source-trace-sheet"><p>Source locator: {item.source_locator}</p><p>Extraction: {item.extraction_method} · Definition: {item.definition_version} · Revision: {item.revision_status}</p></div> : null}
    <div className="source-trace-sheet"><header><span>{item.id}</span><h3>{item.label}</h3><strong>{item.valueLabel}</strong></header><dl><div><dt>Source</dt><dd>{item.source || "Unavailable"}{item.source_url ? <> · <a href={item.source_url} target="_blank" rel="noreferrer">Open source</a></> : null}</dd></div><div><dt>Provider / source status</dt><dd>{humanize(item.provider_status || "UNKNOWN")} / {humanize(item.source_status || item.source_nature)}</dd></div><div><dt>Observed / retrieved</dt><dd>{item.observation_date || item.period} / {item.retrieved_at || "Not recorded"}</dd></div><div><dt>Fiscal period / filing</dt><dd>{item.fiscal_period_end || item.period} / {item.filing_date || "Not recorded"}</dd></div><div><dt>Unit / currency</dt><dd>{item.unit || "Unavailable"} / {item.currency || "Not applicable"}</dd></div><div><dt>Raw concept</dt><dd>{item.raw_concept || item.metric}</dd></div><div><dt>Normalized concept</dt><dd>{item.normalized_concept || item.metric}</dd></div><div><dt>Transformation</dt><dd>{item.transformation || "None recorded"}</dd></div><div><dt>Validation / freshness</dt><dd>{humanize(item.validation_status || "UNKNOWN")} / {freshnessLabel(item.staleness_status, asOf)}</dd></div><div><dt>Evidence IDs</dt><dd>{[item.id, ...item.supporting_evidence_ids].join(", ")}</dd></div><div><dt>Conclusions using evidence</dt><dd>{item.usedIn.join(", ")}</dd></div></dl><section><span>{calculated ? "Calculation / Proxy Derivation" : "Reported Source"}</span><p>{calculated ? item.statement : "This item is treated as reported source evidence. CHAINSTOX does not derive or restate the value in this view."}</p>{item.limitation ? <small>Limitation: {item.limitation}</small> : null}{calculated && item.supporting_evidence_ids.length ? <small>Supporting inputs: {item.supporting_evidence_ids.join(", ")}</small> : null}{calculated && !item.supporting_evidence_ids.length ? <small>Raw calculation operands are not exposed separately by the current backend fixture.</small> : null}</section></div>
  </ResearchWorkspace>;
}

function ValuationWorkspace({ company, onClose, onEvidence, inline = false }: { company: CompanyResearchViewModel; onClose: () => void; onEvidence: (items: EvidenceViewModel[]) => void; inline?: boolean }) {
  const [detail, setDetail] = useState<"reverse" | "assumptions" | "sensitivity" | null>(null);
  const market = company.raw.market_expectations_comparison;
  return <>
    <ResearchWorkspace code="LEVEL 1 / VALUATION" title="Valuation Workspace" ticker={company.ticker} inline={inline} onClose={onClose} inspector={<div className="valuation-workspace-read"><span>ECONOMIC READ</span><h3>{humanize(market.state)}</h3><p>{market.reason}</p><WorkspaceAction onClick={() => onEvidence(market.evidence_ids.map((id) => company.evidenceById[id]).filter(Boolean))}>Trace Valuation Evidence</WorkspaceAction></div>}>
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

function PositioningWorkspace({ company, onClose, inline = false }: { company: CompanyResearchViewModel; onClose: () => void; inline?: boolean }) {
  const liveCard = useLiveCardSnapshot(company.ticker);
  return (
    <ResearchWorkspace code="HOW THE MARKET TREATS THE STOCK" title="Market view" ticker={company.ticker} inline={inline} onClose={onClose}>
      <MarketView card={liveCard as unknown as Record<string, unknown> | null} />
    </ResearchWorkspace>
  );
}

function FinancialWorkspace({ company, onClose, inline = false }: { company: CompanyResearchViewModel; onClose: () => void; inline?: boolean }) {
  return (
    <ResearchWorkspace code="FINANCIAL STATEMENTS" title="Financials & Operating Signals" ticker={company.ticker} inline={inline} onClose={onClose}>
      <FinancialStatements ticker={company.ticker} />
    </ResearchWorkspace>
  );
}

export function CompanyWorkspaces({
  company,
  workspace,
  onClose,
  onEvidence,
  inline = false
}: {
  company: CompanyResearchViewModel;
  workspace: CompanyWorkspaceKind | null;
  selectedNodeId: string | null;
  onNode: (nodeId: string) => void;
  onClose: () => void;
  onEvidence: (items?: EvidenceViewModel[]) => void;
  inline?: boolean;
}) {
  const [evidenceItems, setEvidenceItems] = useState<EvidenceViewModel[] | undefined>();
  const openEvidence = (items?: EvidenceViewModel[]) => { setEvidenceItems(items); onEvidence(items); };
  if (!workspace) return null;
  return <>
    {workspace === "economics" ? (
      <ResearchWorkspace code="COMPANY ECONOMICS" title="Economic Map" ticker={company.ticker} inline={inline} onClose={onClose}>
        <EngineChainView ticker={company.ticker} />
      </ResearchWorkspace>
    ) : null}
    {workspace === "valuation" ? <ValuationWorkspace company={company} inline={inline} onClose={onClose} onEvidence={openEvidence} /> : null}
    {workspace === "thesis" ? <PositioningWorkspace company={company} inline={inline} onClose={onClose} /> : null}
    {workspace === "financials" ? <FinancialWorkspace company={company} inline={inline} onClose={onClose} /> : null}
    {workspace === "evidence" ? (
      <EvidenceWorkspace
        company={company}
        initialItems={evidenceItems}
        inline={inline}
        onResetFilter={() => setEvidenceItems(undefined)}
        onClose={onClose}
      />
    ) : null}
  </>;
}
