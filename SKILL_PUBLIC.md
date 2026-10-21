---
name: market-intelligence-system
description: Use when working on Alvin's Python Market Intelligence System project: a macro-driven market-structure framework for global liquidity, macro fragility, sector rotation, narrative classification, institutional-quality companies, positioning/overheat risk, and final market interpretation. Use for modifying model.py or Valuation_model.py, tuning financial interpretation logic, preserving CLI commands, or explaining outputs without turning the model into buy/sell signals.
metadata:
  short-description: Maintain Alvin's market intelligence model
---

# Market Intelligence System

Use this skill when working on `/Users/alvinlim/Desktop/Startup-Insight-AI/Valuation-model`.

The project is a Python CLI market intelligence framework. Its purpose is to explain market structure, not to generate buy/sell signals.

## Core Philosophy

- Do not turn outputs into recommendations.
- Explain liquidity, capital rotation, narrative strength, institutional positioning, macro fragility, and overheat risk.
- Be careful with wording: avoid overstating “crowded,” “parabolic,” “institutional,” or “overheated” unless the data supports it.
- Treat M2 as a long-term liquidity backdrop, not a short-term timing signal.
- Treat weak or negative price momentum as repair/base-building, not chase risk.

## Main Commands

Keep these commands working:

```bash
python model.py
python model.py full
python model.py risk-regime
python model.py macro
python model.py sectors
python model.py sectors all
python model.py sector semis
python model.py theme energy
python model.py stock NVDA
python model.py company AAPL
python model.py value MSFT
python model.py valuation CRWD --json
```

`model.py` is a thin wrapper. Most logic lives in `Valuation_model.py`.
`risk_regime.py` contains the Risk Regime & Defensive Rotation Monitor.
`intrinsic_valuation.py` contains the Stage 1 Intrinsic Valuation Engine.

## Report Layers

The full report should preserve these layers:

1. Global Liquidity Conditions
2. Risk Regime & Defensive Rotation Monitor
3. Macro Fragility Analysis
4. Sector Rotation Analysis
5. Company Intelligence Report
6. Narrative Classification
7. Positioning / Overheat Analysis
8. Final Market Interpretation
9. Market Intelligence Extensions:
   - Capital Flow Story
   - Market Phase
   - Leadership Durability
   - Regime Playbook
   - Market Risk Map
   - Scenario Analysis
   - Early Rotation Candidates
   - Crowding vs Quality Matrix
   - Watchlist Profile
   - Narrative Decay Warnings

## Approved Indicator Set

Do not add extra indicators unless explicitly requested.

Allowed indicators:

- US 10Y yield
- DXY
- USDJPY
- VIX
- M2 money supply via FRED `M2SL`
- Consumer Sentiment via FRED `UMCSENT`
- ISM Manufacturing PMI via FRED/official ISM fallback
- Sector relative strength vs SPY
- PE expansion
- Breadth participation
- Company fundamentals
- Momentum / positioning metrics

Allowed risk-regime proxies:

- SPY / VOO, RSP, QQQ, SPMO, IWM
- SMH or SOXX, XLY, XLF, XLI, XLV, XLP, XLU
- EWL, EWJ, FEZ, EEM, ACWX
- TLT, IEF, GLD or GLDM, UUP or DXY, HYG, LQD, VIX or VIXY

EWL / Switzerland is one global defensive proxy, not a standalone signal.

## Classification Calibration

### Company Intelligence Reports

Company reports should be evidence-first, not label-first.

For operating companies, preserve these sections:

- Business Fundamental Evidence
- Valuation Reality Check
- Price Action vs Fundamentals
- Narrative & Institutional Conviction
- Positioning / Overheat / Chase Risk
- What Would Strengthen the Case
- What Would Weaken the Case
- Final Company Interpretation

Do not make the quality score the main output. Use actual revenue, margin, FCF, valuation, and price-action evidence where available. If data is unavailable, say unavailable instead of filling with generic labels.

### Sector Crowding

Only call a sector `Crowded Momentum` when the setup is genuinely extreme:

- 6M relative strength is very high
- PE expansion is aggressive
- breadth is very broad
- momentum is parabolic or near-parabolic

For positive but not extreme sectors, prefer:

- `Stable Institutional Rotation`
- `Early-to-Mid Thematic Rotation`
- `Institutional Momentum`

### Company Momentum

Do not call weak or negative 6M performance overheated.

Use repair/base-building language when:

- 6M price performance is negative or weak
- distance from 200MA is negative or only mildly positive
- valuation expansion is low

For these cases, prefer:

```text
The company remains fundamentally supported,
but stock-level momentum is still in a repair phase.
This is not an active chase-risk setup.
```

### Narrative Examples

- `NVDA`: Institutional AI Leader
- `AAPL`: Mature Institutional Quality / Momentum Repair
- `PYPL`: Narrative Decay / Weakening Mature Platform
- `RBLX`: Identity Uncertainty
- `INTC`: Speculative Turnaround
- `OSS`: Speculative Narrative Momentum
- `COIN`: Liquidity-Sensitive Narrative Asset
- `FSLR`: Fundamentally supported when financials are strong, but avoid overheat wording if price momentum is weak.

## Final Interpretation Rules

Use `RSP vs SPY` for breadth language:

- If `RSP vs SPY < 0`: leadership remains relatively concentrated, although selective thematic participation may be expanding.
- If `RSP vs SPY > 0`: leadership breadth is improving beyond mega-cap leaders.

When macro fragility is elevated but M2 is expanding, distinguish:

- short-term liquidity tightness from yields/DXY
- long-term liquidity backdrop support from M2

Preferred wording:

```text
Short-term liquidity remains constrained by elevated yields and a strong dollar,
but expanding M2 suggests a more supportive long-term liquidity backdrop.
```

## Risk Regime Calibration

- Keep the monitor narrative-first, not score-first.
- Do not use phrases like buy signal, crash warning, guaranteed rebound, or Swiss ETF signal.
- Healthy Rotation requires contained credit/volatility and some evidence that breadth or defensives are stable.
- Narrow Leadership Unwind requires momentum, QQQ, semis, or high-beta weakness while RSP and defensives avoid broad collapse.
- Broad Risk-Off requires deterioration across US breadth, global equities, defensives, credit, and volatility.
- Liquidity / Inflation Stress requires equity weakness plus Treasury hedge failure, USD pressure, and/or credit deterioration.
- If proxies are unavailable, show missing evidence clearly and lower confidence rather than failing.

## Intrinsic Valuation Maintenance

- Keep Intrinsic Valuation separate from Company Intelligence and never convert fair value into a buy/sell instruction.
- Preserve the supported Stage 1 frameworks: mature-company FCFF DCF, growth-software revenue-to-FCFF convergence DCF, and cyclical mid-cycle DCF.
- Route from evidence, including quote type, financial statements, growth, profitability, margins, free cash flow, structure, and cyclicality; do not route solely from a sector label.
- Do not apply a conventional company DCF to financial institutions, REITs, pre-profit companies, ETFs/funds, or SPACs. Return the required specialized framework and missing inputs.
- Label annual, fiscal-year, quarterly, TTM, balance-sheet, share-count, and market-price periods. A material mismatch must lower validation confidence.
- Every assumption must retain name, value, unit, source, basis, confidence, scenario, and period.
- Preserve the identities `EV = PV(explicit FCFF) + PV(terminal value)`, `equity value = EV + cash - debt - senior claims`, and `fair value per share = equity value / diluted shares`.
- Bear/base/bull values must remain logically ordered. Bull assumptions must remain economically bounded.
- Reverse DCF must disclose the solved variable, fixed assumptions, bounds, status, residual, and non-convergence reason.
- Sensitivity cells must be full recalculations. Invalid `WACC <= terminal growth` cells must remain invalid, and valid cells should be monotonic.
- JSON mode must emit one uncontaminated JSON document.
- Invalid valuation CLI flags must exit non-zero with a concise error and no traceback.

## Company Economics Maintenance

- Preserve the research chain `FACT -> PROXY -> ECONOMIC MECHANISM -> CONSTRAINT DIAGNOSIS -> GROWTH SUSTAINABILITY -> FINANCIAL IMPLICATION -> VALUATION ASSUMPTION REVIEW`.
- Use reusable archetypes, growth primitives, and constraints. Keep company overrides small and declarative; never add full ticker-specific analysis functions.
- Every inference must cite existing evidence IDs. Facts require source and period metadata; calculated metrics and proxies must be labeled.
- Prefer `UNKNOWN` or `INSUFFICIENT_EVIDENCE` when direct and proxy evidence cannot support a mechanism.
- Calculate only archetype-relevant scaling metrics and handle non-positive incremental-revenue denominators safely.
- Generate observable falsification conditions tied to the growth engine, primary constraint, or scaling economics.
- Company Economics may review valuation assumptions but must never mutate them. Existing DCF math remains deterministic.
- Keep the qualitative evidence provider unavailable until a future filing/transcript implementation exists; no LLM key is required.
- Preserve pure schema-versioned JSON and valid economic-graph nodes/edges.
- Maintain deterministic fixtures for PLTR, NVDA, TSM, MSFT, JPM, COST, AMD, CRM, META, WMT, BAC, CAT, XOM, LLY, V, and UBER.

## Extension Layer Calibration

- Market phase should describe cycle structure, not predict returns.
- Leadership durability should reward sector relative strength, breadth, company quality, and liquidity support, while penalizing macro fragility, high Fed sensitivity, crowding, and excessive heat.
- Early rotation candidates should be improving but not already fully extended.
- Scenario analysis should describe what would confirm or invalidate the current read.
- Watchlist profiles should describe setup types, not direct stock recommendations.
- Narrative decay warnings should flag lagging relative strength, negative 6M performance, below-200MA structure, fading margin expansion, or company weakness despite sector strength.

## Validation Checklist

After changes, run the smallest relevant set:

```bash
python3 -m py_compile Valuation_model.py model.py
python3 model.py macro
python3 model.py full
python3 model.py sectors
python3 model.py sector semis
python3 model.py theme clean-energy
python3 model.py stock NVDA
python3 model.py stock FSLR
python3 risk_regime.py
python3 -m unittest tests.test_intrinsic_valuation -v
python3 model.py value MSFT
python3 model.py value CRWD --wacc 0.10 --terminal-growth 0.03
python3 model.py value MSFT --json
```

Use live-data checks when interpretation logic depends on current market data. If network-restricted commands fail, rerun with appropriate approval.
