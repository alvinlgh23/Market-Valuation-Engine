// Checklist 11.6: one request for the judgment card, shared by the card and the stored-profile summary
// below it (which reads the card's live valuation instead of the stored profile's). Reused for a minute.

export type CardAxis = { state: string; direction: string | null; confidence: string; evidence: string[]; missing: string[]; families: string[]; detail: Record<string, unknown> };
export type CardResult = { card: { axes: Record<string, CardAxis> } & Record<string, unknown> | null; error: string | null };

const REUSE_MS = 60_000;
const inflight = new Map<string, { at: number; promise: Promise<CardResult> }>();

export function loadCompanyCard(ticker: string): Promise<CardResult> {
  const key = ticker.toUpperCase();
  const hit = inflight.get(key);
  if (hit && Date.now() - hit.at < REUSE_MS) return hit.promise;
  const promise = fetch(`/api/research?action=company-verdict&ticker=${encodeURIComponent(key)}`, { cache: "no-store" })
    .then(async (response) => {
      const body = await response.json();
      return body.card ? { card: body.card, error: null } : { card: null, error: body.error || "The judgment card is unavailable." };
    })
    .catch((failure) => ({ card: null, error: String(failure) }));
  inflight.set(key, { at: Date.now(), promise });
  promise.then((result) => { if (result.error) inflight.delete(key); });
  return promise;
}
