# Phase 8 data integrity audit

Audit: 2026-11-03. Documentary retrieval through primary-source web access; provider diagnostic through the repository adapters. No access controls bypassed, paid provider or LLM added.

## Primary disclosures

- [PLTR FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm): MD&A customer and RDV sections; Note 3 RPO; liquidity and Note 6 debt. Values and definitions verified on this run. Historical, not current-quarter data.
- [TSMC annual report](https://investor.tsmc.com/static/annualReports/2025/english/index.html): FY2024–25 shipments and node mix verified. [Issuer PDF cover](https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20Annual%20Report.E.pdf) states printed March 12, 2026. Corrected the inherited March 10 date. This is a document date, not a proven first web-upload time.
- NVIDIA [FY2026](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Fourth-Quarter-and-Fiscal-2026/) and [FY2025](https://investor.nvidia.com/news/press-release-details/2025/NVIDIA-Announces-Financial-Results-for-Fourth-Quarter-and-Fiscal-2025/) releases: Data Center revenue and fiscal endpoints verified. Rounded annual observations, no shipment inference.

## PLTR debt: extraction coverage gap, not no disclosure

The current SEC adapter selects `LongTermDebtNoncurrent` from 2021-12-31, filed 2022-02-24, with no current-debt component. Its output correctly remains `debt=null`, coverage `PARTIAL`.

The FY2025 10-K explicitly reports no outstanding debt balances and an undrawn $500m revolver. Therefore the structured gap is not proof of debt or of absent disclosure. A dated documentary-zero normalization path and lease/other-claim reconciliation are still needed before changing the accounting bridge. No missing value was converted to zero, and no completeness threshold was lowered.

The existing annual-series selector uses FY/form/end metadata; it does not yet generally reject short-duration facts embedded in annual filings. This is a remaining parser-integrity issue, not an approved economic assumption change. The new operational path independently checks measurement duration.

## TSM security units

[FY2025 20-F](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm), Item 6 share ownership footnote (2), confirms five ordinary shares per ADS. TSM is the NYSE ADS; 2330 is the Taiwan ordinary-share security. IFRS accounts are in TWD; the US quotation is USD.

`security_units.py` independently tests equity / total ordinary shares × ordinary-shares-per-ADS × compatible FX. It rejects ADS denominators (double application), wrong currency, nonpositive ratio, unverified date intervals, and missing/misaligned FX. Enterprise/equity value is not changed by this presentation calculation.

The live bridge remains **SECURITY_UNIT_AMBIGUITY**: an applicable effective-date interval, reconciled current total ordinary-share denominator and dated FX were not established together. The documented 5:1 ratio is visible, but no authoritative per-ADR value is emitted by this bridge. The helper is not automatically wired to rescale DCF results.

## Yahoo durability

Bounded diagnostic: 7/7 chart requests succeeded (SPY, QQQ, SMH, IGV, ^TNX, ^VIX, JPY=X). A later independent SPY call also succeeded, with 251 observations ending 2026-11-02. This is limited same-session repeat evidence, not an SLA. Prior Phase 7 HTTP 429 observations remain relevant.

The chart adapter performs one request with a timeout, explicit rate-limit/failure status, and no rate-limit evasion. `Valuation_model` retains its process-local history cache. Cross-process persistent response caching, global budgets, and Retry-After scheduling are not implemented. No provider rewrite was justified by this bounded successful run; those remain durability limitations.

All five SEC benchmark collectors succeeded on this run, but no SEC-only row is DCF-ready: market price/capitalization/beta are missing, PLTR debt is partial, and TSM has a unit bridge gap. Retrieval success is not completeness.

## Status taxonomy and remaining gaps

Provider failures retain Phase 7 typed status; currency, unit, period and revision conflicts retain explicit comparison reasons. Missing curated data is `MISSING`, not a provider error. The requested full normalized taxonomy for parser failure versus reporting-definition/disclosure gaps is not yet implemented across every legacy adapter. Do not describe this as solved.
