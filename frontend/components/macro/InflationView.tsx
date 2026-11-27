"use client";

import type { ResearchSystem } from "../../lib/research-system-types";
import { useProView } from "../../lib/view-mode";
import { ResearchModule } from "../research/ResearchModule";

// Inflation (2026-11-27): plain view first - prices now against what bond markets expect, then five plain category
// cards; Pro view keeps the full 27-indicator workspace. Readings come from the inflation engine and Central Bank
// Compass; the market expectation is the cached 10-year breakeven (FRED T10YIE). Nothing is recalculated.

type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === "object" && !Array.isArray(v) ? (v as Json) : {});
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const lower = (v: unknown) => String(v ?? "").replace(/_/g, " ").toLowerCase();

const CATEGORIES: Array<[string, string, string]> = [
  ["wages", "Pay", "Pay rises feed into the price of services."],
  ["shelter", "Housing", "Rent and housing costs, the biggest single part of consumer prices."],
  ["services", "Services", "Healthcare, transport, recreation and other services."],
  ["energy", "Energy", "Fuel and electricity: they swing fast and move headline inflation."],
  ["goods", "Goods", "Physical goods; producer prices tend to reach shops later."],
];
/** Plain words for the inflation engine's category and horizon readings (display labels only). */
const PLAIN_STATE: Record<string, string> = {
  "Easing": "Cooling", "Sticky / mixed": "Stuck, with mixed signals", "Mixed headline impulse": "Swinging headline prices up and down",
  "Pipeline pressure rising": "Rising at the producer stage", "Mixed / Two-sided": "pulling both ways", "Contained / mixed": "Contained",
  "Elevated": "High", "Uncertain": "Unclear", "Mixed": "Mixed",
};
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
function monthName(ym: string) { const [y, m] = ym.split("-").map(Number); return y && m ? `${MONTHS[m - 1]} ${y}` : ym; }

export function InflationView({ system, breakeven }: { system: ResearchSystem; breakeven: { value: number; date: string } | null }) {
  const [pro, setPro] = useProView();
  const report = obj(system.modules.inflation.payload);
  const states = obj(report.states);
  const iv = obj(obj(obj(system.world.regions.US).engine_specific).central_bank_compass).indicator_values as Json | undefined;
  const headline = num(obj(iv).headline_inflation_yoy), core = num(obj(iv).core_inflation_yoy);
  const month = typeof report.common_month === "string" ? monthName(report.common_month) : null;
  const toggle = <div className="mc-mode" role="group" aria-label="View">
    <button type="button" aria-pressed={!pro} className={!pro ? "on" : ""} onClick={() => setPro(false)}>Plain</button>
    <button type="button" aria-pressed={pro} className={pro ? "on" : ""} onClick={() => setPro(true)}>Pro view</button>
  </div>;
  if (pro) return <div className="infl-pro"><div className="infl-toggle">{toggle}</div><ResearchModule module="inflation" system={system} /></div>;
  const gap = headline != null && breakeven ? headline - breakeven.value : null;
  return <div className="mc infl">
    <header className="mc-top">
      <div><h1>Inflation</h1><p>How fast prices are rising, what bond markets expect, and which parts of the economy are pushing it up or down.</p></div>
      {toggle}
    </header>

    <section className="mc-hero glow-card" aria-label="Prices now against what markets expect">
      <span className="mc-kicker">Prices now vs what markets expect{month ? ` · latest official data ${month}` : ""}</span>
      <div className="infl-anchor">
        <div><small>Prices vs a year ago</small><b>{headline != null ? `${headline.toFixed(1)}%` : "—"}</b><em>all items</em></div>
        <div><small>Excluding food and energy</small><b>{core != null ? `${core.toFixed(1)}%` : "—"}</b><em>the Fed&apos;s main gauge (core PCE)</em></div>
        <div className="infl-market"><small>What bond markets expect, next 10 years</small><b>{breakeven ? `${breakeven.value.toFixed(1)}%` : "—"}</b><em>a year on average{breakeven ? ` · ${breakeven.date}` : ""}</em></div>
        <div><small>Fed target</small><b>2.0%</b><em>a year</em></div>
      </div>
      {gap != null && headline != null && breakeven ? <p className="mc-plain">{gap > 0.5
        ? `Prices are rising faster today (${headline.toFixed(1)}%) than bond markets expect on average over the next ten years (${breakeven.value.toFixed(1)}%).`
        : gap < -0.5 ? `Bond markets expect more inflation over the next ten years (${breakeven.value.toFixed(1)}%) than prices show today (${headline.toFixed(1)}%).` : "Today's inflation is close to what bond markets expect over the next ten years."}</p> : null}
      <p className="mc-tested weak"><b>Note</b>Official price data arrives with a lag{month ? ` (latest: ${month})` : ""}. The bond-market expectation updates daily. This page describes inflation; it is not a forecast of stock prices.</p>
    </section>

    <section className="infl-cats" aria-label="What is pushing inflation">
      <h2>What is pushing prices{typeof report.near_term === "string" ? <small>Next 1–3 months: {(PLAIN_STATE[String(report.near_term)] ?? lower(report.near_term)).toLowerCase()} · 3–12 months: {(PLAIN_STATE[String(report.medium_term)] ?? lower(report.medium_term)).toLowerCase()}</small> : null}</h2>
      <div className="infl-grid">{CATEGORIES.map(([key, label, why]) => <article key={key} className="mc-card">
        <span className="mc-kicker">{label}</span>
        <h3>{typeof states[key] === "string" ? PLAIN_STATE[String(states[key])] ?? String(states[key]).replace(/\s*\/\s*/g, ", ") : "No reading"}</h3>
        <p className="mc-plain">{why}</p>
      </article>)}</div>
    </section>
    <p className="mc-rule">Switch to Pro view for all 27 indicators, their sources and dates.</p>
  </div>;
}
