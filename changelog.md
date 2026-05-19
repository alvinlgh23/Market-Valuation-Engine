# Changelog

This changelog summarizes the evolution of the Market Intelligence System based on the repository commit history and the latest working-tree changes.

## Unreleased

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
