"""SEC structured-company fallback for identity and annual financial facts."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from evidence_contracts import (
    CoverageStatus,
    EvidenceEnvelope,
    ProviderStatus,
    SourceStatus,
    StalenessStatus,
    ValidationStatus,
)


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "sec_company"
USER_AGENT = os.environ.get("CHAINSTOX_SEC_USER_AGENT", "CHAINSTOX deterministic research contact@example.com")
_FETCH_DIAGNOSTICS: dict[str, dict] = {}

DEBT_TOTAL_CONCEPTS = (
    "LongTermDebtAndFinanceLeaseObligations",
    "LongTermDebtAndCapitalLeaseObligations",
    "DebtAndFinanceLeaseObligations",
    "DebtLongtermAndShorttermCombinedAmount",
)
DEBT_CURRENT_CONCEPTS = (
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "DebtCurrent",
    "LongTermDebtCurrent",
)
DEBT_NONCURRENT_CONCEPTS = (
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
    "LongTermDebtNoncurrent",
)

FLOW_METRICS = {
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "capex",
    "sbc",
}
FLOW_SHARE_CONCEPTS = {
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "AdjustedWeightedAverageShares",
    "WeightedAverageShares",
}

US_GAAP_CONCEPTS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "assets": ("Assets",),
    "inventory": ("InventoryNet",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquireOtherPropertyPlantAndEquipment",
    ),
    "sbc": ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
    "cash": ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CashAndCashEquivalentsAtCarryingValue"),
    "shares": (
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesOutstanding",
    ),
}

IFRS_CONCEPTS = {
    "revenue": ("Revenue", "RevenueFromContractsWithCustomers"),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("ProfitLossFromOperatingActivities",),
    "net_income": ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss"),
    "assets": ("Assets",),
    "inventory": ("Inventories",),
    "operating_cash_flow": ("CashFlowsFromUsedInOperatingActivities",),
    "capex": ("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",),
    "sbc": ("ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets",),
    "cash": ("CashAndCashEquivalents",),
    "shares": (
        "AdjustedWeightedAverageShares",
        "WeightedAverageShares",
        "NumberOfSharesIssuedAndFullyPaid",
    ),
}

SKIP_WORKING_CAPITAL_CONCEPTS = {
    "IncreaseDecreaseInCashAndCashEquivalents",
    "IncreaseDecreaseInDeferredIncomeTaxes",
    "IncreaseDecreaseInEquitySecuritiesFvNi",
    "IncreaseDecreaseInOutstandingChecksFinancingActivities",
    "IncreaseDecreaseInDeposits",
    "IncreaseDecreaseInLoansHeldForSale",
    "IncreaseDecreaseInFederalFundsPurchasedAndSecuritiesSoldUnderAgreementsToRepurchaseNet",
}


def _fetch(url: str, cache_path: Path, max_age_days: int = 7) -> dict:
    if cache_path.exists():
        age = dt.datetime.now().timestamp() - cache_path.stat().st_mtime
        if age <= max_age_days * 86400:
            _FETCH_DIAGNOSTICS[url] = {
                "source_status": "OBSERVED_CACHED", "provider_status": "OK", "cache_age_seconds": round(age, 3),
                "retrieved_at": dt.datetime.fromtimestamp(cache_path.stat().st_mtime, dt.timezone.utc).isoformat(),
            }
            return json.loads(cache_path.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        _FETCH_DIAGNOSTICS[url] = {
            "source_status": "OBSERVED_LIVE", "provider_status": "OK", "cache_age_seconds": 0,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        return payload
    except Exception as exc:
        if cache_path.exists():
            _FETCH_DIAGNOSTICS[url] = {
                "source_status": "OBSERVED_STALE", "provider_status": "UNAVAILABLE",
                "cache_age_seconds": round(dt.datetime.now().timestamp() - cache_path.stat().st_mtime, 3),
                "retrieved_at": dt.datetime.fromtimestamp(cache_path.stat().st_mtime, dt.timezone.utc).isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
            }
            return json.loads(cache_path.read_text(encoding="utf-8"))
        _FETCH_DIAGNOSTICS[url] = {"source_status": "PROVIDER_UNAVAILABLE", "provider_status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}
        raise


def sec_fetch_diagnostics() -> dict[str, dict]:
    return {key: dict(value) for key, value in _FETCH_DIAGNOSTICS.items()}


def _company_record(ticker: str) -> dict:
    master = _fetch("https://www.sec.gov/files/company_tickers.json", CACHE_DIR / "company_tickers.json")
    symbol = ticker.upper()
    for row in master.values():
        if str(row.get("ticker", "")).upper() == symbol:
            return row
    raise LookupError(f"{symbol} is not present in the SEC company ticker file.")


def _annual_series(
    facts: dict,
    concepts: tuple[str, ...],
    unit: str = "USD",
    *,
    taxonomy: str = "us-gaap",
    forms: tuple[str, ...] = ("10-K",),
) -> list[dict]:
    """Return one coherent annual concept series with period provenance.

    The selected concept is the first preferred concept that reaches the most
    recent available fiscal end.  This prevents an old first-listed concept
    from masking a current alternate schema while avoiding concept mixing
    within a historical series.
    """
    taxonomy_facts = facts.get("facts", {}).get(taxonomy, {})
    flow_concepts = {
        concept
        for mapping in (US_GAAP_CONCEPTS, IFRS_CONCEPTS)
        for metric, names in mapping.items()
        if metric in FLOW_METRICS
        for concept in names
    } | FLOW_SHARE_CONCEPTS

    def valid_period(row, concept):
        try:
            end = dt.date.fromisoformat(row["end"])
            if concept in flow_concepts:
                return 330 <= (end - dt.date.fromisoformat(row.get("start", ""))).days <= 380
            return not row.get("start")
        except (ValueError, TypeError, KeyError):
            return False

    candidates_by_concept: list[tuple[int, str, list[dict]]] = []
    for priority, concept in enumerate(concepts):
        rows = taxonomy_facts.get(concept, {}).get("units", {}).get(unit, [])
        valid = [
            {**row, "concept": concept, "unit": unit, "taxonomy": taxonomy}
            for row in rows
            if row.get("form") in forms
            and row.get("fp") == "FY"
            and row.get("end")
            and isinstance(row.get("val"), (int, float))
            and valid_period(row, concept)
        ]
        if valid:
            candidates_by_concept.append((priority, max(str(row["end"]) for row in valid), valid))
    if not candidates_by_concept:
        return []
    _, _, selected_rows = max(candidates_by_concept, key=lambda item: (item[1], -item[0]))
    by_end: dict[str, dict] = {}
    for row in selected_rows:
        end = str(row["end"])
        rank = lambda item: (str(item.get("filed", "")), str(item.get("accn", "")), str(item.get("start", "")))
        if end not in by_end or rank(row) > rank(by_end[end]):
            by_end[end] = row
    return [row for _, row in sorted(by_end.items(), reverse=True)[:5]]


def _annual_values(facts: dict, concepts: tuple[str, ...], unit: str = "USD") -> list[float]:
    return [float(row["val"]) for row in _annual_series(facts, concepts, unit)]


def _latest_fy_fact(facts: dict, concepts: tuple[str, ...], unit: str = "USD") -> dict | None:
    """Select the latest annual fact without mixing concepts or reporting periods."""
    series = _annual_series(facts, concepts, unit)
    return series[0] if series else None


def _instant_fact_at_end(
    facts: dict,
    concepts: tuple[str, ...],
    period_end: str,
    unit: str = "USD",
    *,
    taxonomy: str = "us-gaap",
    forms: tuple[str, ...] = ("10-K",),
) -> dict | None:
    taxonomy_facts = facts.get("facts", {}).get(taxonomy, {})
    for concept in concepts:
        rows = [
            {**row, "concept": concept, "unit": unit}
            for row in taxonomy_facts.get(concept, {}).get("units", {}).get(unit, [])
            if row.get("form") in forms
            and row.get("fp") == "FY"
            and row.get("end") == period_end
            and not row.get("start")
            and isinstance(row.get("val"), (int, float))
        ]
        if rows:
            return max(rows, key=lambda item: (str(item.get("filed", "")), str(item.get("accn", ""))))
    return None


def _flow_fact_at_end(
    facts: dict,
    concepts: tuple[str, ...],
    period_end: str,
    unit: str = "USD",
    *,
    taxonomy: str = "us-gaap",
    forms: tuple[str, ...] = ("10-K",),
) -> dict | None:
    taxonomy_facts = facts.get("facts", {}).get(taxonomy, {})
    try:
        end_date = dt.date.fromisoformat(period_end)
    except ValueError:
        return None
    for concept in concepts:
        rows = []
        for row in taxonomy_facts.get(concept, {}).get("units", {}).get(unit, []):
            if (
                row.get("form") not in forms
                or row.get("fp") != "FY"
                or row.get("end") != period_end
                or not row.get("start")
                or not isinstance(row.get("val"), (int, float))
            ):
                continue
            try:
                days = (end_date - dt.date.fromisoformat(row["start"])).days
            except ValueError:
                continue
            if 330 <= days <= 380:
                rows.append({**row, "concept": concept, "unit": unit})
        if rows:
            return max(rows, key=lambda item: (str(item.get("filed", "")), str(item.get("accn", ""))))
    return None


def _select_debt(facts: dict, unit: str = "USD") -> dict:
    """Select total debt from non-overlapping SEC facts with explicit coverage."""
    total = _latest_fy_fact(facts, DEBT_TOTAL_CONCEPTS, unit)
    current = _latest_fy_fact(facts, DEBT_CURRENT_CONCEPTS, unit)
    noncurrent = _latest_fy_fact(facts, DEBT_NONCURRENT_CONCEPTS, unit)

    aligned = current is not None and noncurrent is not None and current["end"] == noncurrent["end"]
    components_are_newer = aligned and total is not None and current["end"] > total["end"]
    if total is not None and not components_are_newer:
        return {
            "value": float(total["val"]),
            "coverage": "COMPLETE",
            "methodology": "consolidated_total",
            "selected_concepts": [total["concept"]],
            "period_end": total["end"],
            "fiscal_year": total.get("fy"),
            "filing_date": total.get("filed"),
            "currency": total["unit"],
            "missing_components": [],
        }

    if aligned:
        selected = [current, noncurrent]
        return {
            "value": sum(float(row["val"]) for row in selected),
            "coverage": "COMPLETE",
            "methodology": "aligned_current_plus_noncurrent",
            "selected_concepts": [row["concept"] for row in selected],
            "period_end": current["end"],
            "fiscal_year": current.get("fy") or noncurrent.get("fy"),
            "filing_date": max(str(current.get("filed", "")), str(noncurrent.get("filed", ""))),
            "currency": current["unit"],
            "missing_components": [],
        }

    # Verified zero current maturities: LongTermDebt equals LongTermDebtNoncurrent on the same
    # period end, next-12-month principal maturities are explicitly reported as 0, and any
    # short-term borrowings / commercial paper on that date are absent or 0.
    if current is None and noncurrent is not None:
        end = str(noncurrent["end"])
        lt_total = _instant_fact_at_end(facts, ("LongTermDebt",), end, unit)
        next_12m = _instant_fact_at_end(
            facts, ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",), end, unit
        )
        short_term = _instant_fact_at_end(facts, ("ShortTermBorrowings", "CommercialPaper"), end, unit)
        if (
            lt_total is not None
            and next_12m is not None
            and float(next_12m["val"]) == 0.0
            and float(lt_total["val"]) == float(noncurrent["val"])
            and (short_term is None or float(short_term["val"]) == 0.0)
        ):
            selected_names = [noncurrent["concept"], lt_total["concept"], next_12m["concept"]]
            if short_term is not None:
                selected_names.append(short_term["concept"])
            return {
                "value": float(noncurrent["val"]),
                "coverage": "COMPLETE",
                "methodology": "noncurrent_with_verified_zero_current_maturities",
                "selected_concepts": selected_names,
                "period_end": end,
                "fiscal_year": noncurrent.get("fy"),
                "filing_date": noncurrent.get("filed"),
                "currency": noncurrent["unit"],
                "missing_components": [],
            }

    available = [row for row in (current, noncurrent) if row is not None]
    return {
        "value": None,
        "coverage": "PARTIAL" if available else "INSUFFICIENT_DATA",
        "methodology": "not_reported_as_total",
        "selected_concepts": [row["concept"] for row in available],
        "period_end": available[0]["end"] if available else None,
        "fiscal_year": available[0].get("fy") if available else None,
        "filing_date": available[0].get("filed") if available else None,
        "currency": available[0]["unit"] if available else unit,
        "missing_components": [
            name
            for name, row in (("current debt", current), ("noncurrent debt", noncurrent))
            if row is None
        ] + (["aligned reporting period"] if current and noncurrent and not aligned else []),
    }


def _working_capital_sign(concept: str) -> int | None:
    """Map an XBRL working-capital flow concept to its cash-flow effect sign (+1 inflow, -1 outflow)."""
    if concept in SKIP_WORKING_CAPITAL_CONCEPTS or "FinancingActivities" in concept or "InvestingActivities" in concept:
        return None
    if concept.startswith(("AdjustmentsForDecreaseIncreaseIn", "AdjustmentsForIncreaseDecreaseIn")):
        return 1
    if not concept.startswith("IncreaseDecreaseIn"):
        return None
    lower = concept.lower()
    if "otheroperatingcapitalnet" in lower or "operatingcapital" in lower:
        return -1
    if any(token in lower for token in ("payable", "liability", "liabilities", "deferredrevenue", "accrued", "obligation", "incometaxes")):
        if "receivable" in lower or "prepaid" in lower:
            return -1
        return 1
    if any(token in lower for token in ("receivable", "inventor", "prepaid", "asset", "deferredcharges", "duefrom")):
        return -1
    return None


def _working_capital_cash_effect(
    facts: dict,
    period_end: str,
    unit: str,
    *,
    taxonomy: str,
    forms: tuple[str, ...],
) -> tuple[float | None, list[str]]:
    """Aggregate operating working-capital cash-flow effects for ``period_end`` without double counting."""
    if taxonomy == "us-gaap":
        aggregate = _flow_fact_at_end(facts, ("IncreaseDecreaseInOperatingCapital",), period_end, unit, taxonomy=taxonomy, forms=forms)
        if aggregate is not None:
            return -float(aggregate["val"]), [aggregate["concept"]]
    taxonomy_facts = facts.get("facts", {}).get(taxonomy, {})
    matched: dict[str, float] = {}
    for concept in sorted(taxonomy_facts):
        sign = _working_capital_sign(concept)
        if sign is None:
            continue
        row = _flow_fact_at_end(facts, (concept,), period_end, unit, taxonomy=taxonomy, forms=forms)
        if row is not None:
            matched[concept] = sign * float(row["val"])
    if not matched:
        return None, []
    # Overlap guards when a filer tags both a combined row and one of its sub-rows.
    if "IncreaseDecreaseInAccountsPayableAndAccruedLiabilities" in matched:
        for child in ("IncreaseDecreaseInAccountsPayable", "IncreaseDecreaseInAccountsPayableTrade", "IncreaseDecreaseInAccruedLiabilities"):
            matched.pop(child, None)
    if "IncreaseDecreaseInAccountsAndOtherReceivables" in matched or "IncreaseDecreaseInReceivables" in matched:
        matched.pop("IncreaseDecreaseInAccountsReceivable", None)
    if "IncreaseDecreaseInContractWithCustomerLiability" in matched:
        matched.pop("IncreaseDecreaseInDeferredRevenue", None)
    return sum(matched.values()), sorted(matched)


def _reconciliation_inputs(
    facts: dict,
    *,
    taxonomy: str,
    unit: str,
    forms: tuple[str, ...],
    period_end: str | None,
    latest_debt: float | None,
) -> dict:
    """Extract period-aligned D&A, tax, interest, working capital and non-cash rows (solution plan C1b)."""
    empty = {
        "depreciation_amortization": None,
        "working_capital_change": None,
        "tax_rate": 0.21,
        "interest_expense": None,
        "after_tax_interest": None,
        "other_non_cash_adjustments": None,
        "sources": {},
    }
    if not period_end or taxonomy not in {"us-gaap", "ifrs-full"}:
        return empty

    sources: dict[str, str] = {}
    if taxonomy == "us-gaap":
        da_row = _flow_fact_at_end(
            facts,
            ("DepreciationAndAmortization", "DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        if da_row is not None:
            da = float(da_row["val"])
            sources["depreciation_amortization"] = f"SEC 10-K {da_row['concept']} ({period_end})"
        else:
            dep = _flow_fact_at_end(facts, ("OtherDepreciationAndAmortization", "Depreciation"), period_end, unit, taxonomy=taxonomy, forms=forms)
            amo = _flow_fact_at_end(facts, ("AdjustmentForAmortization", "AmortizationOfIntangibleAssets"), period_end, unit, taxonomy=taxonomy, forms=forms)
            parts = [row for row in (dep, amo) if row is not None]
            da = sum(float(row["val"]) for row in parts) if parts else None
            if parts:
                sources["depreciation_amortization"] = f"SEC 10-K {' + '.join(row['concept'] for row in parts)} ({period_end})"

        tax_row = _flow_fact_at_end(facts, ("IncomeTaxExpenseBenefit",), period_end, unit, taxonomy=taxonomy, forms=forms)
        pretax_row = _flow_fact_at_end(
            facts,
            (
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            ),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        int_row = _flow_fact_at_end(
            facts,
            ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense"),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        interest_expense = abs(float(int_row["val"])) if int_row is not None else None
        if int_row is not None:
            sources["interest_expense"] = f"SEC 10-K {int_row['concept']} ({period_end})"

        def_tax_row = _flow_fact_at_end(
            facts, ("DeferredIncomeTaxExpenseBenefit", "DeferredIncomeTaxesAndTaxCredits"),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        def_tax = float(def_tax_row["val"]) if def_tax_row is not None else None
        def_label = def_tax_row["concept"] if def_tax_row is not None else None
        if def_tax is None:
            id_def = _flow_fact_at_end(facts, ("IncreaseDecreaseInDeferredIncomeTaxes",), period_end, unit, taxonomy=taxonomy, forms=forms)
            if id_def is not None:
                def_tax = -float(id_def["val"])
                def_label = f"-{id_def['concept']}"
        other_nc = _flow_fact_at_end(facts, ("OtherNoncashIncomeExpense",), period_end, unit, taxonomy=taxonomy, forms=forms)
        other_op = _flow_fact_at_end(facts, ("OtherOperatingActivitiesCashFlowStatement",), period_end, unit, taxonomy=taxonomy, forms=forms)
        other_non_cash = (
            (def_tax or 0.0)
            + (-float(other_nc["val"]) if other_nc is not None else 0.0)
            + (float(other_op["val"]) if other_op is not None else 0.0)
        )
        adj_labels = [item for item in (def_label, f"-{other_nc['concept']}" if other_nc else None, other_op["concept"] if other_op else None) if item]
        sources["other_non_cash_adjustments"] = (
            f"SEC 10-K {' + '.join(adj_labels)} ({period_end})"
            if adj_labels
            else f"SEC 10-K operating cash flow ({period_end}); no separate deferred-tax or other non-cash line filed"
        )
    else:
        da_row = _flow_fact_at_end(
            facts,
            ("AdjustmentsForDepreciationAndAmortisationExpense", "DepreciationAndAmortisationExpense"),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        if da_row is not None:
            da = float(da_row["val"])
            sources["depreciation_amortization"] = f"SEC 20-F {da_row['concept']} ({period_end})"
        else:
            dep = _flow_fact_at_end(facts, ("DepreciationExpense",), period_end, unit, taxonomy=taxonomy, forms=forms)
            amo = _flow_fact_at_end(facts, ("AmortisationExpense",), period_end, unit, taxonomy=taxonomy, forms=forms)
            parts = [row for row in (dep, amo) if row is not None]
            da = sum(float(row["val"]) for row in parts) if parts else None
            if parts:
                sources["depreciation_amortization"] = f"SEC 20-F {' + '.join(row['concept'] for row in parts)} ({period_end})"

        tax_row = _flow_fact_at_end(facts, ("IncomeTaxExpenseContinuingOperations",), period_end, unit, taxonomy=taxonomy, forms=forms)
        pretax_row = _flow_fact_at_end(facts, ("ProfitLossBeforeTax",), period_end, unit, taxonomy=taxonomy, forms=forms)
        int_row = _flow_fact_at_end(facts, ("FinanceCosts", "InterestExpense"), period_end, unit, taxonomy=taxonomy, forms=forms)
        if int_row is not None:
            interest_expense = abs(float(int_row["val"]))
            sources["interest_expense"] = f"SEC 20-F {int_row['concept']} ({period_end})"
        else:
            int_parts = [
                row
                for concept in (
                    "InterestExpenseOnBonds",
                    "InterestExpenseOnBorrowings",
                    "InterestExpenseOnLeaseLiabilities",
                    "InterestExpenseOnOtherFinancialLiabilities",
                )
                if (row := _flow_fact_at_end(facts, (concept,), period_end, unit, taxonomy=taxonomy, forms=forms)) is not None
            ]
            interest_expense = sum(abs(float(row["val"])) for row in int_parts) if int_parts else None
            if int_parts:
                sources["interest_expense"] = f"SEC 20-F {' + '.join(row['concept'] for row in int_parts)} ({period_end})"

        def_tax_row = _flow_fact_at_end(
            facts, ("DeferredTaxExpenseIncome", "DeferredTaxExpenseIncomeRecognisedInProfitOrLoss"),
            period_end, unit, taxonomy=taxonomy, forms=forms,
        )
        other_non_cash = float(def_tax_row["val"]) if def_tax_row is not None else 0.0
        sources["other_non_cash_adjustments"] = (
            f"SEC 20-F {def_tax_row['concept']} ({period_end})"
            if def_tax_row is not None
            else f"SEC 20-F operating cash flow ({period_end}); no separate deferred-tax line filed"
        )

    if interest_expense is None and latest_debt is not None and latest_debt == 0:
        interest_expense = 0.0
        sources["interest_expense"] = f"Verified zero total debt ({period_end})"

    if tax_row is not None and pretax_row is not None and float(pretax_row["val"]) > 0:
        tax_rate = max(0.0, min(0.35, float(tax_row["val"]) / float(pretax_row["val"])))
    else:
        tax_rate = 0.21

    wc_value, wc_concepts = _working_capital_cash_effect(facts, period_end, unit, taxonomy=taxonomy, forms=forms)
    if wc_concepts:
        form_label = "20-F" if taxonomy == "ifrs-full" else "10-K"
        sources["working_capital_change"] = f"SEC {form_label} ({len(wc_concepts)} working-capital rows, {period_end})"

    after_tax_interest = interest_expense * (1 - tax_rate) if interest_expense is not None else None
    return {
        "depreciation_amortization": da,
        "working_capital_change": wc_value,
        "tax_rate": tax_rate,
        "interest_expense": interest_expense,
        "after_tax_interest": after_tax_interest,
        "other_non_cash_adjustments": other_non_cash,
        "sources": sources,
    }


def _growth_inputs_from_facts(facts: dict, revenue: list[float]) -> dict:
    """Compute trailing-12-month or annual growth directly from already-loaded SEC facts."""
    fiscal = revenue[0] / revenue[1] - 1 if len(revenue) >= 2 and revenue[1] > 0 else None
    try:
        from growth_inputs import quarterly_revenue, ttm_growth

        quarters, concept = quarterly_revenue(facts)
        ttm = {**ttm_growth(quarters), "source": "SEC company facts (10-Q/10-K)", "concept": concept}
    except Exception as exc:  # noqa: BLE001
        ttm = {"state": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    if ttm.get("state") == "AVAILABLE":
        selected, basis = ttm["growth"], f"trailing twelve months to {ttm['latest_quarter_end']} vs the twelve months before (SEC filings)"
    elif fiscal is not None:
        selected, basis = fiscal, "latest filed fiscal year vs the year before (trailing twelve months unavailable)"
    else:
        selected, basis = None, "no filed growth available"
    return {"selected_growth": selected, "basis": basis, "ttm": ttm, "fiscal_year_growth": fiscal, "latest_quarter_yoy": None}


def collect_sec_company_data(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    record = _company_record(symbol)
    cik = int(record["cik_str"])
    cik_key = f"CIK{cik:010d}"
    submissions_url = f"https://data.sec.gov/submissions/{cik_key}.json"
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik_key}.json"
    submissions = _fetch(submissions_url, CACHE_DIR / f"{cik_key}-submissions.json")
    facts = _fetch(facts_url, CACHE_DIR / f"{cik_key}-facts.json")
    namespaces = facts.get("facts", {})
    if namespaces.get("us-gaap"):
        taxonomy, framework, forms, concepts = "us-gaap", "US_GAAP", ("10-K",), US_GAAP_CONCEPTS
    elif namespaces.get("ifrs-full"):
        taxonomy, framework, forms, concepts = "ifrs-full", "IFRS", ("20-F",), IFRS_CONCEPTS
    else:
        taxonomy, framework, forms, concepts = "", "UNSUPPORTED", (), {}

    def available_units(metric: str) -> list[str]:
        output = []
        for concept in concepts.get(metric, ()):
            output.extend(namespaces.get(taxonomy, {}).get(concept, {}).get("units", {}).keys())
        return list(dict.fromkeys(output))

    financial_units = available_units("revenue")
    currency = next((item for item in financial_units if item not in {"USD", "shares", "pure"}), None) or ("USD" if "USD" in financial_units or framework == "US_GAAP" else None)
    series: dict[str, list[dict]] = {}
    for metric, metric_concepts in concepts.items():
        unit = "shares" if metric == "shares" else currency or "USD"
        series[metric] = _annual_series(facts, metric_concepts, unit, taxonomy=taxonomy, forms=forms)

    if series.get("shares") and series.get("revenue") and series["shares"][0]["end"] != series["revenue"][0]["end"]:
        series["shares"] = []
    values = {metric: [float(row["val"]) for row in rows] for metric, rows in series.items()}
    revenue = values.get("revenue", [])
    gross_profit = values.get("gross_profit", [])
    operating = values.get("operating_income", [])
    net_income = values.get("net_income", [])
    assets = values.get("assets", [])
    inventory = values.get("inventory", [])
    ocf = values.get("operating_cash_flow", [])
    capex = [abs(value) for value in values.get("capex", [])]
    sbc = values.get("sbc", [])
    cash = values.get("cash", [])
    shares = values.get("shares", [])

    if taxonomy == "us-gaap":
        debt_selection = _select_debt(facts, currency or "USD")
    elif taxonomy == "ifrs-full":
        current = _annual_series(facts, ("CurrentPortionOfLongtermBorrowings", "ShorttermBorrowings"), currency or "USD", taxonomy=taxonomy, forms=forms)
        noncurrent = _annual_series(facts, ("LongtermBorrowings",), currency or "USD", taxonomy=taxonomy, forms=forms)
        if current and noncurrent and current[0]["end"] == noncurrent[0]["end"]:
            debt_selection = {
                "value": float(current[0]["val"]) + float(noncurrent[0]["val"]), "coverage": "COMPLETE",
                "methodology": "ifrs_aligned_current_plus_noncurrent", "selected_concepts": [current[0]["concept"], noncurrent[0]["concept"]],
                "period_end": current[0]["end"], "fiscal_year": current[0].get("fy") or noncurrent[0].get("fy"),
                "filing_date": max(str(current[0].get("filed", "")), str(noncurrent[0].get("filed", ""))),
                "currency": currency, "missing_components": [],
            }
        else:
            debt_selection = {"value": None, "coverage": "PARTIAL" if current or noncurrent else "INSUFFICIENT_DATA", "methodology": "ifrs_components_not_aligned", "selected_concepts": [row[0]["concept"] for row in (current, noncurrent) if row], "period_end": None, "fiscal_year": None, "filing_date": None, "currency": currency, "missing_components": ["aligned current and noncurrent borrowings"]}
    else:
        debt_selection = {"value": None, "coverage": "INSUFFICIENT_DATA", "methodology": "unsupported_taxonomy", "selected_concepts": [], "period_end": None, "fiscal_year": None, "filing_date": None, "currency": currency, "missing_components": ["supported reporting taxonomy"]}

    ocf_by_end = {row["end"]: row for row in series.get("operating_cash_flow", [])}
    capex_by_end = {row["end"]: row for row in series.get("capex", [])}
    cashflow_common_periods = sorted(set(ocf_by_end).intersection(capex_by_end), reverse=True)
    cashflow_period = cashflow_common_periods[0] if cashflow_common_periods else None
    latest_ocf = float(ocf_by_end[cashflow_period]["val"]) if cashflow_period else None
    latest_capex = abs(float(capex_by_end[cashflow_period]["val"])) if cashflow_period else None
    latest_fcf = latest_ocf - latest_capex if latest_ocf is not None and latest_capex is not None else None

    revenue_period = series.get("revenue", [{}])[0].get("end") if series.get("revenue") else None
    operating_period = series.get("operating_income", [{}])[0].get("end") if series.get("operating_income") else None
    reconciled_period = (
        cashflow_period
        if cashflow_period and cashflow_period == revenue_period == operating_period
        else None
    )
    recon = _reconciliation_inputs(
        facts,
        taxonomy=taxonomy,
        unit=currency or "USD",
        forms=forms,
        period_end=reconciled_period,
        latest_debt=debt_selection["value"],
    )

    name = str(submissions.get("name") or record.get("title") or symbol)
    industry = str(submissions.get("sicDescription") or "")
    lower = f"{name} {industry}".lower()
    annual_growth = revenue[0] / revenue[1] - 1 if len(revenue) >= 2 and revenue[1] > 0 else None
    op_margin = operating[0] / revenue[0] if operating and revenue and revenue[0] > 0 else None
    gross_margin = gross_profit[0] / revenue[0] if gross_profit and revenue and revenue[0] > 0 else None
    if " etf" in lower or "exchange traded fund" in lower or ("spdr" in lower and "trust" in lower):
        security_type = "ETF_OR_FUND"
    elif "real estate investment trust" in lower or " reit" in lower:
        security_type = "REIT"
    elif any(term in lower for term in ("blank check", "acquisition corp", "shell company")):
        security_type = "SPAC_OR_SHELL"
    elif "bank" in lower or "financial institution" in lower:
        security_type = "FINANCIAL_INSTITUTION"
    elif not revenue:
        security_type = "INSUFFICIENT_DATA"
    elif symbol == "MU" or any(term in lower for term in ("memory", "steel", "copper", "aluminum", "oil & gas", "petroleum", "commodity", "mining", "semiconductor equipment")):
        security_type = "CYCLICAL_COMPANY"
    elif (
        "software" in lower
        and (gross_margin is None or gross_margin >= 0.45)
        and annual_growth is not None
        and annual_growth >= 0.15
        and latest_fcf is not None
        and latest_fcf > 0
        and (op_margin is None or op_margin < 0.30)
    ):
        security_type = "GROWTH_SOFTWARE_COMPANY"
    elif (op_margin is not None and op_margin < 0) or (latest_fcf is not None and latest_fcf < 0):
        security_type = "PRE_PROFIT_COMPANY"
    else:
        security_type = "MATURE_OPERATING_COMPANY"

    exchanges = submissions.get("exchanges") or []
    facts_diagnostic = _FETCH_DIAGNOSTICS.get(facts_url, {})
    retrieved_at = facts_diagnostic.get("retrieved_at") or dt.datetime.now(dt.timezone.utc).isoformat()
    acquisition_status = SourceStatus(facts_diagnostic.get("source_status", SourceStatus.HISTORICAL_REPORTED.value))
    provider_status = ProviderStatus(facts_diagnostic.get("provider_status", ProviderStatus.OK.value))

    def envelope(metric: str, normalized: str | None = None, transformation: str | None = None) -> dict:
        row = series.get(metric, [None])[0] if series.get(metric) else None
        return EvidenceEnvelope(
            source_id=f"sec:{cik_key}:{row['concept'] if row else metric}", source_name="SEC Company Facts",
            source_url=f"https://data.sec.gov/api/xbrl/companyfacts/{cik_key}.json", source_type="structured_regulatory_data",
            provider_status=provider_status if row else ProviderStatus.MISSING_CONCEPT, retrieved_at=retrieved_at,
            observation_date=row.get("end") if row else None, fiscal_period_start=row.get("start") if row else None,
            fiscal_period_end=row.get("end") if row else None, fiscal_year=row.get("fy") if row else None,
            filing_date=row.get("filed") if row else None, unit=row.get("unit") if row else ("shares" if metric == "shares" else currency),
            currency=None if metric == "shares" else currency, value=float(row["val"]) if row else None,
            raw_concept=row.get("concept") if row else None, normalized_concept=normalized or metric,
            transformation=transformation, coverage_status=CoverageStatus.COMPLETE if row else CoverageStatus.MISSING,
            validation_status=ValidationStatus.VALID if row else ValidationStatus.UNVERIFIED,
            staleness_status=StalenessStatus.HISTORICAL, limitation=None if row else f"No compatible {taxonomy or 'supported'} annual concept was found.",
            entity_identifier=cik_key, source_status=acquisition_status if row else SourceStatus.MISSING,
        ).to_dict()

    evidence_envelopes = {metric: envelope(metric) for metric in series}
    if cashflow_period:
        evidence_envelopes["free_cash_flow"] = EvidenceEnvelope(
            source_id=f"calc:{cik_key}:fcf:{cashflow_period}", source_name="CHAINSTOX SEC normalization", source_type="calculation",
            provider_status=ProviderStatus.OK, retrieved_at=retrieved_at, observation_date=cashflow_period,
            fiscal_period_end=cashflow_period, unit=currency, currency=currency, value=latest_fcf,
            normalized_concept="free_cash_flow", transformation="operating_cash_flow - absolute(capex)",
            coverage_status=CoverageStatus.COMPLETE, validation_status=ValidationStatus.VALID,
            staleness_status=StalenessStatus.HISTORICAL, limitation="Calculated from aligned annual SEC facts; not issuer-defined free cash flow.",
            entity_identifier=cik_key, source_status=SourceStatus.CALCULATED,
        ).to_dict()

    growth_inputs = _growth_inputs_from_facts(facts, revenue)
    shares_row = series.get("shares", [None])[0] if series.get("shares") else None
    shares_period = (
        f"SEC annual diluted/basic shares ({shares_row['concept']}, {shares_row['end']})"
        if shares_row and shares_row["concept"] in FLOW_SHARE_CONCEPTS
        else (f"SEC annual shares ({shares_row['end']})" if shares_row else "Unavailable")
    )
    cash_end = series.get("cash", [{}])[0].get("end") if series.get("cash") else None
    return {
        "ticker": symbol,
        "company": name,
        "provider": "SEC submissions and Company Facts",
        "provider_status": "OK" if framework != "UNSUPPORTED" else "UNSUPPORTED_FRAMEWORK",
        "reporting_framework": framework,
        "reporting_taxonomy": taxonomy or None,
        "security_type": security_type,
        "routing_evidence": [
            f"SEC reporting framework: {framework}",
            f"SIC industry: {industry or 'unavailable'}",
            f"annual revenue periods: {len(revenue)}",
        ],
        "info": {
            "quoteType": "EQUITY",
            "longName": name,
            "exchange": exchanges[0] if exchanges else "",
            "fullExchangeName": exchanges[0] if exchanges else "",
            "currency": currency,
            "financialCurrency": currency,
            "country": "SEC registrant; domicile not inferred from filing venue",
            "sector": "",
            "industry": industry,
            "longBusinessSummary": "",
            "totalRevenue": revenue[0] if revenue else None,
            "totalAssets": assets[0] if assets else None,
            "inventory": inventory[0] if inventory else None,
            "revenueGrowth": growth_inputs.get("selected_growth"),
            "grossMargins": gross_margin,
            "operatingMargins": op_margin,
            "freeCashflow": latest_fcf,
        },
        "income": None,
        "cashflow": None,
        "balance": None,
        "latest_revenue": revenue[0] if revenue else None,
        "latest_operating_income": operating[0] if operating else None,
        "latest_net_income": net_income[0] if net_income else None,
        "latest_ocf": latest_ocf,
        "latest_capex": latest_capex,
        "latest_fcf": latest_fcf,
        "latest_fcff": latest_fcf,
        "sbc": sbc[0] if sbc else None,
        "depreciation_amortization": recon["depreciation_amortization"],
        "working_capital_change": recon["working_capital_change"],
        "other_non_cash_adjustments": recon["other_non_cash_adjustments"],
        "interest_expense": recon["interest_expense"],
        "after_tax_interest": recon["after_tax_interest"],
        "tax_rate": recon["tax_rate"],
        "input_sources": dict(recon["sources"]),
        "growth_inputs": growth_inputs,
        "cash": cash[0] if cash else 0,
        "debt": debt_selection["value"],
        "debt_coverage": debt_selection["coverage"],
        "debt_provenance": debt_selection,
        "shares": shares[0] if shares else None,
        "market_cap": None,
        "price": None,
        "beta": None,
        "currency": currency,
        "revenue_history": revenue,
        "operating_income_history": operating,
        "gross_profit_history": gross_profit,
        "periods": {
            "revenue": revenue_period or "Unavailable",
            "operating_income": operating_period or "Unavailable",
            "fcff": reconciled_period or cashflow_period or "Unavailable",
            "free_cash_flow": cashflow_period or "Unavailable",
            "cash_and_debt": debt_selection.get("period_end") or cash_end or "Unavailable",
            "shares": shares_period,
            "market_price": "Unavailable from SEC Company Facts",
        },
        "as_of": retrieved_at,
        "cik": cik_key,
        "evidence_envelopes": evidence_envelopes,
        "financial_period_alignment": {
            "cashflow_period": cashflow_period,
            "status": "VALID" if cashflow_period else "PERIOD_MISMATCH" if ocf or capex else "MISSING",
            "revenue_period": revenue_period,
            "operating_income_period": operating_period,
        },
    }
