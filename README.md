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
python model.py risk NVDA
python model.py conclusion
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
