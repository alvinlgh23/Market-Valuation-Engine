// Plain-fact headlines and gap-bar inputs shared by Today, the company page and the watchlist (design system v2).
// The headline is the card's own business phrase plus the stored 3-month price move; nothing is judged here.

type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === "object" && !Array.isArray(v) ? (v as Json) : {});
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);

export function factHeadline(business: string | null | undefined, move3m: number | null | undefined): string {
  const lead = business ?? "Business reading unavailable";
  if (move3m == null) return `${lead}.`;
  const size = Math.round(Math.abs(move3m) * 100);
  return `${lead}. ${size === 0 ? "The price is flat" : `The price ${move3m < 0 ? "fell" : "rose"} ${size}%`} in 3 months.`;
}

/** Gap-bar input from a stored judgment card's valuation axis. */
export function gapFromCard(card: Json) {
  const axis = obj(obj(card.axes).valuation);
  const v = obj(axis.detail), band = obj(v.growth_band), bank = obj(v.bank_implied_roe);
  const refs = [num(band.consensus_2y_faded), num(band.history_3y_faded)].filter((x): x is number => x != null).sort((a, b) => a - b);
  return {
    implied: num(v.implied_5y_revenue_cagr), refLow: refs[0] ?? null, refHigh: refs[refs.length - 1] ?? null,
    impliedRoe: num(bank.implied_roe), latestRoe: num(bank.latest_roe), priceToMax: num(v.price_to_max_case),
    valuationState: typeof axis.state === "string" ? axis.state : null,
  };
}
