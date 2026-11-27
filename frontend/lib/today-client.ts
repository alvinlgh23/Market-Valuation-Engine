import type { TodayPayload } from "./today-model";

// One shared request for the per-holding read of the stored cards (Today and the Watchlist Compare table).
let shared: Promise<TodayPayload | null> | null = null;
export function loadTodayHoldings(): Promise<TodayPayload | null> {
  shared ??= fetch("/api/research?action=watchlist-today", { cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<TodayPayload>) : null))
    .catch(() => null)
    .then((d) => { if (!d) shared = null; return d; });
  return shared;
}
export function resetTodayHoldings() { shared = null; }
