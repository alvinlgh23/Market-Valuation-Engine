# CHAINSTOX Visualization Coverage Audit

Audited after the visualization-layer refactor. Research formulas, classifications, evidence rules, source adapters, backend payloads, and analytical conclusions were not changed by this work.

## Visualization mapping

| Backend output | Frontend visualization | Drill-down path | Evidence source |
|---|---|---|---|
| Dashboard research states | Compact state cards | Overview card → owning module/country | `research-system.json.dashboard.reads` |
| Triggered research watches and priority | Ordinal ranked pressure instrument; no synthetic magnitude | Ranked row → evidence link | `dashboard.research_priority` |
| USD/JPY, EUR/USD, USD/SGD YoY changes | Zero-centred diverging bars in a shared `% YoY` group | Bar → date, classification, evidence note | Country Compass `indicator_values` + `evidence` |
| US credit-spread change | Separate zero-centred `pp / 6M` scale | Bar → date and evidence note | US Compass `credit_spread_change` |
| Five integrated regions | Interactive world research map | Hover → brief → click → held brief → country panel | `world.regions` |
| Policy, inflation, growth, liquidity, FX, market/risk states | Economy × research-dimension heatmap | Cell → country component → evidence | `world.regions.*.components` |
| Engine source state and defensible completeness | Coverage bars when numerator/denominator exist; categorical rails otherwise | Engine row → coverage detail/as-of state | `modules.*`, engine quality and registered counts |
| Six Company Economics benchmark fixtures | Comparative company matrix | Company row → existing Company Economics workflow | Company Economics fixtures and validation |
| Inflation category state | Six-category indicator heatmap/matrix | Category → metric cell → indicator inspector | Inflation `states` and `metrics` |
| Inflation current level, 3M/6M momentum | Current-value inspector and zero-centred momentum bars | Metric cell → current/date/source/reference/interpretation | Individual normalized inflation metric fields |
| Central Bank Compass policy blocks | Ranked bars using existing block scores | Country → Compass → block → indicator evidence | `central_bank_compass.blocks` |
| Central Bank Compass liquidity drivers | Diverging bars using exact score contributions | Driver bar → value, classification, explanation | `central_bank_compass.liquidity.drivers` |
| Shadow S$NEER history and estimated centre | Dual-line time-series chart | Singapore → Shadow S$NEER → history | NEER `history` |
| Shadow S$NEER 12-cross basket | Diverging 63-day contribution bars | Currency bar → weight, move, latest cross, contribution | NEER `fx_components` |
| Shadow S$NEER assumptions/coverage | Method disclosure beneath charts | Singapore → Shadow S$NEER → assumptions | NEER `policy_assumptions`, `coverage`, `warnings` |
| KOSPI five factor studies | Ranked factor-score bars | Korea → KOSPI → factor → observed normalized history | KOSPI `sweep.results` |
| KOSPI factor/KOSPI normalized observations | Dual-line time-series chart for selected factor | Factor selection → history chart | `result.detail.history` |
| KOSPI GARCH current volatility | State/KPI block | Korea → KOSPI | `sweep.volatility` |
| Korea export structure | Ranked USD-billion bars | Export row → share, period, source/note | KOSPI `exports.items` |
| Cross-border transmission evidence | Evidence-style graph with solid/dashed/dotted FACT/PROXY/INFERENCE edges | Edge → mechanism inspector → evidence record | `world.transmissions`, `evidence_index` |
| Company economic graph | Existing interactive directed economic map | Company → Economic Map → node → evidence/source | Company `economic_graph`, `evidence_trace` |
| Company valuation scenarios and reverse DCF | Existing valuation workspace and tables | Company → Valuation → Reverse DCF | Intrinsic Valuation / Company Economics payload |

## Quantitative outputs intentionally not drawn as charts

| Output | Reason |
|---|---|
| Inflation full historical observations | The normalized frontend payload supplies current level and 3M/6M momentum, not observation arrays. The indicator inspector states this explicitly; no historical line is reconstructed from deltas. |
| Current broad risk-regime and sector ranking | The last-valid run has 0% risk coverage and zero sector rows. The UI preserves `INSUFFICIENT` instead of drawing empty or misleading comparisons. |
| Compass indicator histories | Current values, thresholds, classifications, contributions, and evidence are supplied; per-indicator history arrays are not. Exact current scores/contributions are visualized instead. |
| KOSPI historical GARCH volatility path | The engine supplies the current GARCH result and persistence, not a normalized volatility time series. It remains a KPI/state. |
| KOSPI Foreign Flows history | Current result has zero observations. It appears as insufficient in the factor comparison and produces no line chart. |
| Official MAS S$NEER band | Official basket, weights, centre, slope, and band are undisclosed. Only the transparent shadow proxy is visualized. |
| Universal company score | No such deterministic backend output exists. Company comparison remains a categorical matrix. |
| Company chase/positioning risk in the comparative matrix | The current six Company Economics fixtures do not expose one consistent cross-company positioning field. Existing company-specific research surfaces retain available positioning evidence. |
| Advanced Compass allocation/backtest/narrative/energy/gold studies | These remain report-only outputs and do not belong to the default daily research screen. |
| Archived Private AI | Inactive, archived, and intentionally excluded. |

## Normalization integrity

Charts consume typed objects from `research-visualization-adapter.ts`. Numeric values, units, dates, states, confidence, evidence IDs, context, and scale groups remain separate. The adapter reads raw engine-specific numeric fields and never extracts numbers from display prose.

Unlike units are separated into independently labelled scale groups. Ordinal research priority uses rank only; it does not imply a magnitude. Coverage bars appear only when a defensible numerator and denominator exist. Missing, single-point, negative, and mixed-frequency inputs are covered by `npm run test:charts`.

## Interaction contract

The implemented sequence is:

`state → visual evidence → selected visual mark → mechanism/evidence panel → source record`

Charts use labels, position, borders, hatching, line style, and text states in addition to color. Country selection does not immediately open a long report: hover previews, click holds the brief, and a separate action enters the country research panel.
