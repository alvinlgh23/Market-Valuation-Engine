"use client";

import { useEffect, useRef, useState } from "react";
import type { CompanyResearchViewModel, EvidenceViewModel } from "../../lib/company-economics-types";
import { humanize } from "../../lib/companyEconomicsAdapter";
import { ConfidenceLabel, DirectionLabel, EvidenceTypeBadge, ResearchLabel, Unavailable } from "./ResearchPrimitives";

type GraphNode = CompanyResearchViewModel["raw"]["economic_graph"]["nodes"][number];
type GraphEdge = CompanyResearchViewModel["raw"]["economic_graph"]["edges"][number];

const OUTCOME_TYPES = ["revenue", "margin", "cash_flow", "valuation"];

function archetypeMapClass(archetype: string): string {
  if (archetype === "BANK") return "economic-map-bank";
  if (archetype.includes("SEMICONDUCTOR")) return "economic-map-semi";
  if (archetype === "HYPERSCALER_CLOUD_PLATFORM") return "economic-map-hybrid";
  if (archetype === "RETAIL_PHYSICAL_NETWORK") return "economic-map-retail";
  return "economic-map-software";
}

function archetypeShapeLabel(archetype: string): string {
  if (archetype === "BANK") return "Balance sheet transmission";
  if (archetype === "SEMICONDUCTOR_FOUNDRY") return "Capacity and node-mix flywheel";
  if (archetype === "FABLESS_SEMICONDUCTOR") return "Demand, ASP, and supply bottleneck";
  if (archetype === "HYPERSCALER_CLOUD_PLATFORM") return "Workload and compute platform";
  if (archetype === "RETAIL_PHYSICAL_NETWORK") return "Store network and membership loop";
  return "Deployment-led software economics";
}

function sortOutcomes(nodes: GraphNode[]) {
  return nodes.sort((left, right) => OUTCOME_TYPES.indexOf(left.type) - OUTCOME_TYPES.indexOf(right.type));
}

function relationshipSummary(node: GraphNode, edges: GraphEdge[]) {
  const relationships = edges
    .filter((edge) => edge.from === node.id || edge.to === node.id)
    .map((edge) => humanize(edge.relationship));
  return Array.from(new Set(relationships)).join(" · ");
}

export function evidenceForEconomicNode(node: GraphNode, company: CompanyResearchViewModel): EvidenceViewModel[] {
  if (company.raw.operational_research?.series.some((series) => series.definition.id === node.id)) return company.evidence.filter((item) => item.metric === node.id);
  if (node.type === "constraint") return company.primaryConstraint.evidence;
  if (node.type === "growth_driver") {
    const driver = company.growthDrivers.find((item) => item.primitive.toLowerCase() === node.id || item.label.toLowerCase() === node.label.toLowerCase());
    return driver?.evidence ?? [];
  }
  const normalized = node.id === "cash_flow" ? "fcf" : node.id;
  return company.evidence.filter((item) => item.metric.includes(normalized)).slice(0, 5);
}

function EconomicNodeDrawer({ node, company, onClose }: { node: GraphNode; company: CompanyResearchViewModel; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const evidence = evidenceForEconomicNode(node, company);
  const isConstraint = node.type === "constraint";
  useEffect(() => {
    closeRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  return (
    <div className="node-drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="node-drawer" role="dialog" aria-modal="true" aria-labelledby="node-drawer-title">
        <button ref={closeRef} className="drawer-close" type="button" onClick={onClose} aria-label="Close economic node details">Close <span aria-hidden="true">×</span></button>
        <div className="node-system-id">CHAINSTOX://NODE</div>
        <ResearchLabel>{humanize(node.type)}</ResearchLabel>
        <h3 id="node-drawer-title">{node.label}</h3>
        {isConstraint ? (
          <div className="drawer-status-grid">
            <div><ResearchLabel>Role</ResearchLabel><p>Primary Scaling Constraint</p></div>
            <div><ResearchLabel>Current Direction</ResearchLabel><p><DirectionLabel value={company.primaryConstraint.direction} /></p></div>
            <div><ResearchLabel>Evidence Basis</ResearchLabel><p>{company.primaryConstraint.basis}</p></div>
            <div><ResearchLabel>Confidence</ResearchLabel><p><ConfidenceLabel value={company.primaryConstraint.confidence} /></p></div>
          </div>
        ) : null}
        <div className="drawer-copy">
          <ResearchLabel>Why it matters</ResearchLabel>
          <p>{isConstraint ? company.primaryConstraint.economic_mechanism : `This node sits in a structural pathway from ${company.growthEquation.toLowerCase()} to valuation assumptions; the map does not establish causality.`}</p>
        </div>
        <div className="drawer-evidence">
          <ResearchLabel>Connected evidence</ResearchLabel>
          {evidence.length ? evidence.map((item) => (
            <div className="drawer-evidence-row" key={item.id}>
              <div><span>{item.label}</span><EvidenceTypeBadge type={item.typeLabel} /></div>
              <strong>{item.valueLabel}</strong>
            </div>
          )) : <Unavailable reason="No directly connected evidence" />}
        </div>
      </aside>
    </div>
  );
}

export function EconomicMap({ company, compact = false, selectedNodeId, onSelectNode, inlineInspector = true }: { company: CompanyResearchViewModel; compact?: boolean; selectedNodeId?: string | null; onSelectNode?: (node: GraphNode) => void; inlineInspector?: boolean }) {
  const [internalSelected, setInternalSelected] = useState<GraphNode | null>(null);
  const { nodes, edges } = company.raw.economic_graph;
  const selected = selectedNodeId ? nodes.find((node) => node.id === selectedNodeId) ?? null : internalSelected;
  const primaryArchetype = company.raw.classification.primary_archetype;
  const growthNodes = nodes.filter((node) => node.type === "growth_driver");
  const constraintNodes = nodes.filter((node) => node.type === "constraint");
  const outcomeNodes = sortOutcomes(nodes.filter((node) => OUTCOME_TYPES.includes(node.type)));
  const selectNode = (node: GraphNode) => onSelectNode ? onSelectNode(node) : setInternalSelected(node);
  const renderNode = (node: GraphNode, zone: string) => (
    <button key={node.id} type="button" className={`economic-node node-${node.type}${selected?.id === node.id ? " economic-node-selected" : ""}`} onClick={() => selectNode(node)} aria-label={`Open details for ${node.label}`} aria-pressed={selected?.id === node.id}>
      <span>{node.label}</span>
      <small>{relationshipSummary(node, edges) || zone}</small>
    </button>
  );
  return (
    <div className={`economic-map ${archetypeMapClass(primaryArchetype)}${compact ? " economic-map-compact" : ""}`}>
      <header className="instrument-panel-header economic-map-header"><div><strong>CHAINSTOX://ECONOMIC SCHEMATIC</strong><span>Interactive causal architecture</span></div><span>{company.ticker} / SELECT NODE</span></header>
      <div className="economic-map-legend" aria-label="Economic map legend">
        <span><i className="legend-driver" /> Growth driver</span>
        <span><i className="legend-constraint" /> Constraint</span>
        <span><i className="legend-outcome" /> Financial outcome</span>
      </div>
      <div className="economic-map-grid" role="group" aria-label={`${company.ticker} economic causal map`}>
        <section className="economic-map-archetype-strip" aria-label={`${company.ticker} archetype structure`}>
          <div><span>ARCHETYPE</span><strong>{company.archetype}</strong><small>{archetypeShapeLabel(primaryArchetype)}</small></div>
          <ol>{company.growthPath.slice(0, 5).map((step) => <li key={step}>{step}</li>)}</ol>
        </section>
        <section className="economic-map-schematic" aria-label="Company economics schematic">
          <div className="economic-map-zone economic-map-inputs">
            <span className="economic-map-zone-label">Growth Inputs</span>
            <div className="economic-map-node-group">{growthNodes.map((node) => renderNode(node, "Growth input"))}</div>
          </div>
          <div className="economic-map-merge" aria-hidden="true"><span>→</span></div>
          <div className="economic-map-zone economic-map-constraint-rail">
            <span className="economic-map-zone-label">Scaling Constraint</span>
            <div className="economic-map-node-group">{constraintNodes.map((node) => renderNode(node, "Scaling bottleneck"))}</div>
          </div>
          <div className="economic-map-merge economic-map-merge-outcome" aria-hidden="true"><span>→</span></div>
          <div className="economic-map-zone economic-map-outcomes">
            <span className="economic-map-zone-label">Financial Translation</span>
            <div className="economic-map-node-group">{outcomeNodes.map((node) => renderNode(node, "Financial outcome"))}</div>
          </div>
        </section>
        <section className="economic-map-edge-ledger" aria-label="Causal relationships">
          {edges.map((edge) => {
            const from = nodes.find((node) => node.id === edge.from);
            const to = nodes.find((node) => node.id === edge.to);
            return <span key={`${edge.from}-${edge.to}-${edge.relationship}`}>{from?.label ?? edge.from}<i>{humanize(edge.relationship)}</i>{to?.label ?? edge.to}</span>;
          })}
        </section>
      </div>
      {inlineInspector && selected ? <EconomicNodeDrawer node={selected} company={company} onClose={() => setInternalSelected(null)} /> : null}
    </div>
  );
}
