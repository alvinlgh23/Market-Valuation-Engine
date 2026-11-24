"""Operating signals from SEC filings, by company type (checklist 18.22).

Standard XBRL fields only (what every filer tags the same way): remaining performance obligations
(order backlog), deferred revenue (customer prepayments), inventory, receivables, deposits, loans,
capital spending and R&D. Same-store sales, book-to-bill and capacity use are not standard fields and
are not read here.

Rule (owner-approved 2026-11-24): each metric's change from a year earlier is compared with sales
growth over the same span. A gap of more than 10 points is a signal:
- backlog, prepayments, deposits, loans growing faster than sales: demand building (supportive);
  slower: demand easing (against)
- inventory, receivables growing faster than sales: strain (against); slower: easing (supportive)
- capital spending, R&D growing faster than sales: heavy investment (mixed, not good or bad)
The constraint is the largest strain; with none, the filings show no operating strain.
Missing fields are reported as missing, never as zero.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

GAP = 0.10
YEAR_TOLERANCE = 45

# (key, label, concepts, kind, direction): kind "instant" (balance) or "annual" (fiscal-year flow).
METRICS = {
    "backlog": ("Order backlog (RPO)", ("RevenueRemainingPerformanceObligation",), "instant", "demand"),
    "prepayments": ("Customer prepayments", ("ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"), "instant", "demand"),
    "inventory": ("Inventory", ("InventoryNet",), "instant", "strain"),
    "receivables": ("Receivables", ("AccountsReceivableNetCurrent",), "instant", "strain"),
    "deposits": ("Deposits", ("Deposits",), "instant", "demand"),
    "loans": ("Loans", ("LoansAndLeasesReceivableNetReportedAmount", "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"), "instant", "demand"),
    "capex": ("Capital spending", ("PaymentsToAcquirePropertyPlantAndEquipment",), "annual", "investment"),
    "rnd": ("R&D", ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"), "annual", "investment"),
}
BY_TYPE = {
    "ENTERPRISE_AI_SOFTWARE": ("backlog", "prepayments", "receivables"),
    "TRADITIONAL_SAAS": ("backlog", "prepayments", "receivables"),
    "HYPERSCALER_CLOUD_PLATFORM": ("backlog", "capex", "receivables"),
    "FABLESS_SEMICONDUCTOR": ("inventory", "receivables", "rnd"),
    "SEMICONDUCTOR_FOUNDRY": ("inventory", "capex", "receivables"),
    "SEMICONDUCTOR_EQUIPMENT": ("backlog", "inventory", "receivables"),
    "CONSUMER_PLATFORM": ("capex", "receivables", "rnd"),
    "RETAIL_PHYSICAL_NETWORK": ("inventory", "capex"),
    "BANK": ("deposits", "loans"),
    "INDUSTRIAL": ("backlog", "inventory", "receivables"),
    "PHARMA_BIOTECH": ("rnd", "inventory", "receivables"),
    "COMMODITY_PRODUCER": ("capex", "inventory"),
    "PAYMENT_NETWORK": ("receivables", "capex"),
    "MARKETPLACE_PLATFORM": ("receivables", "capex"),
    "UTILITY_INFRASTRUCTURE": ("capex", "receivables"),
}
DEFAULT_SET = ("backlog", "inventory", "receivables", "capex")
REVENUE = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet")
FORMS = ("10-Q", "10-K", "10-Q/A", "10-K/A")


def _rows(facts: dict, concepts: tuple[str, ...]) -> tuple[list[dict], str | None]:
    """Rows of the concept with the most recent filing; companies switch tags, and an abandoned tag
    keeps its old values."""
    gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    best: tuple[str, str, list[dict]] | None = None
    for concept in concepts:
        rows = [row for row in ((gaap.get(concept) or {}).get("units") or {}).get("USD", [])
                if row.get("form") in FORMS and isinstance(row.get("val"), (int, float)) and row.get("end")]
        if rows:
            latest = max(row["end"] for row in rows)
            if best is None or latest > best[0]:
                best = (latest, concept, rows)
    return (best[2], best[1]) if best else ([], None)


STALE_DAYS = {"instant": 400, "annual": 560}


def _days(start: str, end: str) -> int:
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def _latest_by_period(rows: list[dict], key) -> dict:
    """One value per period, from the most recent filing."""
    output: dict = {}
    for row in rows:
        period = key(row)
        if period not in output or str(row.get("filed", "")) > str(output[period].get("filed", "")):
            output[period] = row
    return output


def instant_pair(rows: list[dict]) -> tuple[str, float, float] | None:
    """Latest balance and the balance about a year earlier: (date, now, year ago)."""
    points = {end: float(row["val"]) for end, row in _latest_by_period([r for r in rows if not r.get("start")], lambda r: r["end"]).items()}
    if not points:
        return None
    latest = max(points)
    target = dt.date.fromisoformat(latest) - dt.timedelta(days=365)
    earlier = [day for day in points if abs((dt.date.fromisoformat(day) - target).days) <= YEAR_TOLERANCE]
    if not earlier:
        return None
    prior = min(earlier, key=lambda day: abs((dt.date.fromisoformat(day) - target).days))
    return latest, points[latest], points[prior]


def annual_pair(rows: list[dict]) -> tuple[str, float, float] | None:
    """Latest fiscal-year total and the one before it: (year end, now, year before)."""
    years = _latest_by_period([r for r in rows if r.get("start") and 330 <= _days(r["start"], r["end"]) <= 380], lambda r: r["end"])
    ends = sorted(years)
    for latest in reversed(ends):
        target = dt.date.fromisoformat(latest) - dt.timedelta(days=365)
        prior = [day for day in ends if abs((dt.date.fromisoformat(day) - target).days) <= YEAR_TOLERANCE]
        if prior:
            return latest, float(years[latest]["val"]), float(years[prior[0]]["val"])
    return None


def quarter_sales_growth(rows: list[dict], around: str) -> float | None:
    """Sales in the quarter ending near `around` against the same quarter a year earlier (fiscal quarters of
    12 to 16 weeks)."""
    quarters = _latest_by_period([r for r in rows if r.get("start") and 80 <= _days(r["start"], r["end"]) <= 120], lambda r: r["end"])
    def near(day: dt.date):
        hits = [end for end in quarters if abs((dt.date.fromisoformat(end) - day).days) <= 20]
        return float(quarters[hits[0]]["val"]) if hits else None
    now, ago = near(dt.date.fromisoformat(around)), near(dt.date.fromisoformat(around) - dt.timedelta(days=365))
    return now / ago - 1 if now and ago and ago > 0 else None


def annual_sales_growth(rows: list[dict], year_end: str) -> float | None:
    pair = annual_pair([r for r in rows if abs((dt.date.fromisoformat(r["end"]) - dt.date.fromisoformat(year_end)).days) <= 20
                        or abs((dt.date.fromisoformat(r["end"]) - dt.date.fromisoformat(year_end) + dt.timedelta(days=365)).days) <= YEAR_TOLERANCE])
    return pair[1] / pair[2] - 1 if pair and pair[2] > 0 else None


def reading(direction: str, gap: float) -> tuple[str, str]:
    if direction == "demand":
        return ("Demand building", "supportive") if gap > GAP else ("Demand easing", "against") if gap < -GAP else ("In line with sales", "mixed")
    if direction == "strain":
        return ("Building up faster than sales", "against") if gap > GAP else ("Easing", "supportive") if gap < -GAP else ("In line with sales", "mixed")
    return ("Heavy investment", "mixed") if gap > GAP else ("Investment slowing", "mixed") if gap < -GAP else ("In line with sales", "mixed")


def operating_signals(facts: dict, archetype: str | None, today: dt.date | None = None) -> dict[str, Any]:
    revenue, revenue_concept = _rows(facts, REVENUE)
    keys = BY_TYPE.get(archetype or "", DEFAULT_SET)
    signals, missing = [], []
    for key in keys:
        label, concepts, kind, direction = METRICS[key]
        rows, concept = _rows(facts, concepts)
        pair = (instant_pair(rows) if kind == "instant" else annual_pair(rows)) if rows else None
        if pair is None or pair[2] <= 0:
            missing.append(label)
            continue
        if ((today or dt.date.today()) - dt.date.fromisoformat(pair[0])).days > STALE_DAYS[kind]:
            missing.append(f"{label} (last filed {pair[0]})")
            continue
        day, now, ago = pair
        growth = now / ago - 1
        sales = (quarter_sales_growth(revenue, day) if kind == "instant" else annual_sales_growth(revenue, day)) if revenue else None
        if sales is None and kind == "instant" and revenue:
            sales = annual_sales_growth(revenue, day)   # a fiscal year-end balance: the fourth quarter is often filed only in the 10-K
        if key in ("deposits", "loans"):
            sales = None                     # banks: compared with each other below, not with sales
        gap = growth - sales if sales is not None else None
        text, tone = reading(direction, gap) if gap is not None else ("No sales comparison", "unknown")
        signals.append({"key": key, "label": label, "value": now, "change": growth, "sales_change": sales, "gap": gap,
                        "reading": text, "tone": tone, "as_of": day, "concept": concept, "basis": "fiscal year" if kind == "annual" else "balance"})
    bank = {item["key"]: item for item in signals if item["key"] in ("deposits", "loans")}
    if len(bank) == 2:
        gap = bank["loans"]["change"] - bank["deposits"]["change"]
        bank["loans"].update({"gap": gap, "reading": "Lending faster than deposits grow" if gap > GAP else "Deposits outgrowing lending" if gap < -GAP else "Lending in line with deposits",
                              "tone": "against" if gap > GAP else "mixed"})
        bank["deposits"].update({"reading": "Deposits growing" if bank["deposits"]["change"] > 0 else "Deposits shrinking", "tone": "supportive" if bank["deposits"]["change"] > 0 else "against"})
    strains = [item for item in signals if item["tone"] == "against" and item.get("gap") is not None]
    constraint = max(strains, key=lambda item: abs(item["gap"])) if strains else None
    if constraint:
        summary = (f"{constraint['label']}: {constraint['reading'].lower()} ({constraint['change']:+.0%} vs sales {constraint['sales_change']:+.0%} a year earlier)"
                   if constraint.get("sales_change") is not None else f"{constraint['label']}: {constraint['reading'].lower()}")
    elif signals:
        summary = "No operating strain in the filed figures."
    else:
        summary = "No standard operating figures in this company's filings."
    return {"status": "AVAILABLE" if signals else "UNAVAILABLE", "archetype": archetype, "signals": signals, "missing": missing,
            "constraint": constraint, "summary": summary, "revenue_concept": revenue_concept,
            "rule": "Each figure's change from a year earlier against sales growth over the same span; more than 10 points apart is a signal.",
            "source": "SEC XBRL company facts (10-Q / 10-K)"}


def collect(ticker: str, archetype: str | None) -> dict[str, Any]:
    try:
        from growth_inputs import sec_facts
        facts = sec_facts(ticker)
    except Exception as exc:  # noqa: BLE001
        return {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}", "signals": [], "summary": "SEC filings unavailable for this company."}
    return operating_signals(facts, archetype)
