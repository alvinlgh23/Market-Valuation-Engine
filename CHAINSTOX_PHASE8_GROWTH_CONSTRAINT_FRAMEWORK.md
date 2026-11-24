# Phase 8 growth and constraint framework

## Architecture and boundaries

`operational_research.py` adds issuer-specific definitions and dated observations around the existing `EvidenceEnvelope`. It does not replace the Phase 7 claim engine. Company Economics adds these observations to its existing ledger, evidence registry, graph, API profile, inspector, and report. No valuation formula is changed.

Definitions distinguish issuer-defined, standard financial, derived operational, proxy, and analyst-hypothesis categories. The shipped six series are issuer-defined. Definition version and effective coverage dates are explicit; the initial effective date bounds this imported dataset, not a claim about when an issuer first adopted its terminology. Future definition breaks must use separate versions rather than splice histories.

## Comparability

Comparisons require matching issuer, metric, scope, definition, measurement basis, period basis, unit and currency. Annual and quarterly cadence checks prevent bridging missing periods. Flow and period-population observations require compatible durations. Unresolved revisions and unverified observations are rejected. Original and explicitly comparable restated records are allowed; duplicate periods must be resolved before import.

Values are kept at disclosed precision. RDV growth from rounded 5.4 and 11.2 is about 107.4%; it is not substituted for the issuer's 105% growth calculated from unrounded data. Shipment growth from rounded 12.9 and 15.0 is about 16.3%. A 69% to 74% mix movement is **5 percentage points**, not 5% relative growth.

Sparse series are shown as period tables, not interpolated curves. Missing comparisons remain unavailable. There is no automated fiscal-calendar normalization or definition reconciliation.

## Growth attribution

The existing archetype registry remains the source of structural growth drivers. Added reported-series nodes are explicitly labeled and have structural-exposure edges, not causal assertions.

`metric_change` calculates absolute and relative movement only after compatibility checks. `revenue_bridge` uses R = N × R/N with symmetric interaction allocation:

- Population contribution: ΔN × (ARPC₀ + ARPC₁) / 2.
- Revenue-per-population contribution: ΔARPC × (N₀ + N₁) / 2.

The contributions exactly sum to revenue change. This is an accounting identity, not causal identification. A point-in-time customer count is rejected in place of a period population. No real-company numerical customer/revenue decomposition is published because the imported dataset does not yet include a validated matching revenue pair.

## Constraint economics

Phase 7 remains authoritative for structural importance, binding, direction, counterevidence and falsification. New historical KPI series are not automatically connected as direct bottleneck evidence. They remain structural context with unknown current constraint direction.

- PLTR customer expansion does not observe deployment throughput. TCV, RDV, RPO and revenue are different concepts; TCV is not imported as a numeric observation.
- TSM shipments and node mix do not measure utilization or qualified capacity. The pre-existing capacity floor cannot become an exact utilization denominator.
- NVDA Data Center is an end-market revenue classification, not GPU units, product architecture volume, or a reportable segment. Its growth does not verify packaging capacity.

Counterevidence remains available in the established constraint inspector/report and Phase 7 assessment contract. No new current bottleneck/counterbottleneck disclosure was validated in this pass. Empty counterevidence is labeled **not assessed**, never confirmation.

## Translation and valuation

Each definition describes the operating-to-financial mechanism and its limits. These are qualitative mechanisms, not forecast coefficients. Read-only assumption context pairs historical metric changes with an available year-one revenue assumption, explicitly flagging horizon and scope differences. It does not label a forecast supported solely because numbers are close.

WACC, ERP, debt cost, SBC, dilution, FCFF, CapEx, growth fade, terminal value and Reverse DCF are unchanged. Methodology proposals remain subject to the existing governance document and approval.

## Known implementation limits

The symmetric bridge is independently tested but not yet exposed as a real-company decomposition. There is no automated issuer-document extraction, generic quarterly/YTD conversion, empirical causal model, or historical bottleneck event series. Existing archetypes are reused; specialized bank/insurance/REIT operational models are not added.
