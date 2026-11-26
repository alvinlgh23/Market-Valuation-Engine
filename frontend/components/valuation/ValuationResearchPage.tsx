"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { CompanyEconomicsPayload } from "../../lib/company-economics-types";
import { adaptCompanyEconomics, humanize } from "../../lib/companyEconomicsAdapter";
import {
  assumption,
  baseAssumptions,
  hasScenarios,
  valuationState,
  headlineFairValues,
  type ForecastRow,
  type ScenarioResult,
  type ValuationReport,
  type ValuationView
} from "../../lib/valuation-research";
import { ResearchShell, type ResearchDataState } from "../research/ResearchShell";
import { fairValueCoordinates } from "../../lib/fair-value-scale.mjs";

function moneyFormatter(currency?: string) {
  const prefix = !currency || currency === "USD" ? "$" : `${currency} `;
  return (value: unknown) => {
    if (typeof value !== "number" || !Number.isFinite(value)) return "—";
    const size = Math.abs(value);
    if (size < 0.005) return `${prefix}0`;
    const sign = value < 0 ? "−" : "";
    if (size >= 1e12) return `${sign}${prefix}${(size / 1e12).toFixed(2)}T`;
    if (size >= 1e9) return `${sign}${prefix}${(size / 1e9).toFixed(2)}B`;
    if (size >= 1e6) return `${sign}${prefix}${(size / 1e6).toFixed(1)}M`;
    return `${sign}${prefix}${size.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  };
}
function sharesFormatter(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const size = Math.abs(value);
  if (size >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (size >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}
function pct(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const rounded = Number((value * 100).toFixed(1));
  if (rounded === 0) return "0.0%";
  return `${rounded < 0 ? "−" : ""}${Math.abs(rounded).toFixed(1)}%`;
}
function number(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("en-US", { maximumFractionDigits: 1 }) : "—"; }
function stateClass(value?: string) { return (value || "unavailable").toLowerCase().replaceAll("_", "-").replaceAll(" ", "-"); }

const SOURCE_LABELS: Record<string, string> = {
  historical_company_data_and_model_policy: "Filed financials + model policy",
  company_type_policy: "Business-type policy default",
  historical_company_data_or_fallback: "Filed tax rate (21% statutory fallback)",
  user_override: "Your custom assumption",
  user_override_with_scenario_spread: "Your assumption ± scenario spread"
};
function cleanSource(source?: string) {
  if (!source) return "Unavailable";
  return SOURCE_LABELS[source] ?? humanize(source);
}

function ValueBadge({ value }: { value?: string }) {
  return <span className={`valuation-badge valuation-badge-${stateClass(value)}`}>{humanize(value || "UNAVAILABLE")}</span>;
}

function ViewNav({ ticker, view, fixture }: { ticker: string; view: ValuationView; fixture: boolean }) {
  const params = useSearchParams();
  const views: Array<[ValuationView, string]> = [["overview", "Overview"], ["economics-model", "Economics vs Model"], ["dcf", "DCF"], ["assumptions", "Assumptions"], ["reverse-dcf", "Reverse DCF"], ["sensitivity", "Sensitivity"], ["validation", "Validation"], ["evidence", "Evidence"], ["report", "Full Report"]];
  return <nav className="valuation-view-nav" aria-label="Valuation views">{views.map(([key, label]) => { const query = new URLSearchParams(params.toString()); query.set("view", key); query.delete("refresh"); if (fixture) query.set("fixture", "1"); return <Link className={view === key ? "active" : ""} href={`/valuation/${ticker}?${query}`} key={key}>{label}</Link>; })}</nav>;
}

function headlineReverse(report: ValuationReport): Record<string, unknown> {
  return report.fair_value?.method === "PHASED" && report.fair_value.reverse_dcf ? report.fair_value.reverse_dcf : report.reverse_dcf;
}

/** Exact replica of intrinsic_valuation.py _dcf / _dcf_extended for instant 60fps interactive slider feedback. */
function computeInteractiveFairValue(params: {
  revenue: number; currentMargin: number; cash: number; debt: number; shares: number;
  growth0: number; targetMargin: number; wacc: number; terminalGrowth: number; dilution: number;
  extendedWeight: number; unitFactor: number;
}): number | null {
  const { revenue, currentMargin, cash, debt, shares, growth0, targetMargin, wacc, terminalGrowth, dilution, extendedWeight, unitFactor } = params;
  if (!(revenue > 0) || !(shares > 0) || wacc <= terminalGrowth + 0.005) return null;
  const runHorizon = (years: number, firstGrowth: number) => {
    let rev = revenue, pv = 0, lastFcff = 0;
    for (let y = 1; y <= years; y += 1) {
      const g = years === 5
        ? firstGrowth + (terminalGrowth + 0.01 - firstGrowth) * ((y - 1) / 4)
        : firstGrowth + (terminalGrowth - firstGrowth) * ((y - 1) / (years - 1));
      const m = currentMargin + (targetMargin - currentMargin) * (y / years);
      rev *= 1 + g;
      lastFcff = rev * m;
      pv += lastFcff / Math.pow(1 + wacc, y);
    }
    const tv = (lastFcff * (1 + terminalGrowth)) / (wacc - terminalGrowth);
    const ev = pv + tv / Math.pow(1 + wacc, years);
    const eq = ev + (cash - debt);
    const dilShares = shares * Math.pow(1 + dilution, years);
    return (eq / dilShares) * unitFactor;
  };
  const five = runHorizon(5, growth0);
  if (!(extendedWeight > 0)) return five;
  const ten = runHorizon(10, growth0);
  return (1 - extendedWeight) * five + extendedWeight * ten;
}

export function InteractiveValuationSandbox({ report }: { report: ValuationReport }) {
  const money = moneyFormatter(report.company.currency);
  const baseGrowth = assumption(report, "year_1_revenue_growth")?.value;
  const baseMargin = assumption(report, "year_5_fcff_margin")?.value;
  const baseWacc = assumption(report, "wacc")?.value;
  const terminal = Number(assumption(report, "terminal_growth")?.value ?? 0.025);
  const dilution = Number(assumption(report, "annual_dilution")?.value ?? 0.001);
  const extWeight = Number(report.fair_value?.extended_weight ?? 0);
  const observedGrowth = Number(report.fair_value?.observed_growth ?? baseGrowth ?? 0.1);
  const defaultGrowth = extWeight > 0 ? Math.min(observedGrowth, 0.50) : Number(baseGrowth ?? 0.1);
  const defaultMargin = Number(baseMargin ?? 0.2);
  const defaultWacc = Number(baseWacc ?? 0.095);

  const [growth, setGrowth] = useState(defaultGrowth);
  const [margin, setMargin] = useState(defaultMargin);
  const [wacc, setWacc] = useState(defaultWacc);

  const hb = report.historical_base;
  const revenue = Number(hb.latest_annual_revenue ?? 0);
  const currentMargin = Number(hb.fcff_margin ?? defaultMargin);
  const cash = Number(hb.cash ?? 0);
  const debt = Number(hb.debt ?? 0);
  const shares = Number(hb.diluted_shares ?? 0);
  const price = report.company.current_market_price;
  const revSolved = Number(headlineReverse(report).required_year_1_revenue_growth);
  const canSnapToPrice = Number.isFinite(revSolved) && revSolved >= -0.15 && revSolved <= 0.55;

  // Calibrate unit factor so default sliders match report's exact base value (handles ADR / rounding seamlessly).
  const scenariosAvailable = hasScenarios(report);
  const headlineBase = scenariosAvailable ? headlineFairValues(report).base : null;
  const rawDefault = useMemo(() => computeInteractiveFairValue({
    revenue, currentMargin, cash, debt, shares,
    growth0: defaultGrowth, targetMargin: defaultMargin, wacc: defaultWacc,
    terminalGrowth: terminal, dilution, extendedWeight: extWeight, unitFactor: 1
  }), [revenue, currentMargin, cash, debt, shares, defaultGrowth, defaultMargin, defaultWacc, terminal, dilution, extWeight]);
  const unitFactor = rawDefault && headlineBase && Number.isFinite(headlineBase) && Math.abs(rawDefault) > 1e-6 ? headlineBase / rawDefault : 1;

  const simulated = computeInteractiveFairValue({
    revenue, currentMargin, cash, debt, shares,
    growth0: growth, targetMargin: margin, wacc,
    terminalGrowth: terminal, dilution, extendedWeight: extWeight, unitFactor
  });

  if (!scenariosAvailable || !(revenue > 0) || !(shares > 0)) return null;
  const isModified = Math.abs(growth - defaultGrowth) > 0.001 || Math.abs(margin - defaultMargin) > 0.001 || Math.abs(wacc - defaultWacc) > 0.001;
  const deltaVsPrice = simulated != null && price && price > 0 ? simulated / price - 1 : null;

  return (
    <section className="valuation-sandbox" aria-label="Interactive valuation sandbox">
      <header>
        <div>
          <span>WHAT-IF ASSUMPTION SANDBOX</span>
          <h2>Test what the share price requires</h2>
          <p>Drag any assumption to see how model value compares with today&apos;s market price ({money(price)}). Baseline report figures remain untouched.</p>
        </div>
        <div className="sandbox-presets">
          {canSnapToPrice ? (
            <button type="button" onClick={() => { setGrowth(revSolved); setMargin(defaultMargin); setWacc(defaultWacc); }}>
              Match share price ({pct(revSolved)} Y1)
            </button>
          ) : null}
          <button type="button" onClick={() => setWacc(Math.max(0.055, defaultWacc - 0.01))}>
            Lower ERP (−1pt WACC)
          </button>
          {isModified ? (
            <button type="button" className="reset" onClick={() => { setGrowth(defaultGrowth); setMargin(defaultMargin); setWacc(defaultWacc); }}>
              Reset to model base
            </button>
          ) : null}
        </div>
      </header>
      <div className="sandbox-grid">
        <div className="sandbox-controls">
          <label>
            <div><span>Year-1 revenue growth</span><strong>{pct(growth)}</strong></div>
            <input type="range" min={-0.10} max={0.55} step={0.005} value={growth} onChange={(e) => setGrowth(Number(e.target.value))} />
            <small>Model default: {pct(defaultGrowth)}{Number.isFinite(observedGrowth) ? ` · Observed 12M: ${pct(observedGrowth)}` : ""}</small>
          </label>
          <label>
            <div><span>Target FCFF margin</span><strong>{pct(margin)}</strong></div>
            <input type="range" min={0.04} max={0.55} step={0.005} value={margin} onChange={(e) => setMargin(Number(e.target.value))} />
            <small>Model default: {pct(defaultMargin)} · Current FCFF margin: {pct(currentMargin)}</small>
          </label>
          <label>
            <div><span>Discount rate (WACC)</span><strong>{pct(wacc)}</strong></div>
            <input type="range" min={Math.max(terminal + 0.01, 0.055)} max={0.16} step={0.0025} value={wacc} onChange={(e) => setWacc(Number(e.target.value))} />
            <small>Model policy (4.5% ERP): {pct(defaultWacc)} · Terminal growth: {pct(terminal)}</small>
          </label>
        </div>
        <div className="sandbox-result">
          <span>{isModified ? "YOUR SIMULATED VALUE" : "MODEL BASE VALUE"}</span>
          <strong>{money(simulated)}</strong>
          {price != null && deltaVsPrice != null ? (
            <p className={deltaVsPrice >= 0 ? "up" : "down"}>
              {deltaVsPrice >= 0 ? `+${(deltaVsPrice * 100).toFixed(1)}% above` : `−${Math.abs(deltaVsPrice * 100).toFixed(1)}% below`} market price ({money(price)})
            </p>
          ) : null}
          <small>{extWeight > 0 ? `Uses ${Math.round(extWeight * 100)}% 10-year / ${Math.round((1 - extWeight) * 100)}% 5-year horizon blend.` : "Uses 5-year explicit FCFF forecast decaying to 2.5% terminal growth."}</small>
        </div>
      </div>
    </section>
  );
}

function FairValueRange({ report }: { report: ValuationReport }) {
  const money = moneyFormatter(report.company.currency);
  const params = useSearchParams();
  if (report.validation.status === "FAILED" || (!hasScenarios(report) && !report.fallback?.required_specialized_framework)) return <section className="valuation-framework-state"><ValueBadge value={report.validation.status === "FAILED" ? "FAILED" : "INSUFFICIENT_DATA"} /><h2>Fair value withheld</h2><p>{report.validation.reasons?.join(" ") || report.data_quality.reason}</p><p>Inspect Validation and the historical FCFF reconciliation for diagnostic detail.</p></section>;
  if (!hasScenarios(report)) return <section className="valuation-framework-state"><ValueBadge value="FRAMEWORK_REQUIRED" /><h2>Valuation framework required</h2><p>{report.fallback?.why_standard_dcf_is_inappropriate || report.data_quality.reason}</p><dl><div><dt>Company type</dt><dd>{report.company.company_type}</dd></div><div><dt>Required framework</dt><dd>{report.fallback?.required_specialized_framework || report.selected_method}</dd></div><div><dt>Missing evidence</dt><dd>{report.fallback?.missing_data?.join(", ") || report.data_quality.missing?.join(", ") || "Unavailable"}</dd></div></dl></section>;
  const values = headlineFairValues(report);
  const { bear, base, bull } = values;
  const price = report.company.current_market_price;
  const phased = report.fair_value?.method === "PHASED";
  const scale = fairValueCoordinates({ bear, base, bull, market: price });
  if (!scale.valid) return <section className="valuation-framework-state"><ValueBadge value="INSUFFICIENT_DATA" /><h2>Fair-value range unavailable</h2><p>Scenario values are missing or not economically ordered.</p></section>;
  const compressed = price != null && bull != null && bear != null && (scale.positions.bull - scale.positions.bear < 24);
  const modelSpan = bull != null && bear != null ? Math.max(bull - bear, 1e-6) : 1;
  const pointLeft = (key: "bear" | "base" | "bull") => compressed && bear != null && values[key] != null ? 8 + ((values[key]! - bear) / modelSpan) * 52 : scale.positions[key];
  const marketLeft = compressed ? 88 : scale.positions.market;
  const rev = headlineReverse(report);
  const filteredReasons = (report.validation.reasons ?? []).filter(
    (r) => !(phased && rev.status === "CONVERGED" && r.toLowerCase().includes("reverse dcf"))
  );
  return <section className="valuation-range-surface" aria-label="Fair value range">
    <header><span>FAIR VALUE RANGE</span><ValueBadge value={report.validation.status} /><ValueBadge value={valuationState(report)} /></header>
    {report.validation.status === "PROVISIONAL" ? <p>{filteredReasons.length ? filteredReasons.join(" ") : "Headline 10-year reverse DCF converged; 5-year fixed-horizon check exceeded the 50% Year-1 cap."} <Link href={`/valuation/${report.company.ticker}?${new URLSearchParams({ ...Object.fromEntries(params), view: "validation" })}`}>Inspect validation →</Link></p> : null}
    <div className={`valuation-range-track${compressed ? " is-compressed" : ""}`}>
      <div className="valuation-range-line" />
      {(["bear", "base", "bull"] as const).map((key) => <div className={`valuation-range-point ${key}`} key={key} style={{ left: `${pointLeft(key)}%` }}><i /><span>{key}</span><strong>{money(values[key])}</strong></div>)}
      {price != null ? <div className="valuation-market-marker" style={{ left: `${marketLeft}%` }}><i>▲</i><span>Market {money(price)}{compressed && bull ? ` (${(price / bull).toFixed(1)}× bull)` : ""}</span></div> : null}
    </div>
    <footer><span>Bear {money(bear)}</span><span>Base {money(base)}</span><span>Bull {money(bull)}</span></footer>
    {phased ? <p>{report.fair_value?.reason}</p> : null}
  </section>;
}

function EconomicsModelMarket({ report, company }: { report: ValuationReport; company: CompanyEconomicsPayload | null }) {
  const economics = company ? adaptCompanyEconomics(company) : null;
  const baseGrowth = assumption(report, "year_1_revenue_growth");
  const baseMargin = assumption(report, "year_5_fcff_margin");
  const reverse = headlineReverse(report);
  const phased = report.fair_value?.method === "PHASED";
  const modelGrowthVal = phased && typeof report.fair_value?.observed_growth === "number" ? Math.min(report.fair_value.observed_growth, 0.50) : baseGrowth?.value;
  const rows = [
    { label: "Revenue Growth", observed: report.fair_value?.observed_growth ?? economics?.raw.growth_sustainability.current_revenue_growth, observedPeriod: "Trailing 12M / latest reported", model: modelGrowthVal, modelPeriod: phased ? "Headline 10-year blend Y1" : baseGrowth?.period, implied: reverse.required_5y_revenue_cagr ?? reverse.required_year_1_revenue_growth, impliedPeriod: reverse.status === "NO_ECONOMIC_SOLUTION" ? "Exceeds 50% Y1 cap at base margin" : "Reverse DCF implied growth" },
    { label: "FCFF Margin", observed: report.historical_base.fcff_margin, observedPeriod: String(report.historical_base.period_basis && typeof report.historical_base.period_basis === "object" ? (report.historical_base.period_basis as Record<string, unknown>).fcff || "Latest fiscal year" : "Latest fiscal year"), model: baseMargin?.value, modelPeriod: baseMargin?.period, implied: reverse.required_year_5_fcff_margin ?? (reverse.fixed_assumptions as Record<string, unknown> | undefined)?.year_5_fcff_margin, impliedPeriod: "Held at base target in solve" },
    { label: "Dilution", observed: null, observedPeriod: "Not directly observed in Company Economics", model: assumption(report, "annual_dilution")?.value, modelPeriod: "Annual through forecast", implied: reverse.annual_dilution || (reverse.fixed_assumptions as Record<string, unknown> | undefined)?.annual_dilution, impliedPeriod: "Fixed in reverse DCF" }
  ];
  return <section className="valuation-triad">
    <header><span>ECONOMICS / MODEL / MARKET</span><h2>Observed economics vs model assumptions vs market-implied expectations</h2><p>Read-only comparison. Use the Interactive Sandbox above to test custom assumptions.</p></header>
    <div className="valuation-triad-table"><header><span>Dimension</span><span>Observed</span><span>Model</span><span>Market-implied</span><span>Review</span></header>{rows.map((row) => {
      const observed = typeof row.observed === "number" ? row.observed : null;
      const model = typeof row.model === "number" ? row.model : null;
      const implied = typeof row.implied === "number" ? row.implied : null;
      const review = observed == null || model == null ? "Insufficient Evidence" : Math.abs(observed - model) < 0.03 ? "Supported" : observed > model ? "Model Conservative" : "Model Aggressive";
      const scale = Math.max(Math.abs(observed || 0), Math.abs(model || 0), Math.abs(implied || 0), 0.01);
      return <article key={row.label}><strong>{row.label}</strong><div><b style={{ width: `${Math.max(4, Math.abs((observed || 0) / scale) * 100)}%` }} />{pct(observed)}<small>{row.observedPeriod}</small></div><div><b style={{ width: `${Math.max(4, Math.abs((model || 0) / scale) * 100)}%` }} />{pct(model)}<small>{row.modelPeriod}</small></div><div><b style={{ width: `${Math.max(4, Math.abs((implied || 0) / scale) * 100)}%` }} />{pct(implied)}<small>{row.impliedPeriod}</small></div><ValueBadge value={review} /></article>;
    })}</div>
  </section>;
}

function Snapshot({ report, company }: { report: ValuationReport; company: CompanyEconomicsPayload | null }) {
  const money = moneyFormatter(report.company.currency);
  const economics = company ? adaptCompanyEconomics(company) : null;
  const rev = headlineReverse(report);
  return <div className="valuation-overview-grid">
    <FairValueRange report={report} />
    <section className="valuation-read-panel"><span>CURRENT READ</span><h2>{valuationState(report)}</h2><p>{report.final_interpretation.text || report.data_quality.reason || report.fallback?.why_standard_dcf_is_inappropriate}</p><dl><div><dt>Market price</dt><dd>{money(report.company.current_market_price)}</dd></div><div><dt>Validation</dt><dd>{humanize(report.validation.status)}</dd></div><div><dt>Reverse DCF</dt><dd>{humanize(String(rev.status || "Unavailable"))}</dd></div></dl></section>
    <section className="valuation-mini-ledger"><span>OBSERVED ECONOMICS</span><dl><div><dt>Revenue growth</dt><dd>{pct(report.fair_value?.observed_growth ?? economics?.raw.growth_sustainability.current_revenue_growth ?? report.historical_base.current_provider_revenue_growth)}</dd></div><div><dt>FCFF margin</dt><dd>{pct(report.historical_base.fcff_margin)}</dd></div><div><dt>Constraint</dt><dd>{economics?.primaryConstraint.label || "See operating signals"}</dd></div><div><dt>Scaling</dt><dd>{economics?.raw.scaling_economics.interpretation || "Unavailable"}</dd></div></dl></section>
    <section className="valuation-mini-ledger"><span>MODEL ASSUMPTIONS</span><dl>{["year_1_revenue_growth", "year_5_fcff_margin", "wacc", "terminal_growth", "annual_dilution"].map((name) => <div key={name}><dt>{humanize(name)}</dt><dd>{assumption(report, name)?.unit === "multiple" ? number(assumption(report, name)?.value) : pct(assumption(report, name)?.value)}</dd></div>)}</dl></section>
    <section className="valuation-mini-ledger market-implied"><span>MARKET-IMPLIED EXPECTATIONS</span><dl><div><dt>Solved variable</dt><dd>{String(rev.solved_variable || "Year-1 revenue growth")}</dd></div><div><dt>Status</dt><dd>{humanize(String(rev.status || "Unavailable"))}</dd></div><div><dt>Required 5Y revenue CAGR</dt><dd>{pct(rev.required_5y_revenue_cagr)}</dd></div><div><dt>{rev.high_case_value != null ? "Max value at 50% Y1 growth" : "Solved Year-1 growth"}</dt><dd>{rev.high_case_value != null ? money(rev.high_case_value) : pct(rev.required_year_1_revenue_growth)}</dd></div></dl></section>
  </div>;
}

function DcfWorkspace({ report }: { report: ValuationReport }) {
  const money = moneyFormatter(report.company.currency);
  const tenYearForecast = report.fair_value?.ten_year_forecast;
  const phased = report.fair_value?.method === "PHASED" && Array.isArray(tenYearForecast) && tenYearForecast.length > 0;
  const [horizonMode, setHorizonMode] = useState<"headline" | "five">("headline");
  if (!hasScenarios(report)) return <><FairValueRange report={report} /><FcffReconciliation report={report} /></>;
  const scenarios = report.scenarios as Record<"bear" | "base" | "bull", ScenarioResult>;
  const base = scenarios.base;
  const showingTen = phased && horizonMode === "headline";
  const forecastRows: ForecastRow[] = showingTen ? (tenYearForecast as ForecastRow[]) : base.forecast;

  return <div className="valuation-workspace-page">
    <section className="valuation-section"><header><span>HISTORICAL BASE</span><h2>Operating base and period consistency</h2></header><div className="valuation-kpi-grid">{[["Revenue", money(report.historical_base.latest_annual_revenue)], ["3Y revenue CAGR", pct(report.historical_base.three_year_revenue_cagr)], ["Operating margin", pct(report.historical_base.operating_margin)], ["FCFF margin", pct(report.historical_base.fcff_margin)], ["OCF", money(report.historical_base.operating_cash_flow)], ["Capex", money(report.historical_base.capital_expenditure)], ["Cash", money(report.historical_base.cash)], ["Debt", money(report.historical_base.debt)], ["Shares", sharesFormatter(report.historical_base.diluted_shares)]].map(([k, v]) => <article key={k}><span>{k}</span><strong>{v}</strong></article>)}</div><p>{String(report.historical_base.period_consistency || "Period consistency unavailable.")}</p></section>
    <FcffReconciliation report={report} />
    <section className="valuation-section">
      <header>
        <div>
          <span>FORECAST</span>
          <h2>{showingTen ? "Ten-year extended revenue and FCFF path (headline model)" : "Five-year revenue and FCFF path"}</h2>
        </div>
        {phased ? (
          <div className="mkt-horizons" role="tablist" aria-label="Forecast horizon">
            <button type="button" role="tab" aria-selected={showingTen} className={showingTen ? "active" : ""} onClick={() => setHorizonMode("headline")}>10Y Headline ({Math.round((report.fair_value?.extended_weight ?? 1) * 100)}% weight)</button>
            <button type="button" role="tab" aria-selected={!showingTen} className={!showingTen ? "active" : ""} onClick={() => setHorizonMode("five")}>5Y Standard</button>
          </div>
        ) : null}
      </header>
      <ForecastTable rows={forecastRows} currency={report.company.currency} />
    </section>
    <DiscountTerminal report={report} />
    <ScenarioComparison report={report} useHeadline={showingTen} />
  </div>;
}

function FcffReconciliation({ report }: { report: ValuationReport }) {
  const money = moneyFormatter(report.company.currency);
  const r = report.historical_fcff_reconciliation;
  return <section className="valuation-section fcff-reconciliation"><header><span>FCFF RECONCILIATION</span><h2>{humanize(String(r.status || "Unavailable"))}</h2><ValueBadge value={String(r.status || "UNAVAILABLE")} /></header><div className="fcff-bridge">{[["NOPAT", r.nopat], ["+ D&A", r.depreciation_and_amortization], ["- Capex", r.capex], ["− Change in Working Capital", r.change_in_working_capital], ["± Other Adjustments", r.other_adjustments], ["+ SBC Addback", r.sbc_addback], ["= Calculated FCFF", r.calculated_fcff], ["After-tax Interest (CFO bridge)", r.after_tax_interest], ["Operating Cash Flow minus Capex", r.operating_cash_flow_minus_capex], ["Difference vs OCF minus Capex", r.difference_vs_operating_cash_flow_minus_capex], ["CFO-based FCFF", r.cfo_based_fcff], ["Reconciliation Difference", r.reconciliation_difference]].map(([label, value]) => <article key={String(label)}><span>{String(label)}</span><strong>{money(value)}</strong></article>)}</div><p>{String(r.reason || "No reconciliation detail available.")}</p><small>{String(r.sbc_treatment || "")} {String(r.tolerance_policy || "")}</small></section>;
}

function ForecastTable({ rows, currency }: { rows: ForecastRow[]; currency?: string }) {
  const money = moneyFormatter(currency);
  return <div className="valuation-table forecast-table"><header><span>Year</span><span>Revenue Growth</span><span>Revenue</span><span>FCFF Margin</span><span>FCFF</span><span>PV</span></header>{rows.map((row) => <article key={row.year}><strong>Y{row.year}</strong><span>{pct(row.revenue_growth)}</span><span>{money(row.revenue)}</span><span>{pct(row.fcff_margin)}</span><span>{money(row.fcff)}</span><span>{money(row.present_value)}</span></article>)}</div>;
}

function DiscountTerminal({ report }: { report: ValuationReport }) {
  const money = moneyFormatter(report.company.currency);
  if (!hasScenarios(report)) return null;
  const scenarios = report.scenarios as Record<"bear" | "base" | "bull", ScenarioResult>;
  const base = scenarios.base;
  const terminalShare = base.pv_terminal_value / base.enterprise_value;
  return <section className="valuation-section discount-terminal"><header><span>DISCOUNT RATE / TERMINAL VALUE</span><h2>WACC and terminal dependence</h2></header><div className="valuation-kpi-grid">{[["Risk-free rate", pct(report.discount_rate.risk_free_rate)], ["ERP", pct(report.discount_rate.equity_risk_premium)], ["Beta", number(report.discount_rate.beta)], ["Cost of equity", pct(report.discount_rate.cost_of_equity)], ["After-tax debt", pct(report.discount_rate.after_tax_cost_of_debt)], ["Debt weight", pct(report.discount_rate.debt_weight)], ["WACC", pct(report.discount_rate.wacc)], ["Terminal growth", pct(assumption(report, "terminal_growth")?.value)], ["PV terminal / EV (5Y)", pct(terminalShare)], ["Exit multiple cross-check", `${number(base.exit_multiple)}x`], ["Exit value (5Y)", money(base.exit_fair_value_per_share)], ["Gordon vs exit", money(base.terminal_method_difference)]].map(([k, v]) => <article key={k}><span>{k}</span><strong>{v}</strong></article>)}</div><p>{(report.discount_rate.fallbacks as string[] | undefined)?.length ? `Fallbacks used: ${(report.discount_rate.fallbacks as string[]).join(", ")}` : "No discount-rate fallbacks are used in this benchmark fixture."}</p></section>;
}

function ScenarioComparison({ report, useHeadline = false }: { report: ValuationReport; useHeadline?: boolean }) {
  const money = moneyFormatter(report.company.currency);
  if (!hasScenarios(report)) return null;
  const scenarios = report.scenarios as Record<"bear" | "base" | "bull", ScenarioResult>;
  const headlineVals = headlineFairValues(report);
  return <section className="valuation-section"><header><span>SCENARIO COMPARISON</span><h2>Assumptions behind Bear / Base / Bull{useHeadline ? " (Headline 10Y blend)" : ""}</h2></header><div className="valuation-table scenario-table"><header><span>Scenario</span><span>Y1 Growth</span><span>Target Margin</span><span>WACC</span><span>Terminal</span><span>Dilution</span><span>Fair Value</span></header>{(["bear", "base", "bull"] as const).map((name) => {
    const items = report.assumptions[name] as Array<{ name: string; value: number }>;
    const get = (key: string) => items.find((item) => item.name === key)?.value;
    const fv = useHeadline && headlineVals[name] != null ? headlineVals[name] : scenarios[name].fair_value_per_share;
    return <article key={name}><strong>{name}</strong><span>{pct(get("year_1_revenue_growth"))}</span><span>{pct(get("year_5_fcff_margin"))}</span><span>{pct(get("wacc"))}</span><span>{pct(get("terminal_growth"))}</span><span>{pct(get("annual_dilution"))}</span><span>{money(fv)}</span></article>;
  })}</div></section>;
}

function Assumptions({ report }: { report: ValuationReport }) {
  return <section className="valuation-section"><header><span>ASSUMPTION INSPECTOR</span><h2>Why each base-case number is here</h2></header><div className="assumption-inspector-list">{baseAssumptions(report).map((item) => <article key={item.name}><span>{humanize(item.name)}</span><strong>{item.unit === "multiple" ? `${number(item.value)}x` : item.unit === "decimal" ? pct(item.value) : String(item.value)}</strong><dl><div><dt>Source</dt><dd>{cleanSource(item.source)}</dd></div><div><dt>Basis</dt><dd>{item.basis}</dd></div><div><dt>Confidence</dt><dd>{humanize(item.confidence)}</dd></div><div><dt>Period</dt><dd>{item.period}</dd></div><div><dt>Override</dt><dd>{item.overridden ? "User override" : "Model default"}</dd></div></dl></article>)}</div></section>;
}

function ReverseDcf({ report, company }: { report: ValuationReport; company: CompanyEconomicsPayload | null }) {
  const money = moneyFormatter(report.company.currency);
  const reverse = headlineReverse(report);
  const economics = company ? adaptCompanyEconomics(company) : null;
  return <section className="valuation-section reverse-dcf-workspace"><header><span>MARKET-IMPLIED EXPECTATIONS</span><h2>{reverse.status === "NO_ECONOMIC_SOLUTION" ? "Market price exceeds the 50% Year-1 growth bound at base margin & WACC" : humanize(String(reverse.status || "Reverse DCF unavailable"))}</h2><ValueBadge value={String(reverse.status || "UNAVAILABLE")} /></header><div className="valuation-kpi-grid">{[["Current price", money(report.company.current_market_price)], ["Solved variable", String(reverse.solved_variable || "Year-1 revenue growth")], ["Search bounds", Array.isArray((reverse.search_bounds as Record<string, unknown> | undefined)?.year_1_revenue_growth) ? `${pct(((reverse.search_bounds as Record<string, number[]>).year_1_revenue_growth)[0])} to ${pct(((reverse.search_bounds as Record<string, number[]>).year_1_revenue_growth)[1])}` : "−20.0% to 50.0%"], ["Solved 5Y CAGR", pct(reverse.required_5y_revenue_cagr)], ["Year-1 growth", pct(reverse.required_year_1_revenue_growth)], ["Max value at 50% Y1", money(reverse.high_case_value)], ["Residual", money(reverse.residual_per_share)], ["Observed revenue growth", pct(report.fair_value?.observed_growth ?? economics?.raw.growth_sustainability.current_revenue_growth)]].map(([k, v]) => <article key={k}><span>{k}</span><strong>{v}</strong></article>)}</div><p>{String(reverse.reason || "Other assumptions remain fixed; use the Interactive Sandbox on Overview to adjust margin and WACC alongside growth.")}</p>{reverse.status === "NO_ECONOMIC_SOLUTION" ? <ul className="valuation-explain-list"><li>Fixed base-case margin assumption may be more conservative than market pricing.</li><li>4.5% fixed equity risk premium may produce a higher WACC than the market currently applies.</li><li>Market may be pricing multi-decade compounding beyond the 50% Year-1 growth bound.</li></ul> : null}</section>;
}

function Sensitivity({ report, cell, fixture = false }: { report: ValuationReport; cell?: string; fixture?: boolean }) {
  const money = moneyFormatter(report.company.currency);
  if (!hasScenarios(report)) return <FairValueRange report={report} />;
  const [rowIndex, colIndex] = (cell || "2-2").split("-").map((part) => Number(part));
  const selected = report.sensitivity.values?.[rowIndex]?.[colIndex];
  const selectedWacc = report.sensitivity.wacc?.[rowIndex];
  const selectedTerminal = report.sensitivity.terminal_growth?.[colIndex];
  return <section className="valuation-section sensitivity-workspace"><header><span>SENSITIVITY</span><h2>WACC × Terminal Growth</h2></header><div className="sensitivity-layout"><div className="sensitivity-matrix"><header><span>WACC \ Terminal</span>{report.sensitivity.terminal_growth?.map((terminal) => <strong key={terminal}>{pct(terminal)}</strong>)}</header>{report.sensitivity.wacc?.map((wacc, r) => <article key={wacc}><strong>{pct(wacc)}</strong>{report.sensitivity.values?.[r]?.map((value, c) => <Link className={r === rowIndex && c === colIndex ? "active" : ""} href={`/valuation/${report.company.ticker}?view=sensitivity&cell=${r}-${c}${fixture ? "&fixture=1" : ""}`} key={`${r}-${c}`}>{money(value)}</Link>)}</article>)}</div><aside className="sensitivity-inspector"><span>CELL INSPECTOR</span><h3>{money(selected)}</h3><dl><div><dt>WACC</dt><dd>{pct(selectedWacc)}</dd></div><div><dt>Terminal growth</dt><dd>{pct(selectedTerminal)}</dd></div><div><dt>Delta vs market</dt><dd>{typeof selected === "number" && report.company.current_market_price ? pct(selected / report.company.current_market_price - 1) : "—"}</dd></div></dl><p>{report.sensitivity.calculation}</p></aside></div></section>;
}

function Validation({ report }: { report: ValuationReport }) {
  const checks = Object.entries(report.validation.checks || {});
  return <section className="valuation-section validation-workspace"><header><span>VALIDATION</span><h2>{humanize(report.validation.status)}</h2><ValueBadge value={report.validation.status} /></header><div className="validation-check-grid">{checks.map(([key, check]) => <article key={key}><ValueBadge value={check.passed ? "PASSED" : "PROVISIONAL"} /><strong>{humanize(key)}</strong><p>{check.detail}</p></article>)}</div>{report.validation.reasons?.length ? <div className="valuation-explain-list">{report.validation.reasons.map((reason) => <p key={reason}>{reason}</p>)}</div> : null}</section>;
}

function EvidenceQuality({ report }: { report: ValuationReport }) {
  return <div className="valuation-workspace-page"><section className="valuation-section"><header><span>DATA QUALITY</span><h2>{humanize(report.data_quality.status)}</h2></header><p>{report.data_quality.reason}</p><dl className="valuation-quality-dl"><div><dt>As of</dt><dd>{report.company.as_of}</dd></div><div><dt>Financial periods</dt><dd>{Object.values((report.historical_base.period_basis || {}) as Record<string, unknown>).slice(0, 4).join(" / ") || "Unavailable"}</dd></div><div><dt>Fallbacks</dt><dd>{(report.discount_rate.fallbacks as string[] | undefined)?.join(", ") || "None in benchmark fixture"}</dd></div><div><dt>Missing</dt><dd>{report.data_quality.missing?.join(", ") || "None disclosed"}</dd></div></dl></section><Assumptions report={report} /></div>;
}

function FullReport({ report }: { report: ValuationReport }) {
  return <div className="valuation-report-mode"><section><span>FULL VALUATION REPORT</span><h2>{report.company.ticker} intrinsic valuation</h2><p>{report.final_interpretation.text || report.data_quality.reason}</p></section><DcfWorkspace report={report} /><ReverseDcf report={report} company={null} /><Sensitivity report={report} /><Validation report={report} /></div>;
}

export function ValuationResearchPage({ report, company, view = "overview", dataState = "FIXTURE", from, cell }: { report: ValuationReport; company: CompanyEconomicsPayload | null; view?: ValuationView; dataState?: ResearchDataState; from?: string; cell?: string }) {
  const money = moneyFormatter(report.company.currency);
  if (report.validation.status === "FAILED") report = { ...report, scenarios: {}, sensitivity: {}, reverse_dcf: { status: "VALIDATION_FAILED" }, final_interpretation: { text: `Fair value withheld: ${report.validation.reasons?.join(" ") || report.data_quality.reason || "Critical validation failed."}` } };
  return <ResearchShell active="valuation" ticker={report.company.ticker} dataState={dataState}>
    <div className="valuation-research-surface">
      <header className="valuation-object-header">
        <div>
          <div className="valuation-crumb-row">
            <Link className="valuation-back" href={`/company/${report.company.ticker}`}>← {report.company.ticker} company page</Link>
            <span>VALUATION / {report.company.ticker}{from ? ` · FROM ${from.toUpperCase()}` : ""}</span>
          </div>
          <h1>{report.company.name}</h1>
          <p>{report.selected_method}</p>
        </div>
        <aside><ValueBadge value={valuationState(report)} /><strong>{money(report.company.current_market_price)}</strong><small>Current / latest available market price</small></aside>
      </header>
      <ViewNav ticker={report.company.ticker} view={view} fixture={dataState === "FIXTURE"} />
      {report.unit_bridge?.note ? <p className="valuation-unit-note">{report.unit_bridge.note} Quoted price {report.unit_bridge.quote_price != null ? `$${report.unit_bridge.quote_price.toFixed(2)}` : "—"}.</p> : null}
      <p className="valuation-meta-strip" role="status"><ValueBadge value={report.validation.status} /> Source: {dataState} · Report as of: {report.company.as_of || "unavailable"} · <Link href={`/company/${report.company.ticker}?view=economics${dataState === "FIXTURE" ? "&fixture=1" : ""}`}>Company Economics →</Link></p>
      {view === "overview" ? <><Snapshot report={report} company={company} /><InteractiveValuationSandbox report={report} /><EconomicsModelMarket report={report} company={company} /></> : null}
      {view === "economics-model" ? <EconomicsModelMarket report={report} company={company} /> : null}
      {view === "dcf" ? <DcfWorkspace report={report} /> : null}
      {view === "assumptions" ? <Assumptions report={report} /> : null}
      {view === "reverse-dcf" ? <ReverseDcf report={report} company={company} /> : null}
      {view === "sensitivity" ? <Sensitivity report={report} cell={cell} fixture={dataState === "FIXTURE"} /> : null}
      {view === "validation" ? <><Validation report={report} /><FcffReconciliation report={report} /></> : null}
      {view === "evidence" ? <EvidenceQuality report={report} /> : null}
      {view === "report" ? <FullReport report={report} /> : null}
    </div>
  </ResearchShell>;
}
