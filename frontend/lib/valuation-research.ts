import reports from "./fixtures/valuation-research.json";
import type { CompanyEconomicsPayload } from "./company-economics-types";
import { getCompanyResearchFixture } from "./data-provider";

export type ValuationView = "overview" | "economics-model" | "dcf" | "assumptions" | "reverse-dcf" | "sensitivity" | "validation" | "evidence" | "report";

export type ValuationAssumption = {
  name: string;
  value: number | string | null;
  unit?: string;
  source?: string;
  basis?: string;
  confidence?: string;
  scenario?: string;
  period?: string;
  overridden?: boolean;
};

export type ForecastRow = {
  year: number;
  period: string;
  revenue_growth: number;
  revenue: number;
  fcff_margin: number;
  fcff: number;
  discount_factor: number;
  present_value: number;
};

export type ScenarioResult = {
  forecast: ForecastRow[];
  pv_forecast_fcff: number;
  terminal_value: number;
  terminal_year_fcff: number;
  pv_terminal_value: number;
  enterprise_value: number;
  net_cash_debt_adjustment: number;
  other_senior_claims: number;
  equity_value: number;
  diluted_shares: number;
  fair_value_per_share: number;
  exit_multiple: number;
  exit_terminal_value: number;
  exit_enterprise_value: number;
  exit_fair_value_per_share: number;
  terminal_method_difference: number;
  current_price: number | null;
  upside_downside: number | null;
};

export type ValuationReport = {
  report_type: string;
  security_type: string;
  company_type: string;
  selected_method: string;
  company: {
    name: string;
    ticker: string;
    security_type: string;
    company_type: string;
    valuation_method: string;
    as_of: string;
    current_market_price: number | null;
  };
  valuation_method_selection: { company_type: string; selected_framework: string; routing_evidence: string[] };
  data_quality: { status?: string; missing?: string[]; reason?: string };
  historical_base: Record<string, unknown>;
  historical_fcff_reconciliation: Record<string, unknown>;
  assumptions: Record<string, ValuationAssumption[] | Record<string, unknown>>;
  discount_rate: Record<string, unknown>;
  scenarios: Record<"bear" | "base" | "bull", ScenarioResult> | Record<string, never>;
  sensitivity: { wacc?: number[]; terminal_growth?: number[]; values?: Array<Array<number | null>>; validity?: boolean[][]; calculation?: string };
  reverse_dcf: Record<string, unknown>;
  cross_checks: { metrics?: Record<string, number | null>; notes?: string[]; historical_peer_ranges?: string };
  risks: string[];
  fair_value_drivers: { raise?: string[]; lower?: string[]; highest_sensitivity?: string };
  final_interpretation: { bear_to_bull_range?: number[]; base_fair_value?: number; text?: string };
  // Checklist 7.6: headline fair value; the ten-year model is phased in above the type's growth cap.
  fair_value?: {
    method?: "FIVE_YEAR" | "PHASED" | "WITHHELD";
    extended_weight?: number;
    fair_value?: Partial<Record<"bear" | "base" | "bull", number>>;
    five_year?: Partial<Record<"bear" | "base" | "bull", number>>;
    ten_year?: Partial<Record<"bear" | "base" | "bull", number>>;
    reverse_dcf?: Record<string, unknown>;
    reason?: string;
  };
  validation: { status?: string; checks?: Record<string, { passed?: boolean; detail?: string }>; reasons?: string[] };
  fallback?: {
    detected_security_type: string;
    why_standard_dcf_is_inappropriate: string;
    required_specialized_framework: string;
    missing_data: string[];
    next_implementation_stage: string;
  };
};

const valuationReports = reports as unknown as Record<string, ValuationReport>;

export function getValuationReport(ticker: string): ValuationReport | null {
  return valuationReports[ticker.toUpperCase()] ?? null;
}

export function getValuationTickers() {
  return Object.keys(valuationReports);
}

export function getValuationCompany(ticker: string): CompanyEconomicsPayload | null {
  return getCompanyResearchFixture(ticker);
}

export function baseAssumptions(report: ValuationReport): ValuationAssumption[] {
  return Array.isArray(report.assumptions.base) ? report.assumptions.base : [];
}

export function assumption(report: ValuationReport, name: string): ValuationAssumption | undefined {
  return baseAssumptions(report).find((item) => item.name === name);
}

export function hasScenarios(report: ValuationReport): boolean {
  return report.validation.status !== "FAILED" && Boolean((report.scenarios as Record<string, unknown>).base);
}

/** Headline bear/base/bull: the phased values when the engine supplies them, otherwise the five-year scenarios. */
export function headlineFairValues(report: ValuationReport): Record<"bear" | "base" | "bull", number> {
  const phased = report.fair_value?.fair_value;
  if (phased && phased.bear != null && phased.base != null && phased.bull != null) return { bear: phased.bear, base: phased.base, bull: phased.bull };
  const scenarios = report.scenarios as Record<"bear" | "base" | "bull", ScenarioResult>;
  return { bear: scenarios.bear.fair_value_per_share, base: scenarios.base.fair_value_per_share, bull: scenarios.bull.fair_value_per_share };
}

export function valuationState(report: ValuationReport) {
  if (report.fallback?.required_specialized_framework) return "Framework Required";
  if (report.validation.status === "FAILED") return "Failed Validation";
  if (report.data_quality?.status === "FAILED_FCFF_RECONCILIATION") return "Fair Value Not Calculated";
  if (!hasScenarios(report)) return "Insufficient Data";
  const price = report.company.current_market_price;
  if (price == null) return "Market Price Unavailable";
  const { bear, base, bull } = headlineFairValues(report);
  if (price < bear) return "Market Below Bear";
  if (price <= base) return "Within Bear/Base";
  if (Math.abs(price / base - 1) <= 0.05) return "Near Base";
  if (price <= bull) return "Within Base/Bull";
  return "Market Above Bull";
}

export function currentPricePosition(report: ValuationReport) {
  if (!hasScenarios(report) || report.company.current_market_price == null) return 0;
  const { bear, bull } = headlineFairValues(report);
  const span = Math.max(Math.abs(bull - bear), 1);
  return Math.max(-12, Math.min(112, ((report.company.current_market_price - bear) / span) * 100));
}
