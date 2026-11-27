import { readFile } from "node:fs/promises";
import path from "node:path";
import { analyzeValuation } from "./valuation-service";
import type { ValuationReport } from "./valuation-research";

// The downloadable research note reads only what the site already computed: the judgment card (rules + checked AI
// write-up), the valuation report and the stored company profile. Nothing here calculates a new number.

export type Json = Record<string, unknown>;
export type ReportData = {
  ticker: string;
  card: Json | null;
  valuation: ValuationReport | null;
  profile: Json | null;
  snapshot: Json | null;
  chart: PriceChart | null;
  generatedAt: string;
};

/** One year of daily closes for the stock and the S&P 500 (SPY), both rebased to 100 at the start. */
export type PriceChart = { dates: string[]; stock: number[]; index: number[] };

const ROOT = path.resolve(process.cwd(), "..");
const TICKER = /^[A-Z0-9.^=-]{1,12}$/;

async function readJson(file: string): Promise<Json | null> {
  try {
    const parsed = JSON.parse(await readFile(file, "utf8"));
    return parsed && typeof parsed === "object" ? (parsed as Json) : null;
  } catch {
    return null;
  }
}

export async function loadReportData(tickerInput: string): Promise<ReportData | null> {
  const ticker = tickerInput.trim().toUpperCase();
  if (!TICKER.test(ticker) || ticker.startsWith("-")) return null;
  const [card, stored, valuation, chart] = await Promise.all([
    readJson(path.join(ROOT, ".cache", "verdicts", `${ticker}.json`)),
    readJson(path.join(ROOT, ".cache", "company_economics", `${ticker}.json`)),
    analyzeValuation(ticker).then((result) => result.report).catch(() => null),
    priceChart(ticker),
  ]);
  if (!card && !valuation) return null;
  return {
    ticker,
    card,
    valuation,
    profile: (stored?.company_economics as Json | undefined) ?? null,
    snapshot: (stored?.normalized_snapshot as Json | undefined) ?? null,
    chart,
    generatedAt: new Date().toISOString(),
  };
}

async function closes(symbol: string): Promise<Map<string, number> | null> {
  try {
    const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1y&interval=1d`,
      { headers: { "User-Agent": "Mozilla/5.0" }, cache: "no-store", signal: AbortSignal.timeout(15_000) });
    if (!response.ok) return null;
    const result = obj(arr(pick(await response.json(), "chart", "result"))[0]);
    const stamps = arr(result.timestamp).map(num);
    const values = arr(pick(arr(pick(result, "indicators", "quote"))[0], "close")).map(num);
    const out = new Map<string, number>();
    stamps.forEach((stamp, i) => { const value = values[i]; if (stamp != null && value != null) out.set(new Date(stamp * 1000).toISOString().slice(0, 10), value); });
    return out.size > 20 ? out : null;
  } catch {
    return null;
  }
}

/** Share price against the S&P 500 for the note's first page; null (chart left out) when either series is missing. */
async function priceChart(ticker: string): Promise<PriceChart | null> {
  const [stock, index] = await Promise.all([closes(ticker), closes("SPY")]);
  if (!stock || !index) return null;
  const dates = Array.from(stock.keys()).filter((day) => index.has(day)).sort();
  if (dates.length < 20) return null;
  const s0 = stock.get(dates[0])!, i0 = index.get(dates[0])!;
  return { dates, stock: dates.map((d) => (stock.get(d)! / s0) * 100), index: dates.map((d) => (index.get(d)! / i0) * 100) };
}

// ---- small readers for loosely typed JSON ----------------------------------------------------------------------
export function obj(value: unknown): Json {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Json) : {};
}
export function arr(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}
export function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
export function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}
export function pick(source: unknown, ...keys: string[]): unknown {
  let current: unknown = source;
  for (const key of keys) current = obj(current)[key];
  return current;
}

export function pct(value: unknown, digits = 1, signed = false): string {
  const n = num(value);
  if (n == null) return "—";
  const text = `${Math.abs(n * 100).toFixed(digits)}%`;
  if (Math.abs(n * 100) < 0.5 * 10 ** -digits) return `${(0).toFixed(digits)}%`;
  return n < 0 ? `−${text}` : signed ? `+${text}` : text;
}
export function money(value: unknown, currency = "USD", digits = 2): string {
  const n = num(value);
  if (n == null) return "—";
  const sign = n < 0 ? "−" : "";
  const prefix = currency === "USD" ? "$" : `${currency} `;
  return `${sign}${prefix}${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}
export function big(value: unknown, currency = "USD"): string {
  const n = num(value);
  if (n == null) return "—";
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  const prefix = currency === "USD" ? "$" : `${currency} `;
  if (abs >= 1e12) return `${sign}${prefix}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${prefix}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${prefix}${(abs / 1e6).toFixed(1)}M`;
  return `${sign}${prefix}${abs.toLocaleString("en-US")}`;
}
