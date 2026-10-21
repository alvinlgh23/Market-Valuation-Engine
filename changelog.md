# Changelog

This changelog summarizes the evolution of the Market Intelligence System based on the repository commit history and the latest working-tree changes.

## Unreleased

### Company Economics Engine

- Replaced the six-fixture production company surface with on-demand universal ticker resolution, explicit research states, Yahoo-to-SEC structured-provider failover, and a schema-versioned structural profile cache.
- Added deterministic metadata/industry/structural classification across 15 reusable archetypes, override-dependency diagnostics, and a rule preventing financial proxies from being promoted to confirmed primary constraints.
- Added CLI and `/api/research` resolve/analyze/open/index flows plus frontend resolved, analyzing, partial, insufficient-data, unsupported, stale, and failed states.
- Expanded the regression matrix to 16 fixtures and added live structured-provider validation for AMD, CRM, META, WMT, BAC, CAT, XOM, LLY, V, and UBER.
- Added a typed, deterministic company-economic domain model with a normalized `CompanySnapshot`.
- Added 15 reusable archetypes, composable growth primitives, a reusable constraint registry, and small declarative overrides.
- Added FACT / PROXY / INFERENCE provenance, REPORTED / CALCULATED / DERIVED_PROXY / INFERRED source nature, period/source metadata, evidence references, and structured data gaps.
- Added growth architecture, archetype-relevant scaling economics, safe incremental margins, constraint direction/interaction, sustainability, falsification, and financial translation engines.
- Added read-only DCF assumption review and reverse-DCF market-expectation comparison. Company Economics never mutates valuation assumptions.
- Added schema-versioned pure JSON, terminal output, frontend-ready causal graph, structural cache metadata, and comprehensive validation.
- Added no-op qualitative-provider and future extractor interfaces with no LLM/API dependency.
- Added `economics` and `company-economics` CLI aliases; `company` includes the economics layer by default.
- Added deterministic fixtures for PLTR, NVDA, TSM, MSFT, JPM, COST, AMD, CRM, META, WMT, BAC, CAT, XOM, LLY, V, and UBER and 36 focused Company Economics/universal-company tests.
- Allowed intrinsic valuation to accept an already-collected data object so economics and valuation can reuse provider data without changing valuation math.

### Intrinsic Valuation Engine

- Added a company-type-aware Stage 1 valuation engine separate from Company Intelligence.
- Added five-year FCFF DCF support for mature operating companies.
- Added revenue-to-FCFF convergence DCF support for growth software companies.
- Added cycle-adjusted DCF support using normalized mid-cycle economics for cyclical companies.
- Added traceable bear, base, and bull assumptions with source, basis, confidence, scenario, and period metadata.
- Added transparent WACC construction, Gordon-growth terminal value, and exit-multiple reconciliation.
- Added reverse DCF with fixed-assumption disclosure, economic search bounds, residual error, boundary checks, and explicit non-convergence states.
- Added fully recalculated WACC/terminal-growth sensitivity tables with invalid-cell and monotonicity validation.
- Added JSON-only output and manual overrides for revenue growth, Year-5 FCFF margin, WACC, and terminal growth.
- Added friendly non-zero CLI errors for invalid valuation options without tracebacks.
- Added period-basis disclosure and annual/TTM mismatch validation.
- Added graceful specialized-framework fallbacks for financial institutions, REITs, pre-profit companies, ETFs/funds, SPACs, and unresolved securities.
- Added internal checks for forecast arithmetic, terminal value, EV-to-equity reconciliation, diluted shares, scenario ordering, reverse DCF, period consistency, and sensitivity behavior.

### US Inflation Pressure Engine

- Replaced CLI option `8` with `US Inflation Pressure Engine`.
- Added equivalent `inflation`, `cpi`, and `inflation-pressure` command aliases.
- Added a forward 3–6 month framework covering wages, shelter/rent, services, energy, goods, headline/core CPI, and headline/core PCE.
- Added explicit threshold and trend evidence, unavailable-data labels, Fed sensitivity, market implications, and measurable view-change conditions.
- Preserved the former Private AI code and data under `archive/private_ai/`, with no active CLI route.

### Evidence-first company intelligence report

- Added `company_report.py` for a deeper company-level report.
- Reworked mature operating-company output around business fundamentals, valuation reality, price action versus fundamentals, narrative conviction, positioning / overheat risk, strengthening conditions, weakening conditions, and final interpretation.
- Added TTM revenue, prior revenue, revenue growth, operating margin change, TTM FCF, FCF growth, FCF margin, FCF yield, relative strength versus SPY, 200MA distance, and valuation decomposition.
- Added explicit unavailable-data handling for missing revenue, margin, FCF, valuation, estimate, and price fields.
- Preserved non-recommendation language and avoided using quality scores as the main report output.

### Risk regime and defensive rotation monitor

- Added `risk_regime.py` as a standalone Risk Regime & Defensive Rotation Monitor.
- Added narrative-first classification for:
  - `Healthy Rotation`
  - `Narrow Leadership Unwind`
  - `Broad Risk-Off`
  - `Liquidity / Inflation Stress`
- Added evidence matrix using US market structure, momentum/high-beta weakness, defensive sector relative strength, global equity confirmation, EWL / Switzerland defensive proxy, HYG vs LQD credit stress, volatility, Treasury hedge behavior, gold, and USD pressure.
- Added graceful unavailable-data handling so missing proxies do not break the report.
- Added mock examples for all four risk regimes through `python3 risk_regime.py`.
- Integrated the monitor into the macro and full reports.
- Added risk-regime context to sector, company, and ticker risk commands.
- Added `Risk Regime & Defensive Rotation` as option `7` in the CLI menu with `risk-regime`, `regime`, `rotation`, and `defensive-rotation` aliases.
- Documented that EWL / Switzerland is one defensive global proxy, not a standalone trading signal.

### Market intelligence extensions

- Added a full-report extension layer after the final market interpretation.
- Added a capital-flow story to summarize where capital is moving and why.
- Added market phase classification:
  - `Phase 1: Liquidity Repair`
  - `Phase 2: Selective Leadership`
  - `Phase 3: Broad Participation`
  - `Phase 4: Crowded Momentum`
  - `Phase 5: Distribution / Fragility`
- Added leadership durability scoring using sector relative strength, breadth, company quality, heat, macro fragility, Fed sensitivity, and liquidity regime.
- Added regime playbooks showing what is usually favored and vulnerable in each market character.
- Added market risk map for inflation surprise risk, yield pressure, breadth weakness, Fed sensitivity, valuation compression, sector overcrowding, and macro fragility.
- Added scenario analysis with bullish confirmations and bearish invalidations.
- Added early rotation candidate detection for sectors with improving relative strength that are not already fully extended.
- Added crowding vs quality matrix to distinguish healthy accumulation, warming positioning, speculative momentum, and incomplete confirmation.
- Added current watchlist profile and narrative decay warnings.
- Updated README, documentation, and project skill guidance for the new extension layer.

### Interpretation calibration and documentation

- Added `documentation.md` with full project usage, command reference, report layers, sector aliases, validation commands, and interpretation rules.
- Added `changelog.md` to record historical changes.
- Improved momentum heat calibration:
  - `Low`: negative, flat, weak, or below 200MA.
  - `Moderate`: controlled +10% to +40% momentum.
  - `Elevated`: +40% to +80% or accelerating participation.
  - `Extreme`: parabolic, crowded, or above +80%.
- Separated `Momentum Heat` from `Chase Risk` so moderate momentum does not automatically imply high chase risk.
- Added hard-asset company narratives:
  - `Defensive Hard-Asset Rotation`
  - `Inflation-Hedge Rotation`
- Added company archetype:
  - `Expensive Conviction Growth`
- Improved commodity and gold miner interpretation so companies like `NEM` are treated as macro hard-asset rotation stories instead of generic developing narratives.
- Added higher-level `Market Character` classification in the final report, including:
  - `Inflation-Sensitive Rotation`
  - `Selective Narrative Expansion`
  - `Concentrated Institutional Leadership`
  - `Fragile Mega-Cap Dominance`
  - `Liquidity-Driven Risk Expansion`
  - `Speculative Late-Cycle Momentum`
  - `Broad Economic Expansion`
- Improved final market interpretation to synthesize liquidity, fragility, catalysts, breadth, sector rotation, inflation pressure, narrative concentration, and positioning risk.
- Added threshold diagnostics for major macro conclusions:
  - Current value
  - Reference threshold
  - Distance from threshold
  - Classification
  - Interpretation
- Updated local Codex project skill guidance with macro threshold discipline and narrative calibration rules.

## bdd91ee - Added US30Y indicator

- Added US 30Y Treasury Yield to the macro liquidity framework.
- Distinguished 10Y and 30Y Treasury roles:
  - 10Y: medium-term liquidity pressure and valuation discounting.
  - 30Y: long-term fiscal sustainability, structural inflation concerns, and duration stress.
- Added long-term fiscal stress interpretation.
- Added macro catalyst monitor using CPI, Core CPI, final-demand PPI, payrolls, unemployment, wages, claims, and Fed futures when available.
- Integrated macro catalyst sensitivity into the full market report.
- Expanded final macro interpretation around inflation surprise risk, long-duration valuation compression, and volatility expansion.

## 417a1e8 - Add public framework skill document

- Added `SKILL_PUBLIC.md`.
- Documented the project philosophy for future Codex-style maintenance:
  - Do not generate buy/sell signals.
  - Preserve market-structure interpretation.
  - Avoid overstating crowded, parabolic, institutional, or overheated conditions.
  - Keep CLI commands stable.

## a60030c - Adding complete indicator

- Expanded the macro and market intelligence indicator stack.
- Added M2 Money Supply as a long-term liquidity backdrop.
- Added macro fragility analysis using consumer sentiment, ISM Manufacturing PMI, and breadth proxy.
- Added support for final market interpretation that distinguishes short-term liquidity tightness from long-term liquidity support.
- Improved ERP handling and macro output context.

## c998250 - Quantum and space sector was added

- Added Quantum Computing sector/theme support.
- Added Space / Satellite Infrastructure sector/theme support.
- Added aliases such as `quantum`, `space`, `satellite`, and `rklb`.
- Added candidate baskets for quantum and space-related companies.

## 1d1283b - Minor update to the accuracy and sectors recheck

- Refined sector accuracy and sector condition checks.
- Improved specific sector output consistency.
- Rechecked sector ranking and classification behavior.
- Continued tuning around sector-level positioning and crowding.

## 37cb2c6 - Update company analysis model

- Improved company-level intelligence output.
- Added clearer breakdowns for financial quality, narrative strength, momentum / positioning, valuation risk, and chase risk.
- Improved company interpretation logic for specific archetypes and edge cases.

## ca4d319 - Added complete sectors

- Expanded the sector universe beyond the initial limited set.
- Added more GICS sectors, industries, and thematic ETFs.
- Updated README usage guidance.
- Improved support for checking specific sectors directly.

## 02344a0 - Minor correction and refinement to the company analysis

- Refined company analysis wording and classification behavior.
- Improved handling of momentum weakness, valuation risk, and chase-risk distinctions.
- Reduced inconsistent output for companies in correction or base-building phases.

## 87f4f45 - Clean repository cache files

- Added `.gitignore`.
- Removed Python cache artifacts from version control.
- Cleaned repository state.

## ba60fae - Refine narrative and positioning analysis

- Improved narrative classification and positioning / overheat analysis.
- Added more realistic treatment of:
  - speculative narrative momentum
  - identity uncertainty
  - liquidity-sensitive narrative assets
  - narrative decay
  - mature quality names
- Improved overheat logic so negative 6M performance and below-200MA setups are not called parabolic or high chase risk.

## 5bf3add - Upgrade to Market Intelligence System

- Major upgrade from valuation-oriented model to Market Intelligence System.
- Added `model.py` wrapper.
- Reframed the system around:
  - macro environment
  - liquidity / cost of capital
  - sector rotation
  - narrative formation
  - institutional capital flow
  - company rerating
  - valuation expansion / overheating
- Added the interactive CLI menu.
- Added direct command support:
  - `full`
  - `macro`
  - `sectors`
  - `sector`
  - `company`
  - `stock`
  - `risk`
- Reworked README around the new market intelligence philosophy.

## 5ead167 - Merge branch main

- Merged remote main branch.
- README received small upstream additions.

## Initial commits

- Created the original valuation model project.
- Added early Python model files and README.
- Established the initial repository structure.
