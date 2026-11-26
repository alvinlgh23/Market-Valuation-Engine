"use client";
import { useEffect, useState } from "react";
import { loadCompanyCard, type CardAxis } from "../../lib/company-card";
import { humanize } from "../../lib/companyEconomicsAdapter";
import type { RawConstraint } from "../../lib/company-economics-types";

// Checklist 11.6: the stored profile used to print "Not available" / "Unknown" for every company. These read
// what is known instead: the live valuation from the judgment card, and the candidate bottlenecks with the
// operating number each would need before it can be called binding.

/** "direct_market_saturation_kpi" -> "market saturation measure"; "store_count" -> "store count". */
export function kpiLabel(field: string | null | undefined): string | null {
  if (!field) return null;
  const core = field.replace(/^direct_/, "").replace(/_kpi$/, "");
  const words = humanize(core).toLowerCase();
  return field.endsWith("_kpi") ? `${words} measure` : words;
}

export type Candidate = { name: string; needs: string | null };

export function candidateBottlenecks(assessments: RawConstraint[] | undefined, fallback: string[] = [], limit = 3): Candidate[] {
  const rows = assessments?.length
    ? assessments.map((item) => ({ name: humanize(item.constraint), needs: kpiLabel(item.data_gaps?.[0]?.missing_field) }))
    : fallback.map((name) => ({ name: humanize(name), needs: null }));
  return rows.filter((row) => row.name && row.name !== "Unknown").slice(0, limit);
}

export function useLiveValuation(ticker: string): { axis: CardAxis | null; loading: boolean } {
  const [state, setState] = useState<{ axis: CardAxis | null; loading: boolean }>({ axis: null, loading: true });
  useEffect(() => {
    let active = true;
    loadCompanyCard(ticker).then((result) => { if (active) setState({ axis: result.card?.axes?.valuation ?? null, loading: false }); });
    return () => { active = false; };
  }, [ticker]);
  return state;
}

// Checklist 18.22: operating signals from the filings, read with the live judgment card.
export type OperatingSignal = { key: string; label: string; change: number; sales_change: number | null; gap: number | null; days_now?: number | null; days_ago?: number | null; days_change?: number | null; reading: string; tone: string; as_of: string; basis: string };
export type Operating = { status: string; signals: OperatingSignal[]; missing?: string[]; constraint?: OperatingSignal | null; summary: string; rule?: string; source?: string };

export function useOperating(ticker: string): Operating | null {
  const [state, setState] = useState<Operating | null>(null);
  useEffect(() => {
    let active = true;
    loadCompanyCard(ticker).then((result) => { if (active) setState((result.card?.operating as Operating | undefined) ?? null); });
    return () => { active = false; };
  }, [ticker]);
  return state;
}

function signed(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100);
  if (rounded === 0) return "0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded)}%`;
}

export function OperatingSignals({ operating }: { operating: Operating | null | undefined }) {
  if (!operating || operating.status !== "AVAILABLE") return null;
  return <section className="jc-operating" aria-label="Operating signals from filings">
    <header><h3>Operating signals</h3><small title={operating.rule}>From SEC filings · vs sales growth</small></header>
    <p className={operating.constraint ? "tone-against" : ""}>{operating.summary}</p>
    <ul>{operating.signals.map((item) => {
      const daysNote = item.days_now != null && item.days_change != null
        ? ` · ${item.days_now}d of sales (${item.days_change >= 0 ? "+" : "−"}${Math.abs(item.days_change)}d)`
        : "";
      const periodTitle = item.basis === "trailing 4 quarters" ? `Trailing 4 quarters to ${item.as_of}` : item.basis === "fiscal year" ? `Fiscal year to ${item.as_of}` : `Quarter-end balance at ${item.as_of}`;
      return <li key={item.key} title={periodTitle}>
        <span>{item.label}{item.basis === "trailing 4 quarters" ? <small className="jc-op-basis"> TTM</small> : item.basis === "fiscal year" ? <small className="jc-op-basis"> FY</small> : null}</span>
        <b>{signed(item.change)}</b>
        <small>sales {signed(item.sales_change)}</small>
        <em className={`tone-${item.tone}`}>{item.reading}{daysNote ? <small className="jc-op-days">{daysNote}</small> : null}</em>
      </li>;
    })}</ul>
    {operating.missing?.length ? <small className="jc-operating-missing">Not in the filings: {operating.missing.join(", ")}</small> : null}
  </section>;
}

export function BottleneckCandidates({ candidates }: { candidates: Candidate[] }) {
  if (!candidates.length) return <p>No candidate bottleneck is registered for this business type.</p>;
  return <>
    <p>Not confirmed yet. Likely bottlenecks for this type of business, and the operating number that would confirm each:</p>
    <ul className="snapshot-candidates">
      {candidates.map((item) => <li key={item.name}><b>{item.name}</b>{item.needs ? <small>needs {item.needs}</small> : null}</li>)}
    </ul>
  </>;
}
