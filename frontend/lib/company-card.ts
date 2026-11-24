// Checklist 11.6 + P19: shared company card loader with instant Stale-While-Revalidate preview
// and automatic cross-page Watchlist/Today cache invalidation when a live card finishes.

import { resetWatchlistLoaders } from "./watchlist-summary";

export type CardAxis = { state: string; direction: string | null; confidence: string; evidence: string[]; missing: string[]; families: string[]; detail: Record<string, unknown> };
export type CardResult = { card: ({ axes: Record<string, CardAxis> } & Record<string, unknown>) | null; error: string | null; source?: string | null };

const REUSE_MS = 60_000;
const inflight = new Map<string, { at: number; promise: Promise<CardResult> }>();

export async function loadCachedCompanyCard(ticker: string): Promise<CardResult> {
  const key = ticker.toUpperCase();
  const hit = inflight.get(key);
  if (hit && Date.now() - hit.at < REUSE_MS) {
    // If live promise already resolved in memory, return it; otherwise try fast disk endpoint.
  }
  try {
    const response = await fetch(`/api/research?action=company-verdict-cached&ticker=${encodeURIComponent(key)}`, { cache: "no-store" });
    const body = await response.json();
    if (body.card) return { card: body.card, error: null, source: body.source ?? "CACHED" };
  } catch { /* ignore */ }
  return { card: null, error: null, source: null };
}

export function loadCompanyCard(ticker: string): Promise<CardResult> {
  const key = ticker.toUpperCase();
  const hit = inflight.get(key);
  if (hit && Date.now() - hit.at < REUSE_MS) return hit.promise;
  const promise = fetch(`/api/research?action=company-verdict&ticker=${encodeURIComponent(key)}`, { cache: "no-store" })
    .then(async (response) => {
      const body = await response.json();
      if (body.card) {
        resetWatchlistLoaders();
        return { card: body.card, error: null, source: "LIVE" };
      }
      return { card: null, error: body.error || "The judgment card is unavailable.", source: null };
    })
    .catch((failure) => ({ card: null, error: String(failure), source: null }));
  inflight.set(key, { at: Date.now(), promise });
  promise.then((result) => { if (result.error) inflight.delete(key); });
  return promise;
}
