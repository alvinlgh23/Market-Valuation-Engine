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
python model.py macro
python model.py sectors
python model.py sectors all
python model.py sector semis
python model.py theme energy
python model.py company NVDA
python model.py stock AAPL
python model.py risk NVDA
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
```

You can type either a number or a command. For example:

```text
Select: 1
Select: macro
Select: python model.py full
Select: stock NVDA
Select: sector semis
```

## Main Commands

### Full Market Intelligence Report

```bash
python model.py full
```

Runs the complete framework:

1. Global Liquidity Conditions
2. Macro Fragility Analysis
3. Macro Catalyst Monitor
4. Sector Rotation Analysis
5. Sector Positioning Analysis
6. Company Intelligence Report
7. Positioning / Overheat Analysis
8. Final Market Interpretation
9. Market Intelligence Extensions

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
- Macro fragility
- Macro catalyst monitor
- ERP context when available
- Preferred environment

The macro layer includes threshold diagnostics so major conclusions are tied to explicit reference levels.

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

Shows a company-level intelligence report:

- Revenue acceleration
- Margin expansion
- Free cash flow
- Quality score
- Valuation risk
- Financial quality
- Narrative strength
- Momentum / positioning
- Chase risk
- Positioning / overheat analysis
- Market interpretation when relevant

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

### 2. Macro Fragility Analysis

Uses:

- Consumer Sentiment
- ISM Manufacturing PMI
- Market breadth proxy using RSP vs SPY

This layer explains whether asset prices are diverging from real-economy confirmation.

Key references:

- Consumer sentiment below 60 signals household-confidence stress.
- ISM Manufacturing PMI below 50 signals manufacturing contraction.
- Negative RSP vs SPY means equal-weight breadth is weaker than cap-weight leadership.

### 3. Macro Catalyst Monitor

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

### 4. Sector Rotation Analysis

Uses sector ETF relative strength versus SPY across:

- 1 month
- 3 months
- 6 months

The goal is to identify where capital is rotating, not to generate a trade signal.

### 5. Sector Positioning Analysis

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

### 6. Company Intelligence Report

Company analysis separates:

- Financial Quality
- Narrative Strength
- Momentum / Positioning
- Valuation Risk
- Chase Risk

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

### 7. Positioning / Overheat Analysis

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

### 8. Final Market Interpretation

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

### 9. Market Intelligence Extensions

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

## Validation Commands

After code changes, run:

```bash
python3 -m py_compile Valuation_model.py model.py
python3 model.py macro
python3 model.py full
python3 model.py sectors
python3 model.py sector semis
python3 model.py stock NVDA
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
