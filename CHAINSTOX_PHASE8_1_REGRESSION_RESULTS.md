# CHAINSTOX Phase 8.1 — Regression Results

Verification completed across 2026-11-04–05; report date 2026-11-05 (Asia/Kuala_Lumpur). Repository: `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`.

## Python

| Command | Result |
| --- | --- |
| `python3 -m pytest --collect-only -q` | **225 collected** |
| `python3 -m pytest -q --tb=short` | **225 passed, 0 failed, 28 subtests passed**, 378 warnings; final backend run 9.80 seconds |
| `python3 -m pytest tests/test_phase8_1_integrity.py -q --tb=short` | **24 passed, 0 failed** |
| `git diff --check` | Passed |

The complete supported suite includes existing FCFF reconciliation, debt completeness, valuation validation, company reports, macro, Phase 7 evidence and Phase 8 operational tests. `pytest.ini` limits root discovery to `tests/`; nested projects are not falsely included in this result. The 378 warnings are existing pandas chained-assignment warnings from the nested central-bank dependency, not failures.

Historical counts remain distinct: Phase 6.2 recorded pytest 141 versus unittest 118; Phase 8 baseline was pytest 201 plus 28 subtests. The current result is pytest 225, not a claim that unittest discovers 225. Unittest was not rerun for this report. No evidence was found to substantiate the older claimed 130 count.

### Why these regressions catch the audit failures

- Six authority checks use **actual benchmark inputs**, not only hand-built snapshots, and now reject both synthetic bottleneck claims and fixture-only authoritative valuation comparisons.
- Six synchronization checks compare saved frontend JSON with freshly built profiles. Deterministic scaling-metric ordering prevents hash-order drift.
- Annual-flow tests include short and full-year facts in the same filing, reversed order, and an accession tie-break. Instant-fact and stale-share collector tests separately enforce stock-versus-flow semantics and fiscal alignment.
- Unit test uses an explicit physical unit that conflicts with the old heuristic, plus shares and identity strings. Per-employee test verifies base-unit magnitude.
- TSM share-mix test requires absolute +5 and null relative growth, with no revenue-growth tension.
- Three integration cases call `build_valuation_report`, not just the standalone ADR helper, and assert FAILED with empty valuation outputs.
- Positive capacity growth does not imply easing even with a much larger demand/revenue-growth proxy.
- Cache test ensures old authority is rebuilt without mutating the saved payload. Duplicate tests cover both customer and TSM node-mix aliases.
- A provider-contract replay demonstrates that non-fixture financial analysis retains useful comparisons, without claiming that synthetic test data are empirical observations.
- Existing Phase 8 tests preserve issuer isolation, incompatible-period/unit rejection and no DCF mutation.

## Frontend and browser

Frontend commands run from `frontend/`:

| Check | Result / scope |
| --- | --- |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed (ESLint) |
| `npm run build` | Passed, 23 static pages generated; final build includes regenerated fixtures and source-state label correction |
| `npm run smoke:phase8` | Passed: six benchmark snapshots, provenance, missing operational states, TSM gate messaging/date/mix, map inspector, expanded report and valuation navigation |
| `node scripts/phase8-integrity-journey.mjs` | Passed: all **12 company/mode journeys**, actual API, no route mocks |
| `npm run smoke:phase7` | Passed: actual Research API sector data, Markets rendering, Company UNKNOWN state and source drawer; 34 sectors, SMH relative 6M −0.04209286705055715 in the recorded data |
| `npm run smoke:valuation` | Passed: existing valuation route/workspace suite, 24 screenshots |
| `npm run smoke:phase6` | Passed: product regressions, 10 screenshots |

The first sandboxed build failed because Turbopack could not bind a local worker port. The permissioned production build passed; the sandbox failure is not concealed as a test pass. Browsers ran against local production builds. The final isolated verification server uses port 3002 to avoid interfering with other port-3000 servers.

Phase 7, Valuation and Phase 6 browser evidence was reused where later changes only affected the TSM graph alias/cache revision or the Company missing-price text. The affected Company journeys and Phase 8 smoke were rerun after those changes. No earlier failure is counted as a successful final run.

## Actual six-company journey

Path exercised for each: Snapshot → direct Map route → selected Inspector → Trace Evidence → Source / Calculation → full Evidence workspace → Report. Both fixture and provider modes use the same component path and classifications.

| Company | Demo journey | Provider journey | Provider state in recorded result |
| --- | --- | --- | --- |
| PLTR | PASS | PASS | PARTIAL |
| TSM | PASS | PASS | PARTIAL |
| NVDA | PASS | PASS | PARTIAL |
| AMD | PASS | PASS | STALE |
| MSFT | PASS | PASS | PARTIAL |
| COST | PASS | PASS | PARTIAL |

`frontend/artifacts/phase8_1/journey-results.json` records these results. Provider-mode checks require a real API profile, FACT revenue, no FIXTURE entries, current classification revision and UNKNOWN constraint direction. Staleness remains visible; this test does not certify that every historical provider amount has been independently audited.

POST `/api/research` with `company-analyze` was also exercised for PLTR and the initially uncached TSM/NVDA/MSFT/COST. Provider/SEC fallback returned usable partial profiles. TSM `valuation-analyze` returned INSUFFICIENT_DATA with PROVISIONAL unsupported-data validation and no authoritative fair value because coverage was inadequate before the unit gate. Controlled real-engine integration tests are the evidence for currency/ADR gate execution; the live API response is not misrepresented as that test.

## Screenshots and visual review

Regenerated screenshots are in `frontend/artifacts/phase8/` and `frontend/artifacts/phase8_1/`. Representative visual review covered all six companies across the two modes, PLTR's single canonical customer node and expanded inspector, TSM's March 12 provenance and physical/mix units, the evidence source drawer, and Report presentation. Long reports/panels scroll; a viewport screenshot is not claimed to show every report row. Browser DOM assertions verify the expanded observations and absence of contradictory authoritative fixture language beyond the visible viewport.

The additional fixture-financial authority defect was discovered by inspecting images, not by accepting a green smoke test. Tests were strengthened before final screenshots were accepted. A subsequent TSM graph-alias check and provider missing-price-label review also produced small corrections and affected-check reruns.

## Disposition

The six requested P0 defects are remediated in the supported paths, with executable regressions and end-to-end research consistency evidence. Phase 8.1 can close as an **integrity remediation**, subject to the documented data-coverage limits. This does not declare full Phase 8 complete, enable authoritative TSM ADR valuation, approve economic-policy changes, or authorize Phase 9.
