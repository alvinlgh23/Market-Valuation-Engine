# CHAINSTOX Research Tool Inventory

Audited: 2026-08-03. This inventory covers active Python entry points, nested research engines, terminal commands, normalized output contracts, data behavior, and deliberate exclusions. The machine-readable source is `research_capabilities.py`; the cache-aware integration entry point is `research_system.py`.

## Capability matrix

| Engine | Status | Canonical entry point | Primary output | Frontend surface |
|---|---|---|---|---|
| Market Intelligence System | Active / integrated | `python model.py full` | Liquidity, thresholds, fragility, catalysts, ERP, market interpretation | Overview, US macro, priority, changed, freshness |
| Sector Rotation | Active / coverage-gated | `python model.py sectors all` | Ranked sector strength, breadth, breakouts, conditions | Rotation module when live inputs validate |
| Risk Regime | Active / coverage-gated | `python model.py risk-regime` | Regime, confidence, 12-part evidence, conflicts, invalidation | Risk module; conclusion withheld below 50% coverage |
| US Inflation | Active / integrated | `python model.py inflation` | 27 metrics, five driver groups, two horizons, validation | Full inflation module and US country payload |
| Company Intelligence | Active / integrated | `python model.py company PLTR` | Financial and market report, decomposition, warnings | Company snapshot, report, evidence |
| Company Economics | Active / integrated | `python model.py economics PLTR --json` | Archetype, growth, constraints, translation, valuation, graph, ledger | Progressive company workspaces |
| Intrinsic Valuation | Active / partial UI | `python model.py valuation MSFT --json` | FCFF, scenarios, sensitivity, reverse DCF, reconciliation | Company valuation workspace; direct live bridge remains partial |
| Central Bank Compass | Active / integrated | `Centralbank-Compass/central-bank-compass/model.py --economy US` | Policy blocks, thresholds, scores, evidence, probability models, liquidity | Country inspector and specialist engine detail |
| Shadow S$NEER | Active / integrated | `python NEER/SGD.py --json` | 12-cross proxy, estimated centre/bands, 21D vol, 63D contributions, full history | Singapore specialist engine detail |
| KOSPI Monitor | Active / integrated | `python KOSPI/KOSPI_Backend_v2.py --json` | Five factor studies, Granger/OLS/wavelet details, GARCH, exports | Korea specialist engine detail |
| Macro World | Active / integrated | `python model.py macro-world --json` | Five country profiles, evidence, watches, engine-specific payloads, transmission edges | World map, country and edge inspectors |
| Archived Private AI | Archived / excluded | None | Historical private-AI report | Not exposed |

## Verified specialist runs

### US inflation

The current cached run populated 23 of 27 registered metrics. Both 1–3 month and medium-horizon synthesis were `Mixed / Two-sided`; Fed sensitivity was `Moderate`; the common comparison month was 2026-06; validation passed. All 27 records remain in the UI, including unavailable records, retrieval state, transformation, freshness, pressure reason, reference threshold, and source identity.

### Shadow S$NEER

The live 2026-08-03 run populated all 12 observable SGD crosses. The saved last-valid proxy was 113.2306 versus an estimated centre of 110.7687, or +2.2225%, classified as near the estimated upper band. Annualized 21-day proxy volatility was 1.5165%. The UI retains every basket weight, latest cross, 21/63-day move, contribution, gap ratio, history point, watch, and method assumption. The official MAS basket, weights, centre, slope, and band remain explicitly unavailable.

The NEER engine does not model reserves, policy rates, bond flows, equity flows, or imported inflation. These are labeled `NOT_MODELED`; no adjacent series is used as a substitute.

### KOSPI

The live sweep populated Cultural, Tech / AI, Consumption, Macro, and Foreign Flows studies independently. The normalized payload preserves correlations, Bonferroni-adjusted Granger p-values, best lag, OLS beta/R², wavelet SNR, observations, normalized history, data-source description, GARCH volatility, interpretation, and ranking. The current run classified the regime as `Tech-Sensitive` with high-volatility clustering, while warning that the leading Tech / AI relationship was noise-dominated.

The export payload retains total exports, semiconductors, ICT excluding semiconductors, K-content, games, music/K-pop, broadcast/video, each period, share, source, and mixed-period caveat. Portfolio-positioning sentences from the legacy API are intentionally not presented in the frontend because CHAINSTOX is a research system, not a recommendation engine.

### Central Bank Compass

Country integration is available for the United States, Japan, Singapore, and Euro Area. Every normalized country payload retains policy signal/bias, model view, confidence, tool, policy score, five block scores, coverage, indicator evidence, thresholds/reasons, missing indicators, decision rules, and all seven liquidity drivers. US probability and BOJ normalization-specific fields remain under `engine_specific` rather than being flattened away.

Advanced Compass studies—allocation, backtests, energy shock, real yield, dollar tide, Treasury demand, gold drivers, narrative tests, and motive checks—remain terminal/report capabilities. Allocation is educational/report-only; motive checks are not promoted as observable fact; historical CSV/chart artifacts stay report-only.

## Runtime integration

`research_system.py` is the single Python composition layer. It:

1. Calls existing calculations without reimplementing formulas in TypeScript.
2. Isolates engine failures.
3. Saves and reuses last-valid payloads in `.cache/research`.
4. Labels live, cached, stale, insufficient, and unavailable states.
5. Preserves full child payloads under `modules` and `world.regions.*.engine_specific`.
6. Refuses to publish broad risk/rotation output unless at least four of seven core macro inputs exist, risk coverage is at least 50%, and sector rows are populated.

The frontend route `GET /api/research` serves the bundled last-valid system immediately. `?scope=dashboard|world` narrows the response. `?refresh=1` asks the Python bridge for a live refresh and returns the bundled last-valid payload with error metadata if any engine or subprocess fails.

## Data semantics

- `LIVE`: refreshed successfully for this request.
- `CACHED`: last-valid deterministic payload.
- `STALE`: refresh failed; an older valid payload was reused.
- `INSUFFICIENT`: code executed, but evidence coverage failed the publication rule.
- `UNAVAILABLE`: no usable current or cached payload.
- `FIXTURE`: deterministic company research fixture, never represented as live.

Test mocks and pedagogical examples are not current research claims. Archived code is not an active engine. No LLM-generated research was added.
