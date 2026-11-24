# Runtime data-contract reconciliation

Verified 2026-11-05, Asia/Kuala_Lumpur. Targeted repair; existing Phase 7/8/8.1 work preserved. No valuation formulas, evidence policy, nested repositories, commits or pushes changed.

## Root cause and reproduction boundary

The normal dev-browser request is **GET `/api/research?scope=full`**, not a separate Markets action. It returned HTTP 200 and 34 sector rows. In a fresh dev browser **before edits**, the seven curated sectors already displayed their 1M/3M/6M relative strengths after the request completed. I did not reproduce every RS cell remaining unavailable after a successful response. The captured pre-fix screenshot and JSON are retained rather than claiming otherwise.

Confirmed defects:

1. `integrateSectorEngineRows()` iterated the seven-item static structural catalog, silently dropping 27 other API tickers.
2. `RotationMap()` requires both relative strength and crowding. The adapter correctly leaves unsupported crowding/breadth/stage unavailable, so no point qualified. Its explanation was below the empty plot and easy to miss. **No crowding coordinates have been invented to fill the plane.**
3. Markets loaded the API after initially rendering an August bundled snapshot with zero sectors. Labs and Dashboard stayed on that bundle. Dashboard's sector helpers additionally used static semiconductor leadership, breadth and crowding examples instead of the API rows.
4. Observation dates were not shown in the main sector table. API Dashboard text called cached rankings “current live,” and freshness metadata said “Current refresh.” These conflated response generation with observation dates.

## Actual path and repair references

| Stage | File / function | Behavior |
| --- | --- | --- |
| Request | `frontend/components/research/MarketsRuntime.tsx::fetchResearch` | `/api/research?scope=full`; explicit refresh adds `&refresh=1`. Markets, Dashboard and Labs now reuse this runtime. |
| API/cache | `frontend/app/api/research/route.ts::GET` | Existing 15-minute response cache/Python bridge retained. `meta.core_snapshot_id` fingerprints the core payload, independent of response-generation time. |
| Python cache | `research_system.py::isolated` | Existing provider exception/empty-sector fallback retains last-valid payload as STALE; tested against captured data. Dashboard wording now identifies snapshot state and sector observation date. |
| Client state | `frontend/lib/research-response.ts::reconcileResearchResponse` | Failed empty refresh retains the entire prior snapshot, keeping Dashboard claims and Markets measurements together. Successful empty responses remain explicitly empty. Transport failure retains historical values and exposes the failure. |
| Adapter | `frontend/lib/market-research.ts::integrateSectorEngineRows` | All supplied tickers retained; uncatalogued sectors get no invented structural model. Finite historical RS is retained. Existing seven-day stale threshold labels old observations; it does not erase values. Explicit FAILED/INVALID/CONFLICT rows are withheld with their supplied reason. |
| Render | `ObjectResearchSurfaces.tsx::RotationTable`, `SectorSnapshot`, `RotationMap` | Table shows observation date/state; source and missing/invalid reasons appear in tooltips and sector detail. Empty positioning plane has a prominent missing-crowding explanation. |
| Dashboard | `dashboard-orchestration.ts::measuredSectors`, `dashboardStateStrip`, `marketLeadershipSummary` | Uses the API engine ordering and same dated values, not a new ranking formula or static semiconductor claims. Timestamp formatting preserves the actual offset. |
| Labs | `MarketsRuntime.tsx::LabsRuntime`; `app/labs/[section]/page.tsx` | Loads the same response and identifies snapshot generation separately from the missing sentiment observation date. |

## Exact API and browser evidence

Raw response bodies are saved without summarization under `frontend/artifacts/runtime-reconciliation/`:

- `before-api.json`: original cached response, 34 rows, sector observations **2026-10-22**. Healthcare XLV: 1M **0.07824928292270827**, 3M **0.0832637695392553**, 6M **0.17449326248193753**. Source: **Yahoo Finance / Python sector engine**; provider diagnostics identify adjusted daily close, USD, PCX, observation end October 22 and retrieval October 23. These are historical, not November 5 live measurements.
- `initial-network-trace.json` / `initial-after-labs-api.json`: first repaired cross-page run used core snapshot **0a78957806f2b431**, consistently displaying cached data including sentiment **51.70**.
- A real refresh succeeded and advanced sector observation dates to **2026-11-04**, not November 5. Healthcare 6M became **0.26788242388664285** (**+26.8%**); sentiment became **48.10**. This legitimately changed the payload fingerprint.
- `network-trace.json`: the repeat dev run with **Miniconda Python 3.13.12**, no `CHAINSTOX_PYTHON_EXECUTABLE` override, includes actual request URLs/status/meta, successful refresh, and real browser-offline retention. It used snapshot **c5076ffb979e5551**, then refresh **ea1f3660b07fe36c**.
- `presentation-network-trace.json`, `after-markets-api.json`, `after-labs-api.json`, `after-dashboard-api.json`: final presentation check; all three consumers use **ea1f3660b07fe36c**. `refresh-api.json` retains the exact refresh response.

Normal command used: `npm run dev -- --port 3001`. Port 3001 avoided stopping the existing port-3000 process. The final server inherited `/opt/miniconda3/bin` first on PATH to match the owner's shell, with no configured executable override. Initial tool-shell verification used Python 3.14.3; both worked. No Python-selection defect was reproduced.

### Labs 49.50 versus 51.70

This was **different snapshots plus a genuine consumer integration defect**, not evidence that one number was mathematically wrong. `frontend/lib/fixtures/research-system.json` was generated **2026-08-07T11:00:55-04:00**, contained sentiment **49.5** and zero sector rows. Labs rendered it permanently. The original Python cache contained **51.7**; after the actual refresh it contained **48.1**. Labs now follows the API version. The cached fragility contract lacks the sentiment observation date, so the UI explicitly says it is unavailable; it does not substitute the November response-generation date.

## Tests, empty states and failure proof

- Full supported Python suite: **227 passed, 0 failed; 28 subtests passed**, 378 existing nested-macro pandas warnings.
- `node scripts/runtime-reconciliation-test.mjs`: passed. Uses the exact captured 34-row response; asserts every ticker/value/date/source survives, Dashboard ordering matches the API, stale values remain present, invalid rows retain precise reasons, successful empty responses are explicit, and failed-empty refreshes retain one coherent prior snapshot.
- `tests/test_runtime_reconciliation.py`: two provider-boundary cases (exception and empty refresh), using the captured payload and isolated temporary cache. Both preserve all 34 rows and the disk cache as STALE. These are controlled regressions, **not claimed as naturally occurring live outages**.
- `node scripts/runtime-reconciliation-browser.mjs`: passed with real browser/network requests, no route mocks; 34 rendered sector rows, all three snapshot IDs equal, actual provider refresh, and real offline transport failure retaining the table.
- Typecheck, ESLint and production build: passed. Build generated 23 static pages. `git diff --check`: passed.

An actually empty sector response was not produced by the healthy provider during browser verification. Its behavior is proven by adapter/state regressions: no copied sample values, explicit zero rows and per-sector missing reasons. A natural provider failure also did not occur; actual transport failure was tested in-browser, and provider failure/empty-refresh handling at the cache boundary was tested separately.

## Screenshots and remaining limits

Visually inspected: `before-markets.png`, `before-labs.png`, `after-markets.png`, `after-labs.png`, `after-dashboard.png`; refresh/offline captures are `after-refresh.png` and `offline-retained.png`. All are under the artifact directory above. Inspection caught overlapping empty-plane text; it was moved outside the axis area without redesigning the chart.

The interface now exposes all 34 correctly qualified RS rows. Breadth, crowding, stage and stock-level leadership remain unavailable where not supplied. Therefore the two-dimensional positioning plane still has no valid points; it now explains why. Additional sectors have measurements but no fabricated structural graph. The bundled snapshot remains an explicitly identifiable startup/failure fallback, not a current observation source. Successful refreshes used the normal cache-writing path; original observations remain captured in the audit artifacts.

Launch as usual from `frontend/` with `npm run dev`, then open the URL Next.js prints. Allow the Research API request to resolve; the status line identifies its source, row count and core snapshot. No Phase 9 or valuation-methodology work was introduced.
