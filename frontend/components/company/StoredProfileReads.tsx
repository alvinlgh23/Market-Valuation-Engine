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

export function BottleneckCandidates({ candidates }: { candidates: Candidate[] }) {
  if (!candidates.length) return <p>No candidate bottleneck is registered for this business type.</p>;
  return <>
    <p>Not confirmed yet. Likely bottlenecks for this type of business, and the operating number that would confirm each:</p>
    <ul className="snapshot-candidates">
      {candidates.map((item) => <li key={item.name}><b>{item.name}</b>{item.needs ? <small>needs {item.needs}</small> : null}</li>)}
    </ul>
  </>;
}
