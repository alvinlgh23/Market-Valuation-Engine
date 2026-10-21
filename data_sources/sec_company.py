"""SEC structured-company fallback for identity and annual financial facts."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "sec_company"
USER_AGENT = os.environ.get("CHAINSTOX_SEC_USER_AGENT", "CHAINSTOX deterministic research contact@example.com")

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


def _fetch(url: str, cache_path: Path, max_age_days: int = 7) -> dict:
    if cache_path.exists():
        age = dt.datetime.now().timestamp() - cache_path.stat().st_mtime
        if age <= max_age_days * 86400:
            return json.loads(cache_path.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    except Exception:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        raise


def _company_record(ticker: str) -> dict:
    master = _fetch("https://www.sec.gov/files/company_tickers.json", CACHE_DIR / "company_tickers.json")
    symbol = ticker.upper()
    for row in master.values():
        if str(row.get("ticker", "")).upper() == symbol:
            return row
    raise LookupError(f"{symbol} is not present in the SEC company ticker file.")


def _annual_values(facts: dict, concepts: tuple[str, ...], unit: str = "USD") -> list[float]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    observations = []
    for concept in concepts:
        units = us_gaap.get(concept, {}).get("units", {})
        rows = units.get(unit, [])
        for row in rows:
            if row.get("form") == "10-K" and row.get("fp") == "FY" and isinstance(row.get("val"), (int, float)):
                observations.append(row)
        if observations:
            break
    by_end = {}
    for row in observations:
        end = row.get("end")
        if end and (end not in by_end or str(row.get("filed", "")) > str(by_end[end].get("filed", ""))):
            by_end[end] = row
    return [float(row["val"]) for _, row in sorted(by_end.items(), reverse=True)[:5]]


def _latest_fy_fact(facts: dict, concepts: tuple[str, ...], unit: str = "USD") -> dict | None:
    """Select the latest annual fact without mixing concepts or reporting periods."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        rows = us_gaap.get(concept, {}).get("units", {}).get(unit, [])
        candidates = [
            {**row, "concept": concept, "unit": unit}
            for row in rows
            if row.get("form") == "10-K"
            and row.get("fp") == "FY"
            and row.get("end")
            and isinstance(row.get("val"), (int, float))
        ]
        if candidates:
            return max(candidates, key=lambda row: (str(row.get("end")), str(row.get("filed", ""))))
    return None


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
    submissions = _fetch(f"https://data.sec.gov/submissions/{cik_key}.json", CACHE_DIR / f"{cik_key}-submissions.json")
    facts = _fetch(f"https://data.sec.gov/api/xbrl/companyfacts/{cik_key}.json", CACHE_DIR / f"{cik_key}-facts.json")
    revenue = _annual_values(facts, ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"))
    operating = _annual_values(facts, ("OperatingIncomeLoss",))
    net_income = _annual_values(facts, ("NetIncomeLoss", "ProfitLoss"))
    assets = _annual_values(facts, ("Assets",))
    inventory = _annual_values(facts, ("InventoryNet",))
    ocf = _annual_values(facts, ("NetCashProvidedByUsedInOperatingActivities",))
    capex = [abs(value) for value in _annual_values(facts, ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForAdditionsToPropertyPlantAndEquipment"))]
    sbc = _annual_values(facts, ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"))
    cash = _annual_values(facts, ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CashAndCashEquivalentsAtCarryingValue"))
    debt_selection = _select_debt(facts)
    shares = _annual_values(facts, ("CommonStockSharesOutstanding",), "shares")
    latest_ocf = ocf[0] if ocf else None
    latest_capex = capex[0] if capex else None
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
    return {
        "ticker": symbol,
        "company": name,
        "provider": "SEC submissions and Company Facts",
        "security_type": security_type,
        "info": {
            "quoteType": "EQUITY",
            "longName": name,
            "exchange": exchanges[0] if exchanges else "",
            "fullExchangeName": exchanges[0] if exchanges else "",
            "currency": "USD",
            "country": "United States / SEC registrant",
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
        "currency": "USD",
        "revenue_history": revenue,
        "operating_income_history": operating,
        "periods": {
            "revenue": "Latest SEC annual filing periods",
            "operating_income": "Latest SEC annual filing periods",
            "free_cash_flow": "Calculated from latest SEC annual operating cash flow and capex",
            "market_price": "Unavailable from SEC Company Facts",
        },
        "as_of": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cik": cik_key,
    }
