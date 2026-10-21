# CHAINSTOX Dashboard Architecture

Updated: 2026-08-08.

## Phase 4 role

The dashboard is the synthesis layer for CHAINSTOX. It is not a seventh analytical engine and it does not change formulas. It arranges deterministic outputs from Macro, Markets, Companies, Valuation, Risk, and the research-system fixture into one investigation surface.

The dashboard must answer:

- What is happening?
- What changed?
- What matters most?
- Where should the user investigate next?

## Surface contract

```text
Current Market State
  → What Changed
  → Research Priority
  → Active Cross-System Signals
  → Recent / Saved Research Context
  → Data Freshness
  → Watch Conditions
```

Every item is clickable and opens the owning research object. The dashboard does not flatten modules into an aggregate score, expected-return ranking, or buy/sell recommendation. If a source is unavailable, stale, cached, partial, or insufficient, that state remains visible.

## Data sources

| Layer | Deterministic source |
|---|---|
| Headline and state strip | `system.dashboard.headline`, `system.dashboard.reads`, `system.dashboard.valuation_flags` |
| Observed changes | `system.dashboard.what_changed` |
| Research priority | `system.dashboard.research_priority`, plus disclosed sector/risk coverage priorities |
| Cross-system signals | deterministic links between macro reads, inflation reads, risk coverage, and Phase 3 sector objects |
| Market leadership | `frontend/lib/market-research.ts` cached/partial sector research objects |
| Recent companies | `system.dashboard.companies` |
| Operations | `system.dashboard.freshness`, `system.dashboard.watch_conditions` |

## Navigation contract

Global search resolves:

- Company tickers, e.g. `PLTR` → `/company/PLTR`
- Macro regions, e.g. `Japan` → `/macro/world?region=JP`
- Market sectors, e.g. `Semiconductors` → `/markets?sector=semiconductors`
- Modules, e.g. `Inflation` → `/macro/inflation`

Empty search shows priority routes and recent company research so the command palette doubles as a research continuation tool.

## Validation

`npm run smoke:dashboard` captures 18 desktop/mobile screenshots:

- Dashboard overview
- What Changed
- Research Priority
- Cross-System Signals
- Global Macro Snapshot
- Market Leadership
- Recent Company Research
- Data Freshness and Watch Conditions
- Global search default and typed searches
- Deep links to Japan, Semiconductors, PLTR, and Full Market Brief
- Mobile dashboard and mobile search
