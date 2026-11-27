import { axisTone } from "./judgment-tone.mjs";
import type { CompareNumbers, TodayHolding } from "./today-model";

// Watchlist Compare (owner-approved 2026-11-27, replaces the 6-axis matrix): the watchlist side by side by number,
// sortable. Each number comes from the stored card; its dot is the card's own reading on that axis (green = works
// for the company, red = against, amber = mixed). No new reading, no score.

export type Tone = "supportive" | "against" | "mixed" | "unknown";
export type Cell = { text: string; sub?: string | null; tone: Tone | null; sign?: number | null };
export type Column = {
  key: string;
  label: string;
  hint: string;
  axis: string | null;
  sort: (c: CompareNumbers) => number | null;
  cell: (c: CompareNumbers, h: TodayHolding) => Cell;
};

export function pct(v: number | null | undefined, digits = 0, signed = true): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const r = Number((v * 100).toFixed(digits));
  if (r === 0) return "0%";
  return `${r < 0 ? "−" : signed ? "+" : ""}${Math.abs(r).toFixed(digits)}%`;
}

const tone = (axis: string, c: CompareNumbers): Tone => axisTone(axis, c.states[axis] ?? "") as Tone;

/** Price column sort value: how far what the price assumes sits above (+) or below (−) what the business shows.
 *  Above the model's best case sorts beyond everything; banks compare implied with earned return on equity. */
export function priceGap(c: CompareNumbers): number | null {
  if (c.implied != null && c.refLow != null && c.refHigh != null) return c.implied - (c.refLow + c.refHigh) / 2;
  if (c.impliedRoe != null && c.latestRoe != null) return c.impliedRoe - c.latestRoe;
  if (c.priceToMax != null && /model can reach/i.test(c.states.valuation ?? "")) return 10 + c.priceToMax;
  return null;
}

export const COLUMNS: Column[] = [
  {
    key: "price", label: "Price assumes", axis: "valuation",
    hint: "Five-year sales growth today's price requires (reverse DCF) against what analysts' and past growth show once faded. Banks: return on equity the price assumes against what the bank earns. Sorts by the gap.",
    sort: priceGap,
    cell: (c) => {
      if (c.implied != null) return { text: `${pct(c.implied)}/yr`, sub: c.refLow != null ? `shows ${pct(c.refLow)}${c.refHigh != null && Math.abs(c.refHigh - c.refLow) >= 0.005 ? ` to ${pct(c.refHigh)}` : ""}` : null, tone: tone("valuation", c) };
      if (c.impliedRoe != null) return { text: `ROE ${pct(c.impliedRoe, 1, false)}`, sub: c.latestRoe != null ? `earns ${pct(c.latestRoe, 1, false)}` : null, tone: tone("valuation", c) };
      if (c.priceToMax != null && /model can reach/i.test(c.states.valuation ?? "")) return { text: `${c.priceToMax.toFixed(1)}× best case`, sub: "above the model's reach", tone: tone("valuation", c) };
      return { text: "No single reading", sub: c.states.valuation && /cash-flow/i.test(c.states.valuation) ? "depends on cash-flow measure" : null, tone: tone("valuation", c) };
    },
  },
  {
    key: "move", label: "3-month move", axis: null,
    hint: "Share price change over the three months to the last weekly close; below it, the move since then (not yet in the price split).",
    sort: (c) => c.move3m,
    cell: (c, h) => ({ text: pct(c.move3m), sub: h.since?.stock != null ? `${pct(h.since.stock)} since` : null, tone: null, sign: c.move3m }),
  },
  {
    key: "macro", label: "Macro effect, 3M", axis: "macro",
    hint: "The part of the 3-month move the price split gives to mapped macro factors. Dot: the card's macro reading.",
    sort: (c) => c.macroPart,
    cell: (c) => ({ text: pct(c.macroPart, 1), tone: tone("macro", c), sign: c.macroPart }),
  },
  {
    key: "eps", label: "EPS estimate, 90d", axis: "expectations",
    hint: "Change in the consensus next-year earnings-per-share estimate over 90 days; below it, 30-day revisions up and down.",
    sort: (c) => c.eps90,
    cell: (c) => ({ text: pct(c.eps90, 1), sub: c.revUp != null ? `${c.revUp} up · ${c.revDown ?? 0} down` : null, tone: tone("expectations", c), sign: c.eps90 }),
  },
  {
    key: "sales", label: "Latest quarter sales", axis: "fundamentals",
    hint: "Sales in the latest reported quarter against the same quarter a year earlier. Dot: the card's fundamentals reading.",
    sort: (c) => c.qSales,
    cell: (c) => (c.qSales == null ? { text: "—", sub: "not in the quarterly read", tone: null } : { text: pct(c.qSales), sub: "vs a year earlier", tone: tone("fundamentals", c), sign: c.qSales }),
  },
  {
    key: "sector", label: "Sector vs S&P, 1M", axis: "flow",
    hint: "The company's sector ETF against the S&P 500 over one month. Dot: the card's money-flow reading.",
    sort: (c) => c.sectorRel,
    cell: (c) => ({ text: pct(c.sectorRel, 1), sub: c.sectorEtf, tone: tone("flow", c), sign: c.sectorRel }),
  },
  {
    key: "ma200", label: "From 200-day avg", axis: "crowding",
    hint: "How far the price is above or below its 200-day average. Dot: the card's crowding reading.",
    sort: (c) => c.dist200,
    cell: (c) => ({ text: pct(c.dist200), tone: tone("crowding", c), sign: c.dist200 }),
  },
  {
    key: "ps", label: "P/S vs own history", axis: "crowding",
    hint: "Where today's price-to-sales sits in the company's own record since 2023 (0 = cheapest, 100 = most expensive).",
    sort: (c) => c.psPercentile,
    cell: (c) => c.psPercentile != null
      ? { text: `${Math.round(c.psPercentile * 100)} of 100`, sub: c.psPercentile <= 0.1 ? "near its cheapest" : c.psPercentile >= 0.9 ? "near its dearest" : null, tone: c.psPercentile >= 0.8 ? "against" : c.psPercentile <= 0.2 ? "supportive" : "mixed" }
      : { text: "—", sub: c.psState === "CURRENCY_MISMATCH" ? "currencies differ" : null, tone: null },
  },
];

/** Sort holdings by a column; missing values always go last, whichever direction. */
export function sortHoldings(holdings: TodayHolding[], key: string, direction: 1 | -1): TodayHolding[] {
  const column = COLUMNS.find((c) => c.key === key);
  if (!column) return holdings;
  return [...holdings].sort((a, b) => {
    const va = a.compare ? column.sort(a.compare) : null, vb = b.compare ? column.sort(b.compare) : null;
    if (va == null && vb == null) return a.ticker.localeCompare(b.ticker);
    if (va == null) return 1;
    if (vb == null) return -1;
    return (va - vb) * direction || a.ticker.localeCompare(b.ticker);
  });
}
