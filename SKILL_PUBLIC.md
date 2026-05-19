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
python model.py macro
python model.py sectors
python model.py sectors all
python model.py sector semis
python model.py theme energy
python model.py stock NVDA
python model.py company AAPL
```

`model.py` is a thin wrapper. Most logic lives in `Valuation_model.py`.

## Report Layers

The full report should preserve these layers:

1. Global Liquidity Conditions
2. Macro Fragility Analysis
3. Sector Rotation Analysis
4. Company Intelligence Report
5. Narrative Classification
6. Positioning / Overheat Analysis
7. Final Market Interpretation
8. Market Intelligence Extensions:
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

## Classification Calibration

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
```

Use live-data checks when interpretation logic depends on current market data. If network-restricted commands fail, rerun with appropriate approval.
