"use client";

import { useMemo, useState } from "react";
import type { CompanyResearchViewModel, EvidenceViewModel, RawConstraint } from "../../lib/company-economics-types";
import { confidenceLabel, formatValue, humanize } from "../../lib/companyEconomicsAdapter";
import { EconomicMap } from "./EconomicMap";
import {
  ConfidenceLabel,
  DirectionLabel,
  EvidenceTypeBadge,
  InlineMetric,
  ResearchLabel,
  SectionHeading,
  Unavailable,
  WhyItMatters
} from "./ResearchPrimitives";

function EvidenceRows({ items, empty = "No evidence observed in the current structured feed." }: { items: EvidenceViewModel[]; empty?: string }) {
  if (!items.length) return <p className="empty-research-state">{empty}</p>;
  return (
    <div className="evidence-rows">
      {items.map((item) => (
        <div className="evidence-row" key={item.id}>
          <div>
            <span className="evidence-id">{item.id}</span>
            <strong>{item.label}</strong>
            <EvidenceTypeBadge type={item.typeLabel} />
          </div>
          <span className="evidence-value">{item.valueLabel}</span>
        </div>
      ))}
    </div>
  );
}

export function OverviewHero({ company, onOpenReport }: { company: CompanyResearchViewModel; onOpenReport: () => void }) {
  const directConstraintEvidence = company.primaryConstraint.evidence.filter((item) => item.typeLabel === "Direct");
  const interpretation = company.raw.growth_sustainability.interpretation;
  return (
    <section className="company-hero" id="overview">
      <div className="instrument-panel economic-profile-panel">
        <header className="instrument-panel-header"><div><strong>CHAINSTOX://ECONOMIC PROFILE</strong><span>Company growth and constraint architecture</span></div><span>{company.ticker} / ACTIVE</span></header>
        <div className="economic-profile-grid">
          <div className="hero-growth">
            <ResearchLabel>Growth architecture</ResearchLabel>
            <div className="hero-equation">{company.growthEquation.replace(/^Revenue\s*≈\s*/, "")}</div>
            <div className="hero-causal-chain" aria-label="Company growth chain">
              {company.growthPath.map((step, index) => (
                <span key={`${step}-${index}`}>
                  <strong>{step}</strong>
                  {index < company.growthPath.length - 1 ? <i>↓</i> : null}
                </span>
              ))}
            </div>
          </div>
          <div className="hero-constraint">
            <ResearchLabel>Primary constraint</ResearchLabel>
            <h2>{company.primaryConstraint.label}</h2>
            <div className="hero-status-list">
              <InlineMetric label="State" value={<DirectionLabel value={company.primaryConstraint.direction} />} />
              <InlineMetric label="Evidence" value={company.primaryConstraint.basis} />
              <InlineMetric label="Confidence" value={<ConfidenceLabel value={company.primaryConstraint.confidence} />} detail={!directConstraintEvidence.length ? "Direct constraint KPIs are unavailable." : undefined} />
            </div>
          </div>
        </div>
      </div>
      <div className="hero-interpretation">
        <ResearchLabel>Current interpretation</ResearchLabel>
        <p>{interpretation}</p>
        <div className="hero-actions">
          <a className="research-button" href="#economics">Open Economic Map</a>
          <button className="research-button research-button-secondary" type="button" onClick={onOpenReport}>View Report</button>
        </div>
      </div>
    </section>
  );
}

export function EconomicMapSection({ company }: { company: CompanyResearchViewModel }) {
  return (
    <section className="research-section" aria-labelledby="economic-map-title">
      <SectionHeading number="01" title="Economic Map" eyebrow="Causal Architecture" id="economics" />
      <p className="section-intro" id="economic-map-title">Select a node to inspect its role, evidence basis, and connection to the research thesis.</p>
      <EconomicMap company={company} />
    </section>
  );
}

export function GrowthEngineSection({ company }: { company: CompanyResearchViewModel }) {
  return (
    <section className="research-section" id="growth-engine">
      <SectionHeading number="02" title="Growth Engine" eyebrow="Business Equation" />
      <div className="growth-equation">{company.growthEquation}</div>
      <div className="structured-list">
        <div className="research-table-head"><span>Driver</span><span>Observation</span><span>Read</span></div>
        {company.growthDrivers.map((driver) => (
          <div className="growth-driver-row" key={driver.primitive}>
            <div><ResearchLabel>{driver.importance} driver</ResearchLabel><h3>{driver.label}</h3></div>
            <div className="driver-observation">
              {driver.evidence.length ? (
                <><strong>{driver.evidence.map((item) => item.valueLabel).join(" · ")}</strong><small>{driver.evidence.map((item) => item.label).join(" · ")}</small></>
              ) : <Unavailable reason="Direct series unavailable" />}
            </div>
            <div><ResearchLabel>Contribution</ResearchLabel><span>{driver.evidence.length ? "Observable, not isolated" : "Not directly observable"}</span></div>
          </div>
        ))}
      </div>
      <WhyItMatters>The revenue structure is observable; individual contribution is shown only where the backend provides evidence.</WhyItMatters>
    </section>
  );
}

function CompactConstraint({ constraint }: { constraint: RawConstraint & { label: string; evidence: EvidenceViewModel[]; basis: string; directionLabel: string } }) {
  return (
    <details className="secondary-constraint">
      <summary>
        <span><strong>{constraint.label}</strong><small>{constraint.directionLabel} · {confidenceLabel(constraint.confidence)} confidence</small></span>
        <span aria-hidden="true">Expand +</span>
      </summary>
      <div className="secondary-constraint-body">
        <p>{constraint.economic_mechanism}</p>
        <EvidenceRows items={constraint.evidence} />
      </div>
    </details>
  );
}

export function ConstraintsSection({ company }: { company: CompanyResearchViewModel }) {
  const constraint = company.primaryConstraint;
  const direct = constraint.evidence.filter((item) => item.typeLabel === "Direct");
  const indirect = constraint.evidence.filter((item) => item.typeLabel !== "Direct");
  return (
    <section className="research-section" id="constraints">
      <SectionHeading number="03" title="Scaling Constraints" eyebrow="Bottleneck Diagnosis" />
      <div className="primary-constraint-panel">
        <div className="constraint-title-row">
          <div><ResearchLabel>Primary constraint</ResearchLabel><h3>{constraint.label}</h3></div>
          <DirectionLabel value={constraint.direction} />
        </div>
        <p className="constraint-mechanism">{constraint.economic_mechanism}</p>
        <div className="constraint-metadata">
          <InlineMetric label="Evidence basis" value={constraint.basis} />
          <InlineMetric label="Confidence" value={<ConfidenceLabel value={constraint.confidence} />} />
          <InlineMetric label="Model interpretation" value={constraint.inference} />
        </div>
        <div className="constraint-evidence-grid">
          <div><ResearchLabel>Direct evidence</ResearchLabel><EvidenceRows items={direct} empty="Direct evidence unavailable." /></div>
          <div><ResearchLabel>Proxy evidence</ResearchLabel><EvidenceRows items={indirect} empty="No indirect evidence cited." /></div>
        </div>
        {constraint.data_gaps.length ? <div className="constraint-limitations"><ResearchLabel>Evidence limitations</ResearchLabel>{constraint.data_gaps.map((gap) => <p key={gap.missing_field}>— {humanize(gap.missing_field)} unavailable. {gap.confidence_impact}</p>)}</div> : null}
      </div>
      {company.secondaryConstraints.length ? <div className="secondary-constraints"><ResearchLabel>Secondary constraints</ResearchLabel>{company.secondaryConstraints.map((item) => <CompactConstraint key={item.constraint} constraint={item} />)}</div> : null}
    </section>
  );
}

export function ScalingSection({ company }: { company: CompanyResearchViewModel }) {
  return (
    <section className="research-section" id="scaling">
      <SectionHeading number="04" title="Scaling Economics" eyebrow="Operating Leverage" />
      <p className="section-intro">{company.raw.scaling_economics.interpretation}</p>
      <div className="scaling-metrics instrument-data-plate">
        <div className="scaling-table-head"><span>Metric</span><span>Current</span><span>Period</span><span>Research read</span></div>
        {company.scalingMetrics.map((metric) => (
          <article className="scaling-metric" key={metric.name}>
            <ResearchLabel>{metric.label}</ResearchLabel>
            {metric.value === null ? <Unavailable reason="Comparable evidence unavailable" /> : <strong>{metric.valueLabel}</strong>}
            <small>{metric.current_period}</small>
            <WhyItMatters>{metric.interpretation}</WhyItMatters>
          </article>
        ))}
      </div>
      <p className="chart-rule-note">Historical charts are withheld because the fixture contains one comparable period. No unsupported trend arrow is shown.</p>
    </section>
  );
}

export function ThesisSection({ company }: { company: CompanyResearchViewModel }) {
  const sustainability = company.raw.growth_sustainability;
  const support = sustainability.supporting_evidence_ids.map((id) => company.evidenceById[id]).filter(Boolean);
  const contrary = sustainability.contrary_evidence_ids.map((id) => company.evidenceById[id]).filter(Boolean);
  return (
    <section className="research-section" id="thesis">
      <SectionHeading number="05" title="Growth Sustainability" eyebrow="Current Thesis" />
      <div className="thesis-panel">
        <div className="thesis-headline"><ResearchLabel>Current assessment</ResearchLabel><h3>{humanize(sustainability.scaling_structure)}</h3><ConfidenceLabel value={sustainability.confidence} /></div>
        <div className="thesis-columns">
          <div><ResearchLabel>Supporting evidence</ResearchLabel><EvidenceRows items={support} /></div>
          <div><ResearchLabel>Evidence against</ResearchLabel><EvidenceRows items={contrary} empty="None observed in current structured evidence." /></div>
          <div><ResearchLabel>Limitations</ResearchLabel>{company.dataGaps.length ? company.dataGaps.map((gap) => <p key={gap.missing_field}>— {gap.label} unavailable</p>) : <p>No material structured-data gaps identified.</p>}</div>
        </div>
        <div className="thesis-interpretation"><ResearchLabel>Current interpretation</ResearchLabel><p>{sustainability.interpretation}</p></div>
      </div>
      <div className="falsification-panel">
        <div><ResearchLabel>Falsification conditions</ResearchLabel><h3>What would break this view?</h3></div>
        <ol>
          {company.raw.falsification_conditions.map((item) => (
            <li key={item.condition}>
              <span>{item.condition}</span>
              {!company.availableMetrics.has(item.observable_metric) ? <small>Future KPI to monitor</small> : <small>{humanize(item.observable_metric)}</small>}
              <p>{item.rationale}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function FinancialTranslationSection({ company }: { company: CompanyResearchViewModel }) {
  const items = [
    ["revenue_forecast", "Revenue Forecast"],
    ["margin", "Margin"],
    ["capital_intensity", "Capital Intensity"],
    ["fcff_conversion", "FCFF Conversion"]
  ] as const;
  return (
    <section className="research-section" id="financials">
      <SectionHeading number="06" title="Financial Translation" eyebrow="Economics to Cash Flow" />
      <div className="translation-flow" aria-label="Financial translation flow">
        {["Economic Evidence", "Revenue Sustainability", "Margin Sustainability", "FCFF Conversion", "Valuation Assumptions"].map((label, index) => <span key={label}>{label}{index < 4 ? <i>→</i> : null}</span>)}
      </div>
      <div className="translation-list">
        {items.map(([key, label]) => {
          const item = company.raw.financial_translation[key];
          return <div key={key}><ResearchLabel>{label} implication</ResearchLabel><strong>{humanize(item.state)}</strong><p>{item.reason}</p></div>;
        })}
      </div>
    </section>
  );
}

export function ValuationSection({ company }: { company: CompanyResearchViewModel }) {
  const reviews = company.raw.valuation_assumption_review.reviews;
  const market = company.raw.market_expectations_comparison;
  return (
    <section className="research-section" id="valuation">
      <SectionHeading number="07" title="Valuation" eyebrow="Assumption Review" />
      <div className="valuation-unavailable">
        <ResearchLabel>Fair value range</ResearchLabel>
        <Unavailable reason="Scenario values are not present in the Company Economics fixture" />
        <p>Company Economics reviews valuation assumptions. It does not directly change them.</p>
      </div>
      <div className="economics-vs-dcf">
        <div className="comparison-header"><span>Company Economics</span><span>DCF Assumption</span><span>Review</span></div>
        {reviews.map((review) => {
          const observed = review.assumption === "revenue_growth" ? company.raw.growth_sustainability.current_revenue_growth : company.evidence.find((item) => item.metric === "fcf_margin")?.value;
          return (
            <div className="comparison-row" key={review.assumption}>
              <div><ResearchLabel>Observed {humanize(review.assumption)}</ResearchLabel><strong>{formatValue(observed, "decimal")}</strong></div>
              <div><ResearchLabel>{review.assumption === "revenue_growth" ? "Year-1 growth" : "Normalized FCFF margin"}</ResearchLabel><strong>{formatValue(review.dcf_value, "decimal")}</strong></div>
              <div><span className="status-label status-neutral">{humanize(review.state)}</span><p>{review.reason}</p></div>
            </div>
          );
        })}
      </div>
      <div className="market-expectations">
        <header className="instrument-panel-header"><div><strong>CHAINSTOX://MARKET EXPECTATIONS</strong><span>Reverse DCF research instrument</span></div><span>{humanize(market.state)}</span></header>
        {market.market_implied_revenue_cagr === null && market.market_implied_fcff_margin === null ? (
          <Unavailable reason="No converged market-implied solution" />
        ) : (
          <div className="market-metrics">
            <InlineMetric label="Current price" value={company.raw.company.market_price == null ? <Unavailable reason="Unavailable in fixture" /> : formatValue(company.raw.company.market_price, "currency")} />
            <InlineMetric label="5Y revenue CAGR required" value={formatValue(market.market_implied_revenue_cagr, "decimal")} />
            <InlineMetric label="Year-5 FCFF margin required" value={formatValue(market.market_implied_fcff_margin, "decimal")} />
          </div>
        )}
        <p>{market.reason}</p>
      </div>
    </section>
  );
}

type EvidenceFilter = "all" | "direct" | "proxy" | "inference" | "gaps";

export function EvidenceExplorer({ company }: { company: CompanyResearchViewModel }) {
  const [filter, setFilter] = useState<EvidenceFilter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const filtered = useMemo(() => filter === "all" ? company.evidence : filter === "gaps" ? [] : company.evidence.filter((item) => item.typeLabel.toLowerCase() === filter), [company.evidence, filter]);
  const tabs: Array<[EvidenceFilter, string, number]> = [
    ["all", "All", company.evidenceCounts.all], ["direct", "Direct", company.evidenceCounts.direct], ["proxy", "Proxy", company.evidenceCounts.proxy], ["inference", "Inference", company.evidenceCounts.inference], ["gaps", "Data Gaps", company.evidenceCounts.gaps]
  ];
  return (
    <section className="research-section" id="evidence">
      <SectionHeading number="08" title="Evidence" eyebrow={`${company.evidenceCounts.all} Evidence Items`} />
      <div className="evidence-summary">
        <InlineMetric label="Direct facts" value={company.evidenceCounts.direct} />
        <InlineMetric label="Calculated proxies" value={company.evidenceCounts.proxy} />
        <InlineMetric label="Model inferences" value={company.evidenceCounts.inference} />
      </div>
      <div className="evidence-tabs" role="tablist" aria-label="Filter evidence">
        {tabs.map(([key, label, count]) => <button key={key} type="button" role="tab" aria-selected={filter === key} onClick={() => setFilter(key)}>{label} <span>{count}</span></button>)}
      </div>
      {filter === "gaps" ? (
        <div className="data-gap-list">{company.dataGaps.length ? company.dataGaps.map((gap) => <article key={`${gap.missing_field}-${gap.related_constraint}`}><ResearchLabel>{gap.related_constraint ? humanize(gap.related_constraint) : "Data gap"}</ResearchLabel><h3>{gap.label}</h3><Unavailable reason="Direct evidence unavailable" /><p>{gap.why_it_matters}</p><small>{gap.confidence_impact}</small></article>) : <p className="empty-research-state">No material structured-data gaps identified.</p>}</div>
      ) : (
        <div className="evidence-explorer-list">
          {filtered.map((item) => (
            <article className="evidence-item" key={item.id}>
              <button type="button" aria-expanded={expanded === item.id} onClick={() => setExpanded(expanded === item.id ? null : item.id)}>
                <span className="evidence-id">{item.id}</span><span><strong>{item.label}</strong><EvidenceTypeBadge type={item.typeLabel} /></span><span className="evidence-item-value">{item.valueLabel}</span><span aria-hidden="true">{expanded === item.id ? "−" : "+"}</span>
              </button>
              {expanded === item.id ? <div className="evidence-item-details"><InlineMetric label="Period" value={item.period} /><InlineMetric label="Source" value={item.source || "Unavailable"} /><InlineMetric label="Used in" value={item.usedIn.join(" · ")} /><InlineMetric label="Confidence" value={<ConfidenceLabel value={item.confidence} />} /><p>{item.statement}</p></div> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
