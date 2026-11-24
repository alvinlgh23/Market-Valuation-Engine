# CHAINSTOX Phase 8.1 — Implementation Report

Date: 2026-11-05 (Asia/Kuala_Lumpur).

## Implemented

1. One shared evidence pipeline now supplies documentary operational observations before Company Economics judgments. Synthetic operational values are excluded at fixture construction. Fixture financials and their derived proxies are explicitly non-authoritative across the Hero, Map/Inspector, Evidence and Report.
2. Demo financial inputs cannot produce supported valuation comparisons or financial implications. A separate provider-contract regression verifies that valid non-fixture financial inputs still support ordinary analytical comparisons. This is a provenance guard, not a change to DCF mathematics.
3. Constraint movement no longer follows automatically from positive capacity/customer metrics. Primary constraints remain UNKNOWN without defensible evidence.
4. SEC flow observations require annual duration; instant observations reject duration tags. Filing/accession tie-breaking is deterministic, and stale share denominators are withheld.
5. The actual valuation builder now enforces a security-unit publication gate. TSM/identified ADR and explicit currency mismatch paths return FAILED without valuations. A failed refresh cannot fall back to an earlier cached fair-value conclusion. Missing debt remains missing, not zero.
6. Explicit units override naming heuristics. Fixture financial statement amounts use base currency units; per-employee values no longer gain an invented million multiplier.
7. TSM node mix is +5 percentage points, with no relative-share-growth comparison to consolidated revenue. Canonical series replace duplicated customer/wafer/node-mix ledger and graph representations.
8. All 16 fixture profiles were regenerated. TSM publication dates match March 12, 2026. PLTR FY2024 RPO was added from its source-verified SEC filing with independent observation/publication/retrieval dates.
9. Report and Inspector operational tables default open; active provenance drawers expose source, date, unit and classification. Missing-price wording distinguishes provider data from fixtures. Old cached profiles with snapshots are rebuilt under classification revision `phase8.1-evidence-authority-v2` without relabeling saved data as a fresh provider fetch.
10. Root pytest now targets the supported repository suite rather than nested repositories.

## Verification and artifacts

See `CHAINSTOX_PHASE8_1_REGRESSION_RESULTS.md` for exact commands, counts and validity boundaries. The dedicated `frontend/scripts/phase8-integrity-journey.mjs` exercises the actual Research API and Snapshot → Map → Inspector → Evidence → Report for all six benchmarks in fixture and provider modes. It uses no mocked API routes. Screenshots and machine-readable journey results are under `frontend/artifacts/phase8_1/`; the strengthened existing Phase 8 smoke refreshes `frontend/artifacts/phase8/`.

The remediation matrix in `CHAINSTOX_PHASE8_1_REMEDIATION_AUDIT.md` records reproduction, root cause, changed files, correction, regression and remaining limitations for each finding, including the additional fixture-financial-authority issue found during screenshot review.

## Preserved work and model governance

All pre-existing Phase 7/8 work and untracked files were preserved. Existing nested-repository modifications were neither reset nor edited. No commits, pushes, deployments, new APIs, new providers or broad architectural/UI changes were introduced. The project skill guided evidence-qualified wording; the minimal-change workflow kept fixes in existing shared builders and formatters.

Deferred decisions remain: lease debt/expense/FCFF/WACC consistency; documentary-zero borrowing attestations; authoritative ADR FX source/date and ordinary-share denominator; a validated demand/capacity/utilization rule for constraint direction. None was silently selected to improve valuation outputs.

## Limitations

- Real-data mode is not synonymous with complete or fresh data: API states remain PARTIAL or STALE as returned. Current financial snapshots may originate from SEC disk cache. The application does not pretend that classification rebuilds refresh underlying facts.
- Live TSM valuation produced INSUFFICIENT_DATA before the unit gate because provider coverage was inadequate. Controlled tests call the real valuation builder with complete inputs to verify its security-unit gate. No live, validated TSM fair value is claimed.
- Curated operational coverage remains limited to six series across PLTR, TSM and NVDA, now twelve dated observations. AMD/MSFT/COST honestly report missing operational evidence.
- Automatic counterevidence discovery, causal contribution estimates, short transition-year handling, broader foreign-security metadata coverage and inactive-component cleanup remain outside this remediation.
- Existing pandas chained-assignment warnings originate in the nested macro dependency; it was not modified.

Phase 8.1 integrity closure is distinct from full Phase 8 completion. No Phase 9 work is authorized or started.
