"use client";
import { useEffect, useState } from "react";
import { loadCachedCompanyCard, loadCompanyCard } from "../../lib/company-card";
import { fairValueCoordinates } from "../../lib/fair-value-scale.mjs";
import { historyLabel, versusHistory } from "../../lib/plain-words.mjs";
import { OperatingSignals, type Operating } from "./StoredProfileReads";
import { axisTone, confidenceDots, percentileWidth, TONE_GLYPH, TONE_LABEL, type Tone } from "../../lib/judgment-tone.mjs";
import { PriceDriversPanel, type Attribution, type PriceReading } from "./PriceDrivers";

type Axis = { state: string; direction: string | null; confidence: string; evidence: string[]; missing: string[]; families: string[]; detail: Record<string, unknown>; driver_note?: string };
type Card = {
  ticker: string; name: string; archetype: string; sector_etf: string | null; generated_on: string;
  axes: Record<string, Axis>;
  horizons: Record<string, { window: string; context?: string; axes: string[] }>;
  contradictions: string[]; changes: Array<{ axis: string; from: string; to: string; since: string; origin?: string }>; falsification: string[]; operating?: unknown; conclusion?: unknown; valuation_record?: unknown;
  next_catalysts: { earnings: string | null; last_earnings?: string | null; fomc: string | null };
  disclaimer: string;
  attribution?: Attribution; price_reading?: PriceReading;
};

const AXIS_LABEL: Record<string, string> = { macro: "Macro", flow: "Money flow", valuation: "Valuation", crowding: "Crowding", expectations: "Expectations", fundamentals: "Fundamentals" };
const HORIZON_LABEL: Record<string, string> = { tactical: "1–3 months", cyclical: "6–12 months", structural: "3–5 years" };
const ETF_NAME: Record<string, string> = {
  XLK: "Technology (XLK)", XLC: "Communication (XLC)", XLY: "Discretionary (XLY)", XLP: "Staples (XLP)",
  XLV: "Health care (XLV)", XLF: "Financials (XLF)", XLE: "Energy (XLE)", XLI: "Industrials (XLI)",
  XLB: "Materials (XLB)", XLU: "Utilities (XLU)", XLRE: "Real estate (XLRE)", SMH: "Semis (SMH)",
  IGV: "Software (IGV)", XBI: "Biotech (XBI)", KBE: "Banks (KBE)", XRT: "Retail (XRT)"
};

function num(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function money(value: unknown) {
  const n = num(value);
  if (n == null) return "—";
  const sign = n < 0 ? "−" : "";
  const abs = Math.abs(n);
  return `${sign}$${abs.toLocaleString("en-US", { maximumFractionDigits: abs >= 100 ? 0 : 2 })}`;
}
function pct(value: unknown, digits = 1) {
  const n = num(value);
  if (n == null) return "—";
  const rounded = Number((n * 100).toFixed(digits));
  if (rounded === 0) return digits > 0 ? `0.${"0".repeat(digits)}%` : "0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(digits)}%`;
}
function companyChanges(card: { changes: Array<{ axis: string; from: string; to: string; origin?: string }> }) { return card.changes.filter((item) => item.origin === "COMPANY"); }
function words(value: unknown) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\bai\b/g, "AI")
    .replace(/\bsaas\b/g, "SaaS")
    .replace(/^\w/, (c) => c.toUpperCase());
}
function obj(value: unknown) { return (value && typeof value === "object" ? value : {}) as Record<string, unknown>; }
function sectorDisplay(etf: unknown) {
  const code = String(etf ?? "");
  return ETF_NAME[code] ?? (code || "Sector");
}

function PercentileBar({ label, value, note, highIsAgainst = false, period }: { label: string; value: unknown; note?: string; highIsAgainst?: boolean; period: string }) {
  const width = percentileWidth(value);
  if (width == null) return null;
  return <div className="jc-bar" title={[note, versusHistory(value, period)].filter(Boolean).join(" ")}>
    <span>{label}</span>
    <div className={`jc-bar-track${highIsAgainst ? " reverse" : ""}`}><i style={{ left: `${width}%` }} /></div>
    <b>{historyLabel(value, highIsAgainst ? "price" : "strength")}</b>
  </div>;
}

function Chip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`jc-chip tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{children}</span>;
}

function AxisVisual({ name, axis }: { name: string; axis: Axis }) {
  const detail = axis.detail;
  if (name === "flow") return <PercentileBar label={`${sectorDisplay(detail.sector_etf)} vs S&P 500`} value={detail.percentile} note="How the sector did against the S&P 500 over one month, compared with its own record." period="its stored record" />;
  if (name === "crowding") {
    const own = obj(detail.valuation_in_own_history);
    return <PercentileBar label="P/S vs own history" value={own.state === "AVAILABLE" ? own.percentile : null} highIsAgainst note="Price-to-sales compared with the company's own history; higher is more expensive." period="its own history" />;
  }
  if (name === "macro") {
    const rows = Array.isArray(detail.exposures) ? (detail.exposures as Array<Record<string, unknown>>) : [];
    const shown = rows.filter((row) => row.factor_state && row.effect !== 0);
    if (!shown.length) return null;
    return <div className="jc-chips">{shown.map((row) => {
      const isContext = row.weight === "context";
      const isUnconfirmed = row.weight === "unconfirmed";
      const chipTone: Tone = isContext || isUnconfirmed ? "unknown" : Number(row.effect) > 0 ? "supportive" : "against";
      const suffix = isContext ? " · context" : isUnconfirmed ? " · unconfirmed" : "";
      const tip = isContext
        ? "Moved prices, but not counted as a forecast: high readings preceded better returns in the scorecard."
        : isUnconfirmed
          ? "Tracked in historical price attribution above, but did not hold consistently enough over five years to count as a forward tailwind or headwind."
          : undefined;
      return <span key={String(row.factor)} title={tip}><Chip tone={chipTone}>{String(row.label)}: {String(row.factor_state).toLowerCase()}{suffix}</Chip></span>;
    })}</div>;
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
    const quarter = obj(detail.quarterly);
    if (quarter.status === "AVAILABLE") {
      const health = obj(quarter.health);
      const signed = (value: unknown, scale = 100, unit = "%") => {
        if (typeof value !== "number" || !Number.isFinite(value)) return null;
        const digits = unit === "%" ? 0 : 1;
        const rounded = Number((value * scale).toFixed(digits));
        if (rounded === 0) return `0${unit}`;
        return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(digits)}${unit}`;
      };
      const chips: Array<[string, Tone, string]> = [];
      const growth = signed(quarter.revenue_yoy);
      if (growth) chips.push([`Sales ${growth}`, Number(quarter.revenue_yoy) >= 0 ? "supportive" : "against", "Sales against the same quarter a year earlier"]);
      const margin = signed(quarter.margin_change, 100, " pts");
      if (margin) chips.push([`Margin ${margin}`, Number(quarter.margin_change) > 0.01 ? "supportive" : Number(quarter.margin_change) < -0.01 ? "against" : "mixed", "Operating margin against a year earlier"]);
      const beat = signed(quarter.eps_surprise);
      if (beat && quarter.eps_surprise_outsized) chips.push([`EPS vs forecast ${beat}`, "mixed", "A gap this large usually comes from a one-off item; check the filing before reading it as the business"]);
      else if (beat) chips.push([`EPS vs forecast ${beat}`, Number(quarter.eps_surprise) >= 0 ? "supportive" : "against", "Earnings per share against the analysts' forecast"]);
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
    const stretch = num(detail.price_to_max_case);
    const fair = obj(detail.fair_value);
    const price = num(detail.price);
    const bull = num(fair.bull);
    if (implied == null && stretch != null) {
      const withinBull = price != null && bull != null && price <= bull;
      return <div className="jc-compare" title="Share price divided by the value 50% first-year sales growth justifies when base margin and WACC stay fixed. The Bull scenario in the range bar above also widens margins and lowers WACC.">
        <div><span>Price vs 50%-growth cap</span><i style={{ width: `${Math.min(100, (stretch / 4) * 100)}%` }} /><b>{stretch.toFixed(1)}x</b></div>
        {withinBull ? <small className="jc-val-clarify">At fixed base margin &amp; WACC, 50% Y1 growth reaches {money(price / stretch)}; reaching {money(price)} requires bull-case margins or lower WACC (up to {money(bull)}).</small> : null}
      </div>;
    }
    const band = obj(detail.growth_band);
    const rows: Array<[string, number | null]> = band.consensus_2y != null || band.history_3y != null
      ? band.consensus_2y_faded != null || band.history_3y_faded != null
        // Checklist 20.3: the references the reading actually uses, faded to five years.
        ? [["Priced in, 5 yrs", implied], ["Analysts, faded to 5 yrs", num(band.consensus_2y_faded)], ["Past growth, faded", num(band.history_3y_faded)]]
        : [["Priced in, 5 yrs", implied], ["Analysts, 2 yrs", num(band.consensus_2y)], ["Last 3 yrs", num(band.history_3y)]]
      : [["Priced in", implied], ["Consensus", num(detail.consensus_next_year_growth) ?? num(detail.observed_growth)]];
    if (implied == null || rows.slice(1).every(([, value]) => value == null)) return null;
    const top = Math.max(...rows.map(([, value]) => value ?? 0), 0.01);
    return <div className="jc-compare" title="Yearly sales growth the share price assumes for five years, against analysts' two-year forecast and the last three years, each faded in a straight line to 2.5% by year five. More than 5 points above both reads priced high; more than 5 points below both, priced low.">
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
    {typeof axis.driver_note === "string" ? <p className="jc-axis-note">{axis.driver_note}</p> : null}
    {axis.evidence.length ? <details><summary>Why</summary>{axis.evidence.filter((line) => line !== axis.driver_note).map((line) => <p key={line}>{line}</p>)}</details> : null}
  </div>;
}

/** Bear / base / bull with today's price, clamping extreme outliers (e.g. TSLA) so labels never collide. */
function ValueRange({ card }: { card: Card }) {
  const detail = card.axes.valuation?.detail ?? {};
  const fair = obj(detail.fair_value);
  const price = num(detail.price);
  const values = { bear: num(fair.bear), base: num(fair.base), bull: num(fair.bull), market: price };
  const scale = fairValueCoordinates(values);
  const bank = obj(detail.bank_implied_roe);
  if (num(bank.implied_roe) != null && num(bank.latest_roe) != null) return <div className="jc-range jc-range-empty"><span>Price-implied ROE</span><b>{((num(bank.implied_roe) ?? 0) * 100).toFixed(1)}%</b><small>Earns {((num(bank.latest_roe) ?? 0) * 100).toFixed(1)}% · price-to-book {(num(bank.price_to_book) ?? 0).toFixed(2)}</small></div>;
  if (!scale.valid) return <div className="jc-range jc-range-empty"><span>Model value</span><b>Withheld</b><small>{card.axes.valuation?.missing?.[0] ?? card.axes.valuation?.state}</small></div>;
  const weight = num(detail.ten_year_weight);
  const compressed = price != null && values.bull != null && values.bear != null && (scale.positions.bull - scale.positions.bear < 24);
  if (compressed && values.bear != null && values.base != null && values.bull != null && price != null) {
    const modelSpan = Math.max(values.bull - values.bear, 1e-6);
    const pos = (v: number) => 8 + ((v - values.bear!) / modelSpan) * 52;
    const mult = values.bull > 0 ? (price / values.bull).toFixed(1) : null;
    return <div className="jc-range jc-range-outlier" aria-label="Model value range against price">
      <span>Model value {weight ? <small>({Math.round(weight * 100)}% ten-year model)</small> : null}</span>
      <div className="jc-range-track">
        <div className="jc-range-band" style={{ left: "8%", width: "52%" }} />
        {(["bear", "base", "bull"] as const).map((key) => <i key={key} className={`jc-range-tick ${key}`} style={{ left: `${pos(values[key]!)}%` }}><b>{money(values[key])}</b><small>{key}</small></i>)}
        <i className="jc-range-price jc-price-offscale" style={{ left: "88%" }}><b>Price {money(price)}{mult ? ` (${mult}× bull)` : ""} →</b></i>
      </div>
    </div>;
  }
  return <div className="jc-range" aria-label="Model value range against price">
    <span>Model value {weight ? <small>({Math.round(weight * 100)}% ten-year model)</small> : null}</span>
    <div className="jc-range-track">
      <div className="jc-range-band" style={{ left: `${scale.positions.bear}%`, width: `${scale.positions.bull - scale.positions.bear}%` }} />
      {(["bear", "base", "bull"] as const).map((key) => <i key={key} className={`jc-range-tick ${key}`} style={{ left: `${scale.positions[key]}%` }}><b>{money(values[key])}</b><small>{key}</small></i>)}
      {price != null ? <i className="jc-range-price" style={{ left: `${scale.positions.market}%` }}><b>Price {money(price)}</b></i> : null}
    </div>
  </div>;
}

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

// Checklist 20.1: what the data says, in plain sentences, before the detail.
type Conclusion = { sentences: string[]; business: string; agreement: string; note: string };
const AGREEMENT_LABEL: Record<string, string> = { OPPOSED: "Price and business disagree", LEANS_OPPOSED: "Leans against business", LEANS_ALIGNED: "Leans with business", ALIGNED: "Price and business agree", OUTSIDE: "Moved with outside forces", UNCLEAR: "" };
// P20 item 5: whether readings like this one have been followed by better or worse returns - or that it is not tested yet.
type ValuationRecord = { status: "TESTED" | "NOT_TESTED"; group: string; meaning: string; text: string; as_of?: string };
function DataConclusion({ conclusion, record }: { conclusion?: Conclusion; record?: ValuationRecord | null }) {
  if (!conclusion?.sentences?.length) return null;
  const label = AGREEMENT_LABEL[conclusion.agreement] ?? "";
  return <section className={`jc-conclusion agree-${conclusion.agreement.toLowerCase()}`} aria-label="What the data says">
    <header><h3>What the data says</h3>{label ? <span className="jc-agreement">{label}</span> : null}</header>
    <p>{conclusion.sentences.join(" ")}</p>
    {record ? <p className={`jc-record is-${record.status.toLowerCase()}`} title={`Group: ${record.meaning}`}><b>{record.status === "TESTED" ? "Track record" : "Not tested yet"}</b>{" "}{record.text.replace(/^Not tested yet\. /, "")}</p> : null}
    <small>{conclusion.note}</small>
  </section>;
}

export function JudgmentCard({ ticker }: { ticker: string }) {
  return <JudgmentCardBody key={ticker} ticker={ticker} />;
}

function JudgmentCardBody({ ticker }: { ticker: string }) {
  const [card, setCard] = useState<Card | null>(null);
  const [refreshing, setRefreshing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    // 1. Instant (<20ms) saved card preview so the user never stares at a blank 15-second skeleton.
    loadCachedCompanyCard(ticker).then((cached) => {
      if (!active || !cached.card) return;
      setCard((prev) => prev ?? (cached.card as unknown as Card));
    });
    // 2. Live card verification / refresh in background.
    loadCompanyCard(ticker).then((result) => {
      if (!active) return;
      setRefreshing(false);
      if (result.card) setCard(result.card as unknown as Card);
      else setCard((prev) => { if (!prev) setError(result.error); return prev; });
    });
    return () => { active = false; };
  }, [ticker]);

  if (error && !card) return <section className="judgment-card judgment-card-empty" aria-label="Judgment card"><p>Judgment card unavailable: {error}</p></section>;
  if (!card) return <section className="judgment-card judgment-card-empty" aria-label="Judgment card" aria-busy="true"><div className="jc-skeleton" /><p>Building the judgment card from live company data…</p></section>;
  const earnings = card.next_catalysts.earnings ?? (card.next_catalysts.last_earnings ? `not yet set (last ${card.next_catalysts.last_earnings})` : "—");
  const hasHeadlineNumbers = num(card.axes.valuation?.detail?.price) != null;

  return <section className="judgment-card" aria-label="Judgment card">
    <div className="jc-top">
      <span className="jc-type">
        {words(card.archetype)}{card.sector_etf ? ` · ${sectorDisplay(card.sector_etf)}` : ""}
        {refreshing ? <small className="jc-sync-pill"> · Updating live quotes &amp; filings…</small> : null}
      </span>
      <Legend />
    </div>
    <DataConclusion conclusion={card.conclusion as Conclusion | undefined} record={card.valuation_record as ValuationRecord | null | undefined} />
    <PriceDriversPanel attribution={card.attribution} reading={card.price_reading} lastEarnings={card.next_catalysts.last_earnings} />
    {hasHeadlineNumbers || !refreshing ? (
      <div className="jc-headline">
        <NumberStrip card={card} />
        <ValueRange card={card} />
      </div>
    ) : null}
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
      {card.falsification.length ? <details open className="jc-change"><summary>What would change the view</summary><ul>{card.falsification.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
      <details><summary>Missing inputs</summary><ul>{Object.entries(card.axes).flatMap(([name, axis]) => axis.missing.map((item) => <li key={`${name}-${item}`}>{AXIS_LABEL[name] ?? name}: {item}</li>))}</ul></details>
      <small>{card.disclaimer} Card generated {card.generated_on}.</small>
    </footer>
  </section>;
}
