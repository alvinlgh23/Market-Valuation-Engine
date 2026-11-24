"use client";

import type { OperationalResearch as Research } from "../../lib/company-economics-types";
import { humanize } from "../../lib/companyEconomicsAdapter";

export function OperationalResearch({ research, expanded = false }: { research?: Research; expanded?: boolean }) {
  return <section className="operational-research" aria-label="Operational research">
    <header><strong>Operational observations</strong><span>Dated issuer disclosures · provenance applies to each observation</span></header>
    <p>{research?.limitation ?? "Operational evidence unavailable in this saved profile. Refresh company research to load the current contract."}</p>
    {!research?.series.length ? <p>Missing company-specific operational evidence. No benchmark-company substitution.</p> : research.series.map((series) => <details key={series.definition.id} open={expanded || undefined}>
      <summary>{series.definition.name} · {series.definition.scope} · {series.observations.at(-1)?.period}</summary>
      <p>{series.definition.definition}</p>
      <p>Structural pathway: {series.definition.mechanism}</p>
      <p>Binding: {humanize(series.constraint_status)} · Direction: {humanize(series.direction_status)}</p>
      <table><caption>{series.definition.unit} · {series.definition.measurement} · definition {series.definition.version}</caption><thead><tr><th>Period</th><th>Observed value</th><th>Source</th></tr></thead><tbody>{series.observations.map((o) => <tr key={o.id}><td>{o.period} ({o.period_start ? `${o.period_start} – ` : ""}{o.period_end})</td><td>{o.evidence.value.toLocaleString()}</td><td><a href={o.evidence.source_url} target="_blank" rel="noreferrer">{o.evidence.source_name}</a><details><summary>Observation provenance</summary><p>{o.evidence.source_locator}</p><p>Published {o.evidence.filing_date} · Retrieved {o.evidence.retrieved_at}</p><p>{o.evidence.extraction_method} · {o.evidence.validation_status} · {o.revision_status}</p></details></td></tr>)}</tbody></table>
      {series.changes.map((c, i) => <p key={i}>{c.status === "CALCULATED" ? `Comparable change: ${c.absolute?.toLocaleString()} ${series.definition.unit}; ${c.growth == null ? "growth unavailable" : `${(c.growth * 100).toFixed(1)}% relative growth`}. Accounting comparison, not causal attribution.` : `Comparison withheld: ${c.reasons.join(", ")}`}</p>)}
      <p>Limitation: {series.definition.limitation}</p><p>Counterevidence: {series.counterevidence.length ? series.counterevidence.join("; ") : "Not assessed; absence is not confirmation."}</p><p>Next test: {series.falsification}</p>
    </details>)}
    {research?.security_unit_status === "SECURITY_UNIT_AMBIGUITY" ? <p>TSM security-unit ambiguity: authoritative per-ADR conclusions remain blocked pending a dated ratio, share-basis and FX reconciliation.</p> : null}
    {research?.security_unit_evidence ? <p><a href={research.security_unit_evidence.source_url} target="_blank" rel="noreferrer">Documented ratio: {research.security_unit_evidence.ordinary_shares_per_ads} ordinary shares per ADS</a>. {research.security_unit_evidence.limitation}</p> : null}
    {research?.assumption_tensions?.length ? <details><summary>Valuation assumption context</summary>{research.assumption_tensions.map((t) => <p key={t.metric}>{t.metric} ({t.observation_period}): historical change {t.historical_growth == null ? "unavailable" : `${(t.historical_growth * 100).toFixed(1)}%`}; forward consolidated revenue assumption {t.model_assumption == null ? "unavailable" : `${(t.model_assumption * 100).toFixed(1)}%`}. {t.limitation} {t.action}</p>)}</details> : null}
    <p>Read-only research. No DCF assumptions are changed.</p>
  </section>;
}
