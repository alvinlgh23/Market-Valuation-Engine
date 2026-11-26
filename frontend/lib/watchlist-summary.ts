// One shared request for the watchlist's last recorded card states (history only, no network).
export type WatchlistValuationDetail = {
  price: number | null;
  bear: number | null;
  base: number | null;
  bull: number | null;
  price_to_max_case?: number | null;
  implied_roe?: number | null;
  latest_roe?: number | null;
  currency?: string;
  implied_growth?: number | null;
  reference_low?: number | null;
  reference_high?: number | null;
};

export type SummaryRow = {
  ticker: string;
  name?: string | null;
  last_card: string | null;
  axes: Record<string, string>;
  price_to_max_case?: number | null;
  latest_price?: number | null;
  valuation_detail?: WatchlistValuationDetail | null;
  operating_constraint?: string | null;
  conclusion?: { agreement: "OPPOSED" | "ALIGNED" | "OUTSIDE" | "UNCLEAR"; business: string; card_date?: string | null;
                 short?: { business: string | null; price: string | null; value: string | null } | null } | null;
  changed: Array<{ axis: string; from: string; to: string; on: string; origin?: "COMPANY" | "RULES" | "UNKNOWN" }>;
};

let shared: Promise<SummaryRow[]> | null = null;
export function loadWatchlistSummary(): Promise<SummaryRow[]> {
  shared ??= fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
    .then(async (response) => { const body = await response.json(); return Array.isArray(body.rows) ? (body.rows as SummaryRow[]) : []; })
    .catch(() => { shared = null; return []; });
  return shared;
}

// Checklist 18.11: one set of card axes, in one order, with one set of names, on Today and the watchlist.
export const CARD_AXES: ReadonlyArray<readonly [string, string]> = [["flow", "Money flow"], ["crowding", "Crowding"], ["macro", "Macro"], ["expectations", "Estimates"], ["fundamentals", "Fundamentals"], ["valuation", "Valuation"]];

/** Checklist 18.16: the short cell label, with the stretch above the ceiling when it is known. */
export function cellLabel(short: string, axis: string, row: { price_to_max_case?: number | null }) {
  return axis === "valuation" && short === "Beyond model" && typeof row.price_to_max_case === "number" ? `Beyond model · ${row.price_to_max_case.toFixed(1)}x` : short;
}

/** After the list changes, the next read fetches it again (summary, drivers and events). */
export function resetWatchlistLoaders() {
  shared = null;
  void import("./watchlist-drivers").then((module) => module.resetWatchlistDrivers?.());
  void import("./watchlist-events").then((module) => module.resetWatchlistEvents());
}
