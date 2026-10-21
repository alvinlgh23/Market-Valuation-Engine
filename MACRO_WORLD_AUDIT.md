# CHAINSTOX Macro World — Engine Audit and Integration Contract

## Product boundary

Macro is one research surface with two modes: **Regions** and **Transmission**. The initial coverage registry contains only the United States, Japan, South Korea, Singapore, and the Euro Area. Any other economy returns `NOT_AVAILABLE`; the UI does not synthesize a profile.

The progressive path is:

`World → Region → Brief → Component / Mechanism → Transmission → Evidence → Source`

NEER, KOSPI, and Central Bank Compass remain research engines behind the surface. They are not exposed as competing top-level products.

## Audited engines

| Engine | Preserved role | Current coverage | Material limitations |
| --- | --- | --- | --- |
| Central Bank Compass | Policy, inflation, growth, financial and FX blocks | US, JP, SG, Euro Area | Cached observation dates differ by series; gaps are retained in profiles. |
| Shadow S$NEER Proxy | Singapore currency-policy mechanism | Structural proxy | The basket, weights, centre, slope, and ±2% band are explicit assumptions. MAS does not disclose official parameters. No current machine-readable snapshot is persisted. |
| KOSPI Multi-Factor Signal Monitor | Korea market, USD/KRW, export, sector, and foreign-flow relationships | Structural plus annual exports | The current sweep requires external data and is not persisted. Econometric relationships are descriptive and are not causal proof. Annual category periods are mixed. |
| US Inflation Pressure | Existing US inflation research engine | US only | Listed as an integrated research source; its existing command and thresholds are not replaced by this adapter. |

## Regional coverage

| Region | Policy | Inflation | FX | Liquidity | Equity |
| --- | --- | --- | --- | --- | --- |
| United States | Available | Available | Available | Available | Partial market-conditions context |
| Japan | Partial | Partial | Available | Partial | Not available |
| South Korea | Not available | Not available | Structural only | Not available | Structural KOSPI model; current sweep unavailable |
| Singapore | Partial | Partial | Partial proxy coverage | Partial | Not available |
| Euro Area | Available | Available | Available | Partial | Not available |

`Available` describes audited engine coverage, not a guarantee that every series is live. The current frontend artifact is generated from the Compass cache and is labeled `CACHED`; KOSPI and NEER structural records retain their own explicit status.

- **United States:** strongest coverage. Central Bank Compass cached policy features and market conditions are available. Existing long-end yield and inflation engines remain separate deterministic inputs.
- **Japan:** BOJ normalization-pressure model is available. Wage growth, inflation expectations, BOJ balance-sheet trend, and some financial conditions remain gaps.
- **South Korea:** KOSPI/export/FX transmission structure is available. No Bank of Korea policy profile, Korean inflation model, current KOSPI sweep, or current foreign-flow series is integrated.
- **Singapore:** MAS exchange-rate policy framework and cached CPI/GDP/USD-SGD inputs are available. The official NEER position is unavailable; the shadow model is explicitly a proxy and its current output is not persisted.
- **Euro Area:** ECB policy, HICP, area-wide growth, unemployment, EUR/USD, and a sovereign-spread proxy are available. The map represents the monetary union, not every EU member. Services inflation, wages, bank lending, and broader spread coverage remain gaps.

## Transmission ontology

Each relationship has two independent fields:

- `structural_state`: whether the mechanism is defined by the audited research system.
- `current_state`: `DORMANT`, `WATCH`, `ACTIVE`, or `INSUFFICIENT`, calculated only when aligned current evidence exists.

Initial mechanisms are Japan-to-US yen carry/risk appetite, US-to-Japan rates and USD/JPY, Fed/ECB divergence and EUR/USD, US dollar conditions into KRW/KOSPI, and US dollar conditions into Singapore's exchange-rate policy framework. A channel is context, not proof of causation or a forecast.

## Backend contract

`macro_world.py` provides normalized region profiles, evidence records, coverage, and transmission edges. It wraps copied code in offline/cache mode and does not modify engine calculations.

```bash
python model.py macro-world --json
python model.py macro-world SG --json
python model.py macro-world --write-frontend-fixture frontend/lib/fixtures/macro-world.json
```

The legacy command is unchanged:

```bash
python model.py macro
```

## Evidence rules

- Every visible observation is labeled `FACT`, `PROXY`, or an explicit model classification.
- Source path, observation period, freshness, and caveat travel with the evidence.
- Period spreads over 45 days are `MISMATCH` and cannot support a current joint inference without qualification.
- Absent values remain absent. Missing data lowers confidence or yields `INSUFFICIENT`.
- The system produces research context only: no LLM-generated values, recommendations, buy/sell language, or fabricated coverage.
