"use client";
import { useEffect, useState } from "react";
import { fairValueCoordinates } from "../../lib/fair-value-scale.mjs";
import { axisTone, confidenceDots, percentileWidth, TONE_GLYPH, TONE_LABEL, type Tone } from "../../lib/judgment-tone.mjs";

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
const HORIZON_LABEL: Record<string, string> = { tactical: "1–3 months", cyclical: "6–12 months", structural: "3–5 years" };

function num(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function money(value: unknown) { const n = num(value); return n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: n >= 100 ? 0 : 2 }); }
function pct(value: unknown, digits = 1) { const n = num(value); return n == null ? "—" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(digits)}%`; }
function words(value: unknown) { return String(value ?? "").toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()); }
function obj(value: unknown) { return (value && typeof value === "object" ? value : {}) as Record<string, unknown>; }

/** A horizontal 0-100 bar with a marker; label on the left, value on the right. */
/** `highIsAgainst`: for valuation-type readings a high percentile is expensive, so the colours run the other way. */
function PercentileBar({ label, value, note, highIsAgainst = false }: { label: string; value: unknown; note?: string; highIsAgainst?: boolean }) {
  const width = percentileWidth(value);
  if (width == null) return null;
  return <div className="jc-bar" title={note}>
    <span>{label}</span>
    <div className={`jc-bar-track${highIsAgainst ? " reverse" : ""}`}><i style={{ left: `${width}%` }} /></div>
    <b>{Math.round(width)}th pct</b>
  </div>;
}

function Chip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`jc-chip tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{children}</span>;
}

/** Small visual per axis, drawn from the card's detail fields only. */
function AxisVisual({ name, axis }: { name: string; axis: Axis }) {
  const detail = axis.detail;
  if (name === "flow") return <PercentileBar label={`${String(detail.sector_etf ?? "Sector")} vs SPY`} value={detail.percentile} note="One-month relative strength, percentile of its own stored history" />;
  if (name === "crowding") {
    const own = obj(detail.valuation_in_own_history);
    return <PercentileBar label="P/S vs own history" value={own.state === "AVAILABLE" ? own.percentile : null} highIsAgainst note="Price-to-sales percentile in the company's own history; higher is more expensive" />;
  }
  if (name === "macro") {
    const rows = Array.isArray(detail.exposures) ? (detail.exposures as Array<Record<string, unknown>>) : [];
    const shown = rows.filter((row) => row.factor_state && row.effect !== 0);
    if (!shown.length) return null;
    return <div className="jc-chips">{shown.map((row) => <Chip key={String(row.factor)} tone={Number(row.effect) > 0 ? "supportive" : "against"}>{String(row.label)}: {String(row.factor_state).toLowerCase()}</Chip>)}</div>;
  }
  if (name === "expectations") {
    const up = num(detail.revisions_up_30d), down = num(detail.revisions_down_30d);
    if (up == null || down == null || up + down === 0) return null;
    return <div className="jc-split" title="Analyst revisions to next-year EPS, last 30 days">
      <span>Revisions 30d</span>
      <div><i className="tone-supportive" style={{ flexGrow: up }} /><i className="tone-against" style={{ flexGrow: down }} /></div>
      <b>{up} up · {down} down</b>
    </div>;
  }
  if (name === "fundamentals") {
    const parts = obj(detail.financial_translation);
    const entries = Object.entries(parts);
    if (!entries.length) return null;
    const tone = (value: unknown): Tone => value === "POSITIVE" ? "supportive" : value === "NEGATIVE" ? "against" : value === "MIXED" ? "mixed" : "unknown";
    return <div className="jc-chips">{entries.map(([key, value]) => <Chip key={key} tone={tone(value)}>{words(key)}</Chip>)}</div>;
  }
  if (name === "valuation") {
    const implied = num(detail.implied_5y_revenue_cagr);
    const reference = num(detail.consensus_next_year_growth) ?? num(detail.observed_growth);
    if (implied == null || reference == null) return null;
    const top = Math.max(implied, reference, 0.01);
    return <div className="jc-compare" title="Revenue growth the price implies (reverse DCF, five-year CAGR) against consensus next-year growth">
      <div><span>Priced in</span><i style={{ width: `${Math.max(2, (Math.max(implied, 0) / top) * 100)}%` }} /><b>{pct(implied, 0)}</b></div>
      <div><span>Consensus</span><i style={{ width: `${Math.max(2, (Math.max(reference, 0) / top) * 100)}%` }} /><b>{pct(reference, 0)}</b></div>
    </div>;
  }
  return null;
}

function AxisTile({ name, axis }: { name: string; axis: Axis }) {
  const tone = axisTone(name, axis.state);
  const dots = confidenceDots(axis.confidence);
  return <div className={`jc-axis tone-${tone}`}>
    <header>
      <span>{AXIS_LABEL[name] ?? name}</span>
      <i className="jc-dots" title={`${words(axis.confidence)} confidence`} aria-label={`${words(axis.confidence)} confidence`}>{[1, 2, 3].map((n) => <b key={n} className={n <= dots ? "on" : ""} />)}</i>
    </header>
    <strong><em aria-hidden>{TONE_GLYPH[tone]}</em>{axis.state}</strong>
    <AxisVisual name={name} axis={axis} />
    {axis.evidence.length ? <details><summary>Why</summary>{axis.evidence.map((line) => <p key={line}>{line}</p>)}</details> : null}
  </div>;
}

/** Bear / base / bull with today's price, or why it is withheld. */
function ValueRange({ card }: { card: Card }) {
  const detail = card.axes.valuation?.detail ?? {};
  const fair = obj(detail.fair_value);
  const price = num(detail.price);
  const values = { bear: num(fair.bear), base: num(fair.base), bull: num(fair.bull), market: price };
  const scale = fairValueCoordinates(values);
  if (!scale.valid) return <div className="jc-range jc-range-empty"><span>Model value</span><b>Withheld</b><small>{card.axes.valuation?.missing?.[0] ?? card.axes.valuation?.state}</small></div>;
  const weight = num(detail.ten_year_weight);
  return <div className="jc-range" aria-label="Model value range against price">
    <span>Model value {weight ? <small>({Math.round(weight * 100)}% ten-year model)</small> : null}</span>
    <div className="jc-range-track">
      <div className="jc-range-band" style={{ left: `${scale.positions.bear}%`, width: `${scale.positions.bull - scale.positions.bear}%` }} />
      {(["bear", "base", "bull"] as const).map((key) => <i key={key} className={`jc-range-tick ${key}`} style={{ left: `${scale.positions[key]}%` }}><b>{money(values[key])}</b><small>{key}</small></i>)}
      {price != null ? <i className="jc-range-price" style={{ left: `${scale.positions.market}%` }}><b>Price {money(price)}</b></i> : null}
    </div>
  </div>;
}

function NumberStrip({ card }: { card: Card }) {
  const valuation = card.axes.valuation?.detail ?? {};
  const expectations = card.axes.expectations?.detail ?? {};
  const items: Array<[string, string]> = [
    ["Price", money(valuation.price)],
    ["Revenue growth", pct(valuation.observed_growth)],
    ["Consensus next year", pct(expectations.revenue_growth_next_year ?? valuation.consensus_next_year_growth)],
  ];
  return <dl className="jc-numbers">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function Legend() {
  return <div className="jc-legend" aria-label="Legend">{(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}<span className="jc-legend-dots"><i className="jc-dots"><b className="on" /><b className="on" /><b /></i>confidence</span></div>;
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
  if (!card) return <section className="judgment-card judgment-card-empty" aria-label="Judgment card" aria-busy="true"><div className="jc-skeleton" /><p>Building the judgment card from live company data (about half a minute)…</p></section>;
  const earnings = card.next_catalysts.earnings ?? (card.next_catalysts.last_earnings ? `not yet set (last ${card.next_catalysts.last_earnings})` : "—");
  return <section className="judgment-card" aria-label="Judgment card">
    <div className="jc-top">
      <span className="jc-type">{words(card.archetype)}{card.sector_etf ? ` · ${card.sector_etf}` : ""}</span>
      <Legend />
    </div>
    <div className="jc-headline">
      <NumberStrip card={card} />
      <ValueRange card={card} />
    </div>
    <div className="judgment-horizons">
      {Object.entries(card.horizons).map(([key, horizon]) => <article key={key}>
        <header><h3>{HORIZON_LABEL[key] ?? horizon.window}</h3>{horizon.context ? <small>{horizon.context}</small> : null}</header>
        {horizon.axes.map((name) => card.axes[name] ? <AxisTile key={name} name={name} axis={card.axes[name]} /> : null)}
      </article>)}
    </div>
    {card.contradictions.length || card.changes.length ? <div className="jc-flags">
      {card.contradictions.map((item) => <span key={item} className="jc-flag tone-mixed"><em aria-hidden>!</em>{item}</span>)}
      {card.changes.map((item) => <span key={item.axis} className="jc-flag"><em aria-hidden>↻</em>{AXIS_LABEL[item.axis] ?? item.axis}: {item.from} → {item.to}</span>)}
    </div> : null}
    <footer className="judgment-footer">
      <div className="jc-dates"><span><small>Next earnings</small><b>{earnings}</b></span><span><small>Next FOMC</small><b>{card.next_catalysts.fomc ?? "—"}</b></span></div>
      {card.falsification.length ? <details><summary>What would change the view</summary><ul>{card.falsification.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
      <details><summary>Missing inputs</summary><ul>{Object.entries(card.axes).flatMap(([name, axis]) => axis.missing.map((item) => <li key={`${name}-${item}`}>{AXIS_LABEL[name] ?? name}: {item}</li>))}</ul></details>
      <small>{card.disclaimer} Card generated {card.generated_on}.</small>
    </footer>
  </section>;
}
