# CHAINSTOX Company Archetype Coverage

The registry describes reusable economic structures. It does not contain company facts, recommendations, or ticker-specific analysis functions.

| Archetype | Deterministic benchmarks | Useful structured fields | Candidate constraints | Known structured-data weakness |
|---|---|---|---|---|
| Enterprise AI Software | PLTR | revenue, margin, FCF, employees; customers when reported | deployment capacity, adoption, sales capacity, talent | Customer, deployment, RPO, and implementation data are rarely standardized. |
| Traditional SaaS | CRM | revenue, employees, FCF, SBC; subscribers/retention when reported | adoption, churn, sales capacity, saturation | ARR, NRR, seats, and customers are not inferred. |
| Fabless Semiconductor | NVDA, AMD | revenue, gross margin, inventory, capex | packaging, memory, foundry, demand, inventory | Units, ASP, wafers, CoWoS, and HBM are unavailable from generic filings. |
| Semiconductor Foundry | TSM | revenue, capex, assets; wafers/utilization when reported | fab capacity, capital intensity, equipment, power | Node mix, wafer starts, and utilization lack universal structured fields. |
| Hyperscaler Cloud Platform | MSFT | revenue, capex, FCF; cloud growth when reported | compute, power, datacenter, adoption, capital intensity | Workloads and usable compute/power capacity require qualitative disclosure. |
| Consumer Platform | META | revenue, margin, employees; users/engagement when reported | adoption, content, regulation, price elasticity | Engagement, ad load, and monetization inputs are not standardized. |
| Retail Physical Network | COST, WMT | revenue, inventory, assets, capex; stores/comps when reported | store expansion, logistics, saturation, labor, inventory | Store counts and comparable sales are structural unless explicitly sourced. |
| Bank | JPM, BAC | assets, deposits, loans, fees, NIM, credit, capital | deposits, funding cost, capital, credit quality | Generic industrial FCF logic is excluded; bank facts vary by filer taxonomy. |
| Industrial | CAT | revenue, inventory, capex; backlog/volume when reported | backlog execution, production, inputs, labor | Backlog and unit throughput are not consistently tagged. |
| Pharma / Biotech | LLY | revenue, margin, R&D/capex; milestones when reported | pipeline, patent expiry, approvals, manufacturing | Patient counts, probabilities, and patent cliffs are never invented. |
| Commodity Producer | XOM | revenue, capex, FCF; production/price when reported | production, inputs, capital, regulation | Production and realized-price taxonomies differ; new SEC registrants can have sparse facts. |
| Payment Network | V | revenue, margin, FCF; volume/transactions when reported | adoption, regulation, price elasticity | Payment volume and take rate are not inferred from revenue. |
| Marketplace Platform | UBER | revenue, margin, FCF; bookings/users when reported | adoption, supplier participation, regulation, price elasticity | Marketplace liquidity and take rate require direct disclosures. |
| Utility / Infrastructure | fixture-free | assets, capex, revenue; rate base/capacity when reported | capital intensity, approvals, power, inputs | Allowed returns, rate base, and utilization need specialized data. |
| Generic Operating Company | adversarial/ambiguous cases | revenue, operating income, FCF, capex, assets | demand, capacity, labor, capital, inputs remain candidates | Used deliberately when metadata cannot defend a specialized route. |

## Confidence and constraint rules

- `HIGH`: multiple mutually consistent metadata and structural signals.
- `MODERATE`: a defensible industry/description route with partial structural confirmation.
- `LOW`: sparse or ambiguous routing metadata; specialized claims are withheld.
- A current financial ratio or balance-sheet level may rank candidates, but does not establish the primary bottleneck.
- A primary constraint requires directionally useful constraint-specific structured evidence. Otherwise it remains `UNKNOWN`.
- Structural equations describe relevant mechanisms, not observed driver contribution.

## Override dependency

The original benchmark overrides remain small declarative preferences. The six added broad fixtures (`AMD`, `CRM`, `META`, `WMT`, `BAC`, `CAT`) classify without overrides. Of the original override set, only MSFT currently needs its preferred-archetype rule to select the intended primary hybrid route; other preferences reinforce an independently supported classification or constraint ordering.

