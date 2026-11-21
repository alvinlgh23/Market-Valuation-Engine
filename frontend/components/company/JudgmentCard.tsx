"use client";
import { useEffect, useState } from "react";
import { StatusBadge } from "../research/StatusBadge";

type Axis = { state: string; direction: string | null; confidence: string; evidence: string[]; missing: string[]; families: string[]; detail: Record<string, unknown> };
type Card = {
  ticker: string; name: string; archetype: string; sector_etf: string | null; generated_on: string;
  axes: Record<string, Axis>;
  horizons: Record<string, { window: string; context?: string; axes: string[] }>;
  contradictions: string[]; changes: Array<{ axis: string; from: string; to: string; since: string }>; falsification: string[];
  next_catalysts: { earnings: string | null; last_earnings?: string | null; fomc: string | null };
  disclaimer: string;
};

const AXIS_LABEL: Record<string, string> = { macro: "Macro", flow: "Money flow", valuation: "Valuation", crowding: "Crowding", expectations: "Expectations", fundamentals: "Fundamentals" };
const HORIZON_LABEL: Record<string, string> = { tactical: "Next 1–3 months", cyclical: "Next 6–12 months", structural: "Next 3–5 years" };

function num(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function money(value: unknown) { const n = num(value); return n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: n >= 100 ? 0 : 2 }); }
function pct(value: unknown) { const n = num(value); return n == null ? "—" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}%`; }

/** Checklist 8.1: the numbers a reader needs before any judgment. */
function NumberStrip({ card }: { card: Card }) {
  const valuation = card.axes.valuation?.detail ?? {};
  const fair = (valuation.fair_value ?? {}) as Record<string, unknown>;
  const crowd = (card.axes.crowding?.detail?.valuation_in_own_history ?? {}) as Record<string, unknown>;
  const expectations = card.axes.expectations?.detail ?? {};
  const items = [
    ["Price", money(valuation.price)],
    ["Revenue growth (latest)", pct(valuation.observed_growth)],
    ["Consensus growth next year", pct(expectations.revenue_growth_next_year ?? valuation.consensus_next_year_growth)],
    ["Model base value", fair.base == null ? "Withheld" : money(fair.base)],
    ["Price-to-sales vs own history", num(crowd.percentile) == null ? "—" : `${Math.round((crowd.percentile as number) * 100)}th pct`],
  ];
  return <dl className="judgment-numbers">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

export function JudgmentCard({ ticker }: { ticker: string }) {
  const [card, setCard] = useState<Card | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    fetch(`/api/research?action=company-verdict&ticker=${encodeURIComponent(ticker)}`, { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (!active) return; if (body.card) setCard(body.card as Card); else setError(body.error || "The judgment card is unavailable."); })
      .catch((failure) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, [ticker]);
  if (error) return <section className="judgment-card judgment-card-empty" aria-label="Judgment card"><p>Judgment card unavailable: {error}</p></section>;
  if (!card) return <section className="judgment-card judgment-card-empty" aria-label="Judgment card" aria-busy="true"><p>Building the judgment card from live company data (about half a minute)…</p></section>;
  return <section className="judgment-card" aria-label="Judgment card">
    <NumberStrip card={card} />
    <div className="judgment-horizons">
      {Object.entries(card.horizons).map(([key, horizon]) => <article key={key}>
        <header><h3>{HORIZON_LABEL[key] ?? horizon.window}</h3>{horizon.context ? <small>{horizon.context}</small> : null}</header>
        {horizon.axes.map((name) => { const axis = card.axes[name]; if (!axis) return null; return <div className="judgment-axis" key={name}>
          <div><span>{AXIS_LABEL[name] ?? name}</span><StatusBadge value={axis.confidence === "MODERATE" ? "Moderate confidence" : "Low confidence"} /></div>
          <strong>{axis.state}</strong>
          {axis.evidence.map((line) => <p key={line}>{line}</p>)}
        </div>; })}
      </article>)}
    </div>
    {card.contradictions.length ? <section className="judgment-list"><h3>Contradictions</h3><ul>{card.contradictions.map((item) => <li key={item}>{item}</li>)}</ul></section> : null}
    {card.changes.length ? <section className="judgment-list"><h3>Changed since last card</h3><ul>{card.changes.map((item) => <li key={item.axis}>{AXIS_LABEL[item.axis] ?? item.axis}: {item.from} → {item.to} (since {item.since})</li>)}</ul></section> : null}
    <footer className="judgment-footer">
      <span>Next earnings {card.next_catalysts.earnings ?? (card.next_catalysts.last_earnings ? `not yet published (last ${card.next_catalysts.last_earnings})` : "unavailable")} · next FOMC {card.next_catalysts.fomc ?? "unavailable"}</span>
      {card.falsification.length ? <details><summary>What would change the view</summary><ul>{card.falsification.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
      <details><summary>Missing inputs</summary><ul>{Object.entries(card.axes).flatMap(([name, axis]) => axis.missing.map((item) => <li key={`${name}-${item}`}>{AXIS_LABEL[name] ?? name}: {item}</li>))}</ul></details>
      <small>{card.disclaimer} Card generated {card.generated_on}.</small>
    </footer>
  </section>;
}
