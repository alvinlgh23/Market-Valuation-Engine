"use client";
import { useEffect, useState } from "react";
import { loadCompanyCard } from "../../lib/company-card";
import { fairValueCoordinates } from "../../lib/fair-value-scale.mjs";
import { historyLabel, versusHistory } from "../../lib/plain-words.mjs";
import { OperatingSignals, type Operating } from "./StoredProfileReads";
import { axisTone, confidenceDots, percentileWidth, TONE_GLYPH, TONE_LABEL, type Tone } from "../../lib/judgment-tone.mjs";
import { PriceDriversPanel, type Attribution, type PriceReading } from "./PriceDrivers";

type Axis = { state: string; direction: string | null; confidence: string; evidence: string[]; missing: string[]; families: string[]; detail: Record<string, unknown> };
type Card = {
  ticker: string; name: string; archetype: string; sector_etf: string | null; generated_on: string;
  axes: Record<string, Axis>;
  horizons: Record<string, { window: string; context?: string; axes: string[] }>;
  contradictions: string[]; changes: Array<{ axis: string; from: string; to: string; since: string }>; falsification: string[]; operating?: unknown;
  next_catalysts: { earnings: string | null; last_earnings?: string | null; fomc: string | null };
  disclaimer: string;
  attribution?: Attribution; price_reading?: PriceReading;
};

const AXIS_LABEL: Record<string, string> = { macro: "Macro", flow: "Money flow", valuation: "Valuation", crowding: "Crowding", expectations: "Expectations", fundamentals: "Fundamentals" };
const HORIZON_LABEL: Record<string, string> = { tactical: "1–3 months", cyclical: "6–12 months", structural: "3–5 years" };

function num(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function money(value: unknown) { const n = num(value); return n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: n >= 100 ? 0 : 2 }); }
function pct(value: unknown, digits = 1) { const n = num(value); return n == null ? "—" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(digits)}%`; }
// Checklist 18.13: only readings that changed under the same rules are flagged as changes.
function companyChanges(card: { changes: Array<{ axis: string; from: string; to: string; origin?: string }> }) { return card.changes.filter((item) => item.origin === "COMPANY"); }

function words(value: unknown) { return String(value ?? "").toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()); }
function obj(value: unknown) { return (value && typeof value === "object" ? value : {}) as Record<string, unknown>; }

/** A horizontal 0-100 bar with a marker; label on the left, value on the right. */
/** `highIsAgainst`: for valuation-type readings a high percentile is expensive, so the colours run the other way. */
function PercentileBar({ label, value, note, highIsAgainst = false, period }: { label: string; value: unknown; note?: string; highIsAgainst?: boolean; period: string }) {
  const width = percentileWidth(value);
  if (width == null) return null;
  // Plain words instead of a percentile (owner request 2026-11-24); the exact place is in the tooltip.
  return <div className="jc-bar" title={[note, versusHistory(value, period)].filter(Boolean).join(" ")}>
    <span>{label}</span>
    <div className={`jc-bar-track${highIsAgainst ? " reverse" : ""}`}><i style={{ left: `${width}%` }} /></div>
    <b>{historyLabel(value, highIsAgainst ? "price" : "strength")}</b>
  </div>;
}

function Chip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`jc-chip tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{children}</span>;
}

/** Small visual per axis, drawn from the card's detail fields only. */
function AxisVisual({ name, axis }: { name: string; axis: Axis }) {
  const detail = axis.detail;
  if (name === "flow") return <PercentileBar label={`${String(detail.sector_etf ?? "Sector")} vs SPY`} value={detail.percentile} note="How the sector did against the S&P 500 over one month, compared with its own record." period="its stored record" />;
  if (name === "crowding") {
    const own = obj(detail.valuation_in_own_history);
    return <PercentileBar label="P/S vs own history" value={own.state === "AVAILABLE" ? own.percentile : null} highIsAgainst note="Price-to-sales compared with the company's own history; higher is more expensive." period="its own history" />;
  }
  if (name === "macro") {
    const rows = Array.isArray(detail.exposures) ? (detail.exposures as Array<Record<string, unknown>>) : [];
    const shown = rows.filter((row) => row.factor_state && row.effect !== 0);
    if (!shown.length) return null;
    // Checklist 10.5: "context" factors (reversed in the scorecard) are shown neutral, not as a headwind or tailwind.
    return <div className="jc-chips">{shown.map((row) => <span key={String(row.factor)} title={row.weight === "context" ? "Moved prices, but not counted as a forecast: high readings preceded better returns in the scorecard." : undefined}>
      <Chip tone={row.weight === "context" ? "unknown" : Number(row.effect) > 0 ? "supportive" : "against"}>{String(row.label)}: {String(row.factor_state).toLowerCase()}{row.weight === "context" ? " · context" : ""}</Chip></span>)}</div>;
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
    // Checklist 15.5: the latest quarter's numbers, and the finances verdict, as chips.
    const quarter = obj(detail.quarterly);
    if (quarter.status === "AVAILABLE") {
      const health = obj(quarter.health);
      const signed = (value: unknown, scale = 100, unit = "%") => typeof value === "number" ? `${value >= 0 ? "+" : "−"}${Math.abs(value * scale).toFixed(unit === "%" ? 0 : 1)}${unit}` : null;
      const chips: Array<[string, Tone, string]> = [];
      const growth = signed(quarter.revenue_yoy);
      if (growth) chips.push([`Sales ${growth}`, Number(quarter.revenue_yoy) >= 0 ? "supportive" : "against", "Sales against the same quarter a year earlier"]);
      const margin = signed(quarter.margin_change, 100, " pts");
      if (margin) chips.push([`Margin ${margin}`, Number(quarter.margin_change) > 0.01 ? "supportive" : Number(quarter.margin_change) < -0.01 ? "against" : "mixed", "Operating margin against a year earlier"]);
      const beat = signed(quarter.eps_surprise);
      if (beat) chips.push([`EPS vs forecast ${beat}`, Number(quarter.eps_surprise) >= 0 ? "supportive" : "against", "Earnings per share against the analysts' forecast"]);
      if (health.state && health.state !== "UNKNOWN") chips.push([`Finances: ${String(health.label).toLowerCase()}`, health.state === "STRONG" ? "supportive" : health.state === "WEAK" ? "against" : health.state === "FAIR" ? "mixed" : "unknown", String(health.reason ?? "")]);
      return <div className="jc-chips">{chips.map(([text, tone, title]) => <span key={text} title={title}><Chip tone={tone}>{text}</Chip></span>)}</div>;
    }
    const parts = obj(detail.financial_translation);
    const entries = Object.entries(parts);
    if (!entries.length) return null;
    const tone = (value: unknown): Tone => value === "POSITIVE" ? "supportive" : value === "NEGATIVE" ? "against" : value === "MIXED" ? "mixed" : "unknown";
    return <div className="jc-chips">{entries.map(([key, value]) => <Chip key={key} tone={tone(value)}>{words(key)}</Chip>)}</div>;
  }
  if (name === "valuation") {
    const implied = num(detail.implied_5y_revenue_cagr);
    // Checklist 18.16: above the model's ceiling, show how far above, so companies stay comparable.
    const stretch = num(detail.price_to_max_case);
    if (implied == null && stretch != null) {
      return <div className="jc-compare" title="Share price divided by the value even 50% first-year sales growth would justify. 1x would be just reachable; higher means further beyond.">
        <div><span>Price vs best case</span><i style={{ width: `${Math.min(100, (stretch / 4) * 100)}%` }} /><b>{stretch.toFixed(1)}x</b></div>
      </div>;
    }
    // Checklist 15.6: five-year growth the price assumes against two references of similar length.
    const band = obj(detail.growth_band);
    const rows: Array<[string, number | null]> = band.consensus_2y != null || band.history_3y != null
      ? [["Priced in, 5 yrs", implied], ["Analysts, 2 yrs", num(band.consensus_2y)], ["Last 3 yrs", num(band.history_3y)]]
      : [["Priced in", implied], ["Consensus", num(detail.consensus_next_year_growth) ?? num(detail.observed_growth)]];
    if (implied == null || rows.slice(1).every(([, value]) => value == null)) return null;
    const top = Math.max(...rows.map(([, value]) => value ?? 0), 0.01);
    return <div className="jc-compare" title="Yearly sales growth the share price assumes for five years, against analysts' two-year forecast and the last three years. More than 5 points above both reads priced high; more than 5 points below both, priced low.">
      {rows.filter(([, value]) => value != null).map(([label, value]) => <div key={label}><span>{label}</span><i style={{ width: `${Math.max(2, (Math.max(value as number, 0) / top) * 100)}%` }} /><b>{pct(value, 0)}</b></div>)}
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
  // Checklist 12.2: a bank shows the ROE its price implies against the ROE it earns.
  const bank = obj(detail.bank_implied_roe);
  if (num(bank.implied_roe) != null && num(bank.latest_roe) != null) return <div className="jc-range jc-range-empty"><span>Price-implied ROE</span><b>{((num(bank.implied_roe) ?? 0) * 100).toFixed(1)}%</b><small>Earns {((num(bank.latest_roe) ?? 0) * 100).toFixed(1)}% · price-to-book {(num(bank.price_to_book) ?? 0).toFixed(2)}</small></div>;
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

// Owner decision 2026-11-24: "next year" is the fiscal year still mostly ahead, which for a June-to-October year end is the current one.
function fiscalYearTitle(value: unknown): string | undefined {
  if (typeof value !== "string" || !value) return undefined;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? undefined : `Revenue growth for the fiscal year ending ${date.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" })}`;
}

function NumberStrip({ card }: { card: Card }) {
  const valuation = card.axes.valuation?.detail ?? {};
  const expectations = card.axes.expectations?.detail ?? {};
  const basis = String(valuation.growth_basis ?? "");
  const quarter = num(valuation.latest_quarter_yoy);
  const twelveMonth = basis.startsWith("trailing twelve months");
  const items: Array<[string, string, string?]> = [
    ["Price", money(valuation.price)],
    [twelveMonth ? "Revenue growth (12 mo)" : "Revenue growth", pct(valuation.observed_growth), [basis, quarter != null ? `Latest single quarter vs a year earlier: ${pct(quarter)}` : ""].filter(Boolean).join(" · ") || undefined],
    ["Consensus next year", pct(expectations.revenue_growth_next_year ?? valuation.consensus_next_year_growth), fiscalYearTitle(expectations.forward_fiscal_year_end)],
  ];
  return <dl className="jc-numbers">{items.map(([label, value, title]) => <div key={label} title={title}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function Legend() {
  return <div className="jc-legend" aria-label="Legend">{(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}<span className="jc-legend-dots"><i className="jc-dots"><b className="on" /><b className="on" /><b /></i>confidence</span></div>;
}

export function JudgmentCard({ ticker }: { ticker: string }) {
  const [card, setCard] = useState<Card | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    loadCompanyCard(ticker).then((result) => { if (!active) return; if (result.card) setCard(result.card as unknown as Card); else setError(result.error); });
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
    <PriceDriversPanel attribution={card.attribution} reading={card.price_reading} />
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
    <OperatingSignals operating={card.operating as Operating | undefined} />
    {card.contradictions.length || companyChanges(card).length ? <div className="jc-flags">
      {card.contradictions.map((item) => <span key={item} className="jc-flag tone-mixed"><em aria-hidden>!</em>{item}</span>)}
      {companyChanges(card).map((item) => <span key={item.axis} className="jc-flag"><em aria-hidden>↻</em>{AXIS_LABEL[item.axis] ?? item.axis}: {item.from} → {item.to}</span>)}
    </div> : null}
    <footer className="judgment-footer">
      <div className="jc-dates"><span><small>Next earnings</small><b>{earnings}</b></span><span><small>Next FOMC</small><b>{card.next_catalysts.fomc ?? "—"}</b></span></div>
      {card.falsification.length ? <details><summary>What would change the view</summary><ul>{card.falsification.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
      <details><summary>Missing inputs</summary><ul>{Object.entries(card.axes).flatMap(([name, axis]) => axis.missing.map((item) => <li key={`${name}-${item}`}>{AXIS_LABEL[name] ?? name}: {item}</li>))}</ul></details>
      <small>{card.disclaimer} Card generated {card.generated_on}.</small>
    </footer>
  </section>;
}
