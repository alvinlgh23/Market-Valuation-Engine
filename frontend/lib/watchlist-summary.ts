// One shared request for the watchlist's last recorded card states (history only, no network).
export type SummaryRow = { ticker: string; last_card: string | null; axes: Record<string, string>; changed: Array<{ axis: string; from: string; to: string; on: string }> };

let shared: Promise<SummaryRow[]> | null = null;
export function loadWatchlistSummary(): Promise<SummaryRow[]> {
  shared ??= fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
    .then(async (response) => { const body = await response.json(); return Array.isArray(body.rows) ? (body.rows as SummaryRow[]) : []; })
    .catch(() => { shared = null; return []; });
  return shared;
}
