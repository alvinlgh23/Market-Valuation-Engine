// One shared request for the watchlist price attribution (checklists 10.3-10.5).
export type DriverRow = {
  ticker: string;
  reading?: { kind: string; label: string; short?: string };
  attribution?: { windows?: Record<string, { price_change?: number; macro_by_factor?: Record<string, number>; parts?: Record<string, number> }> };
};

let shared: Promise<DriverRow[]> | null = null;
export function loadWatchlistDrivers(): Promise<DriverRow[]> {
  shared ??= fetch("/api/research?action=watchlist-drivers", { cache: "no-store" })
    .then(async (response) => { const body = await response.json(); return Array.isArray(body.rows) ? (body.rows as DriverRow[]) : []; })
    .catch(() => { shared = null; return []; });
  return shared;
}
