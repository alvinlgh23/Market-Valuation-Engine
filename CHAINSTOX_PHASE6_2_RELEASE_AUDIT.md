# CHAINSTOX Phase 6.2 Release Audit

## Pre-edit baseline

Verified repository and Git root: `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`.
Branch `main`; HEAD `6108e9c02ec4ff42bb4ef6037df3df5394c62bf9`.
Recent commits: 6108e9c, bdd91ee, 417a1e8, a60030c, c998250.
The other Projects checkout was not used. Work continues in place because the implementation under review is largely untracked; a clean worktree would omit it.

Pre-existing tracked modifications: .DS_Store, .gitignore, README.md, SKILL_PUBLIC.md, Valuation_model.py, changelog.md, documentation.md, model.py.
Pre-existing relevant untracked directories/files: frontend/, tests/, data_sources/, research_system.py, intrinsic_valuation.py, company_research.py, company_economics*.py, macro_world.py, risk_regime.py, inflation_pressure.py, research_capabilities.py, all Phase 2–6 audit documents, Centralbank-Compass/, KOSPI/, NEER/, archive/, scripts/.
None is disposable. No reset, cleanup, branch switch, staging, or commit performed.

Python 3.14.3: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`.
Node 24.12.0; npm 11.6.2; Next.js 16.2.9.
Core collection command: `python3 -m pytest tests --collect-only -q` (141 collected).
Baseline execution: `python3 -m pytest tests -q`: 141 passed, 0 failed/skipped/deselected, 28 subtests passed, 378 pandas chained-assignment warnings, 9.19 seconds.
Typecheck and ESLint passed. Initial build hit sandbox worker-port restriction; unrestricted retry passed. No build tool was changed.

Existing API actions: company-resolve/open/index GET, company-analyze POST, valuation-analyze GET/POST, full/dashboard/world research scopes.
Existing policies: valuation 15-minute process-local cache with inflight deduplication; research bundled last-valid snapshot; explicit valuation `fixture=1`; company cache retains statement provenance.
Routes: dashboard, demo, macro/world and sections, markets and sectors, company/[ticker], valuation and valuation/[ticker], research labs.

## Initial findings

| Finding | Initial status | Evidence |
|---|---|---|
| Shared runtime | CONFIRMED | Company/research use literal python3; valuation uses configured executable |
| Curve maturity | CONFIRMED | ^IRX/^FVX fallback feeds US 2Y label; core curve can represent 10Y–5Y |
| Sector measurements | CONFIRMED | Empty/missing rows retain static relative strength and breadth |
| Test counts | UNVERIFIED | Current collection is 141; historical invocation records unavailable |

## Phase 6.1 reconciliation

- SEC debt tests remain passing: consolidated debt, current/noncurrent aggregation, no double counting, periods, currencies, zero debt, newer components, and incomplete-coverage valuation gate. No debt extraction formula changed in this phase.
- Shared fair-value coordinates remain passing, including equal-to-base, uneven ranges, outside-range price, identical values, and invalid ordering.
- Dynamic valuation still invokes Python by validated argument arrays. Explicit `fixture=1` remains required for bundled valuation reports. Live valuation no longer imports bundled Company Economics merely because the ticker has a fixture.
- Scenario common-anchor overrides and source labels remain passing. No scenario policy changed.
- Treasury bp conversion was retained; the dashboard's remaining 30Y percentage-return display was corrected to bp, and maturity provenance was added.
- The previous adapter existed, but Markets pages never fetched refreshed research. That runtime gap is now fixed and tested through the actual API.

## Confirmed issues and implemented changes

| Finding | Initial Status | Final Status | Evidence | Remaining Action |
|---|---|---|---|---|
| P62-001 Runtime selection split | CONFIRMED | FIXED | Shared python-runtime.ts; Company, Research, Valuation callers; nested research Python inherits configured executable | Configure deployment interpreter/dependencies |
| P62-002 Runtime errors collapsed | CONFIRMED | FIXED | Explicit executable/version/dependency/timeout/exit/JSON/output-limit codes; argument arrays and allowlists | Provider-specific root causes remain limited by upstream collectors |
| P62-003 Sector pipeline disconnected | CONFIRMED | FIXED | Python-generated measurements changed actual Markets UI +42.0% → −17.0% | Live provider verification |
| P62-004 Missing sectors retain static numbers | CONFIRMED | FIXED | Empty/partial/nonfinite rows withhold dynamic fields; structural objects retained | Obtain verified breadth/crowding inputs before plotting both axes |
| P62-005 Yield maturity substitution | CONFIRMED | FIXED | 5Y and 3M metadata/labels, genuine 2Y preference, bp moves, mixed-date chart gate | Verify fresh provider timestamps in deployment |
| P62-006 Valuation search | PARTIALLY FIXED | FIXED | Reuses resolveCompany; empty/loading/unsupported/provider states; arbitrary ticker routes | Live financial coverage is separate from resolution |
| P62-007 Validation publication | CONFIRMED | FIXED | Critical arithmetic FAILED; authoritative fields withheld; frontend suppresses stale value prose | None within tested contracts |
| P62-008 Context/fixture isolation | PARTIALLY FIXED | FIXED | Router transitions, preserved valuation query context, explicit fixtures, dynamic company-fixture removal | Further investigation semantics belong to Phase 7 |
| P62-009 Last-valid/freshness | PARTIALLY FIXED | FIXED | Stale fallback, cache timestamp separate from observations, no empty-sector overwrite of valid Python cache | TTL is not observation freshness; some source dates remain unknown |
| P62-010 Historical test counts | UNVERIFIED | PARTIALLY FIXED | Current unittest/pytest difference reproduced exactly | Historical 130 invocation not recoverable |
| P62-011 Live sector data | UNVERIFIED | BLOCKED — DATA PROVIDER | Yahoo SMH returned JSONDecodeError and zero rows inside and outside sandbox | Restore and independently verify upstream feed |
| P62-012 Economic model limitations | CONFIRMED | DEFERRED — APPROVAL REQUIRED | Separate method-governance report | Approve only evidence-backed model proposals |

## Sector root cause and runtime evidence

`.cache/research/core-market.json` (dated Aug 4 on disk) and the bundled snapshot contain zero sector rows, six missing market inputs out of seven, and risk coverage 0. `compute_sectors()` is invoked by `build_core_market()`; it skips tickers when `fetch_history()` returns None. Thus execution was not disabled and the row schema was not the original zero-row cause. The cached payload records provider-wide market-history absence. Historical transport details were swallowed by the collector and cannot be reconstructed. A fresh SMH request reproduced JSON decoding failure and zero rows both inside and outside the sandbox. The pages additionally imported the bundled snapshot directly, so even a successful later API refresh had no UI path.

The new browser harness supplies controlled histories to the **existing** Python `compute_sectors` and `build_core_market`, then passes them through `build_research_system`, the configured subprocess bridge, the real `/api/research` handler, and MarketsRuntime. It does not mock the API response or calculate sector strength in JavaScript. Changing the controlled final close changes displayed RS from +42.0% to −17.0%. Empty output shows Unavailable; structural navigation remains. Test-only interpreter selection requires `CHAINSTOX_TEST_MODE=1` and is never a production default.

Classification: **DETERMINISTICALLY VERIFIED / LIVE PROVIDER UNVERIFIED**.

Actual production-configuration API calls for non-fixture TSM and AMD returned HTTP 200, INSUFFICIENT_DATA, matching requested ticker identities, and PYTHON_INTRINSIC_VALUATION provenance. They did not produce current values or substitute fixture companies. This verifies failure behavior, not operational financial coverage.

## Test inventory reconciliation

Working directory: repository root. Interpreter: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` (3.14.3). Dependencies inspected: pytest 9.1.1, pandas 2.2.3, yfinance 0.2.51, requests 2.34.2 in that interpreter's site-packages. No dependency installation or environment replacement was performed.

At Phase 6.2 baseline, `unittest.defaultTestLoader.discover("tests").countTestCases()` returns 118 while `python3 -m pytest tests --collect-only -q` collects 141. The additional 23 are pytest-style tests in test_macro_experience.py, test_macro_world.py, and test_research_capabilities.py. They are omitted by unittest discovery. The prior 108→118 report is consistent with unittest scope. A historical 130 pytest count is arithmetically consistent with 108 plus 22 pytest-style tests before the new yield-move test; however, the old execution log and exact uncommitted snapshot are unavailable. This is a plausible reconciliation, not a reconstructed historical run.

The supported core suite is `python3 -m pytest tests -q`. Nested Centralbank-Compass has four specialist test modules (real yield, Treasury flows, FRED seed, eurozone scoring) and is deliberately not silently included in core counts. KOSPI and NEER are distinct specialist engines. Core tests exercise their existing integration contracts. No tests were removed to reconcile counts.

Final exact counts and frontend/browser gates are recorded in the implementation report. The 378 known pandas chained-assignment FutureWarnings originate in the specialist Compass adapter and are not test skips. A future pandas 3 upgrade requires separate compatibility verification.

## Runtime contract and cache policy

`CHAINSTOX_PYTHON_EXECUTABLE` selects the executable for all three API families; default is `python3`, minimum 3.10. No personal path is embedded. Nested specialist subprocesses prioritize the same variable, then the legacy engine variable, then the active interpreter. The API uses argument arrays, action allowlists, validated queries, 120s company / 180s research+valuation limits, and a 20 MiB output bound. Version preflight is bounded at 10s. Runtime failures carry machine-readable codes and are not recast as financial insufficiency.

Valuation cache keys include ticker and overrides, TTL 15 minutes, with inflight deduplication and prior-report stale fallback. Refresh does not overwrite a good report with insufficient coverage. Research also deduplicates in-flight execution and exposes cached/stale fallback; Python preserves last-valid sector data when refresh returns no rows. A response generation timestamp is not a statement date. Missing observation dates remain explicit. Sector observations older than seven days display STALE; missing fields do not inherit declarative numbers. Detailed source-state classification remains bounded by what existing providers expose.

## Backend/frontend traceability

| Output | Backend source / processing | Structured field | API | Frontend / UI | Validation / evidence / test |
|---|---|---|---|---|---|
| SEC debt | SEC facts / _select_debt | debt, debt_coverage, debt_provenance | valuation-analyze | valuation-service / DCF, Validation | sec_company and intrinsic_valuation tests; concepts and dates |
| FCFF | statements / _historical_fcff_reconciliation | historical_fcff_reconciliation | valuation-analyze | ValuationResearchPage / FCFF bridge | mismatch/missing/SBC tests; tolerance and OCF comparison |
| Valuation status | _validate + report gates | validation, internal_validation | valuation-analyze | status badges, withheld range, Validation, report | corruption and withholding tests; deterministic browser FAILED/PROVISIONAL |
| Current price | collect_valuation_data | company.current_market_price | valuation-analyze | snapshot, shared value scale | missing-price test; provenance timestamp caveat |
| Reverse DCF | _reverse_dcf | reverse_dcf | valuation-analyze | ReverseDcf | residual/bracket/no-solution tests; fixed assumptions disclosed |
| Scenario assumptions | _scenario_assumptions | assumptions.bear/base/bull | valuation-analyze | Assumptions/DCF | common-anchor regression; source/basis/period |
| Sector strength | provider history / compute_sectors → build_core_market | modules.core_market.payload.sectors | full research | integrateSectorEngineRows → MarketsRuntime / table+inspector | real API browser 42→−17 test; date/state/absent fields |
| Treasury moves | compute_macro / yield_return_to_bps | market_transmission.rates.moves | full research | rates consumers | positive/negative/zero/missing tests; bp units |
| Yield curve | treasury_curve → build_market_transmission | rates.metrics.maturity_metadata | full research | MacroRatesRuntime / maturity provenance | proxy, missing, stale, inversion, conflicting dates; mixed-date chart withheld |

## Screenshots and limitations

Representative artifacts are under `frontend/artifacts/phase6-2/`; existing suite screenshots remain in their respective phase directories. Screenshot review found and corrected (1) unavailable sectors plotted at zero and overlapping, (2) stale authoritative prose on failed reports, (3) a mixed-date Treasury plot, and (4) broken numeric word wrapping in narrow sector cells. Final images are reviewed after rerun.

No new research engine, LLM API, operational metric, broad redesign, deployment, commit, or economic valuation formula was introduced. Uncommitted prior phases remain intact. Structural maps remain declarative and are not validated causal conclusions. Phase 7 may build on the engineering baseline, but no new epistemology engine has been implemented.

