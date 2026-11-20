# CHAINSTOX Phase 7 Validation Audit

Audit date: 2026-10-23  
Release classification: **READY TO CLOSE — DOCUMENTED LIMITATIONS**

## Worktree protection

Work continued in the required repository on branch `main` at inspected HEAD `e6136d6eaf48f42f6e24554e56251e61622a1c90`. Pre-existing modifications in the three nested repositories and `frontend/tsconfig.tsbuildinfo` were preserved. No reset, cleanup, branch creation, commit, push, deployment, or nested-repository edit was performed.

## Requirement status

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Compact typed evidence contract | IMPLEMENTED | `evidence_contracts.py`; frontend serialization and provenance view |
| Provider error taxonomy | IMPLEMENTED | rate limit, malformed, empty, unsupported, concept/period/unit/currency/framework states |
| Yahoo root-cause investigation | IMPLEMENTED | earlier chart 429 reproduced; final chart run 7/7; AMD quote-summary 429 confirms intermittency |
| Compatible market-history normalization | IMPLEMENTED | adjusted policy, dates, currency, calendar, replay validation |
| Alternative public provider | BLOCKED — PROVIDER | no compatible lawful no-key fallback; access challenge not bypassed |
| Reproducible provider matrix | IMPLEMENTED | `scripts/phase7_provider_diagnostics.py` |
| SEC coherent concept selection | IMPLEMENTED | latest compatible concept chosen without series mixing |
| IFRS / non-US filing support | IMPLEMENTED | TSM `ifrs-full`, 20-F, TWD |
| AMD and TSM accounting failures | IMPLEMENTED | both now have aligned annual accounting inputs |
| Full market inputs for SEC fallback | BLOCKED — PROVIDER | SEC does not provide price, market cap, beta; TSM ADR bridge missing |
| Cache versus observation freshness | IMPLEMENTED | separate retrieval and observation fields; actual SEC cache time retained |
| Macro observation provenance | PARTIALLY IMPLEMENTED | typed API metrics include provenance; some legacy sources lack dates |
| Operational metric source path | IMPLEMENTED | validated curated registry with primary-source URLs and limitations |
| Automated broad filing/PDF extraction | DEFERRED — OUT OF SCOPE | no speculative scraper or unsupported extraction claim introduced |
| Claim types and multidimensional evidence | IMPLEMENTED | `ResearchClaim`; reliability/directness/time/entity/consistency/binding/direction/causal fields |
| Binding separate from direction | IMPLEMENTED | backend rules, frontend labels, deterministic tests |
| Counterevidence and falsification | IMPLEMENTED | IDs and conflicting states preserved; UI/report inspectable |
| PLTR proxy negative case | IMPLEMENTED | revenue/employee proxy cannot promote deployment constraint |
| NVDA packaging negative case | IMPLEMENTED | archetype alone remains structural candidate |
| TSM capacity scope | IMPLEMENTED | direct defined facts retained; utilization/binding not inferred |
| Structural candidates inspectable | IMPLEMENTED | `candidate_assessments` in API, Constraints view, Report |
| Snapshot → Map → Inspector → Evidence → Report | IMPLEMENTED | existing grammar preserved with Phase 7 status/provenance additions |
| Arbitrary ticker handling | IMPLEMENTED | existing generic resolver preserved; AMD SEC resolution verified under Yahoo 429 |
| Dynamic sector data reaches Markets | IMPLEMENTED | live API 34 rows; UI SMH −4.2% assertion |
| Treasury maturity/date/unit safeguards | IMPLEMENTED / REGRESSION PASSED | Phase 6.2 unit tests and Macro Correction browser suite |
| Valuation formulas unchanged | IMPLEMENTED | no economic formula diff; mutation regression passed |
| Paid API, LLM, broad redesign | DEFERRED — OUT OF SCOPE | none introduced |

## Acceptance gates

### Gate A — Data reliability

PASS. The system now diagnoses provider versus disclosure failures, supports deterministic market replay, improves real benchmark accounting coverage, handles IFRS TSM, validates manual evidence, and completed a live market pass. Provider durability is a limitation, not a hidden failure.

### Gate B — Research epistemology

PASS. Claim type, directness, temporal relevance, consistency, binding, direction, and causal status are distinct. Proxy-only, stale, structural, and conflicting cases have deterministic negative tests.

### Gate C — Integration

PASS. Backend evidence states and provenance reach the frontend, candidate mechanisms remain separate from observed constraints, missing data remains informative, valuation inputs remain immutable, and all relevant browser suites passed.

## Exact verification record

| Command / check | Result |
|---|---|
| `python3 -m py_compile ...` Phase 7 modules | PASS |
| `python3 -m pytest tests --collect-only -q` | 178 collected |
| `python3 -m pytest tests -q` | 178 passed; 0 failed; 28 subtests; 378 warnings |
| unittest discovery count | 118 |
| Focused Phase 7/SEC/Company suite | 63 passed; 22 subtests |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS, 0 errors and 0 warnings on final rerun |
| `npm run build` | PASS |
| bounded market provider matrix | 7/7 live chart successes |
| Python sector engine | 34 rows; requested histories `OK` |
| `/api/research?...refresh=1` | `LIVE_REFRESH`; 34 sector rows; no fallback |
| `smoke:phase7` | PASS; 34 rows; SMH −4.2%; provenance visible |
| `smoke:phase6` | PASS; 10 screenshots |
| `smoke:companies` | PASS; 9 screenshots |
| `smoke:markets` | PASS |
| `smoke:valuation` | PASS; 24 screenshots |
| `smoke:macro` | PASS; 10 screenshots |
| `smoke:macro-correction` | PASS; 11 screenshots |
| `smoke:research` | PASS; 11 screenshots |
| `git diff --check` | PASS on final rerun |

The live API refresh legitimately updated `.cache/research/core-market.json`. Two macro tests initially failed because they implicitly depended on the previous cache contents. Their setup now injects the bundled insufficient-core fixture for the intended missing-feed scenario; the live cache remains intact, and the final full suite passes. This was test isolation, not a change to macro economics.

## Phase 6.1 / 6.2 regression conclusions

- FCFF mismatch/missing-input valuation blockers pass.
- SEC debt aggregation and incomplete-debt gate pass.
- Failed valuation conclusions remain withheld.
- Reverse DCF convergence/no-solution states pass.
- Shared runtime, argument allowlists, and direct-route navigation remain in place.
- Treasury moves remain basis points and mixed-date curves remain withheld.
- Dynamic Markets does not substitute static values for missing measurements.

## Honest release limitations

1. A successful live run does not establish an SLA for Yahoo. HTTP 429 remains observed.
2. SEC accounting coverage cannot supply current market inputs.
3. TSM requires validated ADR/share conversion before a per-ADR valuation.
4. Many operational constraints remain structural hypotheses because direct current KPIs are unavailable.
5. Curated evidence is intentionally manual and narrow.
6. Macro provenance is not yet complete across every legacy upstream adapter.
7. Known nested Compass pandas warnings remain; they do not represent skipped tests but require future pandas 3 compatibility work.

## Decision

Phase 7A, 7B, and 7C each meet their scoped acceptance criteria. Phase 7 may close. CHAINSTOX may proceed to the next phase, but the next plan must preserve explicit provider states and must not describe market-provider durability, broad operational KPI coverage, or SEC-only valuation completeness as solved.
