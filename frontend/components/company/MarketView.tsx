"use client";

import type { ReactNode } from "react";
import { DriverBar, PriceDriversLegend } from "./PriceDrivers";
import { concentration } from "../../lib/market-words";

// Market view (owner-approved 2026-11-27, was "Positioning"): how the market is treating the stock - the price split
// over 1 and 3 months, what analysts expect, sector money flow, crowding, and macro exposure against its measured
// effect. Everything is read from the stored judgment card; the only new text is two factual sentences (how much
// of the 3-month move came in the last month; estimates against price over the same three months).

type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === "object" && !Array.isArray(v) ? (v as Json) : {});
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const str = (v: unknown) => (typeof v === "string" && v.trim() ? v : null);
function pct(v: number | null, digits = 0, signed = true) {
  if (v == null) return "—";
  const r = Number((v * 100).toFixed(digits));
  if (r === 0) return `0%`;
  return `${r < 0 ? "−" : signed ? "+" : ""}${Math.abs(r).toFixed(digits)}%`;
}
const PARTS = [["macro", "Macro"], ["market", "Market"], ["sector", "Sector"], ["company", "Company"]] as const;

function Block({ n, title, aside, children }: { n: number; title: string; aside?: ReactNode; children: ReactNode }) {
  return <section className="mv-block"><header><span>{String(n).padStart(2, "0")}</span><h3>{title}</h3>{aside ? <small>{aside}</small> : null}</header>{children}</section>;
}

/** 0–100 history bar: where today's reading sits in its own record. */
function HistoryBar({ value, low, high, against = "low" }: { value: number | null; low: string; high: string; against?: "low" | "high" }) {
  if (value == null) return <p className="mv-na">No history stored</p>;
  const tone = (against === "low" ? value < 0.2 : value > 0.8) ? "against" : (against === "low" ? value > 0.8 : value < 0.2) ? "supportive" : "mixed";
  return <div className={`mv-hist tone-${tone}`}><div><i style={{ left: `${Math.max(1, Math.min(99, value * 100))}%` }} /></div><p><span>{low}</span><b>{Math.round(value * 100)} of 100</b><span>{high}</span></p></div>;
}

function Stat({ label, value, note, tone }: { label: string; value: ReactNode; note?: ReactNode; tone?: string }) {
  return <div className={`mv-stat${tone ? ` tone-${tone}` : ""}`}><span>{label}</span><b>{value}</b>{note ? <small>{note}</small> : null}</div>;
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;
function day(value: string | null) {
  if (!value || !ISO.test(value)) return value ?? "—";
  return new Date(`${value}T12:00:00Z`).toLocaleDateString("en-US", { day: "numeric", month: "short", timeZone: "UTC" });
}

function EpsLine({ trend }: { trend: Json }) {
  const keys = [["90daysAgo", "90d"], ["60daysAgo", "60d"], ["30daysAgo", "30d"], ["7daysAgo", "7d"], ["current", "Now"]] as const;
  const points = keys.map(([k, label]) => ({ label, v: num(trend[k]) }));
  const vals = points.map((p) => p.v).filter((v): v is number => v != null);
  if (vals.length < 2) return <p className="mv-na">No estimate history stored</p>;
  const lo = Math.min(...vals), hi = Math.max(...vals), w = 300, h = 84, pad = 10;
  const x = (i: number) => pad + (i / (points.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - lo) / (hi - lo || 1)) * (h - 2 * pad - 12);
  const path = points.map((p, i) => (p.v == null ? "" : `${i && points[i - 1].v != null ? "L" : "M"}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`)).join("");
  const up = vals[vals.length - 1] >= vals[0];
  return <svg viewBox={`0 0 ${w} ${h}`} className={`mv-eps ${up ? "up" : "down"}`} role="img" aria-label={`Next-year EPS estimate: ${points.map((p) => `${p.label} ${p.v ?? "—"}`).join(", ")}`}>
    <path d={path} />
    {points.map((p, i) => p.v == null ? null : <g key={p.label}><circle cx={x(i)} cy={y(p.v)} r={3} /><text x={x(i)} y={h - 2} textAnchor="middle">{p.label}</text><text x={x(i)} y={y(p.v) - 7} textAnchor="middle" className="mv-eps-v">{p.v.toFixed(2)}</text></g>)}
  </svg>;
}

export function MarketView({ card }: { card: Json | null }) {
  if (!card) return <p className="eng-empty">Loading the judgment card…</p>;
  const axes = obj(card.axes);
  const att = obj(card.attribution);
  const windows = obj(att.windows);
  const labels = obj(att.factor_labels);
  const w1 = obj(windows["1M"]), w3 = obj(windows["3M"]);
  const reading = obj(card.price_reading);
  const exp = obj(obj(axes.expectations).detail);
  const trend = obj(exp.eps_trend_next_year);
  const flow = obj(obj(axes.flow).detail);
  const sf = obj(flow.sector_flow);
  const crowd = obj(obj(axes.crowding).detail);
  const own = obj(crowd.valuation_in_own_history);
  const macro = obj(obj(axes.macro).detail);
  const tensions = arr(card.contradictions).map(String);
  const epsChange = num(trend.current) != null && num(trend["90daysAgo"]) ? num(trend.current)! / num(trend["90daysAgo"])! - 1 : null;
  const up = num(exp.revisions_up_30d), down = num(exp.revisions_down_30d);
  const r2 = num(obj(att.fit).r2);
  const etf = str(flow.sector_etf) ?? str(sf.etf) ?? "Sector";
  const rs21 = arr(flow.relative_strength_21_obs_ago);
  const measured = obj(w3.macro_by_factor);
  const exposures = arr(macro.exposures).map(obj);
  const curr = str(trend.currency) ?? "";
  const since = obj(obj(att.recent_move).since_window_end);
  const isBank = String(card.archetype ?? "") === "BANK";
  const today = new Date().toISOString().slice(0, 10);
  const nextEarnings = str(obj(card.next_catalysts).earnings);
  const lastEarnings = str(obj(card.next_catalysts).last_earnings);

  return <div className="mv">
    {tensions.length ? <section className="mv-tension" aria-label="Where the market and the business pull apart">
      <span>WHERE THE MARKET AND THE BUSINESS PULL APART</span>
      {tensions.map((t) => <p key={t}><i aria-hidden>!</i>{t}</p>)}
    </section> : <p className="mv-calm">No tension flagged between estimates, sector money flow and the price.</p>}

    <Block n={1} title="What moved the price" aside={<PriceDriversLegend />}>
      <div className="mv-windows">
        {([["1 month", w1], ["3 months", w3]] as const).map(([label, w]) => {
          const parts = obj(w.parts) as { macro: number; market: number; sector: number; company: number };
          return <div key={label} className="mv-window">
            <div className="mv-window-head"><span>{label}</span><b className={(num(w.price_change) ?? 0) < 0 ? "down" : "up"}>{pct(num(w.price_change), 1)}</b></div>
            <DriverBar parts={w.parts ? parts : undefined} />
            <div className="mv-parts">{PARTS.map(([k, l]) => <span key={k}><b className={`pd-seg pd-${k}`} />{l} <em>{pct(num(parts?.[k]), 1)}</em></span>)}</div>
            <ul className="mv-factors">{Object.entries(obj(w.macro_by_factor)).sort((a, b) => Math.abs(Number(b[1])) - Math.abs(Number(a[1]))).map(([id, v]) => {
              const value = Number(v);
              return <li key={id}><span>{str(labels[id]) ?? id}</span><i className={value < 0 ? "down" : "up"} style={{ width: `${Math.min(100, Math.abs(value) * 800)}%` }} /><b>{pct(value, 1)}</b></li>;
            })}</ul>
          </div>;
        })}
      </div>
      {concentration(num(w1.price_change), num(w3.price_change)) ? <p className="mv-sentence">To {day(str(att.as_of))}: {concentration(num(w1.price_change), num(w3.price_change))}</p> : null}
      {num(since.stock_change) != null ? <p className="mv-bridge">Since {day(str(since.from))} (to {day(str(since.to))}, not yet in the split): <b className={num(since.stock_change)! < 0 ? "down" : "up"}>{pct(num(since.stock_change), 1)}</b>, against {pct(num(since.spy_change), 1)} for the S&amp;P 500.</p> : null}
      <p className="mv-foot">Weekly regression on the market, an equal-weight sector basket and mapped macro factors{str(att.as_of) ? `, to ${att.as_of}` : ""}. {r2 != null ? `The model explains ${Math.round(r2 * 100)}% of this stock's weekly moves${r2 < 0.3 ? "; treat the split as rough" : ""}.` : ""}{str(reading.low_fit_note) && r2 == null ? ` ${reading.low_fit_note}` : ""}</p>
    </Block>

    <Block n={2} title="What analysts expect" aside={str(exp.forward_fiscal_year_end) ? `Next fiscal year, ending ${exp.forward_fiscal_year_end}` : undefined}>
      <div className="mv-two">
        <div>
          <p className="mv-label">Next-year earnings per share estimate{curr ? ` (${curr})` : ""}, last 90 days</p>
          <EpsLine trend={trend} />
        </div>
        <div className="mv-stats">
          <Stat label="Estimate change, 90 days" value={pct(epsChange, 1)} tone={epsChange == null ? undefined : epsChange > 0.01 ? "supportive" : epsChange < -0.01 ? "against" : "mixed"} />
          <Stat label="Revisions, 30 days" value={up != null ? `${up} up · ${down ?? 0} down` : "—"} note={up != null && up + (down ?? 0) > 0 ? <span className="mv-ratio"><i style={{ width: `${(up / (up + (down ?? 0))) * 100}%` }} /></span> : undefined} />
          <Stat label="Consensus sales growth, next year" value={pct(num(exp.revenue_growth_next_year), 1)} note={num(exp.analysts_next_year) != null ? `${exp.analysts_next_year} analysts` : undefined} />
          {nextEarnings && nextEarnings >= today ? <Stat label="Next earnings" value={day(nextEarnings)} /> : <Stat label="Last earnings" value={day(lastEarnings ?? str(exp.next_earnings_date))} note="next date not yet announced" />}
        </div>
      </div>
      {epsChange != null && num(w3.price_change) != null ? <p className="mv-sentence">Over about the same three months, the next-year estimate moved {pct(epsChange, 0)} (to today) and the price {pct(num(w3.price_change), 0)} (to {day(str(att.as_of))}{num(since.stock_change) != null ? `; not counting the ${pct(num(since.stock_change), 0)} since` : ""}).</p> : null}
      <p className="mv-foot">{str(exp.source) ?? "Yahoo Finance analyst estimates"}.</p>
    </Block>

    <Block n={3} title={`Is money coming into the sector? (${etf})`} aside={str(sf.as_of) ? `Sector measures to ${sf.as_of}` : undefined}>
      <div className="mv-two">
        <div>
          <p className="mv-label">{etf} against the S&amp;P 500 over one month: <b>{pct(num(flow.relative_strength), 1)}</b></p>
          <HistoryBar value={num(flow.percentile)} low="weakest on record" high="strongest" />
          <p className="mv-small">{num(flow.persistence_of_10) != null ? `The same reading on ${flow.persistence_of_10} of the last 10 days.` : ""} {rs21.length === 2 && num(rs21[1]) != null ? `A month earlier (${rs21[0]}): ${pct(num(rs21[1]), 1)}.` : ""}</p>
        </div>
        <div className="mv-stats">
          <Stat label="Top holdings above 50-day average" value={pct(num(sf.breadth_50), 0, false)} />
          <Stat label="Above 200-day average" value={pct(num(sf.breadth_200), 0, false)} />
          <Stat label="Trading value vs its record" value={num(sf.dollar_volume_percentile) != null ? `${Math.round(num(sf.dollar_volume_percentile)! * 100)} of 100` : "—"} note="higher = busier than usual" />
          <Stat label="Up / down volume, 20 days" value={num(sf.updown_volume_20d)?.toFixed(2) ?? "—"} note="below 1 = more selling volume" tone={num(sf.updown_volume_20d) == null ? undefined : num(sf.updown_volume_20d)! < 0.9 ? "against" : num(sf.updown_volume_20d)! > 1.1 ? "supportive" : "mixed"} />
          <Stat label="Company vs sector, 3 months" value={pct(num(flow.company_vs_sector_3m), 1)} />
        </div>
      </div>
      <p className="mv-foot">{str(sf.breadth_basis) ? `Breadth: ${sf.breadth_basis}. ` : ""}Not available: {arr(obj(axes.flow).missing).map(String).join("; ") || "—"}.</p>
    </Block>

    <Block n={4} title="Is the stock crowded?" aside={str(obj(axes.crowding).state) ?? undefined}>
      <div className="mv-two">
        <div>
          <p className="mv-label">Price-to-sales against its own history{num(own.current) != null ? `: ${num(own.current)!.toFixed(1)}` : ""}{str(own.first) ? ` (since ${String(own.first).slice(0, 4)})` : ""}</p>
          {own.state === "AVAILABLE" ? <HistoryBar value={num(own.percentile)} low="cheapest" high="most expensive" against="high" />
            : <p className="mv-na">{own.state === "CURRENCY_MISMATCH" ? `Not compared: ${str(own.reason) ?? "revenue and price are in different currencies"}` : str(own.reason) ?? "No price-to-sales history stored."}</p>}
          {isBank ? <p className="mv-small">For a bank, sales are mostly interest income, so price-to-sales is a rough guide; the Valuation tab reads the bank on price-to-book and return on equity.</p> : null}
          {own.state === "AVAILABLE" && str(own.note) ? <p className="mv-small">{String(own.note)}</p> : null}
        </div>
        <div className="mv-stats">
          <Stat label="From 50-day average" value={pct(num(crowd.dist_50), 1)} />
          <Stat label="From 200-day average" value={pct(num(crowd.dist_200), 1)} />
          <Stat label="RSI (14 days)" value={num(crowd.rsi)?.toFixed(0) ?? "—"} note="above 70 stretched · below 30 washed out" />
          <Stat label="Six-month change" value={pct(num(crowd.six_month), 1)} />
        </div>
      </div>
      <p className="mv-foot">Not available: {arr(obj(axes.crowding).missing).map(String).join("; ") || "—"}.</p>
    </Block>

    <Block n={5} title="Macro: expected exposure against what it did" aside="Last 3 months">
      {exposures.length ? <table className="mv-table">
        <thead><tr><th>Factor</th><th>Now</th><th>Expected effect</th><th>Measured, 3 months</th></tr></thead>
        <tbody>{exposures.map((e) => {
          const effect = num(e.effect);
          const m = num(measured[String(e.factor)]);
          return <tr key={String(e.factor)} title={str(e.mechanism) ?? undefined}>
            <td>{str(e.label)}</td>
            <td>{str(e.factor_state)}</td>
            {e.weight === "context" ? <td>Context only <small>not counted in the reading</small></td>
              : <td className={effect == null || effect === 0 ? "" : effect < 0 ? "down" : "up"}>{effect == null || effect === 0 ? "Neutral" : effect < 0 ? "Headwind" : "Tailwind"} <small>{e.validation === "CONFIRMED" ? "confirmed" : "unconfirmed"}</small></td>}
            <td className={m == null ? "" : m < 0 ? "down" : "up"}>{m == null ? <small>{e.weight === "context" ? "Context only (not in price split)" : "not in the price split"}</small> : pct(m, 1)}</td>
          </tr>;
        })}</tbody>
      </table> : <p className="mv-na">No macro exposure mapped for this business.</p>}
      <p className="mv-foot">Expected effect from the business mapping (confirmed = it passed our historical check); measured from the 3-month price split. Hover a row for the mechanism. {arr(macro.context_only).map(String).join(" ")}</p>
    </Block>

    <p className="mv-foot mv-end">A description of how the market is treating the stock, not a forecast or a recommendation.</p>
  </div>;
}
