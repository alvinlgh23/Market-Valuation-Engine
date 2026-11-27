// Cross-border channels traced to the watchlist (owner-approved 2026-11-27). Each channel is linked to the
// price-split factors it feeds; the holdings shown are those whose stored 3-month price split gives that factor a
// move of a point or more (the same threshold Today uses). A display mapping only: no reading or rule changes,
// and a channel is not proof that it caused a move.

// One factor family per channel (owner-approved 2026-11-27), so a holding is not counted under several channels.
export const CHANNEL_FACTORS: Record<string, string[]> = {
  "jp-us-yen-carry": ["yen_carry"],
  "us-jp-rate-fx": ["long_rates", "fed_path"],
  "us-eu-rate-fx": ["usd"],
  "us-kr-dollar-kospi": ["semis_cycle"],
};

/** The factors each modelled economy reaches your holdings through (same families as its channel). */
export const REGION_FACTORS: Record<string, string[]> = { US: ["long_rates", "fed_path"], JP: ["yen_carry"], EURO_AREA: ["usd"], KR: ["semis_cycle"] };

export const CHANNEL_CHAIN: Record<string, string[]> = {
  "jp-us-yen-carry": ["BOJ policy", "Japanese rates", "Yen funding", "Carry trade", "Global liquidity", "US risk assets"],
  "us-jp-rate-fx": ["Fed policy", "US rates", "Rate gap", "USD/JPY", "Japanese conditions"],
  "us-eu-rate-fx": ["Fed / ECB policy", "Rate gap", "EUR/USD", "Euro-area conditions"],
  "us-kr-dollar-kospi": ["US rates / dollar", "Capital flows", "USD/KRW", "KOSPI / chip exporters"],
};

export const EFFECT_THRESHOLD = 0.01;

export type DriverLike = { ticker: string; attribution?: { factor_labels?: Record<string, string>; windows?: Record<string, { macro_by_factor?: Record<string, number> }> } };
export type FactorExposure = { factor: string; label: string; holdings: Array<{ ticker: string; value: number }> };

/** Holdings whose 3-month price split gives any of these factors a move of a point or more. */
export function factorExposure(factors: string[], drivers: DriverLike[]): FactorExposure[] {
  const labels: Record<string, string> = {};
  for (const d of drivers) Object.assign(labels, d.attribution?.factor_labels ?? {});
  return factors.map((factor) => ({
    factor,
    label: labels[factor] ?? factor.replace(/_/g, " "),
    holdings: drivers
      .map((d) => ({ ticker: d.ticker, value: d.attribution?.windows?.["3M"]?.macro_by_factor?.[factor] }))
      .filter((h): h is { ticker: string; value: number } => typeof h.value === "number" && Number.isFinite(h.value) && Math.abs(h.value) >= EFFECT_THRESHOLD)
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
  }));
}

export function channelExposure(channelId: string, drivers: DriverLike[]): FactorExposure[] {
  return factorExposure(CHANNEL_FACTORS[channelId] ?? [], drivers);
}


/** Short line for the map's channel cards: the biggest measured effects, or that none reached a point. */
export function exposureLine(channelId: string, drivers: DriverLike[] | null): string {
  return factorsLine(CHANNEL_FACTORS[channelId] ?? [], drivers);
}

/** The same line for any list of factors (used by the economy cards). */
export function factorsLine(factors: string[], drivers: DriverLike[] | null): string {
  if (!drivers) return "Reading your holdings…";
  const all = factorExposure(factors, drivers).flatMap((f) => f.holdings.map((h) => ({ ...h, label: f.label })));
  if (!all.length) return "Moved none of your holdings by a point or more over 3 months.";
  const top = all.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).filter((h, i, list) => list.findIndex((x) => x.ticker === h.ticker) === i).slice(0, 3);
  return `Your holdings, 3 months: ${top.map((h) => `${h.ticker} ${h.value < 0 ? "−" : "+"}${Math.abs(h.value * 100).toFixed(1)}%`).join(" · ")}`;
}
