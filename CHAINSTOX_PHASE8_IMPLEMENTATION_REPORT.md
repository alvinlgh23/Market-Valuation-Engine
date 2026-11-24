# CHAINSTOX Phase 8 implementation report

Date: 2026-11-03. Branch `main`, HEAD `e6136d6eaf48f42f6e24554e56251e61622a1c90`. Phase 7 remains uncommitted; nested Centralbank Compass, KOSPI and NEER worktrees were not edited. No reset, cleanup, commit or push.

## Implemented

- `operational_research.py`: issuer-scoped definitions, observations, dated envelope provenance, compatibility checks, growth calculation, independently tested symmetric revenue bridge, qualitative translation and read-only assumption context.
- `data/operational_series.json`: six definitions and eleven historical observations across PLTR, TSM and NVDA, with source/locator/date metadata. AMD/MSFT/COST/arbitrary companies receive truthful missing states, not copied observations.
- `evidence_contracts.py`: optional locator, extraction, definition and revision metadata on the existing envelope.
- `data_sources/operational_evidence.py`: unverified curated entries no longer claim VALID; source locators retained. Existing TSM document date corrected from issuer evidence.
- `company_economics.py`: new observations enter the existing ledger/registry; reported-series nodes join the economic map; full graph validation runs after integration.
- `company_research.py`: older cached profiles can receive separately dated operational context without rewriting cached financial dates or marking them live. Older saved maps need a full analysis refresh for the new nodes and ledger items.
- `security_units.py`: independent, explicit ordinary-to-ADS conversion checks. Production TSM conversion remains gated.
- Frontend types, Company snapshot, map inspector, shared evidence drawer, report and scoped CSS: expandable operating series, comparable changes, source details, definitions, missing states, and assumption context. No new top-level dashboard or broad redesign.
- Existing deterministic fixture exporter regenerated the 16 profiles. Real documentary observations are labeled separately from demo financial inputs.
- `tests/test_phase8_operational.py`, browser `phase8-operational-smoke.mjs`, npm script, screenshots and five Phase 8 documents added.

## Actual research depth

PLTR: customers, RDV and RPO, with contracting distinctions and no deployment-throughput claim. TSM: output and node-mix changes, with capacity/utilization limitations and explicit ADR gate. NVDA: comparable Data Center revenue, not product units or packaging evidence. AMD, MSFT and COST validate schema/UI compatibility only; no new issuer-specific series has been acquired for them.

The dataset is deliberately sparse and dated. There is no live KPI feed, full company revenue decomposition, comprehensive operating leverage series, or new empirically verified bottleneck. Existing Phase 7 constraint and counterevidence behavior remains available.

## Integration and performance

The existing Company API serializes the additional profile object. A real `company-analyze` PLTR POST returned `PARTIAL`, `LIVE_STRUCTURED_PROVIDER`, three operational metric IDs, and no errors. Each observation retains its own historical source/date; the live provider label is not applied to the curated observations.

Local JSON parsing adds no network calls to profile construction. Evidence is repeated in the compatibility ledger and operational view for existing consumers; no new storage service or dependency was introduced. The minimal-change skill guided reuse of these contracts and native disclosure controls.

## Release classification

| Area | Result |
|---|---|
| Engineering completion | Core operational slice implemented and tested; full brief remains partial |
| Operational data coverage | Six definitions / eleven observations; three primary issuers |
| Source reliability | Primary documents verified; manual, historical curation |
| Metric comparability | Deterministic annual/quarterly guards; no general YTD normalization |
| Constraint validation | Earlier safeguards retained; no new verified current bottleneck |
| Financial translation | Qualitative mechanisms and read-only context; no new numerical forecast |
| Valuation data integrity | Formula/gates preserved; PLTR debt and TSM live bridge unresolved |
| Live provider durability | Bounded success, limited same-session repeat; not production assurance |

## Remaining implementation, not disguised as source absence

1. Broader PLTR commercial/government and NVDA product/end-market mix acquisition and source-specific definition history.
2. A real comparable revenue-driver bridge in the UI (the mathematics is tested but not populated with a matching real dataset).
3. Dated company-specific constraint/counterevidence event series and richer financial/operating leverage translation.
4. A complete common parser/disclosure-gap taxonomy across legacy adapters and SEC duration selection review.
5. Reconcile a dated PLTR documentary-zero debt path, leases and senior claims; reconcile TSM effective dates, total shares and FX before live unit conversion.
6. Secondary-company operational ingestion, if depth beyond truthful missing-data compatibility is required.

No WACC, SBC, FCFF/FCFE, growth fade, CapEx, terminal value, scenario or Reverse DCF formula changed. No economic methodology decision was silently approved. Phase 8 should **not yet be closed as fully complete**, and Phase 9 should wait for the outstanding acceptance scope to be resolved.
