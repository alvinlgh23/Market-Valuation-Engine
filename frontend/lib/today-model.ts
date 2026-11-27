import { axisTone } from "./judgment-tone.mjs";

// Today, rebuilt around exceptions (owner-approved 2026-11-27). The only new rule is which holdings Today puts in
// front of the reader (FOCUS_RULE); every reading shown is the card's own. Nothing here is a forecast or a ranking
// of investments: the order only decides what to show first.

export type TodayHolding = {
  ticker: string;
  name: string | null;
  cardDate: string | null;
  agreement: string | null;
  business: string | null;
  short: { business?: string | null; price?: string | null; value?: string | null } | null;
  valuation: string | null;
  priceChange3m: number | null;
  since: { from: string | null; to: string | null; stock: number | null; spy: number | null } | null;
  last5d: { to: string | null; stock: number | null; spy: number | null } | null;
  earnings: string | null;
  lastEarnings: string | null;
  watch: string[];
  strain: { label: string; reading: string; change: number | null; sales: number | null } | null;
  aiNote: { note: string; quote: string | null; model: string | null; form: string | null } | null;
};
export type TodayPayload = { holdings: TodayHolding[]; missing: string[]; trackCheck: string | null };
export type Change = { axis: string; from: string; to: string; on: string; origin?: string };

export const FOCUS_LIMIT = 4;
export const FOCUS_RULE =
  "A holding is shown here when (1) one of its readings changed for company reasons in the last 7 days, (2) its price and business point opposite ways (or lean that way), or (3) it reports earnings within 14 days. At most 4, in that order; core holdings first within each group. Everything else is in the Watchlist.";

export type FocusReason = "changed" | "disagree" | "earnings";
export type FocusItem = { holding: TodayHolding; reasons: FocusReason[]; changes: Change[]; earningsIn: number | null };

export function daysBetween(from: string | null | undefined, to: string | null | undefined): number | null {
  if (!from || !to) return null;
  const a = Date.parse(`${from.slice(0, 10)}T00:00:00Z`), b = Date.parse(`${to.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(a) || Number.isNaN(b) ? null : Math.round((b - a) / 86_400_000);
}

export function focusItems(holdings: TodayHolding[], changes: Record<string, Change[]>, today: string, core: Set<string>): { items: FocusItem[]; overflow: string[] } {
  const all: FocusItem[] = holdings.map((holding) => {
    const recent = (changes[holding.ticker] ?? []).filter((c) => c.origin === "COMPANY" && (daysBetween(c.on, today) ?? 99) <= 7);
    const earningsIn = daysBetween(today, holding.earnings);
    const reasons: FocusReason[] = [];
    if (recent.length) reasons.push("changed");
    if (holding.agreement === "OPPOSED" || holding.agreement === "LEANS_OPPOSED") reasons.push("disagree");
    if (earningsIn != null && earningsIn >= 0 && earningsIn <= 14) reasons.push("earnings");
    return { holding, reasons, changes: recent, earningsIn };
  }).filter((item) => item.reasons.length);
  const group = (item: FocusItem) => (item.reasons.includes("changed") ? 0 : item.reasons.includes("disagree") ? 1 : 2);
  const within = (item: FocusItem) => (item.holding.agreement === "OPPOSED" ? 0 : 1) * 100 + (item.earningsIn ?? 0);
  all.sort((a, b) => group(a) - group(b) || Number(core.has(b.holding.ticker)) - Number(core.has(a.holding.ticker)) || within(a) - within(b) || a.holding.ticker.localeCompare(b.holding.ticker));
  return { items: all.slice(0, FOCUS_LIMIT), overflow: all.slice(FOCUS_LIMIT).map((item) => item.holding.ticker) };
}

// ---- Holdings at a glance: business direction (columns) × what the price assumes (rows), from the card ----------
export const BUSINESS_COLUMNS = [
  { key: "WORSE", label: "Business getting weaker" },
  { key: "MIXED", label: "Business mixed" },
  { key: "BETTER", label: "Business getting better" },
] as const;
export const VALUE_ROWS = [
  { key: "less", label: "Price assumes less than shown" },
  { key: "inline", label: "Roughly in line" },
  { key: "more", label: "Price assumes more than shown" },
  { key: "beyond", label: "Above the model's reach" },
  { key: "none", label: "No single reading" },
] as const;

export function valueRow(state: string | null): (typeof VALUE_ROWS)[number]["key"] {
  if (!state) return "none";
  if (/model can reach/i.test(state)) return "beyond";
  if (/roughly/i.test(state)) return "inline";
  const tone = axisTone("valuation", state);
  return tone === "supportive" ? "less" : tone === "against" ? "more" : "none";
}

export function businessColumn(business: string | null): (typeof BUSINESS_COLUMNS)[number]["key"] {
  return business === "BETTER" ? "BETTER" : business === "WORSE" ? "WORSE" : "MIXED";
}

export const AGREEMENT_LABEL: Record<string, { label: string; tone: string }> = {
  OPPOSED: { label: "Price and business disagree", tone: "opposed" },
  LEANS_OPPOSED: { label: "Leans against business", tone: "leans" },
  ALIGNED: { label: "Price and business agree", tone: "aligned" },
  LEANS_ALIGNED: { label: "Leans with business", tone: "aligned" },
  OUTSIDE: { label: "Moved with outside forces", tone: "outside" },
  UNCLEAR: { label: "No clear reading", tone: "unclear" },
};

export function signed(value: number | null | undefined, digits = 0) {
  if (value == null || !Number.isFinite(value)) return "—";
  const text = `${Math.abs(value * 100).toFixed(digits)}%`;
  return Math.abs(value * 100) < 0.5 * 10 ** -digits ? `0%` : value < 0 ? `−${text}` : `+${text}`;
}

export function shortDay(day: string | null | undefined) {
  if (!day) return "—";
  const d = new Date(`${day.slice(0, 10)}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? day : d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}
