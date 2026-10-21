# Company Economics Repository Audit

## Architecture before the refactor

`model.py` was a thin wrapper over `Valuation_model.run_cli`. Security resolution, company-type routing, market narrative, and positioning lived in `Valuation_model.py`; the mature-company report lived in `company_report.py`; and intrinsic valuation independently collected and normalized annual statements in `intrinsic_valuation.py`. Risk and inflation were already separate modules and required no architectural change.

The company flow was:

```text
Ticker alias resolution
-> Yahoo security metadata and price history
-> security-type integrity checks
-> mature / pre-profit / fund / shell routing
-> revenue, margin, FCF, valuation, price, narrative, and chase-risk output
```

The valuation flow was independently:

```text
Ticker
-> annual Yahoo statements
-> valuation security classification
-> normalized valuation dictionary
-> deterministic assumptions
-> FCFF DCF / reverse DCF / sensitivity / validation
```

## Data objects and dependencies

- `Valuation_model.resolve_security` returned an untyped dictionary containing requested and resolved ticker, `yfinance.Ticker`, metadata, price history, income and cash-flow frames, provider, and timestamp.
- `company_report.print_company_intelligence_report` fetched its own ticker object, price history, quarterly and annual income statements, and cash-flow statements, then passed ad-hoc comparison dictionaries between local functions.
- `intrinsic_valuation.collect_valuation_data` produced the strongest existing normalized dictionary: identity, classification, statement histories, revenue, operating income, FCF/FCFF inputs, cash, debt, shares, price, periods, and source context.
- `risk_regime.py`, `inflation_pressure.py`, and `data_sources/` do not depend on company report internals.

## Reusable metrics already available

- Revenue and prior-period revenue, revenue growth, and acceleration.
- Operating margin and margin change.
- FCF, FCF growth, FCF margin, and FCF yield.
- Capex, cash, debt, shares, market cap, and statement histories in valuation collection.
- Price returns, relative strength, 200-day moving-average distance, valuation multiples, and chase-risk evidence.
- Deterministic valuation assumptions, historical FCFF reconciliation, reverse DCF, and sensitivity output.

## Duplicated calculations and fetches

- Company reporting, security resolution, and valuation each parsed Yahoo metadata and financial statements independently.
- Revenue, operating margin, and FCF calculations existed in both `company_report.py` and `Valuation_model.py`; valuation used another annual normalization path.
- Security classification existed separately in company routing, company report, and valuation, for different reporting purposes.
- Price history and ticker metadata could be fetched multiple times during one company execution.

The refactor does not remove working legacy calculations. It adds `CompanySnapshot` adapters and lets valuation accept a pre-collected data object, enabling Company Economics and valuation to share collection without changing valuation math.

## Ticker-specific assumptions found

`Valuation_model.py` contains legacy ticker baskets and narrative sets such as AI leaders, mature quality, liquidity-sensitive assets, narrative decay, speculative turnarounds, and hard-asset companies. Those affect narrative/positioning output, not the new Company Economics domain logic.

The new engine has no ticker-specific analysis functions. `company_economics_overrides.py` contains only small declarative routing preferences, constraint priority, secondary archetypes, and future KPI aliases.

## Missing business-model logic before the refactor

- No reusable business-model archetype ontology.
- No explicit composed growth equation or driver observability.
- No reusable constraint registry, primary constraint, direction, interaction, or migration schema.
- No FACT / PROXY / INFERENCE provenance or evidence-reference validation.
- No structured data-gap model.
- No archetype-relevant scaling economics or safe incremental margin layer.
- No falsification engine tied to economic mechanisms.
- No financial translation or read-only valuation-assumption review.
- No market-expectations-versus-economics comparison.
- No company-economics JSON schema, causal graph, structural cache, schema version, or qualitative-provider boundary.

## Architecture after the refactor

```text
Security Resolution / Existing Valuation Collection
-> CompanySnapshot
-> BusinessModelClassifier
-> GrowthArchitectureBuilder
-> ScalingEconomicsAnalyzer
-> ConstraintClassifier + ConstraintDiagnosisEngine
-> GrowthSustainabilityInterpreter
-> FalsificationEngine
-> FinancialTranslationEngine
-> read-only ValuationAssumptionReviewer
-> MarketExpectationsComparator
-> Economic Graph + Validation + JSON / terminal output
```

Intrinsic valuation remains deterministic. Company Economics compares assumptions but never writes to them.

