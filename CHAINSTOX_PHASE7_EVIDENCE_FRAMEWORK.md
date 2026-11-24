# CHAINSTOX Phase 7 Evidence Framework

Version: `phase7-rules-v1`  
Schema: `evidence_contracts.EVIDENCE_SCHEMA_VERSION = 1.0`  
Review date: 2026-10-23

## Purpose

The framework separates four questions that were previously easy to conflate:

1. Did acquisition succeed?
2. Is the observation well-defined, current, and comparable?
3. Does the measurement directly represent the proposed mechanism?
4. Does the available evidence support a binding, directional, or causal conclusion?

Passing code is not proof of an economic claim. Retrieval time is not observation time. A proxy is not the phenomenon it approximates.

## Evidence envelope

`EvidenceEnvelope` carries compact provenance: source identity and URL, source type, provider status, retrieval time, observation/fiscal/filing dates, unit, currency, value, raw and normalized concepts, transformation, coverage, validation, staleness, limitation, entity identifier, and source status.

Acquisition/source states include `OBSERVED_LIVE`, `OBSERVED_CACHED`, `OBSERVED_STALE`, `HISTORICAL_REPORTED`, `CALCULATED`, `PROXY`, `FIXTURE`, `MISSING`, `PROVIDER_UNAVAILABLE`, `UNSUPPORTED`, `INVALID`, and `CONFLICTING`.

Provider failures remain more specific: rate limited, unavailable, malformed, empty, unsupported symbol, missing concept, period mismatch, unit mismatch, currency mismatch, unsupported framework, or invalid.

## Research claim model

`ResearchClaim` records:

- claim and entity identity;
- mechanism and relationship;
- reported fact, derived measurement, indirect proxy, structural hypothesis, economic inference, validated conclusion, unknown, or contradicted classification;
- direct, proxy, counter, and unresolved evidence IDs;
- source reliability, directness, temporal relevance, entity specificity, consistency;
- binding status, directional status, and causal status as independent dimensions;
- limitations, falsification conditions, methodological notes, and classification version.

No arbitrary numeric confidence percentage is generated.

## Constraint sufficiency rules

| Evidence pattern | Binding status | Direction status | Permitted interpretation |
|---|---|---|---|
| No entity-specific measurement | STRUCTURAL_CANDIDATE | DIRECTION_UNKNOWN | Mechanism may be relevant; current state unverified |
| Proxy only | EVIDENCE_INSUFFICIENT | POSSIBLY_EASING / POSSIBLY_TIGHTENING / UNKNOWN | Association may rank a candidate; cannot establish observed binding |
| Current direct measurement | POTENTIALLY_BINDING | OBSERVED_EASING / OBSERVED_TIGHTENING / UNKNOWN | Direction can be observed; binding still requires explicit evidence |
| Explicit direct binding disclosure | OBSERVED_BINDING or OBSERVED_NON_BINDING | observed direction or unknown | Strongest supported current classification |
| Direct evidence plus counterevidence | CONFLICTING_EVIDENCE | MIXED | Conflict must remain visible |
| Stale direct evidence for a current claim | STRUCTURAL_CANDIDATE | DIRECTION_UNKNOWN | Historical context only |

Constraint binding and direction are never inferred as the same field. Causal status remains association-only unless a stronger design is actually present.

## Measurement and comparability rules

- A numeric observation must be finite and have a unit and observation/fiscal period.
- Comparisons validate unit, currency, and—when required—period consistency.
- Annual SEC series select one coherent concept series. Alternate concepts may solve a current-schema gap, but concepts are not mixed across a time series.
- OCF and CapEx must share a fiscal end before calculated FCF is emitted.
- Retrieval freshness and observation freshness use separate fields.
- Missing is never converted to zero.
- Unadjusted market close is explicitly classified as price-return data, not total-return data.

## Priority negative cases

### PLTR deployment capacity

Revenue growth above employee growth remains a calculated productivity proxy. It does not observe deployment throughput, implementation capacity, seat capacity, contract activation, or the binding state of a deployment constraint. The deterministic negative test keeps the primary constraint `UNKNOWN`, classifies deployment capacity `EVIDENCE_INSUFFICIENT`, and allows at most `POSSIBLY_EASING`.

The curated 954-customer disclosure is a valid issuer fact, but its limitation expressly prohibits treating it as deployment capacity.

### NVDA advanced packaging

Advanced packaging remains structurally important for the fabless-semiconductor archetype. Broad revenue, margin, or cash-flow proxies cannot declare packaging capacity observed, binding, or directionally verified. Without a direct current entity-specific series, it remains a structural candidate.

### TSM foundry capacity

Wafer shipments, a capacity lower bound, and advanced-node revenue mix are direct issuer observations of their defined metrics. They do not produce exact utilization because the capacity disclosure is a lower bound, and they do not independently prove that capacity is binding. Stale observations cannot support a current directional claim.

## Counterevidence and falsification

Every diagnosis preserves `contrary_evidence_ids`. Any counterevidence qualifies consistency and can force `CONFLICTING_EVIDENCE` / `MIXED`. Existing mechanism-specific falsification conditions remain visible in the Inspector and Report. The generic evidence contract also requires a direct entity-specific throughput or utilization measure for the same period before upgrading a structural constraint.

## Frontend contract

The established workflow is preserved:

- Snapshot: observed, proxy/inference, unverified/stale, and counterevidence counts; binding and direction shown independently.
- Map: structural nodes remain useful, but candidates are not rendered as observed facts.
- Inspector: direct evidence, proxy/inference evidence, counterevidence, limitations, falsification, binding, and direction.
- Evidence: provider/source status, observation versus retrieval date, fiscal/filing date, unit/currency, raw/normalized concept, transformation, validation, freshness, source link, and limitation.
- Report: claim class, source state, freshness, limitations, validated constraints, and structural candidates are distinguished.

Older fixtures remain type-compatible through optional provenance fields. Regenerated benchmark fixtures expose the full Phase 7 contract and remain explicitly fixtures.

## Valuation boundary

Evidence classifications are read-only with respect to the valuation report. `valuation_assumption_review.mutates_dcf_inputs` remains false and has a regression test. Phase 7 did not alter WACC, SBC, FCFF/FCFE, growth fade, CapEx normalization, terminal value, dilution, scenario, or Reverse DCF formulas.

## Version and extension policy

Classification changes require a new `classification_version`, deterministic replay cases, negative inference tests, and documentation of changed claim sufficiency. Future Macro and Markets adoption should reuse the compact envelope and multidimensional claim rules without forcing all legacy adapters into a single oversized abstraction.
