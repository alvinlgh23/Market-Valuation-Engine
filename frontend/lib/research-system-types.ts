import type { MacroWorld } from "./macro-types";

export type ResearchRow = {
  id?: string;
  label?: string;
  name?: string;
  module?: string;
  value?: string;
  signal?: string;
  context?: string;
  why?: string;
  state?: string;
  availability?: string;
  confidence?: string;
  threshold?: string;
  current?: string;
  period?: string;
  interpretation?: string;
  href?: string;
  rank?: number;
  ticker?: string;
  archetype?: string;
  constraint?: string;
  validation?: string;
  as_of?: string | null;
  [key: string]: unknown;
};

export type EngineResult<T = Record<string, unknown>> = {
  state: string;
  payload: T | null;
  error: string | null;
};

export type MacroTypedMetric = {
  note?: string;
  maturity_metadata?: { long_maturity: string; short_maturity: string | null; fallback: boolean; period_alignment: string; long_observed_at: string | null; short_observed_at: string | null };
  key: string;
  label: string;
  raw_value: number;
  formatted_value: string;
  unit: string;
  date: string | null;
  source: string;
  source_state: string;
  confidence: string;
};

export type MacroCoverageState = {
  coverage_status: "FULL" | "PARTIAL" | "INSUFFICIENT" | "STALE" | "UNAVAILABLE" | string;
  available_fields?: string[];
  missing_fields: string[];
  stale_fields?: string[];
  last_valid_as_of?: string | null;
  source_state: string;
  reason?: string;
};

export type MacroLiquidityDriver = {
  key: string;
  label: string;
  raw_value: number | string | null;
  formatted_value: string;
  unit: string;
  state: string;
  contribution: number;
  explanation: string;
  thresholds: string[];
  date: string | null;
  source: string;
  source_state: string;
};

export type MarketTransmission = {
  coverage: MacroCoverageState;
  rates: MacroCoverageState & { metrics: MacroTypedMetric[]; current_curve: MacroTypedMetric[]; moves: MacroTypedMetric[]; history: unknown[] };
  fx: MacroCoverageState & { metrics: MacroTypedMetric[]; moves: MacroTypedMetric[]; history: unknown[] };
  liquidity: MacroCoverageState & { state: string; score: number | null; available_drivers: number; expected_drivers: number; drivers: MacroLiquidityDriver[] };
  risk: MacroCoverageState & { state: string; confidence: string; coverage: number; summary: string };
};

export type InflationMetric = {
  key: string;
  name: string;
  section: string;
  source: string;
  series: string | null;
  current: number | null;
  date: string | null;
  trend_3m: number | null;
  trend_6m: number | null;
  reference: string;
  pressure_label: string;
  pressure_reason: string;
  status: string;
  freshness: string;
  validation_status: string;
  forward_role: string;
  economic_importance: string;
  endpoint: string | null;
};

export type ResearchSystem = {
  schema_version: string;
  generated_at: string;
  mode: string;
  engine_states: Record<string, string>;
  engine_errors: Record<string, string | null>;
  dashboard: {
    headline: { state: string; summary: string; as_of: string };
    reads: ResearchRow[];
    what_changed: ResearchRow[];
    signals: ResearchRow[];
    research_priority: ResearchRow[];
    global_regions: ResearchRow[];
    companies: ResearchRow[];
    valuation_flags: ResearchRow[];
    freshness: ResearchRow[];
    watch_conditions: ResearchRow[];
  };
  world: MacroWorld;
  market_transmission: MarketTransmission;
  modules: {
    inflation: EngineResult<{ metrics: Record<string, InflationMetric>; available: number; total: number; states: Record<string, string>; near_term: string; medium_term: string; horizon_reason: string; fed_sensitivity: string; common_month: string; latest_source: string; validation: Record<string, unknown>; provisional: boolean }>;
    core_market: EngineResult<Record<string, unknown>>;
    neer: EngineResult<Record<string, unknown>>;
    kospi: EngineResult<Record<string, unknown>>;
    companies: EngineResult<ResearchRow[]>;
  };
  capabilities: Record<string, unknown>;
  disclaimer: string;
};
