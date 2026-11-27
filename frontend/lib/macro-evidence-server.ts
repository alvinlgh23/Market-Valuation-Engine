import { readFile } from "node:fs/promises";
import path from "node:path";

// Server-side reads for the macro pages (2026-11-27): what our own scorecard found for each reading
// (data/signal_validation.json) and the market's 10-year inflation expectation (cached FRED T10YIE).
// Read only; nothing is recalculated.

const ROOT = path.resolve(process.cwd(), "..");
export type ScoreTest = { verdict: string | null; t1m: number | null; samples1m: number | null };
export type MacroEvidence = {
  liquidity: ScoreTest; rates: ScoreTest; risk: ScoreTest;
  regimeSamples: Record<string, number>;
  breakeven10y: { value: number; date: string } | null;
};

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);

function score(macro: Record<string, unknown>, key: string): ScoreTest {
  const item = (macro[key] ?? {}) as { verdict?: string; horizons?: Record<string, { t_stat?: number; samples?: number }> };
  return { verdict: item.verdict ?? null, t1m: num(item.horizons?.["1M"]?.t_stat), samples1m: num(item.horizons?.["1M"]?.samples) };
}

export async function loadMacroEvidence(): Promise<MacroEvidence> {
  let validation: Record<string, unknown> = {};
  try { validation = JSON.parse(await readFile(path.join(ROOT, "data", "signal_validation.json"), "utf8")); } catch { /* no scorecard */ }
  const macro = (validation.macro ?? {}) as Record<string, unknown>;
  const regimes = ((validation.risk_regime_forward_spy ?? {}) as Record<string, Record<string, { non_overlapping_samples?: number }>>)["1M"] ?? {};
  let breakeven10y: MacroEvidence["breakeven10y"] = null;
  try {
    const rows = (await readFile(path.join(ROOT, ".cache", "compass_fred", "T10YIE.csv"), "utf8")).trim().split(/\r?\n/).reverse();
    for (const row of rows) {
      const [date, value] = row.split(",");
      const v = Number(value);
      if (/^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(v) && value !== "") { breakeven10y = { value: v, date }; break; }
    }
  } catch { /* not cached */ }
  return {
    liquidity: score(macro, "liquidity_score"), rates: score(macro, "rate_score"), risk: score(macro, "risk_score"),
    regimeSamples: Object.fromEntries(Object.entries(regimes).map(([k, v]) => [k, num(v?.non_overlapping_samples) ?? 0])),
    breakeven10y,
  };
}
