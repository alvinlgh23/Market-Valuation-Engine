# CHAINSTOX Phase 7 Data Coverage

Audit date: 2026-10-23 (Asia/Kuala_Lumpur)  
Repository: `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`  
Commit inspected: `e6136d6eaf48f42f6e24554e56251e61622a1c90`

## Coverage conclusion

Phase 7 materially improves real accounting and market-history coverage without treating a provider response as proof of valuation completeness.

- Yahoo chart history: a bounded 2026-10-23 run returned 7/7 live series (SPY, QQQ, SMH, IGV, ^TNX, ^VIX, JPY=X). A full sector-engine run produced 34 dated rows. Earlier runs returned HTTP 429, and Yahoo quote-summary still returned HTTP 429 for AMD on the same audit date. The chart adapter is therefore working, but provider reliability remains intermittent.
- SEC Company Facts: cached official observations provide aligned annual accounting inputs for MSFT, PLTR, NVDA, AMD, and TSM. TSM now routes through `ifrs-full` / 20-F concepts in TWD instead of being incorrectly treated as missing US-GAAP data.
- DCF eligibility: none of the five SEC-only rows is valuation-ready because SEC Company Facts does not provide current price, market capitalization, or beta. TSM also needs a validated ADR/ordinary-share ratio and unit bridge. The system correctly preserves those blockers.
- Operational evidence: a validated, cited manual registry supplies selected PLTR and TSM disclosures. These observations remain historical reported facts with explicit limitations; they are not live feeds and do not establish a binding constraint by themselves.

## Data-lineage inventory

| Domain | Acquisition | Normalization / validation | Analytics | API | Frontend / conclusion gate |
|---|---|---|---|---|---|
| Market history | `data_sources/market_history.py::fetch_yahoo_history` | `normalize_yahoo_chart`; typed provider/source states, adjusted-price policy, dates, currency | `Valuation_model.py::fetch_history`, `compute_sectors` | `research_system.py::build_core_market` → `/api/research` | `integrateSectorEngineRows`; missing fields remain unavailable |
| Company filings | `data_sources/sec_company.py::_fetch` | US-GAAP/IFRS concept maps, coherent annual series, aligned OCF/CapEx, debt coverage | `intrinsic_valuation.py`, Company Economics snapshot | company and valuation API actions | valuation completeness gates; Company evidence registry |
| Company market/metadata | yfinance through existing collectors | existing security resolution and typed failure states | company resolution / valuation collection | `/api/research?action=company-*` and valuation actions | unsupported/provider failures remain distinct from disclosure gaps |
| Curated operational facts | `data/operational_evidence.json` | `load_operational_evidence`; required attribution, URL, period, unit, verification status | `enrich_snapshot` | serialized Company Economics profile | Evidence and provenance views; limitations visible |
| Macro / Treasury | existing official/cache adapters and Compass | existing maturity/date/unit gates plus Phase 7 metric provenance | `research_system.py::build_market_transmission` | `/api/research` | current curve withheld unless observation dates align |
| Cached / fixture data | `.cache/`, bundled frontend fixtures | source state and observation dates remain separate | last-valid fallback only | API metadata identifies fallback/cache | fixture mode remains explicit; not reported as live |

## Provider diagnostic matrix

Reproduce with:

```bash
python3 -B scripts/phase7_provider_diagnostics.py --timeout 5
```

| Security | Identity / exchange | Framework / currency | Annual accounting coverage | Debt | Market inputs from SEC | DCF eligibility |
|---|---|---|---|---|---|---|
| MSFT | Microsoft / Nasdaq | US GAAP / USD | revenue, operating income, OCF, CapEx, FCF, cash, shares | COMPLETE | price, market cap, beta missing | BLOCKED — missing market inputs |
| PLTR | Palantir / Nasdaq | US GAAP / USD | aligned FY2025 statements | PARTIAL; no complete aligned debt total | price, market cap, beta missing | BLOCKED — debt and market inputs |
| NVDA | NVIDIA / Nasdaq | US GAAP / USD | aligned FY ended 2026-01-25, including `PaymentsToAcquireProductiveAssets` CapEx | COMPLETE | price, market cap, beta missing | BLOCKED — missing market inputs |
| AMD | AMD / Nasdaq | US GAAP / USD | aligned FY2025 statements | COMPLETE | price, market cap, beta missing | BLOCKED — missing market inputs |
| TSM | TSMC / NYSE ADR | IFRS / TWD / 20-F | aligned FY2024 statements | COMPLETE | price, market cap, beta missing | BLOCKED — market inputs and ADR unit bridge |

Observed SEC cache retrieval timestamps were 2026-10-20 to 2026-10-21. The envelopes now retain those retrieval timestamps rather than replacing them with the analysis time. Fiscal observation dates remain separate.

## Market-history contract

Each result carries ticker, provider, provider status, source status, retrieval time, exchange, instrument type, currency, price type, adjustment policy, trading calendar, observation range, limitation, HTTP status, and observations. API diagnostics remove the observations and retain `observation_count`, so a full price dataset is not duplicated into every research response.

Deterministic replay covers:

- adjusted versus unadjusted close;
- timestamp/value alignment;
- empty and malformed responses;
- unsupported symbols;
- currency mismatch;
- duplicate observation dates;
- explicit warning that unadjusted price returns are not total returns.

## Live verification results

2026-10-23 bounded chart diagnostic:

| Symbol | Status | Type / currency | Observation end | Rows |
|---|---|---|---|---:|
| SPY | OBSERVED_LIVE / OK | ETF / USD | 2026-10-21 | 250 |
| QQQ | OBSERVED_LIVE / OK | ETF / USD | 2026-10-21 | 250 |
| SMH | OBSERVED_LIVE / OK | ETF / USD | 2026-10-21 | 250 |
| IGV | OBSERVED_LIVE / OK | ETF / USD | 2026-10-21 | 250 |
| ^TNX | OBSERVED_LIVE / OK | index / USD | 2026-10-22 | 251 |
| ^VIX | OBSERVED_LIVE / OK | index / USD | 2026-10-22 | 253 |
| JPY=X | OBSERVED_LIVE / OK | currency / JPY | 2026-10-23 | 260 |

The later API refresh returned `LIVE_REFRESH`, 34 sector rows, and compact per-row provenance. SMH reached the Markets UI with a six-month relative-strength observation of −4.2%. This verifies the actual Python engine → research API → React path.

## Operational evidence registry

The import path requires an issuer, metric definition, value, unit, reporting and observation dates, publication date, source title and URL, extraction method, and verification state. Invalid or unattributed records fail validation.

Current curated records:

- PLTR FY2025 customer count from the issuer’s [2025 Form 10-K](https://investors.palantir.com/files/2025%20FY%20PLTR%2010-K.pdf). It is explicitly not deployment capacity, seat count, contract conversion, or future revenue.
- TSM FY2025 wafer shipments, capacity lower bound, and advanced-node revenue mix from the issuer’s [2025 Annual Report](https://investor.tsmc.com/static/annualReports/2025/english/index.html). None is silently converted into exact utilization or an observed binding constraint.

## Remaining limitations

- Yahoo is an unauthenticated best-effort source. Chart history succeeded in the final run, but earlier 429 responses and the current AMD quote-summary 429 demonstrate endpoint-level intermittency.
- No compatible lawful no-key fallback was established. Stooq returned an access challenge and was not bypassed.
- SEC Company Facts is an accounting source, not a market-data source. It cannot make the DCF complete on its own.
- PLTR debt remains partial under the current concept set.
- TSM ADR/share conversion, current market inputs, and newer annual structured facts remain unresolved.
- Curated records require human source verification and are intentionally narrow.
- Current macro provenance is improved at the API metric boundary, but not every legacy upstream adapter exposes a precise observation date.

Release classification: data infrastructure IMPLEMENTED; live chart coverage VERIFIED FOR THE BOUNDED RUN; provider durability LIMITED; SEC-only valuation readiness BLOCKED BY MISSING MARKET INPUTS.
