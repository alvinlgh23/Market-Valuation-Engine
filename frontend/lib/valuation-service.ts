import { runPythonJson, runtimeError, PythonRuntimeError } from "./python-runtime";
import type { ValuationReport } from "./valuation-research";

const TICKER = /^[A-Z][A-Z0-9.-]{0,9}$/;
const CACHE_MS = 15 * 60 * 1000;
const cache = new Map<string, { at: number; report: ValuationReport }>();
const inflight = new Map<string, Promise<ValuationResult>>();

export type ValuationAvailability = "SUPPORTED_VALUATION" | "FRAMEWORK_REQUIRED" | "INSUFFICIENT_DATA" | "UNSUPPORTED_SECURITY" | "PROVIDER_ERROR";
export type ValuationOverrides = { revenue_growth?: number; fcf_margin?: number; wacc?: number; terminal_growth?: number; sbc_policy?: "accounting-fcff" | "owner-earnings" };
export type ValuationResult = {
  status: ValuationAvailability;
  report: ValuationReport | null;
  meta: { data_state: "LIVE" | "CACHED" | "STALE" | "PARTIAL" | "INSUFFICIENT_DATA" | "UNAVAILABLE"; as_of?: string; source: string; error?: string; error_code?: string; response_cached_at?: string };
};

function availability(report: ValuationReport): ValuationAvailability {
  if (["ETF_OR_FUND", "SPAC_OR_SHELL"].includes(report.security_type)) return "UNSUPPORTED_SECURITY";
  if (report.security_type === "INSUFFICIENT_DATA") return "INSUFFICIENT_DATA";
  if (report.fallback?.required_specialized_framework) return "FRAMEWORK_REQUIRED";
  if (!(report.scenarios as Record<string, unknown>).base) return "INSUFFICIENT_DATA";
  return "SUPPORTED_VALUATION";
}

function availableDataState(status: ValuationAvailability, live: boolean) {
  if (status === "INSUFFICIENT_DATA") return "INSUFFICIENT_DATA" as const;
  if (status === "UNSUPPORTED_SECURITY") return "UNAVAILABLE" as const;
  if (status === "FRAMEWORK_REQUIRED") return "PARTIAL" as const;
  return live ? "LIVE" as const : "CACHED" as const;
}

function overrideArgs(overrides: ValuationOverrides) {
  const args: string[] = [];
  if (typeof overrides !== "object" || Array.isArray(overrides)) throw new PythonRuntimeError("INVALID_INPUT", "Overrides must be an object.");
  if (Object.keys(overrides).some(key => !["revenue_growth", "fcf_margin", "wacc", "terminal_growth", "sbc_policy"].includes(key))) throw new PythonRuntimeError("INVALID_INPUT", "Unknown valuation override.");
  const numeric: Array<[keyof ValuationOverrides, string, number, number]> = [
    ["revenue_growth", "--revenue-growth", -0.5, 1],
    ["fcf_margin", "--fcf-margin", -0.5, 0.8],
    ["wacc", "--wacc", 0, 1],
    ["terminal_growth", "--terminal-growth", 0, 0.1],
  ];
  for (const [key, flag, low, high] of numeric) {
    const value = overrides[key];
    if (value == null) continue;
    if (typeof value !== "number" || !Number.isFinite(value) || value <= low || value >= high) throw new PythonRuntimeError("INVALID_INPUT", `Invalid valuation override: ${String(key)}.`);
    args.push(flag, String(value));
  }
  if (overrides.wacc != null && overrides.terminal_growth != null && overrides.terminal_growth >= overrides.wacc) throw new PythonRuntimeError("INVALID_INPUT", "Terminal growth must be below WACC.");
  if (overrides.sbc_policy && !["accounting-fcff", "owner-earnings"].includes(overrides.sbc_policy)) throw new PythonRuntimeError("INVALID_INPUT", "Unsupported SBC policy.");
  if (overrides.sbc_policy) args.push("--sbc-policy", overrides.sbc_policy);
  return args;
}

export async function analyzeValuation(tickerInput: string, options: { refresh?: boolean; overrides?: ValuationOverrides } = {}): Promise<ValuationResult> {
  const ticker = tickerInput.trim().toUpperCase();
  if (!TICKER.test(ticker)) return { status: "UNSUPPORTED_SECURITY", report: null, meta: { data_state: "UNAVAILABLE", source: "VALIDATION", error: "Enter a valid ticker symbol." } };
  const overrides = options.overrides || {};
  const cacheKey = `${ticker}:${JSON.stringify(overrides)}`;
  const cached = cache.get(cacheKey);
  if (!options.refresh && cached && Date.now() - cached.at < CACHE_MS) {
    const status = availability(cached.report);
    return { status, report: cached.report, meta: { data_state: availableDataState(status, false), source: "VALUATION_MEMORY_CACHE", as_of: cached.report.company.as_of, response_cached_at: new Date(cached.at).toISOString() } };
  }
  if (inflight.has(cacheKey)) return inflight.get(cacheKey)!;

  const task = (async (): Promise<ValuationResult> => {
    try {
      const args = ["-B", "model.py", "valuation", ticker, "--json", ...overrideArgs(overrides)];
      const report = await runPythonJson<ValuationReport>(args);
      if (report?.report_type !== "intrinsic_valuation" || report.company?.ticker !== ticker || !report.validation || !report.scenarios || !report.assumptions || !report.historical_base || !report.reverse_dcf || !report.data_quality) throw new PythonRuntimeError("INVALID_JSON", "Valuation engine returned malformed or mismatched JSON.");
      const status = availability(report);
      if (report.validation.status === "FAILED") {
        cache.delete(cacheKey);
        return { status: "INSUFFICIENT_DATA", report, meta: { data_state: "INSUFFICIENT_DATA", source: "PYTHON_INTRINSIC_VALUATION", as_of: report.company.as_of } };
      }
      if (status === "SUPPORTED_VALUATION" || status === "FRAMEWORK_REQUIRED") cache.set(cacheKey, { at: Date.now(), report });
      else if (cached) return { status: availability(cached.report), report: cached.report, meta: { data_state: "STALE", source: "VALUATION_MEMORY_CACHE", as_of: cached.report.company.as_of, response_cached_at: new Date(cached.at).toISOString(), error_code: "DATA_COVERAGE", error: "Refresh returned insufficient financial coverage; showing prior report." } };
      return { status, report, meta: { data_state: availableDataState(status, true), source: "PYTHON_INTRINSIC_VALUATION", as_of: report.company.as_of } };
    } catch (error) {
      if (cached) return { status: availability(cached.report), report: cached.report, meta: { data_state: "STALE", source: "VALUATION_MEMORY_CACHE", as_of: cached.report.company.as_of, response_cached_at: new Date(cached.at).toISOString(), error: runtimeError(error).message, error_code: runtimeError(error).code } };
      return { status: "PROVIDER_ERROR", report: null, meta: { data_state: "UNAVAILABLE", source: "PYTHON_INTRINSIC_VALUATION", error: runtimeError(error).message, error_code: runtimeError(error).code } };
    } finally {
      inflight.delete(cacheKey);
    }
  })();
  inflight.set(cacheKey, task);
  return task;
}
