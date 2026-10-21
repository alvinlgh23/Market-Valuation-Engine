# Deterministic Company Economics Benchmarks

These outputs use offline structured fixtures. Values are test evidence, not current company data or investment recommendations. Complete terminal and JSON representations are reproducible with `python model.py economics TICKER --fixture` and `--json`.

## PLTR

- Archetype: `ENTERPRISE_AI_SOFTWARE` (HIGH); equation: Customers × Revenue per Customer.
- Primary constraint: `DEPLOYMENT_CAPACITY`, EASING, HIGH confidence. Customer growth, deployment headcount/capacity, revenue per employee, and operating leverage support the diagnosis.
- Scaling: revenue growth exceeds employee growth by 23 points; incremental operating margin is 47.8%; incremental FCF margin is 53.3%.
- Sustainability: continued growth is supported while deployment capacity expands, but customer and spend-per-customer persistence remain required.
- Falsification: sharp customer-growth deceleration, labor growth catching revenue, or operating-leverage reversal.
- Data gap: direct revenue-per-customer period detail remains limited.

## NVDA

- Archetype: `FABLESS_SEMICONDUCTOR` (HIGH); equation: Units × ASP × Product Mix.
- Primary constraint: `ADVANCED_PACKAGING`, EASING, MODERATE/HIGH structured confidence; memory and foundry capacity are secondary interacting constraints.
- Scaling: strong incremental operating and FCF margins, high revenue per employee, and inventory growth below revenue growth support scaling.
- Sustainability: above-market growth remains supported while packaging, memory, and foundry capacity expand; current fixture evidence does not establish live lead times.
- Falsification: inventory materially outgrows revenue, gross margin falls as supply eases, or supplier capacity expands faster than demand.
- Data gap: direct shipped-unit history is incomplete.

## TSM

- Archetype: `SEMICONDUCTOR_FOUNDRY` (HIGH); equation: Wafer Volume × Pricing × Node Mix.
- Primary constraint: `FAB_CAPACITY`, EASING, supported by wafer volume and capacity growth; capital intensity and equipment availability remain secondary/candidate constraints.
- Scaling: capex grows more slowly than revenue in the fixture and incremental operating margin is positive; revenue-per-capex remains the central efficiency measure.
- Sustainability: supported by advanced-node mix and utilization, subject to productive use of added fabs.
- Falsification: utilization falls after capacity additions, capex outgrows end demand, or advanced-node mix stalls.
- Data gaps: direct equipment lead-time and complete comparable capex-period evidence.

## MSFT

- Archetype: `HYPERSCALER_CLOUD_PLATFORM` with `TRADITIONAL_SAAS` secondary; equation: Cloud Workloads × Cloud Spend + Software Monetization.
- Primary constraint: `COMPUTE_CAPACITY`, MIXED, with power and datacenter capacity secondary. Capacity is expanding, while capex growth exceeds current revenue growth.
- Scaling: revenue grows much faster than employee count and incremental margins are positive, but revenue-minus-capex growth is negative.
- Sustainability: cloud/workload growth supports duration, but converting infrastructure investment into revenue and FCFF remains necessary.
- Falsification: persistent capex without cloud acceleration or capacity additions that fail to lift utilization.
- Data gap: direct cloud-spend observation.

## JPM

- Archetype: `BANK` (HIGH); equation: Earning Assets × Net Interest Spread + Fees.
- Primary constraint: `DEPOSITS`, EASING, with funding cost, regulatory capital, and credit quality secondary.
- Scaling: deposit and loan growth are observable; industrial-company FCFF ratios are intentionally not used as the core framework.
- Sustainability: balance-sheet growth is supported while funding and CET1 capacity remain adequate and charge-offs controlled.
- Falsification: deposit funding weakens, credit losses accelerate, or regulatory-capital headroom contracts.
- Data gaps: comparable funding-cost history and explicit fee-growth period.

## COST

- Archetype: `RETAIL_PHYSICAL_NETWORK` (HIGH); equation: Store Count × Same-Store Sales + Membership.
- Primary constraint: `STORE_EXPANSION`, EASING; logistics and market saturation are secondary/candidate constraints.
- Scaling: inventory grows more slowly than revenue and incremental operating/FCF margins are positive; store economics require comparable store history.
- Sustainability: new warehouses, same-store sales, and membership growth support the engine while distribution scales.
- Falsification: same-store sales weaken, inventory outgrows sales, or new stores dilute store-level economics.
- Data gaps: prior store count for calculated revenue per store and direct saturation evidence.

## Edge cases

| Ticker | Archetype | Growth engine | Primary constraint | Evidence / scaling conclusion |
| --- | --- | --- | --- | --- |
| XOM | `COMMODITY_PRODUCER` | Production Volume × Commodity Price | `PRODUCTION_CAPACITY`, EASING | Production expands, but incremental margins are pressured; mid-cycle price and replacement-capex evidence remain essential. |
| LLY | `PHARMA_BIOTECH` | Patients × Pricing × Drug Portfolio | `MANUFACTURING_CAPACITY`, EASING | Patient and capacity growth support scaling; pipeline and approvals remain interacting dependencies. |
| V | `PAYMENT_NETWORK` | Payment Volume × Take Rate | `CUSTOMER_ADOPTION`, EASING | Volume and transaction growth plus strong incremental margins support network scaling. |
| UBER | `MARKETPLACE_PLATFORM` | Gross Bookings × Take Rate | `CUSTOMER_ADOPTION`, EASING | Bookings/users grow faster than labor and incremental margins improve; supply and regulatory constraints remain relevant. |

