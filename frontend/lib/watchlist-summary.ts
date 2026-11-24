// One shared request for the watchlist's last recorded card states (history only, no network).
export type SummaryRow = { ticker: string; last_card: string | null; axes: Record<string, string>; price_to_max_case?: number | null; changed: Array<{ axis: string; from: string; to: string; on: string; origin?: "COMPANY" | "RULES" | "UNKNOWN" }> };

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
