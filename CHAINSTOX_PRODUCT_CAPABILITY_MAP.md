# CHAINSTOX Product Capability Map

Canonical audit date: 2026-08-06. Machine-readable authority: `research_capabilities.py`. `FULL` means the normalized payload has a deliberate interactive or report route; `PARTIAL` means the route exists but a deeper live adapter or validated current data is incomplete.

## Engine-to-product matrix

| Backend engine | CLI / entry point | Data produced | Previous frontend | Target module | Interaction depth | Coverage |
|---|---|---|---|---|---|---|
| Market Intelligence System | `model.py`, `full`, `macro` | rates, dollar, liquidity, M2, valuation/ERP, fragility, catalysts, interpretation | Overview summary | Dashboard; Macro Overview; Full Market Brief | summary → module → report | FULL |
| Sector Rotation | `sectors`, `sectors all`, `sector semis`, `theme utilities` | ranking, 1M/3M/6M RS, breakout, breadth, positioning, companies | Rotation tool | Markets → Sector Rotation → Sector Research | ranking → sector mechanism → evidence | FULL when validated; cached snapshot INSUFFICIENT |
| Risk Regime | `risk-regime`, `regime`, `rotation`, `defensive-rotation` | regime, confidence, evidence, conflicts, invalidation, unavailable inputs | Risk tool | Macro → Risk Regime; Markets → Defensive Rotation | state → cross-asset evidence → rules | FULL |
| US Inflation Pressure | `inflation`, `cpi`, `inflation-pressure`, `inflation-debug` | 27 metrics, grouped drivers, two horizons, Fed tension, watches, validation | Placeholder/module | Macro → Inflation | synthesis → driver map → all indicators → validation | FULL |
| Company Intelligence | `company NVDA`, `stock MU`, `risk NVDA` | identity, fundamentals, margins, FCF, valuation, momentum, chase risk, report warnings | Separate company tool | Company → Overview / Positioning / Full Report | synthesis → workspace → report | PARTIAL live normalization; report preserved |
| Company Economics | `economics PLTR`, `company-economics PLTR --json` | archetype, growth architecture, constraints, scaling, falsification, translation, graph, evidence, gaps | Strong company page | Company → Economics / Economic Map / Evidence | overview → graph → node → evidence | FULL |
| Intrinsic Valuation | `value`, `valuation`, `dcf`, `fair-value` | routing, FCFF, assumptions, scenarios, sensitivity, reverse DCF, checks, validation | Company valuation workspace | Valuation and Company → Valuation | overview → DCF/reverse/sensitivity → validation | PARTIAL direct live UI; FULL backend/report |
| Central Bank Compass | nested Compass CLI | policy blocks, scores, thresholds, liquidity, probability models, specialist studies | Country summary | Macro → World / Central Banks / regional detail | region → component → evidence → specialist engine | FULL core; advanced studies REPORT-ONLY |
| Shadow S$NEER | `NEER/SGD.py --json` | 12-cross proxy, centre/bands, deviation, volatility, contributions, history, assumptions | Singapore summary | Macro → World → Singapore → FX/NEER | brief → engine workspace → chart/evidence/method | FULL when live |
| KOSPI Monitor | `KOSPI_Backend_v2.py --json` | factors, correlations, adjusted Granger p, OLS, wavelet, GARCH, exports, history | Korea summary | Macro → World → South Korea → Markets/FX | brief → factor workspace → method/evidence | FULL when live |
| Macro World | `macro-world [region] --json` | five profiles, coverage, components, evidence, watches, transmissions | World page | Macro → World Map | map → region/edge → component → evidence | FULL |
| Research System | `research-system inventory|dashboard|full --json` | normalized system, states, errors, dashboard, modules, capabilities | API fixture | all product objects via `/api/research` | snapshot → typed scope → child payload | FULL |
| Universal Company Resolver | `company_research.py resolve|analyze|open|index` | security identity, support state, cache metadata, normalized profile | Fixture index | Companies entry + global search | resolve → analyze → cached object | FULL |
| Archived Private AI | no active CLI | archived static comparisons | none | none | archived | INTENTIONALLY EXCLUDED |

## Meaningful output-field disposition

| Payload block / fields | Frontend location | Depth | Disposition |
|---|---|---|---|
| `core_market.macro.*` including front rate, 10Y, 30Y, curve, DXY, USDJPY, VIX, M2, HYG/IEF, PE, earnings yield, ERP, liquidity/macro/risk scores | Macro Overview; Rates; Liquidity; FX; Full Brief | state/mechanism/report | VISIBLE or REPORT-ONLY |
| `core_market.fragility.*` including ISM, sentiment, breadth, interpretation | Labs → Fragility; Markets → Breadth; Full Brief | mechanism/report | VISIBLE |
| `core_market.catalysts.*` including CPI/core/PPI, labor, wages, claims, Fed expectation and interpretations | Full Brief; Macro Inflation context | mechanism/report | VISIBLE / REPORT-ONLY |
| `core_market.risk.regime/confidence/coverage/summary/evidence/interpretation/invalidation/unavailable` | Macro Risk; Markets Defensive Rotation | state/evidence/model | VISIBLE |
| `core_market.sectors[*].*` | Markets Rotation; Sector Research | ranking/mechanism | DRILL-DOWN when validated |
| `inflation.available/total/states/near_term/medium_term/horizon_reason/fed_sensitivity/common_month/latest_source/provisional` | Macro Inflation header/KPIs | state | VISIBLE |
| `inflation.metrics[*].key/name/section/source/series/current/date/trend_3m/trend_6m/reference/pressure_label/pressure_reason/status/freshness/validation_status/forward_role/economic_importance/endpoint` | Macro Inflation driver matrix and indicator inspector | mechanism/evidence | VISIBLE / endpoint metadata REPORT-ONLY |
| `inflation.validation`, `coverage`, `critical_missing` | Inflation evidence/report | model/validation | DRILL-DOWN / REPORT-ONLY |
| `world.regions[*].availability/confidence/brief/framework/as_of/components/gaps/watches/engines` | World Map and region inspector | state/mechanism | VISIBLE |
| `world.regions[*].evidence[*]` label/value/type/classification/period/freshness/source/source_path/note | Region evidence | evidence | VISIBLE |
| `world.regions[*].engine_specific.central_bank_compass` | Country specialist detail; Full JSON | model | DRILL-DOWN |
| `world.regions.SG.engine_specific.shadow_neer_live.current/fx_components/history/policy_assumptions/watch_conditions` | Singapore currency/NEER workspace | mechanism/evidence/model | DRILL-DOWN when live |
| `world.regions.KR.engine_specific.kospi_live.sweep.results/volatility/history/interpretation`, `exports` | Korea market/FX workspace | mechanism/evidence/model | DRILL-DOWN when live |
| `world.transmissions[*].source/target/label/structural_state/current_state/confidence/mechanism/summary/caveat/evidence_ids` | World Transmission graph + edge inspector | mechanism/evidence | VISIBLE |
| Company `classification`, `core_economic_question`, `growth_architecture` | Company Overview/Economics | state/mechanism | VISIBLE |
| Company `constraints`, `scaling_economics`, `growth_sustainability`, `falsification_conditions` | Economics graph/thesis/inspector | mechanism/model | VISIBLE |
| Company `financial_translation`, `valuation_assumption_review`, `market_expectations_comparison` | Financials/Valuation workspaces | mechanism/model | VISIBLE |
| Company `economic_graph.nodes/edges` | Economic Map | mechanism | VISIBLE |
| Company `evidence_trace`, `data_gaps`, `validation` | Evidence and Full Report | evidence/validation | VISIBLE |
| Valuation `company`, `valuation_method_selection`, `data_quality`, `historical_base`, `historical_fcff_reconciliation` | Valuation overview/DCF/report | state/mechanism | PARTIAL UI / REPORT-ONLY |
| Valuation `assumptions`, `discount_rate`, `scenarios`, `sensitivity`, `reverse_dcf`, `cross_checks`, `risks`, `fair_value_drivers`, `validation`, `fallback` | Valuation contextual workspace and full backend report | model/validation | PARTIAL UI / REPORT-ONLY |
| Capability registry, country coverage, transmission coverage, engine errors/states, freshness | Dashboard coverage; data-state badges; documentation | operations | VISIBLE / DOCUMENTED |
| Compass backtests, educational allocation, motive checks, raw debug exceptions | explicit reports/debug only | report/debug | INTENTIONALLY OMITTED FROM DAILY UI |

## Coverage result

- Deliberate disposition coverage: 100% of audited active engine blocks have an interactive, drill-down, report-only, partial, or unavailable disposition.
- Fully or conditionally interactive engine coverage: 9 of 11 analytical engines.
- Partial live UI bridges: Company Intelligence positioning normalization and Intrinsic Valuation deep rendering.
- No useful backend field is silently deleted; full normalized child payloads remain accessible to report/API consumers.

