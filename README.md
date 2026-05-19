# Market Intelligence System

A live Yahoo Finance market commentary system for reading how capital moves through markets.

The model is designed to explain:

- liquidity and cost of capital
- asset class attraction
- sector rotation
- narrative acceleration
- institutional-quality company rerating
- valuation stretch and overheating risk
- positioning risk and chase-risk stage
- sector-wide overcrowding risk
- market phase and leadership durability
- scenario confirmation / invalidation
- early rotation candidates and narrative decay warnings

## Flow

```text
Macro Environment
-> Liquidity / Cost of Capital
-> Sector Rotation
-> Narrative Formation
-> Institutional Capital Flow
-> Quality Companies Get Rerated
-> Valuation Expansion / Overheating
```

## Layers

1. Macro regime engine: rates, yield curve, DXY, VIX, and credit-risk preference.
2. Capital destination: relative strength of sector ETFs and asset proxies versus SPY.
3. Institutional target quality: growth, profitability, cash flow, balance sheet, and execution proxies.
4. Chase-risk engine: valuation stretch, RSI, moving-average distance, and vertical price acceleration.
5. Final market-structure read: a narrative output, not a buy/sell signal.
6. Intelligence extensions: regime playbook, risk map, scenario analysis, leadership durability, watchlist profile, and narrative decay checks.

## Usage

```bash
pip install yfinance pandas
python model.py
python Valuation_model.py
python model.py 6
python model.py full
python model.py macro
python model.py 1
python model.py sectors
python model.py sectors all
python model.py 2
python model.py sector semis
python model.py theme utilities
python model.py company NVDA
python model.py stock MU
```

Default menu:

```text
Market Intelligence System

1. Macro Regime Scan
2. Hottest Sector Leaderboard
3. Specific Sector Condition / Crowding
4. Specific Company Condition / Chase Risk
5. Company Overheat Check
6. Full Hottest-Market Report
```

Use `full` when you want the system to identify the current hottest sector and strongest candidate automatically.
The full report also adds a capital-flow story, market phase, leadership durability score, regime playbook, market risk map, scenario analysis, early rotation candidates, crowding-versus-quality matrix, watchlist profile, and narrative decay warnings.
Use `sector <name>` or `company <ticker>` when you want to inspect a specific sector or company regardless of whether it is currently ranked first.

Some macro indicators such as Fed Funds, M2, Reverse Repo, CPI, and credit spreads need external or manual data feeds for a complete institutional-grade stack.
