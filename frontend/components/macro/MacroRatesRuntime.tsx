"use client";
import { useEffect, useState } from "react";
import type { ResearchSystem } from "../../lib/research-system-types";
import { MacroTransmissionDetail } from "./MacroOverviewSurface";

export function MacroRatesRuntime({ initial }: { initial: ResearchSystem }) {
  const [system, setSystem] = useState(initial);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    fetch("/api/research?scope=full", { cache: "no-store" }).then(r => r.json()).then(result => {
      if (!result.data?.market_transmission) throw new Error("Current rates response unavailable; showing bundled dated observations.");
      if (active) { setSystem(result.data); setError(result.meta?.error || ""); }
    }).catch(e => { if (active) setError(String(e)); });
    return () => { active = false; };
  }, []);
  return <>{error ? <p role="status">{error}</p> : null}<MacroTransmissionDetail section="rates" system={system} /><section className="macro-metric-ledger" aria-label="Curve maturity provenance">{system.market_transmission.rates.metrics.filter(metric => metric.maturity_metadata).map(metric => <article key={metric.key}><strong>{metric.label}</strong><p>{metric.note}</p><small>Long leg: {metric.maturity_metadata?.long_observed_at || "unknown date"} · Short leg: {metric.maturity_metadata?.short_observed_at || "unknown date"} · {metric.source_state}</small></article>)}</section></>;
}
