# CHAINSTOX Valuation Architecture

Updated: 2026-08-09.

## Current Valuation UX Audit

Before Phase 5, the backend valuation engine was substantially richer than the frontend. `intrinsic_valuation.py` already exposed company-type routing, historical base, FCFF reconciliation, scenario assumptions, WACC, terminal value, sensitivity, reverse DCF, cross-checks, validation, data quality, and framework-required fallbacks. The frontend only showed a thin valuation index plus a Company Economics valuation workspace that carried assumption-review and market-expectations summaries.

Old frontend gaps:

- Bear/Base/Bull range was not shown from intrinsic valuation JSON.
- DCF mechanics, forecast path, terminal value, WACC, and FCFF reconciliation were not first-class.
- Reverse DCF was present only as a Company Economics summary.
- Sensitivity and validation were effectively unavailable in direct UI.
- Framework-required states were clearer in Company resolver than in Valuation.
- Dashboard valuation flags linked to company valuation context rather than the unified valuation object.

## Backend Schema Audit

`intrinsic_valuation.py` valuation JSON fields:

- `company`, `security_type`, `company_type`, `selected_method`
- `valuation_method_selection`
- `historical_base`
- `historical_fcff_reconciliation`
- `assumptions` with Bear/Base/Bull plus policy assumptions
- `discount_rate`
- `scenarios`
- `sensitivity`
- `reverse_dcf`
- `cross_checks`
- `risks`
- `fair_value_drivers`
- `final_interpretation`
- `validation` / `internal_validation`
- `data_quality`
- `fallback`

Unsupported framework states include financial institutions, REITs, pre-profit companies, ETFs/funds, SPAC/shell structures, and insufficient verified data. These must not be forced through generic FCFF DCF.

Assumptions carry value, unit, source, basis, confidence, scenario, period, and override status. Reverse DCF carries solved variable, fixed assumptions, search bounds, status, residual, and solved result when converged. Validation carries named checks and reasons. Data quality carries missing fields, provider/fallback context, and failure reasons.

## Phase 5 Object Model

```text
Company Economics
  → Model Assumptions
  → Intrinsic Value
  → Market-Implied Expectations
  → Assumption Gap
  → Sensitivity
  → Validation
  → Evidence
```

Routes:

- `/valuation`
- `/valuation/[ticker]`
- `/valuation/[ticker]?view=economics-model`
- `/valuation/[ticker]?view=dcf`
- `/valuation/[ticker]?view=assumptions`
- `/valuation/[ticker]?view=reverse-dcf`
- `/valuation/[ticker]?view=sensitivity`
- `/valuation/[ticker]?view=validation`
- `/valuation/[ticker]?view=evidence`
- `/valuation/[ticker]?view=report`

Company, Dashboard, Markets-to-company paths, and Global Search route into the same valuation object.

## Surface Coverage

Valuation Snapshot:

- Current price
- Bear/Base/Bull fair-value range
- Market marker versus scenario range
- Valuation state
- Observed economics
- Base-case model assumptions
- Market-implied expectations
- Validation and reverse DCF state

Economics / Model / Market triad:

- Observed company economics
- Base-case DCF assumptions
- Market-implied expectations
- Period labels and read-only review

DCF workspace:

- Historical operating base
- FCFF reconciliation bridge
- Forecast table
- Discount-rate inspector
- Terminal-value analysis
- Scenario comparison

Reverse DCF:

- Current price
- Solved variable
- Search bounds
- Fixed assumptions
- Solver status
- Solved result and residual
- Observed economics comparison
- `NO_ECONOMIC_SOLUTION` as analytical state, not software failure

Sensitivity:

- WACC × Terminal Growth matrix
- Exact fair value per cell
- Base/current selected cell
- Cell inspector with WACC, terminal growth, and delta versus market

Validation:

- Forecast arithmetic
- Terminal value
- EV-to-equity bridge
- Share count
- Scenario ordering
- WACC above terminal growth
- Reverse DCF convergence
- Period consistency
- Sensitivity monotonicity
- FCFF reconciliation

Evidence and Data Quality:

- As-of and period basis
- Missing fields
- Discount-rate fallbacks
- FCFF policy and assumption provenance
- Framework-routing evidence

## Read-Only Boundary

Company Economics reviews valuation assumptions and market-implied expectations. It does not mutate DCF inputs. Manual overrides remain explicit backend valuation options and are displayed through assumption `overridden` metadata when present.

## Benchmark Fixtures

`frontend/lib/fixtures/valuation-research.json` is generated from the existing Python intrinsic valuation engine using deterministic test fixture inputs. It is a UX validation benchmark, not a second valuation engine.

Benchmarks:

- MSFT: converged DCF, passed validation.
- GOOG: FCFF/SBC reconciliation benchmark, converged DCF.
- PLTR: market price above scenario range, reverse DCF `NO_ECONOMIC_SOLUTION`.
- NVDA: cross-company no-solution reverse DCF state.
- COST: supported converged valuation.
- XOM: cyclical-company valuation.
- JPM: financial-institution `FRAMEWORK REQUIRED`.

Live Yahoo/provider access returned 429 rate limits during Phase 5 validation. The UI therefore keeps live insufficient-data states visible and uses deterministic fixtures for interaction QA.

## Validation

`npm run smoke:valuation` captures 24 screenshots:

1. Valuation Search
2. MSFT Valuation Snapshot
3. Fair Value Range
4. Economics vs Model
5. Economics / Model / Market triad
6. MSFT DCF workspace
7. Historical base
8. FCFF reconciliation
9. Forecast
10. Discount Rate Inspector
11. Terminal Value
12. Scenario Comparison
13. Reverse DCF
14. Reverse DCF No-Solution
15. Sensitivity matrix
16. Sensitivity cell inspector
17. Validation workspace
18. Data Quality / Fallback inspector
19. GOOG valuation
20. PLTR valuation from Company Economics
21. Framework Required state
22. Full Report
23. Mobile Valuation Snapshot
24. Mobile Reverse DCF
