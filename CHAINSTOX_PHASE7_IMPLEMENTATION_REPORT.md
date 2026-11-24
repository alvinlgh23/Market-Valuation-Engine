# CHAINSTOX Phase 7 Implementation Report

Completion date: 2026-10-23 (Asia/Kuala_Lumpur)  
Scope: Phase 7A data reliability, Phase 7B research epistemology, Phase 7C integration and verification  
Branch / inspected HEAD: `main` / `e6136d6eaf48f42f6e24554e56251e61622a1c90`

## Outcome

Phase 7 is complete within the approved scope. CHAINSTOX now distinguishes provider acquisition state, observation freshness, measurement validity, and research-claim sufficiency; improves US-GAAP and IFRS accounting coverage; restores verified live market-history flow for the final bounded run; and exposes the evidence states through Snapshot → Map → Inspector → Evidence → Report.

This is not a claim that every supported ticker is valuation-ready or that a public market provider is continuously reliable.

## Implemented changes

### Phase 7A — data reliability

- Added `evidence_contracts.py` with compact evidence, provider, coverage, validation, staleness, claim, binding, direction, and causal states.
- Added a typed/replayable Yahoo chart adapter in `data_sources/market_history.py`. HTTP 429, malformed JSON, empty responses, unsupported symbols, currency conflicts, and schema errors no longer collapse into an empty DataFrame.
- Routed `Valuation_model.fetch_history` through the typed adapter while preserving the existing in-process cache and analytics formulas.
- Kept provider diagnostics compact in API payloads; raw observations are available only when explicitly requested for replay.
- Extended SEC normalization to coherent current concept series, IFRS/20-F, reporting currency, aligned cash-flow periods, newer alternate US-GAAP concepts, and evidence envelopes.
- Fixed the prior TSM false-missing path by using `ifrs-full`; fixed current NVDA CapEx coverage through `PaymentsToAcquireProductiveAssets`; preserved AMD aligned US-GAAP coverage.
- Added `scripts/phase7_provider_diagnostics.py` for a reproducible company/market matrix.
- Added a strictly validated, source-attributed operational evidence registry and import path.
- Added compact macro metric provenance and propagated market-provider diagnostics through `research_system.py`.

### Phase 7B — research epistemology

- Added explicit claim types and independent binding, direction, and causal states.
- Applied conservative sufficiency rules: proxy-only claims never become observed constraints; direct direction does not automatically prove binding; stale evidence cannot establish current direction; counterevidence stays visible.
- Preserved candidate assessments instead of discarding unsupported structural mechanisms.
- Added an evidence registry and versioned research claims to Company Economics serialization.
- Added curated PLTR and TSM evidence with limitations that prevent metric substitution.
- Added negative tests for PLTR deployment capacity, NVDA packaging, TSM stale/counter evidence, and non-mutation of DCF inputs.

### Phase 7C — integration

- Extended frontend types and adapters to preserve provenance, constraint status, direction status, research claims, evidence registry, candidates, and qualification counts.
- Snapshot now separates observed, proxy/inference, unverified/stale, and counterevidence counts.
- Constraint Inspector and report show binding and direction separately.
- Evidence provenance view exposes source link, provider/source state, observation/retrieval dates, fiscal/filing dates, unit/currency, concepts, transformation, validation, freshness, and limitation.
- Structural candidates remain inspectable and explicitly unvalidated.
- Regenerated deterministic Company Economics fixtures from the backend serializer.
- Added a Phase 7 Playwright smoke for real Markets measurements and PLTR/NVDA/TSM evidence states.

## Live and deterministic verification

### Provider results

- Bounded Yahoo chart run: 7/7 live successes for SPY, QQQ, SMH, IGV, ^TNX, ^VIX, and JPY=X.
- Full Python sector engine: 34 rows; every requested sector history in that run reported `OK`.
- Actual API refresh: `LIVE_REFRESH`, 34 sector rows, no fallback.
- Actual Markets UI: SMH six-month relative strength rendered as −4.2% from the refreshed Python row.
- SEC official-data cache: aligned annual accounting coverage for all five benchmark companies; TSM IFRS/TWD path confirmed.
- AMD arbitrary-ticker resolution: succeeded through SEC metadata when Yahoo quote-summary returned HTTP 429. Resolution was supported; its research state remained stale/partial and no market data was fabricated.

Deterministic replay success is not labeled live success. Earlier Yahoo chart attempts and the final AMD quote-summary call demonstrate intermittent 429 behavior even though the final chart run passed.

## Test and build evidence

### Python

Command: `python3 -m pytest tests --collect-only -q`  
Result: **178 collected**.

Command: `python3 -m pytest tests -q`  
Final result after isolating the live-refresh cache from the macro fixture test: **178 passed, 0 failed, 28 subtests passed, 378 warnings**, 7.74 seconds.

The warnings are the known pandas chained-assignment FutureWarnings in the nested Centralbank Compass FRED adapter. No failures, skips, or deselections were hidden.

`unittest.defaultTestLoader.discover("tests").countTestCases()` remains **118**. The difference is now 60 pytest-style cases, including the 21 Phase 7 cases, which unittest discovery does not collect. The previous Phase 6 baseline was 157 pytest cases and 118 unittest cases; Phase 7 added 21 pytest-style cases. Historical count reconstruction was not attempted without evidence.

### Frontend

- `npm run typecheck`: passed.
- `npm run lint`: passed after removing four unused-import warnings; final rerun recorded in the validation audit.
- `npm run build`: passed; Next.js 16.2.9 compiled, typechecked, generated 23 static pages, and retained dynamic API/company/valuation routes.

### Browser suites

- `npm run smoke:phase7`: passed; 34 API sector rows, SMH −4.2%, PLTR/NVDA/TSM evidence qualification, provenance view.
- `npm run smoke:phase6`: passed; 10 screenshots.
- `npm run smoke:companies`: passed; 9 screenshots.
- `npm run smoke:markets`: passed.
- `npm run smoke:valuation`: passed; 24 screenshots.
- `npm run smoke:macro`: passed; 10 screenshots.
- `npm run smoke:macro-correction`: passed; 11 screenshots.
- `npm run smoke:research`: passed; 11 screenshots.

The initial Phase 7 Playwright launch was denied by the macOS sandbox before a page opened. The approved rerun passed; this is recorded as an environment retry, not a product failure.

## Screenshot review

Representative refreshed artifacts under `frontend/artifacts/phase6-product/` were visually inspected:

- Markets sector rotation showed dated live relative-strength values while breadth and crowding remained `Unavailable`; the empty rotation plane correctly withheld unsupported positioning coordinates.
- Company Economics retained the existing dark workstation layout and Snapshot/Map/Inspector hierarchy with no broad redesign or clipping regression.
- Phase 6, Companies, Valuation, Macro, and integrated research suites captured their normal evidence sets after the Phase 7 changes.

Phase 7-specific captures are `frontend/artifacts/phase7/01-live-markets.png` and `02-evidence-provenance.png`. The first confirms the live numerical sector rows while withholding unsupported breadth/crowding; the second confirms that fixture provenance is explicitly labeled and that observation/retrieval, concepts, transformation, validation, and freshness fields render without layout failure.

## Preserved safeguards

- Historical FCFF reconciliation and valuation blocking remain tested.
- SEC debt completeness gates remain tested.
- Failed valuation publication remains withheld.
- Treasury maturity, basis-point unit, and same-date curve gates remain tested and browser-verified.
- Shared configured Python runtime remains used by Company, Research, and Valuation API actions.
- Explicit fixture provenance, search/navigation, arbitrary ticker handling, reverse-DCF failure states, and scenario consistency remain intact.

## No economic-formula changes

No WACC, ERP, cost-of-debt, SBC, dilution, FCFF/FCFE, forecast horizon, growth fade, CapEx normalization, terminal value, scenario, or Reverse DCF formula changed. Evidence review remains advisory and read-only. Existing proposals in `CHAINSTOX_VALUATION_METHOD_GOVERNANCE.md` still require explicit approval and stronger evidence.

## Remaining limitations

- Yahoo endpoints remain intermittent and can rate-limit independently.
- There is no validated no-key alternate market-history provider.
- SEC-only data cannot complete a market-based DCF; TSM additionally needs an ADR unit bridge.
- PLTR debt coverage remains partial.
- Operational evidence coverage is intentionally curated and sparse.
- Direct current constraint KPIs remain unavailable for many companies; correct unknown/candidate states are expected.
- Some legacy macro observations still lack precise upstream observation dates.
- The generated evidence registry increases deterministic fixture size; it avoids live dataset duplication but could later be normalized for storage efficiency.

## Release decision

- Phase 7A: **COMPLETE WITH DOCUMENTED PROVIDER LIMITATIONS**.
- Phase 7B: **COMPLETE**.
- Phase 7C: **COMPLETE**.
- Real financial coverage improved: **YES** (IFRS TSM, aligned AMD/NVDA/benchmark accounting facts).
- Real market coverage improved: **YES FOR THE VERIFIED RUN** (34 live sector rows), with intermittent provider risk.
- Research claims appropriately evidence-qualified: **YES**.
- Phase 7 ready to close: **YES**.
- Ready for the next development phase: **YES**, provided the next phase treats provider durability, issuer-specific unit bridges, and broader direct operational evidence as explicit work rather than assuming they are solved.
