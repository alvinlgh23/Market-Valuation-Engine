# CHAINSTOX UI Coverage

Updated: 2026-08-08. See `CHAINSTOX_PRODUCT_CAPABILITY_MAP.md` for field-level dispositions and `CHAINSTOX_INFORMATION_ARCHITECTURE.md` for routes and interaction rules.

## Surface matrix

| Backend source | Frontend location | Display depth | Visualization | Status |
|---|---|---|---|---|
| Research System dashboard | `/` | synthesis command center | current state strip, observed changes, research priorities, cross-system tensions, recent context, freshness/watch ledger | FULL PHASE 4 |
| Full market composition | `/brief` | report | structured report blocks | FULL |
| Core market macro | `/macro`, rates/liquidity/FX views | state → quantitative evidence → coverage | current yield curve, comparable FX moves, liquidity contributions; missing series grouped once | PARTIAL CURRENT FEED / FULL HONEST COVERAGE |
| Macro World | `/macro/world` | map → region → component → evidence | world map, transmission graph | FULL |
| Central Bank Compass | world regions, `/macro/central-banks` | mechanism → evidence/model | contribution/details when supplied | FULL CORE; REPORT-ONLY advanced studies |
| US Inflation | `/macro/inflation` | synthesis → group → indicator | driver matrix, comparable momentum bars | FULL (all 27 metrics) |
| Risk Regime | `/macro/risk`, `/markets/defensive-rotation` | state → coverage → evidence | compact coverage gate; missing ledger disclosed | FULL; CURRENT CONCLUSION WITHHELD |
| Sector Rotation | `/markets` | snapshot → positioning map → table | leadership/crowding plane, precise sector table | FULL PHASE 3 UX / CACHED BENCHMARK DATA |
| Sector Research | `/markets?sector=...`, `/markets/sector/[sector]` | snapshot → structure → inspector → report | sector structure map, node inspector, evidence ledger | FULL FOR BENCHMARK SECTORS; STRUCTURAL PARTIAL WHERE LABELED |
| Breadth/Crowding | `/markets?sector=...&view=breadth`, `/markets?sector=...&view=positioning`, legacy `/markets/breadth`, `/markets/crowding` | evidence lens | evidence ledger and gap strip | PARTIAL CURRENT DATA / PROXY-LABELED |
| Company resolver | `/companies`, global search | entry → resolution → analysis | deterministic progress state | FULL |
| Company Economics | `/company/[ticker]?view=economics` | overview → graph → node → evidence | economic graph/workspaces | FULL |
| Company positioning | `?view=positioning` | thesis/market expectations | supplied metrics only | PARTIAL LIVE NORMALIZATION |
| Company evidence/report | `?view=evidence`, Full Report | evidence/report | evidence ledger/report | FULL for normalized profile |
| Intrinsic valuation | `/valuation`, `/valuation/[ticker]` | snapshot → economics/model/market triad → DCF → reverse DCF → sensitivity → validation → evidence/report | fair-value range, FCFF bridge, forecast table, sensitivity matrix, validation grid | FULL PHASE 5 UX / DETERMINISTIC BENCHMARK DATA |
| Fragility | `/labs/fragility` | experimental mechanism | available fields | FULL at current coverage |
| Historical | `/labs/historical` | cache ledger | none fabricated | PARTIAL (last-valid states only) |

## Data-state and error coverage

The shell and research gateways expose `LIVE`, `CACHED`, `STALE`, `PARTIAL`, `INSUFFICIENT`, `UNAVAILABLE`, `FIXTURE`, `NOT_ANALYZED`, `ANALYZING`, `UNSUPPORTED`, `FAILED`, and `INSUFFICIENT_DATA`. Provider failure, cache reuse, unsupported security, coverage gates, and missing observations are first-class states. Fixture profiles remain explicitly labeled.

## Dashboard synthesis coverage

Phase 4 replaces the old dashboard-as-chart-index with a deterministic synthesis surface. It uses existing dashboard payload fields (`headline`, `reads`, `what_changed`, `research_priority`, `signals`, `global_regions`, `companies`, `valuation_flags`, `freshness`, and `watch_conditions`) plus Phase 3 cached sector research objects for market leadership context. It does not invent aggregate market scores, rank assets by expected return, or produce buy/sell language.

| Dashboard layer | Source | Route behavior | Current disposition |
|---|---|---|---|
| Current Market State | dashboard reads, valuation flags, sector leadership fixture | each read links to owning object | VISIBLE |
| What Changed | `dashboard.what_changed` | observed move rows link to source module | VISIBLE |
| Research Priority | `dashboard.research_priority` plus disclosed sector/risk coverage priorities | ranked investigation links | VISIBLE |
| Active Cross-System Signals | deterministic tensions between macro, inflation, risk coverage, and market leadership | routes to the object that can explain the tension | VISIBLE |
| Recent/Saved Research Context | cached company rows and valuation flags | links to company or valuation object | VISIBLE |
| Freshness/Watch Conditions | freshness and watch-condition ledgers | compact operational QA | VISIBLE |
| Global Search | shell command surface | resolves module, region, sector, and ticker routes | VISIBLE |

## Valuation field and surface mapping

Phase 5 consumes the intrinsic valuation JSON contract without changing valuation formulas. The deterministic benchmark fixture is generated from the existing Python valuation engine and test fixture mechanics; live Yahoo failures continue to surface as `INSUFFICIENT_DATA`.

| Backend valuation output | Frontend surface | Current disposition |
|---|---|---|
| `company.current_market_price` | Snapshot header, range marker, reverse DCF, sensitivity inspector | VISIBLE |
| `valuation_method_selection` / `fallback` | Snapshot, framework-required state, evidence view | VISIBLE |
| `historical_base` | DCF → Historical Base, Evidence/Data Quality | VISIBLE |
| `historical_fcff_reconciliation` | DCF → FCFF Reconciliation bridge | VISIBLE; failed state blocks fair value when backend blocks scenarios |
| `assumptions.bear/base/bull` | Snapshot, Assumptions inspector, Scenario Comparison | VISIBLE |
| `assumptions.policies` | Evidence/Data Quality and report context | VISIBLE AS POLICY CONTEXT |
| `discount_rate` | DCF → Discount Rate inspector | VISIBLE |
| `scenarios` | Fair-value range, DCF forecast, Scenario Comparison, Terminal Value | VISIBLE |
| `sensitivity` | WACC × Terminal Growth matrix and cell inspector | VISIBLE |
| `reverse_dcf` | Snapshot market-implied read and Reverse DCF workspace | VISIBLE; `NO_ECONOMIC_SOLUTION` is first-class |
| `cross_checks` | Full Report / valuation architecture mapping | VISIBLE IN REPORT CONTEXT |
| `fair_value_drivers`, `risks` | Full Report | VISIBLE |
| `validation` | Validation workspace and snapshot state | VISIBLE |
| `data_quality` | Evidence/Data Quality inspector | VISIBLE |
| Company Economics valuation review | Economics / Model / Market triad | VISIBLE; `mutates_dcf_inputs=false` preserved |

Benchmark coverage: MSFT and GOOG converged DCF, PLTR and NVDA no-solution reverse DCF, COST and XOM cross-company supported valuation, JPM framework-required financial institution state.

## Macro field and surface mapping

The Macro overview uses the existing `/api/research` payload. `research_system.market_transmission` is a typed presentation adapter over existing deterministic engine results; it adds no scoring or research formulas.

| Normalized source | Frontend route / depth | Surface | Current disposition |
|---|---|---|---|
| `market_transmission.coverage` | `/macro` → Data Coverage | coverage/freshness summary and disclosed available/missing fields | VISIBLE |
| `market_transmission.rates.current_curve` | `/macro` → Market Transmission → Rates; `/macro/rates` | current 2Y/10Y yield-curve chart | VISIBLE / CACHED |
| `market_transmission.rates.metrics.us_10y_real` | `/macro/rates` | compact typed metric | VISIBLE / CACHED |
| `market_transmission.rates.metrics.us_10y_2y` | `/macro` and `/macro/rates` | compact curve-spread metric | VISIBLE / CACHED |
| Missing 30Y, 3M rate moves and Treasury history | Rates coverage disclosure | one grouped partial-coverage state | VISIBLE AS GAP |
| `market_transmission.fx.moves` | `/macro` → Market Transmission → FX; `/macro/fx` | comparable YoY FX diverging bars, isolated from credit units | VISIBLE / CACHED |
| Missing DXY/current USDJPY/3M moves/history | FX coverage disclosure | one grouped partial-coverage state | VISIBLE AS GAP |
| `market_transmission.liquidity.drivers` | `/macro` and `/macro/liquidity` | seven-driver contribution view plus per-driver evidence and thresholds | VISIBLE / 5 OF 7 OBSERVED |
| `market_transmission.risk` | `/macro` and `/macro/risk` | insufficient-evidence state and compact missing-input disclosure | VISIBLE / COVERAGE-GATED |
| `world.regions` | `/macro` → World Map; `/macro/world` | supported map states, hover coverage, regional brief | VISIBLE |
| Unsupported geography | World Map | disabled/unavailable marker and explicit research-status tooltip | VISIBLE AS NOT AVAILABLE |
| `world.regions.*.engine_specific.central_bank_compass` | country brief → Compass | state, blocks, policy pressure, liquidity drivers, special policy model, evidence | VISIBLE |
| `modules.inflation.payload` | `/macro/inflation`; US regional evidence | 27-indicator deterministic engine | VISIBLE |
| `modules.neer.payload.history` | Singapore → Open NEER | 299-observation shadow S$NEER history vs estimated centre | VISIBLE / CACHED |
| `modules.neer.payload.fx_components` | Singapore → NEER → Contribution | all 12 currencies, weights, 21D/63D moves and numeric 63D contributions | VISIBLE / CACHED |
| NEER component historical arrays | currency inspector | explicit statement that no component series is supplied | VISIBLE AS GAP; NOT SYNTHESIZED |
| `modules.neer.payload.policy_assumptions`, `coverage`, `warnings`, `source`, `as_of` | Singapore → NEER → assumptions/evidence | transparent proxy assumptions and source trace | VISIBLE |
| `modules.kospi.payload.sweep.results` | South Korea → Open KOSPI | five factor studies, four observed histories, missing foreign flow isolated | VISIBLE / CACHED |
| `modules.kospi.payload.sweep.volatility` | South Korea → KOSPI → Volatility | GARCH current vs sample-average comparison, regime, clustering, persistence | VISIBLE / CACHED |
| `modules.kospi.payload.exports.items` | South Korea → KOSPI → Export structure | six-category ranked comparison | VISIBLE / CACHED |
| `world.transmissions` | `/macro` → Cross-Border Channels; `/macro/world?mode=transmission` | compact current states, graph, structural/current distinction, evidence inspector | VISIBLE |

### Macro re-audit dispositions

| Classification | Fields / cause | Resolution |
|---|---|---|
| Backend value existed; frontend wrong path | US 2Y, 10Y, 10Y–2Y, real yield, VIX and credit-spread evidence were under the US Compass/liquidity result rather than the generic core-market macro record | Added typed presentation mapping; values now reach charts/metrics with raw number, unit, date, source, state and confidence |
| Valid last-value cache | US Compass, Japan/Euro/Singapore Compass, NEER history/components, KOSPI factors/GARCH/exports | Shown as `CACHED` with last-valid dates; cache is not rendered as a failure |
| Integration-order mapping loss | Cached NEER/KOSPI evidence was attached after the initial world relationship build | Re-evaluated mapping-only edge state after attaching cached evidence; no analytical formula changed |
| Live provider failure / truly unavailable | US 30Y, 3M Treasury moves, Treasury history, DXY current/3M, USDJPY current/3M and comparable market histories | Retained as grouped missing coverage; no values or history fabricated |
| Coverage-gated | Cross-asset risk regime has 0% qualifying current inputs | Conclusion remains withheld; UI presents an intentional insufficient-evidence state |
| Intentionally undisclosed / unavailable | Official MAS basket and official NEER band position; component-level NEER histories; reliable current KOSPI foreign flows | Explicit gap or proxy label; no synthetic substitute |

## Macro progressive depth

`/macro` follows Global State → Market Transmission → World Map → Cross-Border Channels → Coverage. Regional investigation follows World Map → economy brief → component/specialist engine → evidence/source. Transmission investigation follows channel summary → structural mechanism/current state → evidence/counter-evidence/missing-evidence. The global navigation and other CHAINSTOX application surfaces are unchanged.

## Markets field and surface mapping

The Phase 3 Markets UI preserves the existing CLI semantics while avoiding frontend formula duplication. Live CLI commands remain:

- `python model.py sectors`
- `python model.py sectors all`
- `python model.py sector semis`
- `python model.py theme utilities`

Provider access returned Yahoo 429s during regression, so the interactive frontend uses deterministic cached/partial benchmark sector objects in `frontend/lib/market-research.ts`. These objects expose backend-compatible field names and label structural assumptions separately from current market state.

| Backend / CLI concept | Frontend route / depth | Surface | Current disposition |
|---|---|---|---|
| `compute_sectors`: ticker, name, rel_1m, rel_3m, rel_6m, breakout/score semantics | `/markets` | rotation positioning map and sector table | VISIBLE via cached benchmark fields; formulas unchanged |
| `sector_positioning`: relative_strength_6m | `/markets` map/table; sector snapshot | leadership axis and metric strip | VISIBLE |
| `sector_positioning`: breadth_label, breadth_tickers | sector snapshot; `view=breadth` | breadth state, participation ratio, evidence ledger | VISIBLE / PROXY-LABELED |
| `sector_positioning`: momentum_structure, stage | sector snapshot; positioning view | categorical stage and momentum read | VISIBLE |
| `sector_positioning`: narrative_type / risk / crowding | sector snapshot; `view=positioning` | crowding separated from momentum | VISIBLE / PROXY-LABELED |
| `SECTOR_CANDIDATES` | structure map and leadership | company links into `/company/[ticker]` | VISIBLE |
| Sector/theme aliases | `/markets?sector=...`, `/markets/sector/[sector]` | canonical sector lookup | VISIBLE |
| Sector structure ontology | `SectorStructureTemplate` | structural sector map and node inspector | VISIBLE; `STRUCTURAL_MODEL_PARTIAL` where support is limited |
| Direct positioning/options/capacity data | node inspector and evidence views | data-gap strip | VISIBLE AS GAP; NOT SYNTHESIZED |
| Risk Regime defensive context | `/markets/defensive-rotation` | defensive rotation evidence cards | VISIBLE; shared backend payload |

Benchmark coverage includes Semiconductors, Technology, Energy, Financials, Healthcare, Industrials, and Utilities. Semiconductors, Energy, Financials, and Utilities have visibly different structural maps; Healthcare and Industrials are labeled partial because current repository support does not justify deeper operational maps.

## Coverage percentage

Audited disposition coverage is 100%: every meaningful normalized research block has a named UI, drill-down, report-only, partial, debug-only, or intentionally excluded destination. Nine of eleven active analytical engines have full or conditional interactive coverage. The two remaining partial live bridges are documented above; this report does not claim they are complete.
