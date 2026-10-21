# CHAINSTOX Universal Company Research Audit

## Outcome

CHAINSTOX now has an on-demand deterministic path:

`ticker → SecurityResolver → one normalized snapshot → business-model classification → archetype registry → growth architecture → candidate constraints → structured evidence → scaling economics → sustainability → valuation review → validation → structural cache → progressive-depth UI`

No LLM API, embeddings, or qualitative document generator was added. Company Economics reviews valuation assumptions but does not mutate them.

## Previous six-company limitation

The economics ontology was reusable, but production presentation was fixture-bound:

- `frontend/components/research/ResearchShell.tsx` filtered a six-row `COMPANY_INDEX`.
- `frontend/app/company/[ticker]/page.tsx` generated only six routes and returned `notFound()` otherwise.
- `frontend/lib/data-provider.ts` exposed only six imported JSON payloads.
- `frontend/lib/research-visualization-adapter.ts` imported the same six fixtures as the dashboard company matrix.
- `research_system.py::company_research_index()` read frontend fixture files and labeled them as the company module.

Those fixtures were therefore being treated as the visible universe even though the backend classifier and archetype registry were broader.

## Production architecture

### Security resolution

`company_research.SecurityResolver` normalizes the ticker, collects identity and security metadata, maps the security type, checks the structural cache, and returns an explicit research state. The provider chain prefers the existing Yahoo/yfinance collector and falls back to SEC submissions plus Company Facts when the primary source is unavailable.

Supported routes: operating equities, financial institutions, and ADR operating companies. Explicit specialized-framework states are returned for ETFs/funds, REITs, and SPAC/shell structures. Invalid or unresolved inputs fail without creating a profile.

Version 1 prioritizes direct ticker resolution. It does not pretend to resolve arbitrary company names when a reliable provider lookup is unavailable.

### Normalized snapshot

`CompanySnapshot` now carries identity, exchange, currency, country, quote type, sector, industry, description, market/financial metrics, histories, periods, sources, source nature, and optional operational metrics. One collected snapshot is reused by classification, economics, evidence, and valuation review.

The SEC fallback supplies annual filing facts such as revenue, operating income, net income, operating cash flow, capex, SBC, cash, debt, shares, assets, and inventory where tagged. Missing fields remain absent.

### Classification

`BusinessModelClassifier` combines description patterns, industry patterns, sector support, gross-margin structure, capex intensity, and balance/operating evidence. Numeric structure can reinforce a metadata route but cannot create a specialized archetype by itself. Hybrid secondary archetypes are allowed. Sparse metadata falls back to `GENERIC_OPERATING_COMPANY` with low confidence.

Every profile includes routing evidence, confidence, whether an override was used, whether it changed the primary route, and the declarative changes involved.

### Constraints and evidence

The archetype registry produces candidate constraints; it does not declare them active. Financial proxies can rank candidates but cannot establish the primary constraint. Directionally useful, constraint-specific structured evidence is required; otherwise the primary constraint is `UNKNOWN` and the UI shows a qualitative research gap.

Evidence retains `FACT`, `PROXY`, and `INFERENCE`, plus `REPORTED`, `CALCULATED`, `DERIVED_PROXY`, and `INFERRED` source nature, evidence IDs, source, period, confidence, and inference references.

### Cache and states

Structural profiles are stored under `.cache/company_economics/` with schema version, source, financial period, analysis time, research state, and a normalized snapshot. Market price is explicitly excluded from the structural profile contract. The recent-research index is local history, not a supported-universe list.

States: `NOT_ANALYZED`, `ANALYZING`, `AVAILABLE`, `PARTIAL`, `INSUFFICIENT_DATA`, `UNSUPPORTED`, `STALE`, and `FAILED`. Profiles can be refreshed manually; age-based stale detection defaults to 30 days.

### CLI and API

- `python model.py economics AMD`
- `python model.py economics AMD --json`
- `python model.py economics AMD --json --refresh`
- `python company_research.py resolve AMD`
- `python company_research.py analyze AMD`
- `python company_research.py open AMD`
- `python company_research.py index`

The existing `/api/research` bridge now supports company resolve, cached open, recent index, and POST analysis. It does not introduce a competing API service.

### Frontend

`/companies` accepts an arbitrary ticker and labels recent research correctly. Global search routes ticker-shaped input to on-demand resolution. An uncached `/company/AMD` shows resolved identity and `NOT_ANALYZED`; Analyze runs named deterministic stages and then reuses the existing snapshot, Economic Map, evidence, financial, thesis, report, and valuation workspaces. Unsupported and failed states are explicit.

The six original JSON fixtures load only through explicit development mode (`?fixture=1`). They are no longer the production search list or dashboard universe.

## Classification validation

### Live structured-provider run, 2026-08-06

Yahoo returned rate-limit errors, so the production failover used SEC submissions and Company Facts. This is live structured validation, not fixture validation.

| Ticker | Live archetype | Confidence | Primary constraint | State / limitation |
|---|---|---:|---|---|
| AMD | Fabless Semiconductor | Moderate | Unknown | Partial; SEC industry and annual facts available; direct unit/supply evidence absent. |
| CRM | Traditional SaaS | Moderate | Unknown | Partial; subscriber/retention evidence absent. |
| META | Generic Operating Company | Low | Unknown | Partial; SEC SIC metadata cannot defend consumer-platform economics without description/user evidence. |
| WMT | Retail Physical Network | Moderate | Unknown | Partial; store/comparable-sales evidence absent. |
| BAC | Bank | Moderate | Unknown | Partial; bank route supported, constraint-specific funding/credit evidence incomplete. |
| CAT | Industrial | Moderate | Unknown | Partial; backlog/throughput evidence absent. |
| XOM | Commodity Producer | High | Unknown | Insufficient data; current SEC registrant facts did not provide a usable revenue history. |
| LLY | Pharma / Biotech | High | Unknown | Partial; pipeline/patient/patent evidence absent. |
| V | Payment Network | Moderate | Unknown | Partial; payment-volume/take-rate evidence absent. |
| UBER | Marketplace Platform | Moderate | Unknown | Partial; bookings/user/supply evidence absent. |

The META generic result and XOM insufficient-data result are intentional confidence discipline, not silently patched ticker exceptions.

### Deterministic fixture run

| Ticker | Fixture archetype | Primary constraint | Override used | Validation |
|---|---|---|---:|---|
| PLTR | Enterprise AI Software | Deployment Capacity | Yes | Passed |
| NVDA | Fabless Semiconductor | Advanced Packaging | Yes | Provisional |
| TSM | Semiconductor Foundry | Fab Capacity | Yes | Provisional |
| MSFT | Hyperscaler Cloud Platform | Compute Capacity | Yes; primary route changed | Provisional |
| JPM | Bank | Deposits | Yes | Provisional |
| COST | Retail Physical Network | Store Expansion | Yes | Provisional |
| AMD | Fabless Semiconductor | Advanced Packaging | No | Provisional |
| CRM | Traditional SaaS | Churn | No | Provisional |
| META | Consumer Platform | Customer Adoption | No | Provisional |
| WMT | Retail Physical Network | Store Expansion | No | Provisional |
| BAC | Bank | Deposits | No | Provisional |
| CAT | Industrial | Backlog Execution | No | Provisional |
| XOM | Commodity Producer | Production Capacity | Yes | Passed |
| LLY | Pharma / Biotech | Manufacturing Capacity | Yes | Provisional |
| V | Payment Network | Customer Adoption | Yes | Passed |
| UBER | Marketplace Platform | Customer Adoption | Yes | Passed |

Fixture operational fields are deliberately richer than generic live feeds and are never presented as live production evidence.

## Regression and static safeguards

- Six original fixtures remain regression examples.
- Ten broader companies cover additional archetypes.
- Ambiguous structures fall back or use secondary archetypes rather than forced certainty.
- Static tests reject functions such as `analyze_amd()` or `analyze_crm()`.
- Overrides are declarative data only.
- JSON serialization, evidence references, graph integrity, sources, periods, and non-mutation of DCF inputs are validated.

## Remaining structured-data limitations

- Full company-name lookup is not guaranteed in Version 1.
- SEC data has identity/SIC and standardized filings but usually lacks rich business descriptions and operating KPIs.
- Units, ASP, capacity, customers, ARR, NRR, seats, stores, same-store sales, deposits, NIM, backlog, production, prices, patients, pipeline probabilities, payment volumes, and bookings are used only when directly available.
- Period mismatch remains explicit; current employee counts are not silently treated as annual trend observations.
- Market price and market-implied valuation can be unavailable while Company Economics remains partial and useful.
- REIT NAV/AFFO, ETF holdings, and SPAC/pre-combination frameworks remain unsupported.
- Pre-profit biotechnology may classify structurally while constraint and valuation coverage remain insufficient.
- Direct operational evidence will eventually benefit from filings, calls, and IR-document research through the no-op qualitative interface. No LLM was called or added in this phase.

