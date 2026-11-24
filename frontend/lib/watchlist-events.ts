// Checklist 18.14: scheduled events for the watchlist (next earnings dates, next FOMC decision).
export type WatchlistEvents = { date?: string; earnings: Array<{ ticker: string; date: string | null }>; fomc?: { date: string | null } };

let shared: Promise<WatchlistEvents> | null = null;
export function loadWatchlistEvents(): Promise<WatchlistEvents> {
  shared ??= fetch("/api/research?action=watchlist-events", { cache: "no-store" })
    .then(async (response) => { const body = await response.json(); return { earnings: Array.isArray(body.earnings) ? body.earnings : [], fomc: body.fomc, date: body.date }; })
    .catch(() => { shared = null; return { earnings: [] }; });
  return shared;
}
export function resetWatchlistEvents() { shared = null; }
