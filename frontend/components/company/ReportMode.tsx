"use client";

import { useEffect, useRef } from "react";
import type { CompanyResearchViewModel } from "../../lib/company-economics-types";
import { confidenceLabel, formatValue, freshnessLabel, humanize } from "../../lib/companyEconomicsAdapter";
import { EvidenceTypeBadge } from "./ResearchPrimitives";
import { OperationalResearch } from "./OperationalResearch";

function ReportSection({ number, title, children }: { number: number; title: string; children: React.ReactNode }) {
  return <section className="report-section"><header><span>{String(number).padStart(2, "0")}</span><h2>{title}</h2></header>{children}</section>;
}

export function ReportMode({ company, onClose }: { company: CompanyResearchViewModel; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  const sustainability = company.raw.growth_sustainability;
  const market = company.raw.market_expectations_comparison;
  return (
    <div className="report-mode" role="dialog" aria-modal="true" aria-label={`${company.ticker} full company economics report`}>
      <div className="report-toolbar">
        <div><strong>CHAINSTOX / RESEARCH REPORT</strong><span>{company.ticker} · {company.asOf} · schema {company.raw.company_economics_schema_version}</span></div>
        <div><button type="button" onClick={() => window.print()}>Print</button><button ref={closeRef} type="button" onClick={onClose}>Close ×</button></div>
      </div>
      <article className="report-document">
        <header className="report-cover">
          <span>Company Economics Intelligence Report</span>
          <h1>{company.name}</h1>
          <p>{company.ticker} / {company.archetype}</p>
          <dl><div><dt>As of</dt><dd>{company.asOf}</dd></div><div><dt>Analysis confidence</dt><dd>{company.confidence}</dd></div><div><dt>Validation</dt><dd>{humanize(company.raw.validation.status)}</dd></div></dl>
          <blockquote>{company.coreQuestion}</blockquote>
        </header>
        <ReportSection number={1} title="Business Model Architecture"><p className="report-equation">{company.growthEquation}</p><div className="report-chain">{company.growthPath.join(" → ")}</div></ReportSection>
        <ReportSection number={2} title="Growth Engine">{company.growthDrivers.map((driver) => <div className="report-row" key={driver.primitive}><strong>{driver.label}</strong><span>{driver.evidence.length ? driver.evidence.map((item) => `${item.label}: ${item.valueLabel}`).join(" · ") : "Not directly observable"}</span></div>)}</ReportSection>
        <ReportSection number={3} title="Primary Scaling Constraint"><h3>{company.primaryConstraint.label}</h3><p>{company.primaryConstraint.economic_mechanism}</p><dl className="report-dl"><div><dt>Binding status</dt><dd>{humanize(company.primaryConstraint.constraint_status || "EVIDENCE_INSUFFICIENT")}</dd></div><div><dt>Directional status</dt><dd>{humanize(company.primaryConstraint.direction_status || company.primaryConstraint.direction)}</dd></div><div><dt>Basis</dt><dd>{company.primaryConstraint.basis}</dd></div></dl></ReportSection>
        <ReportSection number={4} title="Constraint Evidence">{company.primaryConstraint.evidence.map((item) => <div className="report-row" key={item.id}><span>{item.id} / {item.label}</span><strong>{item.valueLabel}</strong><EvidenceTypeBadge type={item.typeLabel} /></div>)}</ReportSection>
        <ReportSection number={5} title="Bottleneck Direction"><p>{company.primaryConstraint.inference}</p>{company.primaryConstraint.data_gaps.map((gap) => <p key={gap.missing_field}>Limitation — {humanize(gap.missing_field)} unavailable. {gap.confidence_impact}</p>)}</ReportSection>
        <ReportSection number={6} title="Secondary Constraints">{company.secondaryConstraints.map((item) => <div className="report-row" key={item.constraint}><strong>{item.label}</strong><span>{humanize(item.constraint_status || "EVIDENCE_INSUFFICIENT")} / {humanize(item.direction_status || item.direction)}</span></div>)}{company.raw.constraints.candidate_assessments?.map((item) => <div className="report-row report-row-copy" key={`candidate-${item.constraint}`}><strong>{humanize(item.constraint)} / structural candidate</strong><p>{item.inference}</p></div>)}</ReportSection>
        <ReportSection number={7} title="Scaling Economics">{company.scalingMetrics.map((metric) => <div className="report-metric" key={metric.name}><span>{metric.label}</span><strong>{metric.valueLabel}</strong><p>{metric.interpretation}</p></div>)}</ReportSection>
        <ReportSection number={8} title="Growth Sustainability"><h3>{company.raw.scaling_economics.interpretation}</h3><p>{sustainability.interpretation}</p><p>Confidence: {confidenceLabel(sustainability.confidence)}</p></ReportSection>
        <ReportSection number={9} title="What Would Break the Thesis"><ol>{company.raw.falsification_conditions.map((item) => <li key={item.condition}><strong>{item.condition}</strong><p>{item.rationale}</p></li>)}</ol></ReportSection>
        <ReportSection number={10} title="Financial Translation">{Object.entries(company.raw.financial_translation).map(([key, item]) => <div className="report-row report-row-copy" key={key}><strong>{humanize(key)} / {humanize(item.state)}</strong><p>{item.reason}</p></div>)}</ReportSection>
        <ReportSection number={11} title="Valuation Connection">{company.raw.valuation_assumption_review.reviews.map((review) => <div className="report-row report-row-copy" key={review.assumption}><strong>{humanize(review.assumption)} / {formatValue(review.dcf_value, "decimal")} / {humanize(review.state)}</strong><p>{review.reason}</p></div>)}<p className="report-note">Company Economics does not directly set fair value or mutate DCF inputs.</p></ReportSection>
        <ReportSection number={12} title="Market Expectations"><dl className="report-dl"><div><dt>5Y revenue CAGR</dt><dd>{formatValue(market.market_implied_revenue_cagr, "decimal")}</dd></div><div><dt>Year-5 FCFF margin</dt><dd>{formatValue(market.market_implied_fcff_margin, "decimal")}</dd></div><div><dt>Comparison</dt><dd>{humanize(market.state)}</dd></div></dl><p>{market.reason}</p></ReportSection>
        <ReportSection number={13} title="Data Gaps">{company.dataGaps.length ? company.dataGaps.map((gap) => <div className="report-row report-row-copy" key={`${gap.missing_field}-${gap.related_constraint}`}><strong>{gap.label} — Unavailable</strong><p>{gap.why_it_matters} {gap.confidence_impact}</p></div>) : <p>No material structured-data gaps identified.</p>}</ReportSection>
        <ReportSection number={14} title="Final Interpretation"><p>{sustainability.interpretation}</p><p>{market.observed_economics}</p></ReportSection>
        <ReportSection number={15} title="Evidence Trace">{company.evidence.map((item) => <article className="report-evidence" key={item.id}><header><strong>{item.id} / {item.label}</strong><span>{item.valueLabel}</span></header><p>{item.statement}</p><dl><div><dt>Claim class</dt><dd>{item.typeLabel}</dd></div><div><dt>Source status</dt><dd>{humanize(item.source_status || item.source_nature)}</dd></div><div><dt>Observation / freshness</dt><dd>{item.observation_date || item.period} / {freshnessLabel(item.staleness_status, company.asOf)}</dd></div><div><dt>Source</dt><dd>{item.source || "Unavailable"}</dd></div><div><dt>Used in</dt><dd>{item.usedIn.join(", ")}</dd></div><div><dt>Limitation</dt><dd>{item.limitation || "No specific limitation recorded."}</dd></div></dl></article>)}</ReportSection>
        <OperationalResearch research={company.raw.operational_research} expanded />
      </article>
    </div>
  );
}
