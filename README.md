# CHAINSTOX

## CHAINSTOX Macro World

The macro frontend is backed by a normalized research-engine integration spanning the United States, Japan, South Korea, Singapore, and the Euro Area. See [MACRO_WORLD_AUDIT.md](MACRO_WORLD_AUDIT.md) for the coverage matrix, proxy disclosures, transmission ontology, CLI examples, and known data gaps.

A market intelligence and valuation research system for reading how capital moves through markets.

The model is designed to explain:

- liquidity and cost of capital
- asset class attraction
- sector rotation
- narrative acceleration
- institutional-quality company rerating
- forward US inflation pressure across wages, shelter, services, energy, and goods
- valuation stretch and overheating risk
- positioning risk and chase-risk stage
- sector-wide overcrowding risk
- risk regime and defensive rotation
- market phase and leadership durability
- scenario confirmation / invalidation
- early rotation candidates and narrative decay warnings
- company-type-aware intrinsic valuation, reverse DCF, and sensitivity analysis
- business-model, growth-engine, constraint, and evidence-traceable Company Economics

## Flow

```text
Macro
-> Sector
-> Company Fundamentals
-> Company Economics
-> Growth Sustainability
-> Intrinsic Valuation
-> Market Expectations
-> Positioning / Chase Risk
```

## Layers

1. Macro regime engine: rates, yield curve, DXY, VIX, and credit-risk preference.
2. Risk Regime & Defensive Rotation Monitor: rotation versus leadership unwind, broad risk-off, or liquidity / inflation stress.
3. Capital destination: relative strength of sector ETFs and asset proxies versus SPY.
4. Institutional target quality: growth, profitability, cash flow, balance sheet, and execution proxies.
5. Chase-risk engine: valuation stretch, RSI, moving-average distance, and vertical price acceleration.
6. Final market-structure read: a narrative output, not a buy/sell signal.
7. Intelligence extensions: regime playbook, risk map, scenario analysis, leadership durability, watchlist profile, and narrative decay checks.

## Usage

```bash
pip install yfinance pandas
python model.py
python Valuation_model.py
python model.py 6
python model.py full
python model.py 7
python model.py risk-regime
python model.py macro
python model.py 1
python model.py sectors
python model.py sectors all
python model.py 2
python model.py sector semis
python model.py theme utilities
python model.py company NVDA
python model.py economics PLTR
python model.py company-economics NVDA --json
python model.py stock MU
python model.py risk NVDA
python model.py conclusion
python model.py inflation
python model.py cpi
python model.py inflation-pressure
python model.py value MSFT
python model.py valuation CRWD --json
python model.py dcf MSFT --wacc 0.10 --terminal-growth 0.03
python risk_regime.py
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
7. Risk Regime & Defensive Rotation
8. US Inflation Pressure Engine
9. Intrinsic Valuation Engine
10. Company Economics Engine
```

Use `full` when you want the system to identify the current hottest sector and strongest candidate automatically.
The full and macro reports include a Risk Regime & Defensive Rotation Monitor to distinguish healthy rotation, narrow leadership unwind, broad risk-off, and liquidity / inflation stress.
The full report also adds a capital-flow story, market phase, leadership durability score, regime playbook, market risk map, scenario analysis, early rotation candidates, crowding-versus-quality matrix, watchlist profile, and narrative decay warnings.
Use `sector <name>` or `company <ticker>` when you want to inspect a specific sector or company regardless of whether it is currently ranked first.

Company reports are evidence-first. `company <ticker>` and `stock <ticker>` now separate business fundamentals, valuation reality, price action versus fundamentals, narrative conviction, positioning risk, strengthening conditions, weakening conditions, and a final evidence-based interpretation.

## Company Economics Engine

Company Economics is the deterministic bridge between company fundamentals and intrinsic valuation. It classifies a company into a small reusable archetype library, composes its growth equation, identifies supported or candidate scaling constraints, calculates only archetype-relevant efficiency metrics, generates observable falsification conditions, and reviews valuation assumptions without modifying them.

```bash
python model.py economics PLTR
python model.py company-economics NVDA --json
python model.py economics TSM --fixture  # deterministic offline benchmark
python company_research.py resolve AMD
python company_research.py analyze AMD
python company_research.py open AMD
python company_research.py index
```

Version 1 includes enterprise AI software, SaaS, fabless semiconductor, foundry, hyperscaler, consumer platform, physical retail, bank, industrial, pharma/biotech, commodity producer, payment network, marketplace, utility/infrastructure, and generic operating-company archetypes. Growth engines and constraints are composed from reusable primitives rather than full per-ticker functions.

Every material conclusion follows `FACT -> PROXY -> INFERENCE`. Facts retain source and period metadata, calculated ratios are labeled, and every inference cites evidence IDs. Missing operating KPIs become structured data gaps. `UNKNOWN` and `INSUFFICIENT_EVIDENCE` are intended outputs.

The JSON envelope is versioned at `company_economics_schema_version: "1.1"` and includes the company, classification, growth architecture, constraints, scaling economics, sustainability, falsification, financial translation, valuation review, market expectations, separate research-quality fields, data gaps, evidence trace, validation, and a frontend-ready economic graph. Structural profile cache files exclude live market price.

Company research is on demand rather than a fixed ticker universe. `SecurityResolver` prefers the existing structured Yahoo collector and falls back to SEC submissions and Company Facts; the local schema-versioned cache records structural profiles and explicit research states. ETFs/funds, REITs, and SPAC/shell structures return specialized-framework states instead of being forced through operating-company economics.

Limitations: Version 1 primarily uses structured financial evidence. Company-specific operating KPIs may be unavailable; qualitative filing, transcript, and presentation extraction is a no-op interface for now. A financial proxy may rank candidate constraints but cannot establish the primary constraint, which remains `UNKNOWN` without directionally useful constraint-specific evidence. Segment economics and historical bottleneck migration remain future work. The engine has no LLM or API-key dependency and does not produce investment recommendations.

The US Inflation Pressure Engine is a forward 3–6 month framework rather than a CPI display. It connects wages, shelter and rent, services, energy, and goods pressure to the Fed reaction function, rates, liquidity, and equity valuation sensitivity. It uses public FRED series, prints explicit thresholds and unavailable-data reasons, and produces evidence-based `Easing`, `Sticky`, `Reaccelerating`, or `Mixed / Two-sided` classifications without a black-box score.

The retired Private AI module and its manually maintained data are preserved under `archive/private_ai/`. They are inactive and have no CLI route.

## Intrinsic Valuation Engine

The valuation engine is separate from Company Intelligence. Company Intelligence
explains business quality, narrative, market structure, and positioning; Intrinsic
Valuation estimates value under explicit operating assumptions.

```text
Ticker
-> Security Classification
-> Valuation Method
-> Historical Base
-> Forecast Assumptions
-> Discount Rate
-> Scenario Valuation
-> Reverse DCF
-> Sensitivity
-> Interpretation
```

The first implemented valuation frameworks are a five-year FCFF DCF for mature
operating companies, a revenue-to-FCFF convergence DCF for growth software, and a
cycle-adjusted DCF for cyclical companies. Each produces traceable bear/base/bull
assumptions, a transparent WACC, Gordon-growth terminal value, calculated
WACC/terminal-growth sensitivity, reverse DCF, and JSON output. Manual overrides
are supported for revenue growth, Year-5 FCF margin, WACC, and terminal growth.

```bash
python model.py value MSFT
python model.py valuation CRWD --json
python model.py dcf MSFT --revenue-growth 0.12 --fcf-margin 0.25
python model.py value CRWD --wacc 0.10 --terminal-growth 0.03
```

Reverse DCF solves for the Year-1 revenue growth path, reports the resulting
five-year CAGR, keeps WACC, Year-5 FCFF margin, terminal growth, and dilution
fixed, and discloses its search bounds, residual, and convergence status. Invalid
or boundary-only solutions are not presented as convergence.

Financial institutions, REITs, pre-profit companies, ETFs/funds, and SPACs route
to their economically appropriate framework but do not receive a fair value when
the required residual-income, NAV/AFFO, runway, portfolio NAV, or trust-structure
data is unavailable. The engine names the missing framework instead of applying
an industrial-company DCF.

Fair value is presented as a scenario range because small changes in long-duration
growth, margins, discount rates, terminal economics, and dilution can materially
change present value. Historical and peer ranges are displayed only when verified
data is available; the engine does not invent them.

Every report labels revenue, FCFF, balance-sheet, share-count, and price periods.
Mixed annual/TTM inputs lower validation confidence. Internal validation checks
forecast arithmetic, terminal value, the enterprise-to-equity bridge, share
conversion, scenario ordering, WACC versus terminal growth, reverse DCF,
period consistency, and sensitivity monotonicity.

This is research infrastructure, not investment advice, and it never emits a
buy/sell recommendation.

## Risk Regime & Defensive Rotation Monitor

This module explains whether weakness is mostly rotation within equities or a broader risk-off event.

It compares US market structure, defensive sectors, global confirmation, credit, volatility, Treasuries, gold, and USD pressure. EWL / Switzerland is included as one global defensive equity proxy, not as a standalone signal.

Classifications:

- Healthy Rotation: momentum or high beta weakens, but breadth, defensives, credit, and volatility remain stable.
- Narrow Leadership Unwind: crowded leaders such as momentum, mega-cap growth, or semiconductors weaken while broader breadth is not collapsing.
- Broad Risk-Off: US, global, defensive, credit, and volatility evidence deteriorate together.
- Liquidity / Inflation Stress: equities fall while Treasuries fail to hedge, USD strengthens, and credit weakens.

The monitor influences sector and company interpretation by raising or lowering the required evidence for dip-buying, momentum continuation, and valuation discipline. It is not a trading signal.

Some macro inputs remain provider-dependent or unavailable; reports disclose missing evidence and data gaps.

## Integrated Research Frontend

CHAINSTOX now has a cache-aware composition layer and progressive web interface for the audited research engines:

```bash
python model.py research-system inventory --json
python model.py research-system dashboard --json
python model.py research-system full --json
python model.py research-system full --live --json

cd frontend
npm run dev
```

Open `http://localhost:3000` for the integrated command center and `/macro` for the world, country, transmission, Central Bank Compass, Shadow S$NEER, and KOSPI workspaces. `GET /api/research` serves the bundled last-valid payload; `?refresh=1` requests a live Python refresh and falls back cleanly if a source fails.

The complete engine audit is in `CHAINSTOX_TOOL_INVENTORY.md`; before/after frontend parity and deliberate gaps are in `CHAINSTOX_UI_COVERAGE.md`. Research calculations remain in Python. The frontend does not recreate formulas, add an LLM, or emit buy/sell recommendations.

## API Backend

The CLI can also run behind a FastAPI service.

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API locally:

```bash
uvicorn api.main:app --reload
```

Endpoints:

```text
GET  /health
GET  /v1/modes
POST /v1/analyze
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode":"company","input":"NVDA"}'
```

Supported API modes:

- `macro`
- `full`
- `sectors`
- `sectors_all`
- `sector`
- `company`
- `risk`
- `overheat`
- `conclusion`

Supported API aliases:

- `1` -> `macro`
- `2` -> `sectors`
- `3`, `theme`, `sector-condition`, `check-sector` -> `sector`
- `4`, `stock`, `company-condition`, `check-company` -> `company`
- `5` -> `risk`
- `6` -> `full`
- `sectors-all`, `all-sectors` -> `sectors_all`

`POST /v1/analyze` also accepts `{"mode":"sectors","input":"all"}` as an alias
for `python model.py sectors all`.

Security model:

- no arbitrary shell execution
- strict mode whitelist
- ticker validation with uppercase `A-Z`, 1-6 characters
- sector whitelist
- subprocess execution uses an argument array
- timeout protection via `ANALYSIS_TIMEOUT_SECONDS`
- output length cap via `MAX_OUTPUT_CHARS`

Reliability layer:

- in-memory response cache enabled by default
- default cache TTL is 15 minutes via `CACHE_TTL_SECONDS=900`
- cache key is normalized `mode + input`, for example `macro`, `sectors_all`, `company_NVDA`
- `company`, `risk`, and `overheat` can use `COMPANY_CACHE_TTL_SECONDS` when a shorter TTL is desired
- lightweight per-IP rate limiting defaults to `RATE_LIMIT_PER_MINUTE=10`
- timeout errors return a friendly `504` response without stack traces
- Yahoo Finance `429` / provider rate-limit failures return `503`
- temporary provider/network failures return `503`

Every analysis response includes:

```json
{
  "ok": true,
  "cached": false,
  "duration_ms": 1234,
  "timestamp_utc": "2026-06-12T00:00:00+00:00"
}
```

Error responses use the same metadata shape:

```json
{
  "ok": false,
  "cached": false,
  "duration_ms": 5000,
  "timestamp_utc": "2026-06-12T00:00:00+00:00",
  "error": "Market data provider is temporarily rate-limited. Please try again later."
}
```

Expanded health check:

```json
{
  "status": "ok",
  "service": "market-intelligence-api",
  "version": "v1",
  "cache_enabled": true
}
```

Future hooks are intentionally isolated in `api/cache.py` and `api/rate_limit.py`
so Redis, Postgres, or background jobs can be added later without changing the
research engine.

## Render Deployment

This repository includes `render.yaml`.

Recommended Render settings:

```text
Service type: Web Service
Build command: pip install -r requirements.txt
Start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```text
ANALYSIS_TIMEOUT_SECONDS=90
MAX_OUTPUT_CHARS=60000
CACHE_ENABLED=true
CACHE_TTL_SECONDS=900
COMPANY_CACHE_TTL_SECONDS=900
RATE_LIMIT_PER_MINUTE=10
```

No database is required for the first API version. The backend returns live
stdout reports from the existing CLI and does not store user requests.
