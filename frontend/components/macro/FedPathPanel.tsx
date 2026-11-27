"use client";

import { useEffect, useState } from "react";
import { loadMarketStory, type FomcOutlook } from "../../lib/market-story";

// What fed funds futures price for the next Fed meetings (2026-11-27). Forward-looking by construction: these are
// the market's own odds, read with the CME FedWatch method in market_story.py. Not a CHAINSTOX forecast.

function month(key: string) {
  const d = new Date(`${key}-15T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? key : d.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}
function day(iso?: string) {
  if (!iso) return "—";
  const d = new Date(`${iso}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { day: "numeric", month: "short", timeZone: "UTC" });
}

export function FedPathPanel() {
  const [fomc, setFomc] = useState<FomcOutlook | null | undefined>(undefined);
  useEffect(() => { let active = true; loadMarketStory().then((d) => { if (active) setFomc(d.fomc ?? null); }); return () => { active = false; }; }, []);
  if (fomc === undefined) return <section className="fed-path glow-card"><p className="fed-quiet">Reading fed funds futures…</p></section>;
  if (!fomc || fomc.status !== "AVAILABLE" || fomc.rate_before == null) return <section className="fed-path glow-card"><p className="fed-quiet">{fomc?.reason ?? "Fed funds futures are unavailable right now."}</p></section>;
  const p = Math.round((fomc.probability_move ?? 0) * 100);
  const step = Math.abs((fomc.rate_after_if_move ?? fomc.rate_before) - fomc.rate_before);
  const headline = fomc.decision === "hold"
    ? `Markets expect the Fed to hold rates on ${day(fomc.meeting)}`
    : `Markets are betting on a ${step.toFixed(2)}-point rate ${fomc.decision === "raise" ? "rise" : "cut"} on ${day(fomc.meeting)} (${p >= 95 ? "near-certain" : `${p}% likely`})`;
  const contracts = Object.entries(fomc.contracts ?? {}).sort(([a], [b]) => a.localeCompare(b));
  const lo = Math.min(fomc.rate_before, ...contracts.map(([, v]) => v)) - 0.1, hi = Math.max(fomc.rate_before, ...contracts.map(([, v]) => v)) + 0.05;
  // further_moves is the share of one more 0.25-point move priced by that month (market_story.py), not basis points.
  // Same reading and threshold as the Market story's sentence (market_story.fomc_sentence).
  const further = fomc.further_moves != null && fomc.further_by && Math.abs(fomc.further_moves) >= 0.3
    ? `Another 0.25-point ${fomc.further_moves > 0 ? "rise" : "cut"} by ${month(fomc.further_by)}: about ${Math.round(Math.min(1, Math.abs(fomc.further_moves)) * 100)}% priced` : null;
  return <section className="fed-path glow-card" aria-label="What fed funds futures price">
    <span className="fed-kicker">US central bank (Fed) · what markets expect next</span>
    <h2 className="display-h2">{headline}.</h2>
    <div className="fed-nums">
      <div><small>Fed rate now</small><b>{fomc.rate_before.toFixed(2)}%</b></div>
      <div><small>Expected after {day(fomc.meeting)}</small><b>{(fomc.implied_after ?? fomc.rate_before).toFixed(2)}%</b></div>
      {further ? <div><small>Further out</small><b className="fed-small">{further}</b></div> : null}
    </div>
    {contracts.length ? <div className="fed-bars" role="img" aria-label={`Expected average Fed rate by month: ${contracts.map(([k, v]) => `${month(k)} ${v.toFixed(2)}%`).join(", ")}`}>
      {contracts.map(([k, v]) => <div key={k}><i style={{ height: `${Math.max(6, ((v - lo) / (hi - lo)) * 100)}%` }} /><b>{v.toFixed(2)}%</b><small>{month(k)}</small></div>)}
    </div> : null}
    <p className="fed-foot">From fed funds futures ({fomc.method?.replace(/\.$/, "")}). This is what markets are pricing, not a CHAINSTOX forecast.</p>
  </section>;
}
