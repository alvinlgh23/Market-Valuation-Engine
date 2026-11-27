import type { ValuationReport } from "./valuation-research";

// Client-safe types and formatters for the research note, the Financials tab and the Economic map.

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
