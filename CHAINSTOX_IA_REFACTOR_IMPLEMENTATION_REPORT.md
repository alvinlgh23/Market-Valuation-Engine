# CHAINSTOX IA and Frontend Routing Refactor — Implementation Report

Completed: 2026-08-06

## Executive result

CHAINSTOX now presents one object-driven research system rather than a list of Python commands. The frontend is organized around Dashboard, Macro, Markets, Companies, Valuation, and Labs; Python remains the analytical authority. The deterministic `FACT / PROXY / INFERENCE` ontology, provenance, cache state, CLI aliases, and long-form report modes were preserved. No LLM was added and no analytical formula was changed.

This report is the requested 56-point delivery record. The canonical field audit is in `CHAINSTOX_PRODUCT_CAPABILITY_MAP.md`; route and interaction rules are in `CHAINSTOX_INFORMATION_ARCHITECTURE.md`; field-to-surface dispositions are in `CHAINSTOX_UI_COVERAGE.md`.

## 1–7. Audit, architecture, and navigation

1. **Repository audit findings.** The audit covered the CLI dispatcher, market model, research compositor, company report/economics stack, intrinsic valuation, inflation, risk regime, macro-world and central-bank integrations, S$NEER, KOSPI, data sources, cache/fixtures, tests, documentation, frontend, charts, and `/api/research`. The backend is substantially richer than the former UI: it already produces nested state, mechanism, evidence, provenance, coverage, model, and validation blocks. The principal defect was discoverability and routing, not a lack of engines.
2. **Complete backend capability inventory.** `CHAINSTOX_PRODUCT_CAPABILITY_MAP.md` records each meaningful engine/output, CLI entry, current/target surface, depth, and coverage status. The inventory includes macro regime, global/region research, Compass, inflation, liquidity/rates/FX, risk/defensive rotation, sector rotation/research, company condition/economics/positioning, evidence, valuation, fragility, historical/cache, and reports.
3. **Old frontend architecture.** Overview, Macro, Inflation, Rotation, Risk, Companies, Watchlist, and Historical were mixed as peers in a static command-shaped rail. A user needed to understand which tool owned a question.
4. **New frontend architecture.** The product hierarchy is `research payload → research object → state → mechanism → evidence → model/validation`. The same company object owns Overview, Economics, Positioning, Valuation, Evidence, and Full Report; sector and macro research use the same progressive-depth pattern.
5. **CLI → UI mapping.** `macro` maps to Macro Overview; `full` to Full Market Brief; `risk-regime` to Macro Risk and Markets Defensive Rotation; `sectors` to Sector Rotation; `sector/theme` to Sector Research; `company/stock` to Company Overview/Positioning; `inflation` to Macro Inflation; `value/valuation/dcf/fair-value` to a company valuation workspace; `economics/company-economics` to Company Economics; research-system commands feed the shared shell and report surfaces.
6. **New top navigation.** The primary navigation is exactly Dashboard, Macro, Markets, Companies, Valuation, and Labs, with the CHAINSTOX identity, global search, and explicit data-state indicator.
7. **Contextual sidebar architecture.** Macro, Markets, Company, Valuation, and Labs each receive an object-specific rail. Desktop shows the rail; tablet compacts navigation; mobile uses a primary drawer and horizontally scrollable contextual navigation.

## 8–16. Dashboard and Macro

8. **Dashboard.** `/` is an interactive launchpad, not the `full` report. It combines macro regime, inflation, risk, liquidity, regional state, priorities, observed moves, engine coverage, recent company research, valuation flags, and freshness. Cards route to their owning research object.
9. **Macro.** `/macro` is an integrated overview of policy, inflation, rates, liquidity, FX, risk, and regional tensions, with contextual access to all macro workspaces.
10. **World Map.** `/macro/world` preserves the map architecture. United States, Japan, South Korea, Singapore, and Euro Area are visibly available; unsupported economies are explicitly `NOT AVAILABLE`.
11. **Regional research.** Region selection opens a concise state card and then the complete available regional workspace. The UI retains Fed/US inflation and risk context, BOJ normalization/JPY, BOK/KOSPI factors, MAS/shadow S$NEER, and ECB/Euro signals according to backend coverage.
12. **Cross-region transmission.** Supplied deterministic transmission edges are exposed as an investigation graph and evidence inspector. Edges such as carry, USD/NEER, and policy/financial-condition channels are displayed only when present in the normalized backend payload.
13. **Inflation.** `/macro/inflation` exposes synthesis, horizon pressure, driver groups, driver map, and every normalized indicator rather than collapsing the 27-indicator engine to one badge. Missing inputs remain visible.
14. **Rates.** `/macro/rates` renders the actual policy/yield/curve fields supplied by the snapshot and routes deeper regional context through the macro object. Unsupported terms are not invented.
15. **Liquidity.** `/macro/liquidity` shows state, score/direction, available and missing drivers, and evidence depth. Coverage gaps are first-class content.
16. **Risk Regime.** `/macro/risk` is the macro home for regime state and evidence; `/markets/defensive-rotation` reuses that payload without recalculation.

## 17–22. Markets

17. **Markets.** `/markets` is the public-market-structure environment with Sector Rotation, Sector Research, Breadth, Crowding, and Defensive Rotation.
18. **Sector Rotation.** The hottest-sector output is presented as a scannable research-object table. A validated row opens its sector object.
19. **Sector Research.** `/markets/sector/[sector]` organizes Condition, Relative Strength, Breadth, Crowding, Leadership, and Companies. Human-readable aliases hide CLI alias mechanics.
20. **Breadth.** `/markets/breadth` owns validated breadth evidence. The current bundled snapshot is insufficient for a full time series, so the UI shows `INSUFFICIENT` rather than a static invented chart.
21. **Crowding.** `/markets/crowding` and sector/company contexts reference the same normalized evidence instead of duplicating calculations.
22. **Defensive Rotation.** `/markets/defensive-rotation` presents the shared risk engine through defensive leadership, cyclicals, credit, volatility, breadth, and rates when those fields exist.

## 23–29. Companies

23. **Company architecture.** `/companies` is a universal ticker/company entry. `/company/[ticker]` is one persistent research object with query-addressable views.
24. **Company Overview.** The overview synthesizes ticker/company, archetype, fundamental direction, growth, margins, cash flow, positioning, primary constraint, valuation context, confidence, and deliberate next investigations.
25. **Company Economics.** `?view=economics` preserves business-model architecture, growth engine, primary/secondary constraints, evidence/direction, scaling economics, sustainability, falsification, financial translation, valuation connection, expectations, gaps, and trace.
26. **Economic Map.** The economics view opens an interactive graph/workspace. Clicking a node opens deeper mechanism and evidence; `node=` keeps that state linkable and reloadable. It avoids turning the entire economics report into the default page.
27. **Positioning.** `?view=positioning` exposes the supplied market-expectations, thesis, chase-risk, and overheat context. Live normalization of every legacy positioning metric remains partial and is not overstated.
28. **Evidence.** `?view=evidence` exposes value, source, period, classification, confidence, freshness, gaps, and trace where supplied, retaining `FACT / PROXY / INFERENCE`.
29. **Full Company Report.** Long-form company output remains an explicit Full Report workspace rather than the overview interaction model.

## 30–35. Valuation and Labs

30. **Valuation architecture.** `/valuation` supplies the universal entry. `/valuation/[ticker]` resolves to the same `/company/[ticker]` valuation object and preserves fixture state, avoiding a duplicate model or provider request.
31. **DCF.** `?view=dcf` owns historical operating base, FCFF reconciliation, forecast years, present value, terminal value, enterprise-to-equity bridge, and shares when normalized valuation data is available. Direct live rendering is currently partial and reports unavailable fields rather than fabricating them.
32. **Reverse DCF.** `?view=reverse-dcf` is a dedicated investigation state for price, solved variable, bounds, fixed assumptions, required economics, and solver status. Failure states such as `NO_ECONOMIC_SOLUTION` remain prominent when supplied.
33. **Sensitivity.** `?view=sensitivity` is the destination for the supplied WACC × terminal-growth matrix and supported sensitivity dimensions. It does not convert missing matrices to prose or fake cells.
34. **Validation.** `?view=validation` owns forecast arithmetic, terminal value, EV/equity, share count, scenario ordering, `WACC > g`, reverse DCF, period consistency, and monotonicity statuses from Python.
35. **Labs.** `/labs`, `/labs/fragility`, and `/labs/historical` contain only implemented research. Fragility exposes its actual partial state; Historical is clearly a last-valid snapshot ledger, not an invented archive.

## 36–45. Search, state, API, and coverage

36. **Global search.** The existing keyboard-accessible search now returns typed COMPANY, SECTOR, REGION, and MODULE results for supported objects/routes, with recent universal-company results. Known regions/modules suppress false ticker guesses.
37. **Deep-link architecture.** Routes and query state preserve company views, economics nodes, valuation workspaces, macro submodules, region selection, and region detail on refresh. Verified examples include `/company/PLTR?fixture=1&view=economics&node=deployment_capacity` and `/macro/world?region=JP&detail=policy`.
38. **Cache/data-state handling.** The shell and surfaces distinguish `LIVE`, `CACHED`, `PARTIAL`, `STALE`, `INSUFFICIENT`, `UNAVAILABLE`, `FIXTURE`, analyzing, unsupported, and failed states. Freshness/as-of/source/confidence remain accessible. Loading labels describe actual deterministic work and do not invent percentages.
39. **API bridge changes.** `/api/research` remains the coherent gateway. Typed scopes select dashboard/world/full snapshots; refresh invokes Python and falls back to the last-valid bundled snapshot with error metadata. Typed company resolve/open/index/analyze operations use the same route and normalized company snapshot.
40. **Previously missing fields.** Regional child engines, inflation indicator detail, liquidity gaps, transmission edges, company constraint/evidence/falsification blocks, valuation assumptions/model checks, cache provenance, coverage states, and report payloads were previously absent or stranded behind command-shaped surfaces.
41. **How fields are now exposed.** Each field is assigned to summary, investigation workspace, evidence inspector, model/validation workspace, explicit report, conditional coverage gate, or documented debug exclusion. The exact field-level dispositions are in the capability and UI matrices.
42. **UI coverage percentage.** Deliberate audited disposition is **100%**: no meaningful normalized research block is silently dropped. Nine of eleven active analytical engines have full or conditional interactive coverage. Company positioning normalization and direct live intrinsic-valuation rendering are the two partial bridges.
43. **Deliberately report-only fields.** Long narrative reports, specialist Compass allocation/backtest/motive studies, some CSV/chart studies, raw debug diagnostics, and exhaustive engine traces stay in report/evidence modes because they would degrade the primary investigation flow.
44. **Still-missing backend capability.** No backend command was removed. Product gaps are presentation/data gaps: current cached sector rows lack sufficient breadth/crowding history; official MAS basket weights/centre/slope/band are unavailable; KOSPI foreign flow may be unavailable; historical is not a full time-indexed archive; the two live bridges above remain partial.
45. **Fixture/live separation.** Fixture use is explicit in route state and visible UI badges. Production provider failures do not silently substitute a fixture. Last-valid cache fallback carries its own error and freshness metadata.

## 46–52. Validation results

46. **Python regression results.** `python3 -m compileall -q .` passed. The main unittest suite passed **108/108**. The main pytest suite passed **121 tests** plus **28 subtests** (256 upstream deprecation warnings). The Central Bank Compass suite passed **14/14** (4 warnings). Bare root `pytest -q` has a collection-root collision with the nested Compass package's `src` import; running the two repository-standard roots explicitly is green.
47. **CLI regression results.** Passed: risk-regime; sectors; sectors all; sector semis; theme utilities; company NVDA; stock MU; inflation; inflation-debug; value MSFT `--json`; economics PLTR fixture `--json`; research-system inventory/dashboard/full `--json`; and macro. The live macro run completed with a Yahoo HTTP 429 diagnostic handled by its fallback. `model.py full` was exercised but exceeded the 90-second validation limit under provider throttling; it was not claimed as a pass. CLI dispatch and aliases remain intact.
48. **Frontend typecheck.** `npm run typecheck` passed.
49. **Frontend lint.** `npm run lint` passed.
50. **Frontend production build.** `npm run build` passed and generated all 22 app/API routes, including the new object and compatibility routes.
51. **Browser-flow validation.** Desktop and 390×844 mobile layouts were inspected in the in-app browser. Dashboard-to-module routes, typed search, company economics/economic-map depth, valuation workspaces, World Map regional investigations, refresh-persistent deep links, mobile drawer, contextual navigation, dialog sizing, focusable controls, and horizontal overflow were checked. Locale-dependent hydration mismatches were fixed.
52. **Screenshot locations.** Twenty-two reviewed screenshots are stored in `frontend/artifacts/ia-routing-refactor/`, covering every requested desktop state plus mobile navigation and the mobile economic map. Smoke suites also produced their own artifacts: macro (10), research capability (11), and visualization (6).

## 53–56. Remaining gaps and guarantees

53. **Remaining product gaps.** Priorities are completing direct live intrinsic-valuation normalization, completing legacy positioning normalization, persisting historical snapshots, and providing validated breadth/crowding history. Provider latency/rate limiting remains an operational issue for live full-report execution. These are documented states, not hidden defects.
54. **No LLM.** Confirmed: no LLM API, generated commentary, prompt layer, or synthetic research interpretation was added.
55. **Analytical formulas.** Confirmed: no analytical formula was changed. The only Python integration correction was allowing the already-supported `--refresh` option through `Valuation_model.py`'s company-economics CLI whitelist; it changes dispatch, not analysis.
56. **CLI availability.** Confirmed: existing commands and aliases remain available. The refactor changes frontend vocabulary and navigation, not the command-driven Python interface.

## Acceptance conclusion

The intended journeys now read naturally without CLI knowledge: market state begins at Dashboard/Macro/Markets; Japan begins at Macro → World Map → Japan; semiconductors begin at Sector Rotation → Sector Research; PLTR begins as one company object with Economics and Positioning; MSFT valuation reaches that same company object's valuation workspace. CHAINSTOX now exposes engines through research objects while preserving deterministic analytical depth and explicit coverage limits.
