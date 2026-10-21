# Market Intelligence System Documentation

## Purpose

This project is a rule-based Python market intelligence framework. It is designed to explain market structure, capital rotation, liquidity conditions, narrative strength, and positioning risk.

It is not a buy/sell signal generator, a trading bot, or a machine learning system.

The model should be read like a macro strategy desk note:

- What liquidity regime is dominant?
- Is macro fragility rising?
- What catalysts could destabilize the current structure?
- Where is capital rotating?
- Is leadership broad, narrow, institutional, speculative, or defensive?
- Are companies being rerated because of quality, narrative, liquidity, or momentum?
- Is positioning becoming crowded or overheated?

## Main Files

| File | Purpose |
| --- | --- |
| `model.py` | Thin CLI wrapper that imports and runs `Valuation_model.py`. |
| `Valuation_model.py` | Main market intelligence logic, data fetching, scoring, classification, and output formatting. |
| `inflation_pressure.py` | Forward US inflation-pressure engine using public FRED data and explicit thresholds. |
| `risk_regime.py` | Risk Regime & Defensive Rotation Monitor, including mock examples for the four core regimes. |
| `intrinsic_valuation.py` | Company-type-aware Stage 1 DCF, reverse DCF, sensitivity, fallback, and validation engine. |
| `company_economics.py` | Typed Company Economics domain model, deterministic builders, validation, JSON, graph, cache, and terminal output. |
| `company_research.py` | Universal security resolution, provider failover, research-state orchestration, structural cache, and JSON CLI. |
| `company_economics_registry.py` | Reusable archetype, growth-primitive, and constraint ontology. |
| `company_economics_overrides.py` | Small declarative routing/KPI exceptions; no per-ticker analysis functions. |
| `company_economics_fixtures.py` | Offline fixtures for 16 architecture benchmark companies. |
| `data_sources/sec_company.py` | SEC submissions and Company Facts fallback for identity and standardized annual filing data. |
| `README.md` | Short project overview and quick-start command list. |
| `SKILL_PUBLIC.md` | Public Codex skill guidance for maintaining the framework. |
| `documentation.md` | Full usage documentation. |
| `changelog.md` | Historical record of major project changes. |

## Installation

Install the required Python packages:

```bash
pip install yfinance pandas
```

The model uses live market and macro data from Yahoo Finance and public FRED CSV endpoints where available. Output can change as market data changes.

## Core Command Pattern

Run the interactive menu:

```bash
python model.py
```

Run commands directly:

```bash
python model.py full
python model.py risk-regime
python model.py macro
python model.py sectors
python model.py sectors all
python model.py sector semis
python model.py theme energy
python model.py company NVDA
python model.py economics PLTR
python model.py company-economics NVDA --json
python model.py stock AAPL
python model.py risk NVDA
python model.py inflation
python model.py cpi
python model.py inflation-pressure
python model.py value MSFT
python model.py valuation CRWD --json
python model.py dcf MU
```

`python Valuation_model.py` also works, but `python model.py` is the cleaner default entry point.

## Interactive Menu

When running `python model.py`, the system displays:

```text
Market Intelligence System

1. Macro Regime Scan
2. Hottest Sector Leaderboard
3. Specific Sector Condition / Crowding
4. Specific Company Condition / Chase Risk
5. Company Overheat Check
6. Full Hottest-Market Report
7. Risk Regime & Defensive Rotation
8. US Inflation Pressure Engine
9. Intrinsic Valuation Engine
10. Company Economics Engine
```

You can type either a number or a command. For example:

```text
Select: 1
Select: macro
Select: python model.py full
Select: stock NVDA
Select: sector semis
Select: risk-regime
Select: 8
Select: inflation
Select: 9
Select: value MSFT
```

## Main Commands

### Full Market Intelligence Report

```bash
python model.py full
```

Runs the complete framework:

1. Global Liquidity Conditions
2. Risk Regime & Defensive Rotation Monitor
3. Macro Fragility Analysis
4. Macro Catalyst Monitor
5. Sector Rotation Analysis
6. Sector Positioning Analysis
7. Company Intelligence Report
8. Positioning / Overheat Analysis
9. Final Market Interpretation
10. Market Intelligence Extensions

Use this when you want the model to identify the leading sector, strongest institutional-quality candidates, and current market character automatically.

The extension layer adds:

- Capital Flow Story
- Market Phase
- Leadership Durability Score
- Regime Playbook
- Market Risk Map
- Scenario Analysis
- Early Rotation Candidates
- Crowding vs Quality Matrix
- Current Watchlist Profile
- Narrative Decay Warnings

### Macro Regime Scan

```bash
python model.py macro
```

Shows:

- Global liquidity regime
- 10Y and 30Y Treasury yield context
- DXY trend
- USDJPY carry condition
- VIX risk perception
- M2 long-term liquidity backdrop
- Risk Regime & Defensive Rotation Monitor
- Macro fragility
- Macro catalyst monitor
- ERP context when available
- Preferred environment

The macro layer includes threshold diagnostics so major conclusions are tied to explicit reference levels.

### Risk Regime & Defensive Rotation

```bash
python model.py risk-regime
python model.py regime
python model.py rotation
python model.py 7
```

Runs the standalone Risk Regime & Defensive Rotation Monitor without the rest of the macro report.

### US Inflation Pressure Engine

```bash
python model.py inflation
python model.py cpi
python model.py inflation-pressure
python model.py 8
```

Runs one shared forward 3–6 month inflation report across wage pressure, the shelter/rent pipeline, services stickiness, energy/headline risk, and goods/supply-chain pressure. The synthesis uses explicit levels and trends to classify forward inflation pressure as `Easing`, `Sticky`, `Reaccelerating`, or `Mixed / Two-sided`, then connects the evidence to Fed sensitivity, yields, liquidity, and equity valuation sensitivity.

Public FRED series are used where available. Zillow, Apartment List, core PCE services ex housing, and ISM Prices Paid are clearly labeled `Unavailable` or `Not yet connected` until a stable free data path is configured. The engine does not create a black-box score or a trading recommendation.

### Intrinsic Valuation Engine

```bash
python model.py value MSFT
python model.py valuation CRWD
python model.py dcf MU
python model.py fair-value MSFT --json
python model.py value CRWD --wacc 0.10 --terminal-growth 0.03
python model.py value MSFT --revenue-growth 0.12 --fcf-margin 0.25
```

Stage 1 supports three complete frameworks:

- Mature operating company: five-year FCFF DCF.
- Growth software company: revenue-to-FCFF convergence DCF.
- Cyclical company: cycle-adjusted FCFF DCF using normalized mid-cycle economics.

Company-type routing uses quote type, sector and industry, verified financial
statements, revenue growth, gross and operating margins, free cash flow, and
cyclicality evidence. The report prints the selected framework and the evidence
that produced the route.

Financial institutions, REITs, pre-profit companies, ETFs/funds, and SPACs are
not forced through an industrial-company DCF. Their fallback reports identify
the required residual-income/dividend, NAV/AFFO, runway, portfolio NAV, or
trust-structure framework; list missing inputs; and name the next implementation
stage.

Bear, base, and bull cases use explicit revenue growth, Year-5 FCFF margin, WACC,
terminal growth, dilution, tax, and exit-multiple assumptions. Each assumption
includes its source, basis, confidence, scenario, and period. CLI overrides apply
to the base case and are marked as user overrides.

Reverse DCF solves for Year-1 revenue growth and reports the resulting five-year
CAGR while holding WACC, Year-5 FCFF margin, terminal growth, and dilution fixed.
It publishes search bounds, residual error, iteration count, and solver status.
Missing prices, unstable cash flow, boundary solutions, and out-of-range market
expectations are reported as non-convergence.

The WACC/terminal-growth sensitivity table recalculates every DCF cell. Cells
where WACC is not above terminal growth print `N/M`. Valid cells are checked for
the expected monotonic behavior.

Internal validation covers:

- forecast arithmetic
- Gordon-growth terminal value
- enterprise-value to equity-value bridge
- diluted-share conversion
- bear/base/bull ordering
- WACC above terminal growth
- reverse DCF convergence
- annual/TTM period consistency
- sensitivity monotonicity

JSON mode writes a single JSON document to standard output and contains the
company type, selected method, historical base, assumptions, discount rate,
scenarios, sensitivity, reverse DCF, cross-checks, risks, fair-value drivers,
data quality, validation, and final interpretation.

Supported override flags are `--revenue-growth`, `--fcf-margin`, `--wacc`,
`--terminal-growth`, and `--json`. Invalid values produce a concise error on
standard error and exit status 2 without a traceback.

### Sector Rotation Leaderboard

```bash
python model.py sectors
python model.py sectors all
```

`sectors` shows the top rotation leaders.

`sectors all` shows the full sector leaderboard.

The ranking is based on relative strength versus SPY across multiple time windows.

### Specific Sector Condition

```bash
python model.py sector semis
python model.py theme crypto
python model.py theme clean-energy
python model.py sector quantum
python model.py sector space
```

Shows a specific sector or theme regardless of whether it is currently ranked first.

The output includes:

- Top institutional-quality candidates in the sector
- Revenue acceleration
- Margin expansion
- Free cash flow
- Valuation risk
- Sector positioning analysis
- Sector PE expansion
- Breadth participation
- Sector narrative type
- Momentum structure
- Crowding or overcrowding risk

### Specific Company Condition

```bash
python model.py company NVDA
python model.py stock PLTR
python model.py stock NEM
```

Shows an evidence-first company intelligence report:

- Business fundamental evidence: TTM revenue, prior revenue, revenue growth, margin change, FCF growth, and FCF margin.
- Valuation reality check: forward PE, price / sales, EV / revenue, EV / EBITDA, FCF yield, and valuation sensitivity.
- Price action versus fundamentals: 6M performance, relative strength versus SPY, 200MA distance, PE change, and decomposition.
- Narrative and institutional conviction: evidence supporting and contradicting the narrative.
- Positioning / overheat / chase risk: distinguishes active chase risk from valuation reset or base-building.
- Measurable conditions that would strengthen or weaken the case.
- Final evidence-based company interpretation.

The company report does not use the quality score as the main output and does not turn the evidence into a buy/sell recommendation.

### Company Overheat Check

```bash
python model.py risk NVDA
```

Focuses on narrative strength, valuation expansion, momentum heat, and chase risk for a single company.

## Supported Sector Aliases

Common aliases include:

| Alias | Sector / Theme |
| --- | --- |
| `semis`, `semiconductors`, `ai`, `ai-infrastructure` | Semiconductors / AI Memory |
| `tech`, `technology` | Technology |
| `software`, `saas` | Software / SaaS |
| `cyber`, `cybersecurity` | Cybersecurity |
| `crypto`, `bitcoin` | Bitcoin / Crypto Infrastructure |
| `quantum`, `quantum-computing` | Quantum Computing |
| `space`, `satellite`, `rklb` | Space / Satellite Infrastructure |
| `energy` | Energy |
| `utilities` | Utilities / Power Demand |
| `defensives` | Consumer Staples |
| `healthcare` | Healthcare |
| `financials` | Financials |
| `industrials` | Industrials |
| `materials` | Materials |
| `real-estate` | Real Estate |
| `clean-energy`, `cleanenergy` | Clean Energy |
| `solar` | Solar |
| `uranium`, `nuclear` | Uranium / Nuclear Power |
| `commodities` | Broad Commodities |
| `gold` | Gold / Miners |
| `copper` | Copper / Electrification |
| `silver` | Silver |
| `agriculture` | Agriculture |

## Report Layers

### 1. Global Liquidity Conditions

Uses:

- US 10Y Treasury Yield
- US 30Y Treasury Yield
- DXY
- USDJPY
- VIX
- M2 Money Supply Trend

The layer distinguishes:

- Short-term liquidity pressure
- Long-term liquidity backdrop
- Long-duration fiscal stress
- Carry-trade liquidity support or unwind risk

Threshold diagnostics show:

- Current value
- Reference threshold
- Distance from threshold
- Classification
- Interpretation

Examples:

- 10Y yield near or above 4.50% means tighter valuation discount pressure.
- 30Y yield above 5.00% means elevated long-term fiscal stress.
- VIX below 15 means complacency; above 25 means stress.
- M2 above +0.50% over six months means an expanding long-term liquidity backdrop.

### 2. Risk Regime & Defensive Rotation Monitor

This module determines whether a selloff is best understood as:

- Healthy Rotation
- Narrow Leadership Unwind
- Broad Risk-Off
- Liquidity / Inflation Stress

It uses evidence across:

- US market structure: SPY / VOO, RSP, QQQ, SPMO, IWM
- Sector/style behavior: SMH or SOXX, XLY, XLF, XLI, XLV, XLP, XLU
- Global confirmation: EWL, EWJ, FEZ, EEM, ACWX
- Cross-asset stress: TLT, IEF, GLD or GLDM, UUP or DXY, HYG, LQD, VIX or VIXY

The output is narrative-first:

- Regime
- Confidence
- Market structure summary
- Evidence matrix
- Interpretation
- Invalidation triggers
- Portfolio stance

EWL / Switzerland is treated only as one global defensive equity proxy. It is never interpreted as a standalone signal.

The module influences sector and company-level interpretation:

- Healthy Rotation: company weakness may be constructive if fundamentals, sector strength, and breadth remain intact.
- Narrow Leadership Unwind: overheated momentum names are penalized and first-dip buying is treated cautiously.
- Broad Risk-Off: company-level quality needs a higher margin of safety and stronger balance-sheet confirmation.
- Liquidity / Inflation Stress: valuation multiples may compress even for good companies.

### 3. Macro Fragility Analysis

Uses:

- Consumer Sentiment
- ISM Manufacturing PMI
- Market breadth proxy using RSP vs SPY

This layer explains whether asset prices are diverging from real-economy confirmation.

Key references:

- Consumer sentiment below 60 signals household-confidence stress.
- ISM Manufacturing PMI below 50 signals manufacturing contraction.
- Negative RSP vs SPY means equal-weight breadth is weaker than cap-weight leadership.

### 4. Macro Catalyst Monitor

Uses:

- CPI
- Core CPI
- Final-demand PPI
- Non-Farm Payrolls
- Unemployment Rate
- Average Hourly Earnings
- Initial Jobless Claims
- Fed funds futures if available

This layer answers:

```text
What could destabilize or reinforce the current market structure?
```

It interprets catalyst risk through:

- Fed sensitivity
- Inflation-surprise risk
- Labor-market weakening risk
- Long-duration valuation compression
- Volatility expansion risk
- Growth-stock sensitivity

### 5. Sector Rotation Analysis

Uses sector ETF relative strength versus SPY across:

- 1 month
- 3 months
- 6 months

The goal is to identify where capital is rotating, not to generate a trade signal.

### 6. Sector Positioning Analysis

Sector positioning includes:

- 6M relative strength versus SPY
- Sector PE expansion
- Breadth participation
- Momentum structure
- Sector narrative type
- Current stage
- Crowding or overcrowding risk

Sector narrative types include:

- Institutional Momentum
- Stable Institutional Rotation
- Defensive Rerating
- Speculative Rebuilding
- Crowded Momentum
- Early-to-Mid Thematic Rotation
- Inflation-Hedge Rotation
- Defensive Hard-Asset Rotation

Crowding should only be called extreme when relative strength, PE expansion, breadth, and momentum all support it.

### 7. Company Intelligence Report

Company analysis separates:

- Business fundamental evidence
- Valuation reality check
- Price action versus fundamentals
- Narrative and institutional conviction
- Positioning / overheat / chase risk
- Strengthening and weakening conditions
- Final company interpretation

Narrative classifications include:

- Institutional AI Leader
- Mature Institutional Quality / Momentum Repair
- Expensive Conviction Growth
- Narrative Decay / Weakening Mature Platform
- Identity Uncertainty
- Speculative Turnaround
- Speculative Narrative Momentum
- Liquidity-Sensitive Narrative Asset
- Defensive Hard-Asset Rotation
- Inflation-Hedge Rotation
- Fundamentally Supported, Market Momentum Weakening

Example calibrations:

- `NVDA`: Institutional AI Leader
- `PLTR`: Expensive Conviction Growth
- `COIN`: Liquidity-Sensitive Narrative Asset
- `RBLX`: Identity Uncertainty
- `INTC`: Speculative Turnaround
- `NEM`: Defensive Hard-Asset Rotation
- `OSS`: Speculative Narrative Momentum
- `PYPL`: Narrative Decay / Weakening Mature Platform

### 8. Positioning / Overheat Analysis

Uses:

- 6M price performance
- Forward PE expansion
- Distance from 200MA
- Momentum structure
- Valuation heat
- Momentum heat

Momentum structure follows this philosophy:

- Negative 6M return and below 200MA means correction / base-building.
- +10% to +40% 6M performance is controlled or moderate momentum.
- +40% to +80% is elevated momentum.
- Above +80% or far above the 200MA can indicate parabolic acceleration.

Important distinction:

```text
Momentum Heat is not the same as Chase Risk.
```

A company can have moderate momentum heat without being an active high-chase-risk setup.

### 9. Final Market Interpretation

The final section synthesizes:

- Liquidity regime
- Macro fragility
- Macro catalyst sensitivity
- Leadership breadth
- Sector rotation
- Narrative concentration
- Inflation pressure
- Positioning risk

It also outputs a higher-level market character, such as:

- Selective Narrative Expansion
- Liquidity-Driven Risk Expansion
- Concentrated Institutional Leadership
- Inflation-Sensitive Rotation
- Speculative Late-Cycle Momentum
- Defensive Hard-Asset Rotation
- Broad Economic Expansion
- Fragile Mega-Cap Dominance

### 10. Market Intelligence Extensions

The extension layer turns the final market character into a more useful desk-note framework.

It includes:

- Capital Flow Story: a short explanation of where capital is moving and why.
- Market Phase: liquidity repair, selective leadership, broad participation, crowded momentum, or fragility.
- Leadership Durability: a score based on sector strength, breadth, company quality, macro fragility, Fed sensitivity, and heat.
- Regime Playbook: what usually works and what is usually vulnerable in the current regime.
- Market Risk Map: the highest-priority risks implied by macro, breadth, catalysts, and positioning.
- Scenario Analysis: bullish confirmations and bearish invalidations that would change the read.
- Early Rotation Candidates: sectors showing improving relative strength without already being fully extended.
- Crowding vs Quality Matrix: separates high-quality accumulation from speculative momentum risk.
- Current Watchlist Profile: the type of setup the regime currently rewards.
- Narrative Decay Warnings: signs that a leader or candidate is lagging, losing momentum, or failing to confirm its sector.

These additions are still descriptive. They should not be read as buy/sell recommendations.

## Company Economics Engine

### Purpose and pipeline

The Company Economics Engine explains how a business grows, what limits scaling, whether the constraint is easing or tightening, and how the evidence should inform—but never automatically change—valuation assumptions.

```text
Security Resolution
-> Company Data Collection / CompanySnapshot
-> Business Model Classification
-> Growth Architecture and Drivers
-> Primary / Secondary Constraints
-> Constraint Evidence and Direction
-> Scaling Economics
-> Growth Sustainability
-> Falsification Conditions
-> Financial Translation
-> Valuation Assumption Review
-> Market Expectations Comparison
-> Final Economic Interpretation
```

### Ontology

Version 1 supports 15 archetypes: enterprise AI software, traditional SaaS, fabless semiconductor, semiconductor foundry, hyperscaler/cloud platform, consumer platform, retail physical network, bank, industrial, pharma/biotech, commodity producer, payment network, marketplace platform, utility/infrastructure, and generic operating company.

Growth equations compose reusable primitives including customers, users, subscribers, seats, ARPU, pricing, volume, units, ASP, product mix, stores, same-store sales, membership, workloads, cloud spend, transaction volume, take rate, assets, spreads, fees, wafer volume, node mix, capacity, utilization, backlog, patients, drug portfolio, production, commodity price, engagement, ad inventory, and gross bookings.

Constraints are reusable mechanisms such as deployment or sales capacity, adoption/churn/saturation, compute/power/datacenter capacity, foundry/packaging/memory/fab capacity, capital intensity, store/logistics/labor limits, bank funding/capital/credit, backlog/production/raw-material limits, pipeline/patent/approval/manufacturing dependencies, inventory, concentration, and price elasticity.

### Evidence, confidence, and gaps

Evidence is explicitly `FACT`, `PROXY`, or `INFERENCE`. Source nature is separately `REPORTED`, `CALCULATED`, `DERIVED_PROXY`, or `INFERRED`. Facts identify source and period. Inferences must cite supporting evidence IDs; validation fails for orphan references.

Confidence is rule-based:

- `HIGH`: multiple direct, consistent observations plus supporting evidence.
- `MODERATE`: direct evidence plus a proxy, or several consistent proxies.
- `LOW`: mainly indirect evidence.
- `INSUFFICIENT`: no defensible evidence.

Unavailable operating KPIs produce `DataGap` objects containing the missing field, related driver/constraint, why it matters, confidence effect, and any fallback proxy. Period mismatch remains visible and should lower confidence rather than be silently combined.

### Scaling, falsification, and valuation boundary

Scaling metrics are selected from the archetype registry. Incremental operating and FCF margins use `Δincome / Δrevenue` only when the revenue denominator is positive. The engine does not calculate irrelevant ratios merely because fields exist and emits no 0–100 business score.

Falsification conditions are observable thesis-break conditions such as customer deceleration, inventory outrunning revenue, utilization falling after capacity additions, or capex failing to convert into workload growth. Generic filler risks are excluded.

Financial translation classifies revenue, margin, capital intensity, and FCFF implications. The valuation review compares those observations with DCF growth and normalized margin assumptions. It is read-only: `mutates_dcf_inputs` must remain `false`. Reverse DCF, when converged, is compared with supported economics through categorical states rather than an automatic numerical adjustment.

### JSON, Economic Graph, cache, and future qualitative evidence

Pure JSON uses the top-level `company_economics` envelope and schema version `1.1`. It includes a causal `economic_graph` with node types `growth_driver`, `constraint`, `resource`, `revenue`, `margin`, `cash_flow`, `valuation`, and `risk`; relationships are `drives`, `limits`, `supports`, `pressures`, `converts_to`, or `depends_on`.

Structural cache files live under `.cache/company_economics/` and explicitly exclude live market price. Interfaces separate structured financial, structured operational, and qualitative evidence. The Version 1 qualitative extractor returns `UNAVAILABLE`; there is no LLM dependency.

On-demand research uses `ticker -> SecurityResolver -> normalized snapshot -> classifier -> archetype registry -> evidence/constraint engine -> valuation review -> structural cache`. Research states are `NOT_ANALYZED`, `ANALYZING`, `AVAILABLE`, `PARTIAL`, `INSUFFICIENT_DATA`, `UNSUPPORTED`, `STALE`, and `FAILED`. The Yahoo/yfinance collector falls back to SEC submissions and Company Facts; missing operational KPIs remain explicit gaps.

Benchmark fixtures cover PLTR, NVDA, TSM, MSFT, JPM, COST, AMD, CRM, META, WMT, BAC, CAT, XOM, LLY, V, and UBER. See `company_economics_benchmarks.md`, `COMPANY_ARCHETYPE_COVERAGE.md`, and `UNIVERSAL_COMPANY_AUDIT.md` for mechanisms, routing coverage, live validation, and limitations.

### Limitations

- Version 1 relies mainly on structured financial evidence.
- Company-specific operating KPIs may be unavailable. Proxies may rank candidate constraints but cannot establish a primary constraint.
- Filing, transcript, and investor-presentation extraction is not live.
- `UNKNOWN` is an intended output, not a runtime failure.
- Segment-level economics and historical bottleneck migration remain future work.
- The system does not generate investment recommendations.

## Validation Commands

After code changes, run:

```bash
python3 -m compileall .
python3 -m unittest discover -s tests -v
python3 -m pytest -q tests
python3 model.py economics PLTR --fixture
python3 model.py company-economics NVDA --fixture --json
python3 company_research.py open AMD
python3 company_research.py index
python3 model.py macro
python3 model.py full
python3 model.py sectors
python3 model.py sector semis
python3 model.py stock NVDA
python3 risk_regime.py
```

For narrative calibration, also test examples:

```bash
python3 model.py stock PLTR
python3 model.py stock COIN
python3 model.py stock RBLX
python3 model.py stock OSS
python3 model.py stock NEM
```

## Interpretation Rules

- Do not make unsupported macro claims.
- Keep threshold diagnostics for major macro conclusions.
- Do not call weak momentum overheated.
- Do not call every positive trend crowded.
- Separate financial quality from narrative quality.
- Separate valuation risk from chase risk.
- Treat M2 as a long-term liquidity backdrop, not a timing signal.
- Treat 10Y yield as valuation discount pressure.
- Treat 30Y yield as long-term fiscal and duration stress.
- Treat commodity and gold leadership as macro hard-asset rotation when inflation pressure and fragility are elevated.
