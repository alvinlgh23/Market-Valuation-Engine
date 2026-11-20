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
)
DEBT_CURRENT_CONCEPTS = (
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "LongTermDebtCurrent",
)
DEBT_NONCURRENT_CONCEPTS = (
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
    "LongTermDebtNoncurrent",
)

US_GAAP_CONCEPTS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "assets": ("Assets",),
    "inventory": ("InventoryNet",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForAdditionsToPropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
    "sbc": ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
    "cash": ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CashAndCashEquivalentsAtCarryingValue"),
    "shares": ("CommonStockSharesOutstanding",),
}

IFRS_CONCEPTS = {
    "revenue": ("Revenue", "RevenueFromContractsWithCustomers"),
    "operating_income": ("ProfitLossFromOperatingActivities",),
    "net_income": ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss"),
    "assets": ("Assets",),
    "inventory": ("Inventories",),
    "operating_cash_flow": ("CashFlowsFromUsedInOperatingActivities",),
    "capex": ("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",),
    "sbc": ("ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets",),
    "cash": ("CashAndCashEquivalents",),
    "shares": ("NumberOfSharesIssuedAndFullyPaid",),
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
    flow_concepts = {concept for mapping in (US_GAAP_CONCEPTS, IFRS_CONCEPTS) for metric, names in mapping.items() if metric in {"revenue", "operating_income", "net_income", "operating_cash_flow", "capex", "sbc"} for concept in names}
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


def _select_debt(facts: dict) -> dict:
    """Select total debt from non-overlapping SEC facts with explicit coverage."""
    total = _latest_fy_fact(facts, DEBT_TOTAL_CONCEPTS)
    current = _latest_fy_fact(facts, DEBT_CURRENT_CONCEPTS)
    noncurrent = _latest_fy_fact(facts, DEBT_NONCURRENT_CONCEPTS)

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

    available = [row for row in (current, noncurrent) if row is not None]
    return {
        "value": None,
        "coverage": "PARTIAL" if available else "INSUFFICIENT_DATA",
        "methodology": "not_reported_as_total",
        "selected_concepts": [row["concept"] for row in available],
        "period_end": available[0]["end"] if available else None,
        "fiscal_year": available[0].get("fy") if available else None,
        "filing_date": available[0].get("filed") if available else None,
        "currency": available[0]["unit"] if available else "USD",
        "missing_components": [
            name
            for name, row in (("current debt", current), ("noncurrent debt", noncurrent))
            if row is None
        ] + (["aligned reporting period"] if current and noncurrent and not aligned else []),
    }


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
        debt_selection = _select_debt(facts)
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
    name = str(submissions.get("name") or record.get("title") or symbol)
    industry = str(submissions.get("sicDescription") or "")
    lower = f"{name} {industry}".lower()
    if " etf" in lower or "exchange traded fund" in lower or ("spdr" in lower and "trust" in lower):
        security_type = "ETF_OR_FUND"
    elif "real estate investment trust" in lower or " reit" in lower:
        security_type = "REIT"
    elif any(term in lower for term in ("blank check", "acquisition corp", "shell company")):
        security_type = "SPAC_OR_SHELL"
    elif "bank" in lower or "financial institution" in lower:
        security_type = "FINANCIAL_INSTITUTION"
    else:
        security_type = "MATURE_OPERATING_COMPANY" if revenue else "INSUFFICIENT_DATA"
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
    return {
        "ticker": symbol,
        "company": name,
        "provider": "SEC submissions and Company Facts",
        "provider_status": "OK" if framework != "UNSUPPORTED" else "UNSUPPORTED_FRAMEWORK",
        "reporting_framework": framework,
        "reporting_taxonomy": taxonomy or None,
        "security_type": security_type,
        "info": {
            "quoteType": "EQUITY",
            "longName": name,
            "exchange": exchanges[0] if exchanges else "",
            "fullExchangeName": exchanges[0] if exchanges else "",
            "currency": currency,
            "country": "SEC registrant; domicile not inferred from filing venue",
            "sector": "",
            "industry": industry,
            "longBusinessSummary": "",
            "totalRevenue": revenue[0] if revenue else None,
            "totalAssets": assets[0] if assets else None,
            "inventory": inventory[0] if inventory else None,
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
        "cash": cash[0] if cash else None,
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
        "periods": {
            "revenue": series.get("revenue", [{}])[0].get("end") if series.get("revenue") else "Unavailable",
            "operating_income": series.get("operating_income", [{}])[0].get("end") if series.get("operating_income") else "Unavailable",
            "free_cash_flow": cashflow_period or "Unavailable",
            "market_price": "Unavailable from SEC Company Facts",
        },
        "as_of": retrieved_at,
        "cik": cik_key,
        "evidence_envelopes": evidence_envelopes,
        "financial_period_alignment": {
            "cashflow_period": cashflow_period,
            "status": "VALID" if cashflow_period else "PERIOD_MISMATCH" if ocf or capex else "MISSING",
            "revenue_period": series.get("revenue", [{}])[0].get("end") if series.get("revenue") else None,
            "operating_income_period": series.get("operating_income", [{}])[0].get("end") if series.get("operating_income") else None,
        },
    }
