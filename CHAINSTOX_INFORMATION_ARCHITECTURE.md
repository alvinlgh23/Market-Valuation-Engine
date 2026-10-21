# CHAINSTOX Information Architecture

Audited and refactored: 2026-08-08.

## Product model

The Python interface remains command-driven. The frontend is now research-object-driven:

```text
BACKEND ENGINE
  → STRUCTURED RESEARCH PAYLOAD
  → RESEARCH OBJECT
  → STATE
  → MECHANISM
  → EVIDENCE
  → MODEL / VALIDATION
```

No CLI alias was removed, no LLM was added, and no analytical formula was changed. Python remains the analytical authority. The frontend reads normalized research-system and company-economics payloads.

## Old frontend architecture

The former shell treated Overview, Macro, Inflation, Rotation, Risk, Companies, Watchlist, and Historical as peer navigation items. That reflected CLI commands rather than user research intent. Macro, inflation, risk, and rotation were disconnected top-level concepts; one static left rail mixed unrelated objects.

## New frontend architecture and routes

| Research object | Primary route | Contextual routes / state |
|---|---|---|
| Dashboard | `/` | Full Market Brief at `/brief` |
| Macro | `/macro` | `/macro/world`, `/macro/central-banks`, `/macro/inflation`, `/macro/rates`, `/macro/liquidity`, `/macro/fx`, `/macro/risk` |
| Markets | `/markets` | `/markets/sectors`, `/markets/sector/[sector]`, `/markets/breadth`, `/markets/crowding`, `/markets/defensive-rotation` |
| Companies | `/companies` | `/company/[ticker]?view=overview|economics|positioning|valuation|evidence`; workspaces and node state remain query-deep-linkable |
| Valuation | `/valuation` | `/valuation/[ticker]?view=assumptions|dcf|reverse-dcf|sensitivity|validation`, canonically opening the same company valuation object |
| Labs | `/labs/fragility` | `/labs/historical` |

The global header owns the six primary objects. Dashboard is full-width with no contextual sidebar. Desktop research-object pages use a contextual left sidebar; tablet uses compact primary navigation; mobile converts primary navigation to a menu and contextual navigation to a horizontally scrollable row.

Global search resolves company tickers, macro regions, market sectors, and modules. Empty search opens the highest-priority investigation routes plus recent company context.

## Research objects

### Dashboard

Dashboard is the Phase 4 synthesis command center. It answers four questions before asking the user to navigate: what is happening, what changed, what matters most, and where to investigate next.

The dashboard is organized as:

```text
CURRENT MARKET STATE
  → WHAT CHANGED
  → RESEARCH PRIORITY
  → ACTIVE CROSS-SYSTEM SIGNALS
  → RECENT / SAVED RESEARCH CONTEXT
  → DATA FRESHNESS + WATCH CONDITIONS
```

Every card routes to its owning research object: Macro, World/region, Markets/sector, Company, Valuation, Risk, or Full Market Brief. Dashboard does not calculate buy/sell signals, expected returns, or aggregate scores. It surfaces deterministic backend reads, cached sector research objects from Phase 3, recent company context from Phase 2, and explicit coverage gaps.

### Macro

Macro Overview integrates policy, inflation, rates, liquidity, FX, and risk. World Map retains only the five implemented economies: United States, Japan, South Korea, Singapore, and Euro Area. Unsupported regions say `NOT AVAILABLE`. Region → component → evidence and transmission-edge inspectors preserve progressive depth. Central Bank Compass, shadow S$NEER, KOSPI, and US inflation child payloads remain nested under their correct regional objects.

### Markets

Sector Rotation is the entry point and now acts as the bridge between Macro and Company research:

```text
MARKET
  → SECTOR ROTATION
  → SECTOR SNAPSHOT
  → SECTOR STRUCTURE
  → LEADERSHIP / BREADTH / CROWDING
  → COMPANY
  → EVIDENCE
```

The default `/markets` surface compares sectors on a positioning plane and precise table using backend-compatible sector fields: 1M/3M/6M relative strength, breadth, crowding/extension, momentum stage, primary theme, and data state. Selecting a sector keeps the user inside the same research object with query state such as `/markets?sector=semiconductors&view=structure&node=advanced-packaging`.

Sector Structure is deliberately separate from current market state. Structural maps are declarative `SectorStructureTemplate` objects with nodes, relationships, companies, evidence IDs, and data gaps. A node inspector uses the shared CHAINSTOX grammar: role, current state, why it matters, evidence, related companies, and data gaps. Company links route to the existing Phase 2 Company object, e.g. `/company/NVDA?from=markets&sector=semiconductors`; Markets does not duplicate Company analytics.

The current live research-system fixture still has zero publishable sector rows because its provider coverage gate is insufficient. Phase 3 therefore ships deterministic cached/partial market research fixtures for the interactive UX benchmark while preserving Python as the analytical authority. These fixtures are labeled `CACHED` or `STRUCTURAL_MODEL_PARTIAL`, disclose unsupported claims, and do not add frontend calculations. Risk Regime is shared with Defensive Rotation rather than recalculated.

### Companies

The universal entry starts with a ticker/company query. A company owns Overview, Economics, Positioning, Valuation, Evidence, and explicit Full Report. Existing economics, financial, thesis, valuation, evidence, and economic-map workspaces are preserved. Query state makes economics, positioning, valuation, evidence, and selected economic nodes reloadable.

### Valuation

Valuation is now the Phase 5 intrinsic-value research object:

```text
COMPANY ECONOMICS
  → MODEL ASSUMPTIONS
  → INTRINSIC VALUE
  → MARKET-IMPLIED EXPECTATIONS
  → ASSUMPTION GAP
  → SENSITIVITY
  → VALIDATION
  → EVIDENCE
```

Top-level `/valuation` opens the valuation entry and `/valuation/[ticker]` opens the same object used by Company, Dashboard, and Global Search deep links. Valuation starts with economic reality versus market expectations rather than WACC mechanics. The snapshot shows current price, Bear/Base/Bull range, market position, observed economics, model assumptions, market-implied expectations, and validation state.

The deeper views are `/valuation/[ticker]?view=economics-model|dcf|assumptions|reverse-dcf|sensitivity|validation|evidence|report`. Company Economics remains read-only: it reviews assumptions and does not mutate DCF inputs. Unsupported company types route to `FRAMEWORK REQUIRED` instead of being forced through a generic industrial FCFF DCF.

### Labs

Only implemented research appears: Fragility and Historical. Historical currently exposes available last-valid engine states, not an invented time-series archive.

## Shared interaction and data rules

- Summary surfaces show the state and route into an investigation.
- Workspaces/drawers show the mechanism.
- Evidence inspectors retain metric, value, source, period, freshness, `FACT / PROXY / INFERENCE`, and confidence where supplied.
- Model/validation views expose formulas, assumptions, checks, gaps, and invalidation conditions from Python payloads.
- `LIVE`, `CACHED`, `STALE`, `PARTIAL`, `INSUFFICIENT`, `UNAVAILABLE`, `FIXTURE`, `ANALYZING`, and failure states are visually and textually distinct.
- Charts are used only for supplied quantitative or historical data. No categorical chart or fake time series is generated.
- Long scrolling is reserved for explicit report mode.

## API and cache architecture

`GET /api/research` remains the single normalized system bridge. `scope=dashboard|world|full` narrows the same snapshot; `refresh=1` invokes the Python composition layer and falls back to the bundled last-valid payload with error metadata. Company operations use typed actions (`company-resolve`, `company-open`, `company-index`, and POST `company-analyze`) through the same route. Python cache isolation and one normalized company snapshot prevent TypeScript from duplicating calculations or provider requests.

## Known gaps

- Live intrinsic valuation can still be rate-limited by Yahoo/provider access. Phase 5 therefore ships deterministic benchmark valuation fixtures generated from the existing Python engine for UX validation; live provider failures remain visible as insufficient-data or framework-required states.
- Current live sector refresh can be blocked by Yahoo/provider rate limits; the Phase 3 Markets UI uses explicit cached/partial research fixtures for deterministic interaction tests and keeps provider-derived formulas in Python.
- Official MAS S$NEER basket, weights, centre, slope, and band position are unavailable; the existing transparent shadow proxy remains labeled as such.
- KOSPI foreign-flow data can remain unavailable independently of other factors.
- Compass allocation, backtests, motive checks, and some specialist CSV/chart studies remain explicit report-only capabilities.
- Historical is a last-valid snapshot ledger, not yet a full persisted research-state browser.
