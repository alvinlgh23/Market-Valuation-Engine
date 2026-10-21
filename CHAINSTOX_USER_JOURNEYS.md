# CHAINSTOX User Journey Audit

This audit measures the Phase 6 first-time and expert flows against the four-surface grammar: Snapshot, Map, Inspector, Report.

| Journey | Route / Clicks | Expected Answer | Friction | Fix |
| --- | --- | --- | --- | --- |
| A. What matters today? | `/` / 0 clicks | Dashboard shows What Changed, Research Priority, Cross-System Signals | First-time users need one sentence explaining CHAINSTOX | Add compact orientation panel inside Dashboard |
| B. Why could Japan affect US assets? | `/` -> Research Priority Japan, or `/macro/world?mode=transmission&edge=jp-us-yen-carry` / 1-2 clicks | Transmission map and edge inspector explain mechanism/evidence | Need demo route to preserve stable context | Add `/demo` guide with Japan -> US route |
| C. Which sector is leading? | `/markets` / 0 clicks, or Dashboard -> Semiconductors / 1 click | Sector rotation map/table and sector snapshot | Good; no dead end because sector opens structure/company | Preserve route |
| D. How does PLTR/NVDA grow? | `/company/PLTR?fixture=1&view=economics` / 0 clicks from direct route | Company Economic Map explains growth engine/constraint/evidence | Failure state could feel like app break when API fails | Harden loading/failure language |
| E. What does this stock price imply? | `/valuation/PLTR?view=reverse-dcf` or `/valuation/MSFT?view=reverse-dcf` / 0 clicks from direct route | Reverse DCF and no-solution states separate market expectations from intrinsic assumptions | Good; state labeling needs global consistency | Extend shell state vocabulary |
| F. Show me the evidence. | Macro/component/company/valuation evidence views / 1-3 clicks | Evidence rows expose source/calculation/limitations | Metadata styles vary by module | Document as remaining polish; avoid formula/data rewrites |

## Click Depth

| Flow | Click Depth | Result |
| --- | ---: | --- |
| Dashboard -> Japan-US evidence | 2 | Dashboard priority -> Macro transmission -> edge evidence |
| Dashboard -> Semiconductors -> NVDA | 2 | Dashboard -> sector -> company link |
| Company -> Valuation -> Reverse DCF | 2 | Company valuation action -> valuation view |
| Valuation -> Company Economics | 1 | Origin/context link retained through `from` parameters where supported |
| Search -> PLTR company | 1 keyboard submit | Cmd/Ctrl+K, type PLTR, Enter |
| Search -> PLTR valuation | 1 click after search | Cmd/Ctrl+K, type PLTR, select Valuation |

## Dead Ends

- Macro region has next actions into mechanism, transmission, evidence, and focused macro workspaces.
- Transmission edge has evidence and interpretive-limit blocks.
- Sector snapshot has structure, leadership, breadth, crowding, report, and company links.
- Company object has economics, positioning, valuation, evidence, and full report.
- Valuation object has DCF, assumptions, reverse DCF, sensitivity, validation, evidence, and full report.
- Labs intentionally exposes only implemented partial tools.

## Phase 6 Journey Standard

Each important object should answer:

1. What is this object?
2. What is happening?
3. What mechanism or tension matters most?
4. How confident is the system?
5. What should I inspect next?
