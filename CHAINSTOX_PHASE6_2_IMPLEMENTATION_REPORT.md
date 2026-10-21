# CHAINSTOX Phase 6.2 — Residual Integrity & Release Verification Report

Date: 2026-10-21, Asia/Kuala_Lumpur.

**Release classification: engineering baseline verified; live-data production readiness withheld.** Phase 6.2's implemented contracts pass deterministic tests and the browser journeys exercised here. Live-provider limitations remain explicitly open. Phase 7 can proceed on this bounded engineering baseline without treating the current research conclusions as economically validated.

## Required completion record

| # | Requirement | Result / evidence |
|---|---|---|
| 1 | Repository / HEAD | `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`, main, `6108e9c02ec4ff42bb4ef6037df3df5394c62bf9` |
| 2 | Initial tree | Materially dirty; tracked edits and untracked Phases 2–6 preserved; inventory in release audit. No commit, reset, cleanup, or branch switch |
| 3 | Environment | Python 3.14.3; Node 24.12.0; npm 11.6.2; Next 16.2.9; pytest 9.1.1; pandas 2.2.3; yfinance 0.2.51; requests 2.34.2 |
| 4 | Exact Python collection | `python3 -m pytest tests --collect-only -q`: **157**, 0 collection errors, 0.51s |
| 5 | Test-count reconciliation | Baseline pytest 141 versus unittest 118 reproduced; 23 pytest-style tests omitted by unittest. Historical 108/130 explanation is plausible, not reconstructed; see audit |
| 6 | Phase 6.1 regressions | SEC debt, FCFF/SBC, common-anchor scenarios, numerical fair-value transform, dynamic routing and fixture opt-in retained; relevant Python/JS/browser tests pass |
| 7 | Unified runtime | Company, Research, Valuation all use shared configured interpreter; nested specialist research follows same variable |
| 8 | Runtime errors | Executable missing, Python <3.10, dependency missing, timeout, exit failure, output limit, invalid JSON, invalid input/action classified; mock runtime and actual API harness pass |
| 9 | Sector zero-row cause | Cached market-history absence; collector skips missing histories. Fresh Yahoo SMH probe also fails. Separate UI disconnect confirmed: pages previously read only bundled payload |
| 10 | Sector integration | Actual research API fetched by Markets/sector routes; Python measurements mapped by ETF; unknown/nonfinite/missing data cannot inherit static values |
| 11 | Deterministic sector E2E | Existing Python compute_sectors with controlled histories → build_core_market → research JSON → actual API → UI. Display changed **+42.0% → −17.0%**; empty rows withheld metrics |
| 12 | Curve fallback finding | ^FVX/^IRX could be mislabeled 2Y; remaining dashboard 30Y relative-percent display also found |
| 13 | Maturity fix | Explicit 10Y/2Y/5Y/3M metadata, source, dates, pp units, fallback and alignment; true 2Y preferred; mixed-date chart withheld, individual observations retained |
| 14 | Valuation Search | Shared Company resolver; empty/loading/unsupported/provider feedback; TSM non-fixture navigation tested with configured Python harness |
| 15 | Deep links/history | reverse-dcf, sensitivity, validation, evidence, report; direct reload and Back/Forward tested; fixture/from context preserved in view navigation |
| 16 | Validation UI | PASSED/PROVISIONAL/FAILED visible; provisional reasons beside range; critical failures withhold range, sensitivity and stale value narrative; diagnostics remain |
| 17 | SEC debt | Complete/current+noncurrent/period/unit/zero/partial cases pass; incomplete debt continues blocking EV-equity valuation |
| 18 | Fixture isolation | Explicit fixture opt-in preserved; dynamic valuation no longer pulls bundled economics; real TSM/AMD requests preserve ticker and return insufficiency |
| 19 | Cache/stale behavior | 15-minute response caches; deduplication; prior-valid fallback marked STALE; statement/measurement freshness not inferred from TTL; empty Python sector refresh preserves prior measurements |
| 20 | Cost of debt | Historical interest/debt ratio, clamps and fallback are a limited forward proxy; no formula change; governance G1 |
| 21 | Growth fade | Five-year fade is a design choice, not measured advantage duration; six archetypes reviewed; governance G2 |
| 22 | SBC/dilution | Both bookkeeping policies consistent under tests; fixed dilution and terminal claims remain substantive limitations; governance G3 |
| 23 | FCFF/FCFE | Unlevered cash discounted at WACC; CFO route includes after-tax interest; raw CFO−CapEx comparison displayed; no FCFE engine added; governance G4 |
| 24 | Reverse DCF | One-variable bounded solve retained; no-solution and missing-price states preserved; governance G5 |
| 25 | CapEx | Actual spending preserved; latest-period base and implicit margin normalization limitations documented; governance G6 |
| 26 | Formula changes | **No economically consequential valuation formula changed.** Treasury unit/maturity presentation corrected; critical validation publication gate strengthened |
| 27 | Deferred methods | Forward debt-cost hierarchy, growth duration, evidenced dilution/terminal claims, reinvestment normalization, alternative inverse modes all require separate approval |
| 28 | Python execution | `python3 -m pytest tests -q`: **157 passed, 0 failed, 0 skipped, 0 deselected**, 28 subtests passed, 378 existing warnings, **7.67s** |
| 29 | TypeScript | `npm run typecheck`: passed |
| 30 | ESLint | `npm run lint`: passed |
| 31 | Production build | `npm run build`: passed; initial sandbox worker-port failure resolved by permitted execution, not tool replacement |
| 32 | Playwright | Macro, Dashboard, Companies, Markets, Valuation, Phase 6 cross-module and new Phase 6.2 integration suite all ran and passed. Initial stale-selector/loading failures fixed and rerun |
| 33 | Screenshots | Representative phase6-2 images inspected for failed/provisional values, search, dynamic/empty sectors, curve provenance. Existing suites cover mobile layouts and global navigation. Controlled-harness screenshots are synthetic test evidence, not market observations |
| 34 | Files modified | Exact scoped list below; broader dirty status includes prior work |
| 35 | Files created | Exact scoped list below |
| 36 | Remaining critical issues | No known unaddressed critical engineering defect in exercised contracts; operational live-data coverage is blocked |
| 37 | Remaining high priorities | Restore data provider; independently validate source freshness; address method-governance proposals before stronger valuation claims; pandas 3 compatibility remains future work |
| 38 | External data | Yahoo SMH returned zero rows/JSONDecodeError even outside sandbox. Real TSM/AMD returned INSUFFICIENT_DATA, not computed values. Fresh production coverage is unverified |
| 39 | Phase 7 readiness | Engineering foundation available with recorded limitations; no epistemology features preimplemented |
| 40 | Overall release | **DETERMINISTICALLY VERIFIED / LIVE PROVIDER UNVERIFIED**; not certified for full production research validity |

## Files modified in Phase 6.2

- Backend: `Valuation_model.py`, `research_system.py`, `intrinsic_valuation.py` (validation/publication only in the last file).
- Runtime/API/adapters: `frontend/app/api/research/route.ts`, `frontend/lib/valuation-service.ts`, `frontend/lib/market-research.ts`, `frontend/lib/valuation-research.ts`, `frontend/lib/research-system-types.ts`.
- Routes: `frontend/app/page.tsx`, `frontend/app/demo/page.tsx`, `frontend/app/macro/[section]/page.tsx`, `frontend/app/markets/page.tsx`, `frontend/app/markets/[section]/page.tsx`, `frontend/app/markets/sector/[sector]/page.tsx`, `frontend/app/valuation/[ticker]/page.tsx`.
- Components/styles: `frontend/components/company/CompanyResearchPage.tsx`, `frontend/components/research/ObjectResearchSurfaces.tsx`, `frontend/components/valuation/ValuationResearchPage.tsx`, `frontend/app/globals.css` (sector-cell readability only).
- Existing browser assertions: `frontend/scripts/markets-phase3-smoke.mjs`, `frontend/scripts/valuation-phase5-smoke.mjs`.

These files were already modified or untracked before this phase; this list does not claim ownership of their entire contents.

## Files created in Phase 6.2

- `treasury_semantics.py`
- `frontend/lib/python-runtime.ts`
- `frontend/components/research/MarketsRuntime.tsx`
- `frontend/components/macro/MacroRatesRuntime.tsx`
- `frontend/components/valuation/ValuationSearch.tsx`
- `frontend/app/valuation/[ticker]/loading.tsx`
- `tests/test_phase6_2_integrity.py`
- `tests/phase6_2_python_bridge.py` (guarded test-only interpreter harness)
- `frontend/scripts/phase6-2-unit-test.mjs`
- `frontend/scripts/phase6-2-integration.mjs`
- `CHAINSTOX_PHASE6_2_RELEASE_AUDIT.md`
- `CHAINSTOX_PHASE6_2_IMPLEMENTATION_REPORT.md`
- `CHAINSTOX_VALUATION_METHOD_GOVERNANCE.md`

Generated screenshots/logs are in `frontend/artifacts/phase6-2/` and the existing smoke-suite artifact directories.

## Reproducible runtime and verification

Start the frontend from `frontend/`. Optionally set `CHAINSTOX_PYTHON_EXECUTABLE` to the Python executable in the intended dependency environment; otherwise `python3` is used. Python must be at least 3.10 and have the project's dependencies installed. The toolchain verified here is 3.14.3. Do not point production at the test harness. `CHAINSTOX_ENGINE_PYTHON` remains a legacy nested-engine fallback only when the shared variable is unset.

Core commands from the repository root:

```sh
python3 -m pytest tests --collect-only -q
python3 -m pytest tests -q
python3 -m py_compile Valuation_model.py model.py research_system.py intrinsic_valuation.py treasury_semantics.py
```

Frontend commands from `frontend/`:

```sh
npm run typecheck
npm run lint
npm run build
node scripts/phase6-2-unit-test.mjs
npm run test:fair-value-scale
node scripts/phase6-2-integration.mjs
```

The Phase 6.2 integration script starts and stops an isolated local production-build server on port 3012 and explicitly selects its guarded deterministic Python harness. Browser execution needs permission to launch Chromium and bind a local port. Existing smoke suites use a normal `npm run start` server on port 3000: `smoke:macro`, `smoke:dashboard`, `smoke:companies`, `smoke:markets`, `smoke:valuation`, `smoke:phase6`.

The unit script emits a benign Node module-type inference warning when importing TypeScript directly under Node 24; it is not a test failure. Core Python warnings are recorded above rather than suppressed.

## Final finding table

| Finding | Initial Status | Final Status | Evidence | Remaining Action |
|---|---|---|---|---|
| Runtime configuration/errors | CONFIRMED | FIXED | Shared runtime unit cases + API harness | Deployment dependency configuration |
| Sector API/UI connection | CONFIRMED | FIXED | Python-to-browser +42% → −17% | Live feed verification |
| Missing/static market values | CONFIRMED | FIXED | Empty-row UI; structural links retained | Verified breadth/crowding data |
| Treasury maturity/units | CONFIRMED | FIXED | Metadata, bp, proxy and date tests | Current provider observations |
| Search/context/status | PARTIALLY FIXED | FIXED | Browser routes/history/status checks | None in exercised scope |
| Critical validation publication | CONFIRMED | FIXED | Corrupted-PV regression; failed narrative/range withheld | None in exercised scope |
| Phase 6.1 safeguards | CONFIRMED | PRESERVED | Core regression, value-scale, Python, and browser tests | Preserve in future phases |
| Cache/provenance | PARTIALLY FIXED | FIXED | Stale fallback and explicit dates | Unknown source dates remain unknown |
| 118 versus 141 counts | UNVERIFIED | FIXED | Both discovery mechanisms reproduced | Use pytest core command |
| Historical 130 count | UNVERIFIED | UNVERIFIED | No historical log/snapshot | Do not claim exact reconstruction |
| Live data | UNVERIFIED | BLOCKED — DATA PROVIDER | Zero live SMH rows; TSM/AMD insufficient | Restore and verify feed |
| Economic methodology extensions | CONFIRMED | DEFERRED — APPROVAL REQUIRED | Governance G1–G6 | Separate approved evidence-backed designs |
