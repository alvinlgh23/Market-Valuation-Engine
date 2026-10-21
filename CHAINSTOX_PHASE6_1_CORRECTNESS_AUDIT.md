# CHAINSTOX Phase 6.1 Correctness Audit

Audit date: 2026-10-20 (Asia/Kuala_Lumpur)

Scope note: the supplied specification ends mid-sentence at Section 31 ("Inspect the current Valuation landing"). All complete requirements through Section 30 were treated as authoritative scope; the truncated remainder cannot be audited without the missing text.

## Repository and runtime baseline

- Repository: `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`
- Git root: same as repository path
- Branch / HEAD: `main` / `6108e9c`
- Recent commit: `6108e9c Add market intelligence extension layer`
- Working tree: materially dirty before Phase 6.1, including prior user/agent edits and many untracked Phase 2–6 files. Those changes were preserved.
- Python: 3.14.3 at `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
- Node.js: 24.12.0
- npm: 11.6.2
- Next.js: 16.2.9
- Baseline Python tests: 108 passed
- Baseline TypeScript: passed
- Baseline ESLint: passed
- Baseline production build: passed; 23 routes generated
- Existing valuation smoke: Playwright Phase 5 workflow with 24 screenshots
- Existing API actions: company resolve/open/index, company analyze, research scopes
- Dynamic routes: company, valuation, market sector, macro/market/lab section routes
- Valuation framework states: operating-company DCF, growth-software convergence, cyclical DCF, and explicit specialized-framework gates
- Existing SEC fallback: Company Facts identity/annual data after Yahoo failure; pre-fix debt represented current debt only

## Findings

### P61-001 — SEC total debt extraction

- **Original Gemini Claim:** SEC fallback may use only current debt concepts and misstate total debt.
- **Current Code Reference:** `data_sources/sec_company.py`, former `debt = _annual_values(...Current...)`.
- **Reproduction:** Static inspection confirmed only `LongTermDebtAndFinanceLeaseObligationsCurrent` and `LongTermDebtCurrent` were selected.
- **Observed Result:** Noncurrent debt could be omitted while the result was labeled `debt` and consumed downstream.
- **Expected Result:** Consolidated total debt or aligned, mutually exclusive current and noncurrent components with provenance and coverage.
- **Impact:** Potential understatement of debt, overstatement of equity value, and incorrect WACC capital weights.
- **Root Cause:** No debt-concept hierarchy or coverage state.
- **Status:** FIXED
- **Proposed Fix:** Select a reliable consolidated total first; otherwise sum aligned current/noncurrent components; never mix periods/units or report partial debt as total.
- **Tests:** `tests/test_sec_company.py`; SEC partial-debt valuation block in `tests/test_intrinsic_valuation.py`.
- **Final Outcome:** Debt now records concepts, period, fiscal year, filing date, currency, methodology, coverage, and missing components. PARTIAL/INSUFFICIENT debt blocks the EV-to-equity bridge.

### P61-002 — Fair-value range coordinate mismatch

- **Original Gemini Claim:** Bear/Base/Bull were fixed at 0/50/100 while market used a numeric scale.
- **Current Code Reference:** `frontend/components/valuation/ValuationResearchPage.tsx`.
- **Reproduction:** Confirmed scenario coordinates used `index * 50`; market used `(price - bear)/(bull - bear)`.
- **Observed Result:** A market price equal to Base could render away from Base when scenario spacing was uneven.
- **Expected Result:** Every marker uses one numerical transform.
- **Impact:** Misleading valuation visualization.
- **Root Cause:** Mixed categorical and quantitative coordinate systems.
- **Status:** FIXED
- **Proposed Fix:** Shared domain containing all valid scenario and market values; one transform for every marker.
- **Tests:** `frontend/scripts/fair-value-scale-test.mjs` covers equal-to-base, above/below range, uneven spreads, identical values, missing data, and invalid ordering.
- **Final Outcome:** Scenario and market markers are proportional and invalid scenarios render an unavailable state.

### P61-003 — Fixture-only valuation routing

- **Original Gemini Claim:** `/valuation/[ticker]` returned 404 outside seven fixture tickers.
- **Current Code Reference:** `frontend/app/valuation/[ticker]/page.tsx`, `frontend/lib/valuation-research.ts`.
- **Reproduction:** Confirmed the page called `getValuationReport()` and `notFound()` for all non-fixtures.
- **Observed Result:** Resolved arbitrary companies could not open Valuation.
- **Expected Result:** Dynamic typed valuation backed by the existing Python engine, with explicit supported/gated/error states.
- **Impact:** Broken Companies → Valuation journey and misleading fixture universe.
- **Root Cause:** Phase 5 frontend stopped at bundled reports.
- **Status:** FIXED
- **Proposed Fix:** Typed `valuation-analyze` bridge using argument arrays and Python JSON output; no TypeScript DCF.
- **Tests:** Production build/typecheck, live API/runtime checks, existing Python valuation suite.
- **Final Outcome:** Arbitrary valid tickers route to Python. States distinguish `SUPPORTED_VALUATION`, `FRAMEWORK_REQUIRED`, `INSUFFICIENT_DATA`, `UNSUPPORTED_SECURITY`, and `PROVIDER_ERROR`. Fixture use requires `?fixture=1` and remains labeled FIXTURE.

### P61-004 — Python interpreter selection

- **Original Gemini Claim:** Hardcoded `python3` may select an environment without dependencies.
- **Current Code Reference:** former Next research bridge behavior.
- **Reproduction:** Existing bridge invoked literal `python3` without a version preflight.
- **Observed Result:** Environment selection was implicit.
- **Expected Result:** Configurable documented executable and clear failure.
- **Impact:** Runtime/provider failures that appear as valuation failures.
- **Root Cause:** No interpreter contract.
- **Status:** FIXED for dynamic valuation; PARTIALLY CONFIRMED for older research actions
- **Proposed Fix:** `CHAINSTOX_PYTHON_EXECUTABLE`, fallback to `python3`, Python 3 preflight, explicit service error.
- **Tests:** Typecheck/build and runtime API invocation.
- **Final Outcome:** Dynamic valuation uses the configurable executable. Legacy company/research actions retain their previous invocation pending a broader bridge refactor.

### P61-005 — Treasury yield change units

- **Original Gemini Claim:** Treasury yield changes may be represented with incorrect units.
- **Current Code Reference:** `research_system.py` rate-move adapter.
- **Reproduction:** `price_change()` returns a fractional percentage return in the yield level, which was multiplied by 100 and labeled `% 3M`.
- **Observed Result:** The UI described relative yield returns rather than the economically standard absolute basis-point move.
- **Expected Result:** Absolute change in basis points.
- **Impact:** Rates transmission could be materially misread.
- **Root Cause:** Equity-style percentage-return adapter reused for yields.
- **Status:** FIXED
- **Proposed Fix:** Recover prior yield from current level and fractional return, then calculate `(current - prior) * 100` basis points.
- **Tests:** `test_treasury_yield_moves_are_absolute_basis_points`.
- **Final Outcome:** 2Y/10Y/30Y moves are emitted as `bp 3M`.

### P61-006 — Markets sector-engine integration

- **Original Gemini Claim:** Markets may display frontend sector fixtures instead of backend sector-engine results.
- **Current Code Reference:** `frontend/lib/market-research.ts`, `ObjectResearchSurfaces.tsx`.
- **Reproduction:** Confirmed static sector metrics were used even when `core_market.payload.sectors` existed. Current bundled payload contains zero sector rows.
- **Observed Result:** UI is honestly labeled cached/structural but could not consume future engine rows.
- **Expected Result:** Use backend rows when present while preserving structural maps and explicit partial coverage.
- **Impact:** Current sector ranks could diverge from the Python engine.
- **Root Cause:** No adapter between engine rows and declarative structure objects.
- **Status:** FIXED with PARTIAL runtime coverage
- **Proposed Fix:** Overlay Python 1M/3M/6M relative-strength rows by ETF ticker; retain declarative structure and label the combined object PARTIAL.
- **Tests:** Typecheck/build and existing Markets smoke compatibility.
- **Final Outcome:** Backend sector rows now flow into the UI whenever supplied. With zero bundled rows, the existing cached structural object remains explicit rather than being presented as live.

### P61-007 — Cache and provenance semantics

- **Original Gemini Claim:** Fixtures/stale results may appear live.
- **Current Code Reference:** new `frontend/lib/valuation-service.ts` and valuation route.
- **Reproduction:** Prior valuation pages had no runtime source distinction because all reports were fixtures.
- **Observed Result:** A fixture report looked like the only supported valuation state.
- **Expected Result:** LIVE/CACHED/STALE/FIXTURE/PARTIAL/INSUFFICIENT_DATA/UNAVAILABLE reflect actual provenance.
- **Impact:** Research freshness ambiguity.
- **Root Cause:** No dynamic valuation service envelope.
- **Status:** FIXED
- **Proposed Fix:** Typed result envelope, 15-minute in-memory cache, request de-duplication, stale-last-valid behavior, explicit fixture opt-in.
- **Tests:** Runtime API checks and build.
- **Final Outcome:** Every dynamic valuation result carries source, data state, and as-of timestamp; no ticker falls back to another company.

### P61-008 — Scenario override consistency

- **Original Gemini Claim:** Scenario overrides may be inconsistent across Bear/Base/Bull.
- **Current Code Reference:** `intrinsic_valuation.py::_scenario_assumptions`.
- **Reproduction:** Confirmed manual overrides replaced only Base after Bear/Bull had already been constructed from the original model anchor.
- **Observed Result:** Override scenarios could lose their intended spreads or fail logical ordering.
- **Expected Result:** A manual override is the Base anchor; deterministic Bear/Bull spreads derive from that same anchor.
- **Impact:** Misleading scenario comparisons and avoidable validation failures.
- **Root Cause:** Overrides were applied inside the Base-only branch after scenario construction.
- **Status:** FIXED
- **Proposed Fix:** Apply validated overrides to central anchors, then derive all scenarios; label derived cases `user_override_with_scenario_spread`.
- **Tests:** `test_manual_overrides_anchor_all_scenario_spreads` plus scenario ordering.
- **Final Outcome:** All scenarios now share one override-consistent basis without changing assumptions to target market price.

## Regression summary

- Python unit suite after changes: 118 passed.
- Frontend fair-value coordinate tests: passed.
- TypeScript: passed after implementation.
- ESLint: passed after implementation.
- Production build: passed after implementation.
- Valuation Phase 5 Playwright smoke: passed; 24 screenshots.
- Markets Phase 3 Playwright smoke: passed.
- Phase 6 cross-module Playwright smoke: passed; 10 screenshots.
- Dynamic runtime checks: non-fixture routes return HTTP 200 with typed availability; invalid ticker returns `UNSUPPORTED_SECURITY`; provider-unavailable TSM returns `INSUFFICIENT_DATA` without fixture substitution.
- The first final build attempt hit a sandbox-only Turbopack worker-port denial; the required escalated rerun passed. This was an execution restriction, not an application build defect.
- No valuation assumption was altered to move fair value toward market price.
- Company Economics remains read-only with respect to DCF inputs.
