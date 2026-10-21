# CHAINSTOX Valuation Method Governance

Review date: 2026-10-21 (Asia/Kuala_Lumpur). Scope: existing implementation, not a new valuation model. Source authority: `intrinsic_valuation.py`, SEC extraction, existing controlled tests, and the Phase 6.2 reproduction below. No WACC, SBC, growth, terminal, CapEx, or reverse-solver formula was changed.

## G1 — Cost of debt and WACC

**Classification: MODEL ASSUMPTION / INSUFFICIENT EVIDENCE for forward borrowing cost.**

- **Current implementation:** `_market_rates` uses latest annual interest expense / reported debt, clamped to 2.5%–12%; fallback 5.5%. After-tax debt cost multiplies by `(1-effective tax rate)`. Equity cost is risk-free + beta × 4.5% ERP. Risk-free comes from ^TNX or 4.3% fallback; beta defaults to 1. Equity weight uses market capitalization; debt weight uses reported debt. `_base_parameters` bounds WACC to 6.5%–15%; scenario bounds are 5.5%–18%.
- **Interpretation:** embedded historical borrowing cost is being used as a forward proxy. Numerator is a flow; denominator is a balance-sheet stock, not average debt. Dates are not independently reconciled for this ratio. Floating-rate resets, currency matching, refinancing spreads, and market debt value are not explicitly modeled. Complete SEC debt coverage is now required before the bridge, but completeness alone does not establish aligned interest periods.
- **Potential distortion / materiality:** material for leveraged businesses, refinancing changes, and long-duration cash flows. Both fallback assumptions and clipping can dominate an apparently precise WACC. With interest 5 and debt 100, pre-tax cost is 5%; at 21% tax it is 3.95%. Interest 20 / debt 100 is clipped from 20% to 12%.
- **Reproduction:** inspect `_market_rates`, `_base_parameters`, `_scenario_assumptions`; reproduce the stated ratios without changing the engine. Existing discount-rate fallback disclosures are retained; the detailed distinction is recorded here.
- **Alternative / trade-offs:** contemporaneous traded bond yield, or aligned risk-free plus evidenced credit spread, better targets marginal financing cost but requires debt currency, maturity, liquidity, and credit evidence. A synthetic rating is not a validated substitute merely because it is available. [Damodaran’s cost-of-debt material](https://pages.stern.nyu.edu/~adamodar/pdfiles/country/Brcapstr.pdf) defines the concept as the current market borrowing rate.
- **Recommendation:** retain the proxy with explicit limitations; design a source hierarchy and period checks before replacing it.
- **Implementation status:** reviewed; economic change deferred.
- **Required approval:** Product Owner approval for proxy hierarchy, bounds, ERP, debt weights, or spread methodology.
- **Tests needed:** dated debt/interest alignment, floating/fixed debt examples, currency matching, observable yield comparison, sensitivity to bounds.

## G2 — Five-year forecast and growth fade

**Classification: DESIGN CHOICE / MODEL ASSUMPTION.**

- **Current implementation:** five explicit years. `growth_y = growth_1 + (terminal_growth + 1% - growth_1) × (y-1)/4`; margin linearly converges to target over five years. Terminal FCFF grows at terminal growth after year five. Base terminal growth 2.5%. This is not an estimated competitive-advantage period.
- **Interpretation:** rapid transition to a fixed steady-state policy. Forecast length, growth persistence, and investment duration are conflated by the fixed five-year path.
- **Reproduction:** controlled fixture on 2026-10-21, data from `tests/test_intrinsic_valuation.py::fixture_data`: 12%, 9.875%, 7.75%, 5.625%, 3.5% growth for mature/growth cases. Cyclical case starts at 8%, then 6.875%, 5.75%, 4.625%, 3.5%. These are synthetic observations, not company estimates.
- **Potential distortion / materiality:** material where durable growth or investment cycles differ from five years. Extending the horizon can raise or lower value depending on reinvestment and margins; a higher result is not validation.
- **Alternative / trade-offs:** separately model explicit horizon, persistence, maturation, and reinvestment, requiring much stronger evidence and more assumptions.
- **Recommendation:** preserve current horizon; propose a separately governed multi-stage design only after benchmarking.
- **Implementation status:** reviewed; unchanged.
- **Required approval:** any horizon, fade, target margin, or terminal policy change.
- **Tests needed:** six archetypes below, reinvestment constraints, terminal continuity and sensitivity.

| Archetype | Current route under ordinary positive operating evidence | Material limitation |
|---|---|---|
| Growth software | Growth software when classification thresholds pass | Fixed convergence may suppress persistence; SBC economics matter |
| Mature software | Mature operating | Competitive durability not explicitly estimated |
| Fabless semiconductor | Generally mature operating | Cyclicality and outsourced capacity commitments are not a dedicated model |
| Foundry | Generally mature operating | Multi-year capacity investment is embedded in margins, not a capacity model |
| Retail | Generally mature operating | Working capital and lease economics need company-specific review |
| Energy | Cyclical when industry terms match | Mid-cycle blend is not a reserves/commodity-price model |

Routes depend on actual metadata; this table is not ticker-specific routing authorization.

## G3 — SBC and dilution

**Classification: MODEL ASSUMPTION; bookkeeping tests pass, economic sufficiency unverified.**

- **Current implementation:** accounting-FCFF adds SBC back once to NOPAT cash flow and retains it in CFO; annual dilution is 0.5% for growth software and 0.1% for other supported types, with scenario spreads. Owner-earnings retains SBC as an expense (subtracts it from CFO-based FCFF) and disables forecast dilution. All equity value is divided by shares compounded for five years. Repurchase cash costs, gross grants, vesting, option terms, and net issuance are not separately forecast.
- **Interpretation:** two explicit conventions. The first relies on a fixed dilution assumption to capture employee equity cost; the second treats SBC as a cash-like expense. NOPAT already contains the compensation expense, so owner earnings must not subtract it a second time.
- **Reproduction:** synthetic fixture dated 2026-07-23, executed 2026-10-21: accounting NOPAT FCFF 166 vs CFO FCFF 165.8; owner-earnings 146 vs 145.8. Both residuals 0.2. Starting shares 100 become 102.525125 at 0.5% annual dilution or 100.501001 at 0.1%.
- **Potential distortion / materiality:** high for SBC-heavy companies. A fixed five-year share adjustment does not prove appropriate treatment of existing options, future grants, repurchases, tax benefits, or terminal-period dilution. The model’s double-count check is an accounting consistency check, not economic validation. [Damodaran’s management-options discussion](https://pages.stern.nyu.edu/adamodar/New_Home_Page/valquestions/mgtoption.htm) distinguishes equity claims from simple diluted-share counting.
- **Alternative / trade-offs:** grant/vesting/repurchase and share-roll-forward evidence, or consistently expensed SBC with separately valued existing claims. More faithful but data intensive. `SBC / market cap` is not adopted as net dilution.
- **Recommendation:** retain both clearly labeled policies; require dilution evidence before stronger confidence.
- **Implementation status:** reviewed; unchanged.
- **Required approval:** any policy default, dilution schedule, terminal dilution, option valuation, or tax adjustment change.
- **Tests needed:** dated net share issuance, repurchase funding, grants versus vesting, SBC tax reconciliation, terminal treatment, both policies.

## G4 — FCFF versus FCFE and reconciliation

**Classification: DESIGN CHOICE; critical missing-input and mismatch gates ALREADY RESOLVED.**

- **Current implementation:** NOPAT + D&A − CapEx − investment in working capital + explicit other noncash adjustments, with explicit SBC policy. CFO route adds after-tax interest to CFO − CapEx; owner earnings additionally subtracts SBC. FCFF is discounted at WACC; cash is added, debt and senior claims deducted before share conversion. No FCFE engine is introduced.
- **Interpretation:** unlevered operating cash flow and enterprise-to-equity bridge are internally consistent under the chosen definitions. CFO − CapEx alone is not labeled unlevered FCFF. The tax and interest classification assumptions still need statement-level evidence, particularly across accounting regimes.
- **Reproduction:** NOPAT 158, D&A 40, CapEx 60, working-capital investment 10, other adjustments 18, SBC 20 gives accounting FCFF 166. CFO 210 − CapEx 60 = 150; add after-tax interest 15.8 → 165.8. Difference from raw CFO−CapEx is 16, of which 15.8 is the disclosed interest bridge and 0.2 is residual. Tolerance is max(5% of larger absolute FCFF, 1% revenue), here 10.
- **Potential distortion / materiality:** revenue-based tolerance can be permissive when FCFF is small. Deferred taxes and nonoperating items can differ in definition. Reconciliation is latest-period, not a multi-year reconciliation audit.
- **Alternative / trade-offs:** dated multi-period bridges and a tighter materiality policy improve scrutiny but require data and policy approval.
- **Recommendation:** preserve the hard gate and displayed raw OCF comparison; review tolerance separately rather than changing it to force acceptance.
- **Implementation status:** economic formulas unchanged; frontend now exposes after-tax interest, raw OCF−CapEx comparison, and failed-report diagnostics.
- **Required approval:** tolerance, tax/interest classification assumptions, multi-year normalization, or FCFE expansion.
- **Tests needed:** existing mismatch, missing-input, SBC, statement-alias, debt-coverage and EV-equity tests; future IFRS interest-classification cases.

## G5 — Reverse DCF

**Classification: DESIGN CHOICE.**

- **Current implementation:** solves year-one revenue growth within −20% to +50%, with the existing five-year fade. WACC, terminal growth, target margin, and dilution stay fixed. Bisection allows 80 iterations and $0.005/share residual. Missing price, unstable cash flow, unbracketed solution, nonconvergence, and boundary solution remain explicit.
- **Interpretation:** a conditional one-variable solve; the reported five-year CAGR is derived, not the solved variable. `NO_ECONOMIC_SOLUTION` means no solution inside the tested assumptions/bounds, not proof that market expectations are irrational.
- **Reproduction:** existing converged-residual and no-solution tests; PLTR fixture produces NO_ECONOMIC_SOLUTION and remains PROVISIONAL. Missing-price case remains NO_MARKET_PRICE. Positive supported margins produce a monotonic growth-value relationship within the controlled benchmarks, not a universal theorem for arbitrary cash flows.
- **Potential distortion / materiality:** high if users interpret the solved number as a unique market forecast or ignore fixed margin assumptions.
- **Alternative / trade-offs:** separate implied-margin, implied-duration, and feasible-combination modes would expose conditionality but expand model scope.
- **Recommendation:** preserve solver and no-solution states; defer new modes.
- **Implementation status:** reviewed; unchanged.
- **Required approval:** new modes, growth bounds, numerical tolerance, or fixed-assumption policy.
- **Tests needed:** current bracket, residual, boundary, nonconvergence, missing price, and negative base tests; future evidence for alternative modes.

## G6 — CapEx and normalization

**Classification: MODEL ASSUMPTION / PROPOSED ENHANCEMENT.**

- **Current implementation:** latest reported CapEx is deducted in historical FCFF. Forecast investment is embedded in FCFF-margin convergence. Cyclical target blends historical after-tax operating margin with current FCFF margin. Maintenance/growth CapEx and infrastructure capitalization are not independently split.
- **Interpretation:** cash investment is preserved, but a one-period capital-spending shock influences the starting margin and can fade mechanically without an explicit investment schedule.
- **Reproduction:** in the G4 synthetic bridge, increasing CapEx from 60 to 100 reduces both FCFF routes by 40 if the same reported CFO is retained; no adjustment is allowed merely because value falls. `_base_parameters` subsequently applies its existing margin policy.
- **Potential distortion / materiality:** high for foundries, infrastructure, retail expansion and energy; D&A is not automatically maintenance CapEx.
- **Alternative / trade-offs:** multi-year capital-intensity evidence, maintenance/growth disclosures and investment cohorts; more explanatory but much more data dependent.
- **Recommendation:** retain observed spending. Prepare an evidence-led reinvestment design separately.
- **Implementation status:** reviewed; unchanged.
- **Required approval:** any normalization or forecast reinvestment policy change.
- **Tests needed:** dated multi-year CapEx, capitalization consistency, acquisitions versus operating investment, working-capital interaction.

## G7 — Critical validation classification

**Classification: CONFIRMED DEFECT. Implementation status: FIXED.**

`_validate` previously labeled every nonpassing result PROVISIONAL, including arithmetic and EV-equity failures. A controlled +100 corruption of forecast PV reproduces the issue. Critical arithmetic, terminal identity, share count, ordering, bridge and WACC/terminal consistency failures now produce FAILED. Published scenarios, sensitivity and value summary are withheld; diagnostic scenarios remain separately available. This changes publication governance, not a valuation formula. No additional economic approval was required. `tests/test_phase6_2_integrity.py` verifies both classification and withholding. Reverse-DCF nonconvergence and disclosed assumption uncertainty still produce PROVISIONAL.
