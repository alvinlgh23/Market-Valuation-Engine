# CHAINSTOX Phase 6 Product Audit

Phase 6 goal: make the existing Dashboard, Macro, Markets, Companies, Valuation, Labs, Search, and Report surfaces feel like one finished research product. This audit was performed against the current frontend route/component architecture and the Phase 1-5 smoke artifacts already captured in `frontend/artifacts`.

## Interaction Grammar

CHAINSTOX now uses four product surfaces:

| Surface | Purpose | Primary Existing Routes |
| --- | --- | --- |
| Snapshot | Orientation and current read | `/`, `/macro`, `/markets`, `/companies`, `/valuation`, `/company/[ticker]`, `/valuation/[ticker]` |
| Map | Mechanism and transmission | `/macro/world`, `/markets?view=structure`, `/company/[ticker]?view=economics` |
| Inspector | Evidence-driven investigation | Macro region/edge inspectors, sector node inspector, company workspace panels, valuation sensitivity/assumption inspectors |
| Report | Complete read | `/brief`, company full report, `/valuation/[ticker]?view=report`, sector report |

## Surface Audit

| Surface | Route | Purpose | Visual Pattern | Interaction Pattern | Loading | Empty/Error | Deep Link / Back | Mobile | Terminology | Issues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dashboard | `/` | What changed, priority, cross-system signals | Command-center snapshot | Ranked links into objects | Fixture load is immediate | Company empty state present | Links preserve object routes | Existing mobile smoke passes | Current Read, State, Evidence mostly stable | MAJOR: first-time user orientation is implicit; no demo-safe entry point |
| Macro Overview | `/macro` | Regional macro orientation | Object header + macro overview | Opens world/research modules | Fixture load immediate | Missing coverage explicit | Context nav works | Existing mobile smoke passes | State, Direction, Evidence | MINOR: no shared product grammar label |
| World Macro Map | `/macro/world` | Regional and transmission map | Full map + inspector | Region/edge selection, ESC close, URL state | Fixture load immediate | Unsupported country notice | Query state preserved; popstate handled | Existing mobile smoke passes | Availability/confidence explicit | MINOR: state styles should align with global state legend |
| Macro Workspaces | `/macro/inflation`, `/macro/rates`, `/macro/liquidity`, `/macro/risk`, `/macro/fx` | Focused mechanism detail | Object module + evidence ledger | Context nav and evidence links | Fixture load immediate | Coverage-gated content | Direct route stable | Scroll-first mobile | Evidence/provenance | POLISH: report-like evidence metadata varies by module |
| Markets Rotation | `/markets` | Sector rotation snapshot | Map/table/snapshot | Sector dot/table links | Fixture load immediate | Sector coverage shown | Query state stable | Existing mobile smoke passes | Breadth/Crowding/Stage | MAJOR: report mode uses raw JSON-looking blocks |
| Sector Structure | `/markets?sector=semiconductors&view=structure` | Industry structure map | Map canvas + inspector | Node selection via URL | Fixture load immediate | Data gaps explicit | Node deep links preserved | Scroll/table on mobile | Constraint/evidence | MINOR: inspector order mostly matches standard but not fully named |
| Companies Index | `/companies` | Resolve company research | Entry/search object | Form route to company | Immediate | Search guidance present | Route-based | Mobile simple | Research state | MINOR: no cross-link to valuation object from entry |
| Company Snapshot | `/company/[ticker]` | Company economics object | Snapshot + workspaces | Workspace links/buttons | Gateway loading state | Research failed state | Query workspace/node preserved | Existing mobile smoke passes | Growth Engine, Constraint, Evidence | MAJOR: failure state should distinguish app error from analytical uncertainty |
| Company Economic Map | `/company/[ticker]?view=economics` | Business mechanism map | Node map + inspector | Node selection via query | Fixture/API | Data gaps explicit | Node preserved | Mobile smoke passes | Constraint/Evidence | MINOR: map affordance differs from sector/macro but acceptable semantically |
| Valuation Index | `/valuation` | Valuation entry | Object launch grid | Opens benchmark valuation object | Fixture immediate | Framework-required route available | Direct route stable | Mobile simple | Observed Economics, Model Assumptions | MINOR: needs demo-safe language |
| Valuation Object | `/valuation/[ticker]` | Intrinsic value vs market expectations | Snapshot/workspace/report | View nav, sensitivity cell links | Fixture immediate | No-solution/framework-required states explicit | View/cell/from preserved | Existing mobile smoke passes | Validation/Market-Implied Expectations | MINOR: state display should align with global state legend |
| Labs | `/labs` | Implemented experimental tools only | Object module | Context nav | Fixture immediate | Partial state explicit | Route-based | Mobile simple | Partial/Cached | POLISH: should not imply unimplemented tools exist |
| Global Search | shell dialog | Research navigation | Command palette | Cmd/Ctrl+K, ESC, Enter | Immediate | Generic invalid query copy | Routes modules/regions/sectors/company/valuation | Existing mobile smoke passes | Research Priority, Recent Research | MAJOR: unsupported/invalid empty copy needs stronger first-time clarity |
| Full Market Brief | `/brief` | Whole-market report | Report mode in shell | Back to dashboard | Fixture immediate | Raw unavailable sections | Route-based | Scroll | Data State/Coverage | MAJOR: print styling should hide app chrome globally |

## Issue Classification

### CRITICAL

None found. Phase 1-5 core routes are implemented and smoke-tested.

### MAJOR

1. First-time orientation is implicit. A judge has to infer what CHAINSTOX is from headings across modules.
2. There is no deterministic demo entry route even though fixtures exist and live providers can rate-limit.
3. Global Search invalid/unsupported states are too generic for a research navigator.
4. Application failure and analytical uncertainty are not consistently distinguished in user-facing empty states.
5. Full reports need common print behavior across shell/report surfaces.

### MINOR

1. State vocabulary is mostly preserved but shell-level accepted states are incomplete.
2. Report surfaces vary in formatting polish; sector and full brief still expose raw payloads where useful but should be framed as report data.
3. Map affordances are recognizable but not fully standardized across macro, sector, and company maps.
4. Context nav names need to preserve module origin when crossing Dashboard -> Macro/Markets/Company/Valuation.

### POLISH

1. Too many modules repeat data state in slightly different visual treatments.
2. Some evidence cards use dense metadata walls rather than a stable VALUE/PERIOD/SOURCE/USED BY structure.
3. Labs should remain clearly limited to implemented tools.
4. Hover/focus timing and print mode should be final-pass standardized in shared CSS.

## Phase 6 Fix Priority

1. Add deterministic demo route and demo guide using existing fixtures only.
2. Add subtle first-time product orientation inside Dashboard.
3. Harden shell state vocabulary and data-state display for LIVE/CACHED/DEMO/FIXTURE/PARTIAL/STALE/UNKNOWN/INSUFFICIENT_EVIDENCE/FRAMEWORK_REQUIRED/FAILED.
4. Improve Global Search empty/unsupported copy and keep Cmd/Ctrl+K, ESC, Enter behavior.
5. Improve company loading/failure copy so failed resolution does not imply analytical insufficiency.
6. Add shared print CSS and Phase 6 smoke coverage.

## Non-Goals Preserved

- No new research engines.
- No LLM.
- No formula rewrites.
- No recommendation language.
- No new visual identity.
- No fake demo data.
