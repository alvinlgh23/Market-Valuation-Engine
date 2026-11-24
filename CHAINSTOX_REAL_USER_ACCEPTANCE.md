# CHAINSTOX real-user acceptance — Markets runtime repair

Status: **Markets runtime mismatch repaired and verified on the owner's LAN URL.** This is a targeted Markets result, not acceptance of Company or Valuation workflows.

## Reproduction and root cause

- The normal local dev server was listening on port 3000 (PID 45237); no fixture/test mode was enabled. Direct `GET /api/research?scope=full` returned HTTP 200, `CACHE_FIRST`, `core_market: CACHED`, 34 sector rows, and core snapshot `ea1f3660b07fe36c`.
- Before the repair, `frontend/app/markets/page.tsx` and `frontend/app/markets/[section]/page.tsx` passed the bundled `research-system.json` (zero sector rows) into `MarketsRuntime`. The actual `/markets` server HTML contained eight `No sector row in this snapshot.` messages. Only `MarketsRuntime.useResearchRuntime()` could replace those rows, by client-side `GET /api/research?scope=full`.
- On the owner's `http://192.168.0.105:3000` origin, the Next.js dev log explicitly reported: `Blocked cross-origin request to Next.js dev resource /_next/webpack-hmr from "192.168.0.105"`. The first LAN browser trace waited two minutes without seeing the research API request. The blocked dev origin made the initial empty page especially persistent. This is not a Python provider or sector-adapter failure.
- The adapter in `frontend/lib/market-research.ts` correctly maps `ticker`, `rel_1m`, `rel_3m`, `rel_6m`, `as_of`, and `source`. Validated-failed rows still withhold numerical measurements. Breadth, crowding, stage, and company-level leadership remain unavailable without independent evidence.

## Implemented correction

- `frontend/lib/research-server.ts` is now the shared server-side research loader for the API route and Markets pages. Markets receives the same Python cached data at first render, before hydration. Failed Python refresh retains a prior populated snapshot; an unexplained zero-row refresh cannot silently replace it.
- `frontend/lib/research-response.ts` retains 34 prior rows if an incoming empty response lacks an explicit `empty_reason`, and marks the retained snapshot stale. A justified empty result can still be displayed.
- `frontend/next.config.mjs` allows the owner's exact LAN dev origin, `192.168.0.105`, in addition to `127.0.0.1`. Next dev restarted after the configuration change. The subsequent LAN browser trace recorded `GET http://192.168.0.105:3000/api/research?scope=full` with HTTP 200.
- `frontend/components/research/MarketsRuntime.tsx` exposes the server snapshot ID, row count, source and cache state immediately. `frontend/lib/market-research.ts` labels the valid Nov 4 rows `CACHED` and carries provider status into the sector explanation. `frontend/components/research/ObjectResearchSurfaces.tsx` displays source/date in the table and no longer draws a quantitative-looking bar for unmeasured company leadership.

## Before/after browser evidence

| Check | Before | After |
| --- | --- | --- |
| `/markets` server HTML | 8 `No sector row` messages | 34 dated sector measurements; zero `No sector row` messages |
| Normal LAN browser | All sector performance unavailable | 34 rows; healthcare 6M RS **+26.8%** vs SPY |
| `/markets?sector=semiconductors` | No row / observation date unavailable | SMH 6M RS **−12.0%** vs SPY, observed **2026-11-04**, source **Yahoo Finance / Python sector engine** |
| Browser API request | Not observed in the blocked-origin trace | `GET /api/research?scope=full`, HTTP 200, same core snapshot ID as direct API |
| Breadth/crowding/company leadership | Unknown despite decorative bars | Still unavailable; no fabricated measurements or quantitative bars |

The Nov 4 values are cached historical observations, **not live Nov 5 measurements**. The API row's provider diagnostic reports `OK` for the saved Yahoo Finance observation; that does not imply a fresh request at page-render time.

Artifacts: `frontend/artifacts/real-user-acceptance/markets-api.json`, `markets-browser-api.json`, `markets-server.html`, `markets-network-trace.json`, `markets-client.png`, `semiconductors-client.png`, and `semiconductors-leadership.png`.

## Verification

- `CHAINSTOX_BASE_URL=http://192.168.0.105:3000 node scripts/markets-runtime-acceptance.mjs`: **passed**; asserts 34 direct API rows, same browser/API snapshot, all dates in server HTML and browser table, semiconductors value/source/date, and no unmeasured leadership bars.
- `node scripts/runtime-reconciliation-test.mjs`: **passed**; covers all 34 captured rows, invalid measurement rejection, missing breadth/crowding, unexplained empty response retention, justified empty response, and failed-refresh retention.
- `npm run typecheck`: **passed**. `npm run lint`: **passed**. No Python or DCF code changed in this targeted repair. A production build was not run against the owner's active dev server.

## Remaining limitations and acceptance boundary

- The permitted LAN address is specific to the owner's current `192.168.0.105` address; if DHCP changes it, the new local address must be added to `allowedDevOrigins` and the dev server restarted.
- Individual-company leadership measurements, breadth, crowding, positioning, and stage remain unsupported by this sector payload; their unavailable labels are intentional.
- This verification does **not** establish real-user success for Company or Valuation, including PLTR historical FCFF reconciliation. Those workflows need separate acceptance before CHAINSTOX as a whole can be declared operationally ready.
