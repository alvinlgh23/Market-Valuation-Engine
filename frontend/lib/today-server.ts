import { readFile } from "node:fs/promises";
import path from "node:path";
import type { TodayHolding, TodayPayload } from "./today-model";

// Today's per-holding read: only the stored judgment cards (.cache/verdicts) and the track record. No network, no
// Python, nothing recalculated - each field is copied from what the card's fixed rules and checked AI review stored.

const ROOT = path.resolve(process.cwd(), "..");
type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === "object" && !Array.isArray(v) ? (v as Json) : {});
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const str = (v: unknown) => (typeof v === "string" && v.trim() ? v : null);

async function readJson(file: string): Promise<Json | null> {
  try { return obj(JSON.parse(await readFile(file, "utf8"))); } catch { return null; }
}

function holding(ticker: string, card: Json): TodayHolding {
  const axes = obj(card.axes);
  const conclusion = obj(card.conclusion);
  const recent = obj(pick(card, "attribution", "recent_move"));
  const since = obj(recent.since_window_end), last5 = obj(recent.last_5d);
  const operating = obj(card.operating);
  const constraint = obj(operating.constraint);
  const review = obj(pick(card, "ai", "review"));
  const note = obj(arr(review.notes)[0]);
  const catalysts = obj(card.next_catalysts);
  return {
    ticker,
    name: str(card.name),
    cardDate: str(card.generated_on),
    agreement: str(conclusion.agreement),
    business: str(conclusion.business),
    short: obj(conclusion.short) as TodayHolding["short"],
    valuation: str(obj(axes.valuation).state),
    priceChange3m: num(pick(card, "price_reading", "price_change")),
    since: num(since.stock_change) != null ? { from: str(since.from), to: str(since.to), stock: num(since.stock_change), spy: num(since.spy_change) } : null,
    last5d: num(last5.stock_change) != null ? { to: str(recent.latest_date), stock: num(last5.stock_change), spy: num(last5.spy_change) } : null,
    earnings: str(catalysts.earnings),
    lastEarnings: str(catalysts.last_earnings),
    watch: arr(card.falsification).map(String).filter((line) => /^(Valuation|Fundamentals|Estimates):/.test(line)).slice(0, 2),
    strain: str(constraint.label) ? { label: String(constraint.label), reading: str(constraint.reading) ?? "", change: num(constraint.change), sales: num(constraint.sales_change) } : null,
    aiNote: str(note.note) ? { note: String(note.note), quote: str(note.quote), model: str(review.model), form: str(pick(review, "source", "form")) } : null,
  };
}

function pick(source: unknown, ...keys: string[]): unknown {
  let current: unknown = source;
  for (const key of keys) current = obj(current)[key];
  return current;
}

export async function loadToday(): Promise<TodayPayload> {
  const list = await readJson(path.join(ROOT, "data", "watchlist.json"));
  const tickers = arr(list?.tickers).map(String).filter((t) => /^[A-Z0-9.^=-]{1,12}$/.test(t));
  const cards = await Promise.all(tickers.map((t) => readJson(path.join(ROOT, ".cache", "verdicts", `${t}.json`))));
  const track = await readJson(path.join(ROOT, "data", "history", "track_record.json"));
  const checks = Object.values(obj(track?.groups)).map((g) => str(pick(g, "horizons", "1m", "next_check"))).filter((d): d is string => !!d).sort();
  return {
    holdings: tickers.flatMap((t, i) => (cards[i] && cards[i]!.axes ? [holding(t, cards[i]!)] : [])),
    missing: tickers.filter((_, i) => !cards[i]?.axes),
    trackCheck: checks[0] ?? null,
  };
}
