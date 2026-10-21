# CHAINSTOX Competition Demo

The competition demo uses real implemented CHAINSTOX surfaces with deterministic fixture/cached research states. It does not require live Yahoo/API calls for the core path.

## Recommended Fixture State

- Dashboard: cached `research-system.json`
- Macro: cached `macro-world.json`
- Markets: deterministic sector fixtures in `market-research.ts`
- Company: deterministic company economics fixtures, prefer `PLTR` or `NVDA`
- Valuation: deterministic Phase 5 valuation fixture, use `PLTR` for no-solution market-implied expectations or `MSFT` for converged DCF mechanics

Open: `/demo`

The route labels the product as deterministic demo mode and links into the real product routes.

## 60-Second Demo

| Time | Route / Action | Say |
| --- | --- | --- |
| 0-10s | `/demo` | CHAINSTOX maps economic mechanisms from global policy to company valuation. It starts with what changed, not a watchlist. |
| 10-25s | Open Japan -> US transmission | The macro layer separates region state from transmission. Click the edge to show mechanism and evidence. |
| 25-40s | Open Semiconductors | The market layer translates macro context into sector leadership, breadth, crowding, and structure. |
| 40-55s | Open PLTR company economics | The company layer maps growth engine, constraint, financial translation, and evidence. |
| 55-60s | Open PLTR valuation reverse DCF | The valuation layer asks what the price requires and whether the economics support it. |

## 3-Minute Demo

1. Start at `/demo`.
2. Use the Dashboard research priority to open Japan growth pressure.
3. Switch to Transmission and open Japan -> US.
4. Expand one evidence item and show source/period/confidence.
5. Open `/markets?sector=semiconductors&view=structure`.
6. Select a sector structure node and show linked companies.
7. Open `/company/PLTR?fixture=1&view=economics`.
8. Select the primary constraint node and show evidence/data gaps.
9. Open `/valuation/PLTR?view=reverse-dcf&from=company`.
10. Show market-implied expectations and the no-economic-solution state if present.

Expected outcome: the judge sees GLOBAL MECHANISM -> INDUSTRY MECHANISM -> COMPANY MECHANISM -> PRICE EXPECTATION -> EVIDENCE.

## 5-Minute Demo

1. Dashboard: What changed and Research Priority.
2. Macro: World Map, Japan region, Japan -> US transmission.
3. Evidence: open a macro evidence row and explain fact/proxy/inference boundaries.
4. Markets: Semiconductors rotation, sector structure, leadership/breadth/crowding.
5. Company: PLTR or NVDA company snapshot, economic map, constraint inspector.
6. Valuation: Snapshot, reverse DCF, sensitivity, validation.
7. Report: open Full Report or Full Market Brief to show print-ready complete read.

## Fallbacks

- If company live resolution fails, open `/company/PLTR?fixture=1&view=economics`.
- If valuation for a searched ticker is unavailable, open `/valuation/MSFT` for converged DCF or `/valuation/PLTR?view=reverse-dcf` for market-implied expectations.
- If internet is unavailable, use `/demo`, `/macro/world`, `/markets?sector=semiconductors`, `/company/PLTR?fixture=1`, and `/valuation/PLTR`.
- If a report surface is too dense for the time limit, return to Dashboard and use the snapshot/map/inspector sequence.
