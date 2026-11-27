import { readFile } from "node:fs/promises";
import path from "node:path";
import { analyzeValuation } from "./valuation-service";

// The downloadable research note reads only what the site already computed: the judgment card (rules + checked AI
// write-up), the valuation report and the stored company profile. Nothing here calculates a new number.

export type { Json, ReportData, PriceChart } from "./report-format";
export { obj, arr, num, str, pick, pct, money, big } from "./report-format";
import { arr, num, obj, pick, type Json, type PriceChart, type ReportData } from "./report-format";

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

export async function loadReportData(tickerInput: string, options: { chart?: boolean } = {}): Promise<ReportData | null> {
  const ticker = tickerInput.trim().toUpperCase();
  if (!TICKER.test(ticker) || ticker.startsWith("-")) return null;
  const [card, stored, valuation, chart] = await Promise.all([
    readJson(path.join(ROOT, ".cache", "verdicts", `${ticker}.json`)),
    readJson(path.join(ROOT, ".cache", "company_economics", `${ticker}.json`)),
    analyzeValuation(ticker).then((result) => result.report).catch(() => null),
    options.chart === false ? Promise.resolve(null) : priceChart(ticker),
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

