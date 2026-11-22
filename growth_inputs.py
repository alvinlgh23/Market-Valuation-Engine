"""Revenue growth inputs (checklist 9.2).

Yahoo's `revenueGrowth` is one quarter against the same quarter a year earlier. For a cyclical or
lumpy company it swings widely (AMAT: +53% for one quarter while the last fiscal year grew 4%), and
the ten-year phase-in (checklist 7.6) used it both as its trigger and as first-year growth.

Trailing-12-month growth
    Sum of the latest four reported quarters divided by the sum of the four before them, minus one.
    Quarters come from SEC company facts (10-Q and 10-K, US-GAAP revenue). A fiscal fourth quarter is
    not filed on its own, so it is the fiscal-year value minus the three quarters inside that year.
    The eight quarters must be consecutive (each 80-120 days, ends 80-120 days apart; 120 allows
    16-week retail quarters) and the newest must end within 200 days, or the reading is not used.

Fallback
    Companies without US-GAAP quarterly filings (for example 20-F filers such as TSM) use the latest
    filed fiscal year's growth from the valuation data. The basis is always stated.

Cache
    SEC files are stored in .cache/sec_quarterly/ (7-day reuse). Other cache folders are never written.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / ".cache" / "sec_quarterly"
REVENUE_CONCEPTS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet")
MAX_AGE_DAYS = 7
QUARTER_DAYS = (80, 120)
STALE_AFTER_DAYS = 200


def _days(start: str, end: str) -> int:
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def _fetch(url: str, path: Path) -> dict:
    from data_sources.sec_company import USER_AGENT

    if path.exists() and dt.datetime.now().timestamp() - path.stat().st_mtime <= MAX_AGE_DAYS * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def sec_facts(ticker: str) -> dict:
    master = _fetch("https://www.sec.gov/files/company_tickers.json", CACHE_DIR / "company_tickers.json")
    record = next((row for row in master.values() if str(row.get("ticker", "")).upper() == ticker.upper()), None)
    if record is None:
        raise LookupError(f"{ticker} is not in the SEC ticker file")
    key = f"CIK{int(record['cik_str']):010d}"
    return _fetch(f"https://data.sec.gov/api/xbrl/companyfacts/{key}.json", CACHE_DIR / f"{key}-facts.json")


def quarterly_revenue(facts: dict) -> tuple[list[dict[str, Any]], str | None]:
    """Discrete quarters (newest first) from the revenue concept that reaches the latest period."""
    taxonomy = facts.get("facts", {}).get("us-gaap", {})
    best: tuple[str, str, list[dict]] | None = None
    for concept in REVENUE_CONCEPTS:
        rows = [row for row in taxonomy.get(concept, {}).get("units", {}).get("USD", [])
                if row.get("form") in ("10-Q", "10-K", "10-Q/A", "10-K/A") and row.get("start") and row.get("end") and isinstance(row.get("val"), (int, float))]
        if not rows:
            continue
        latest = max(row["end"] for row in rows)
        if best is None or latest > best[1]:
            best = (concept, latest, rows)
    if best is None:
        return [], None
    concept, _, rows = best
    latest_filed: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["start"], row["end"])
        if key not in latest_filed or str(row.get("filed", "")) > str(latest_filed[key].get("filed", "")):
            latest_filed[key] = row
    quarters = {end: {"start": start, "end": end, "value": float(row["val"]), "derived": False}
                for (start, end), row in latest_filed.items() if QUARTER_DAYS[0] <= _days(start, end) <= QUARTER_DAYS[1]}
    for (start, end), row in latest_filed.items():
        if not 330 <= _days(start, end) <= 380 or end in quarters:
            continue
        inside = [item for item in quarters.values() if item["start"] >= start and item["end"] < end]
        if len(inside) == 3:
            quarters[end] = {"start": max(item["end"] for item in inside), "end": end, "value": float(row["val"]) - sum(item["value"] for item in inside), "derived": True}
    return sorted(quarters.values(), key=lambda item: item["end"], reverse=True), concept


def ttm_growth(quarters: list[dict[str, Any]], today: dt.date | None = None) -> dict[str, Any]:
    if len(quarters) < 8:
        return {"state": "INSUFFICIENT_HISTORY", "reason": f"{len(quarters)} quarters; eight are needed"}
    window = quarters[:8]
    age = ((today or dt.date.today()) - dt.date.fromisoformat(window[0]["end"])).days
    if age > STALE_AFTER_DAYS:
        return {"state": "STALE", "reason": f"newest filed quarter ends {window[0]['end']} ({age} days ago)"}
    for newer, older in zip(window, window[1:]):
        if not QUARTER_DAYS[0] <= _days(older["end"], newer["end"]) <= QUARTER_DAYS[1]:
            return {"state": "GAP", "reason": f"quarters ending {older['end']} and {newer['end']} are not consecutive"}
    recent, prior = sum(item["value"] for item in window[:4]), sum(item["value"] for item in window[4:])
    if prior <= 0:
        return {"state": "INVALID", "reason": "prior twelve-month revenue is not positive"}
    return {"state": "AVAILABLE", "growth": recent / prior - 1, "ttm_revenue": recent, "prior_ttm_revenue": prior,
            "latest_quarter_end": window[0]["end"], "derived_fourth_quarters": sum(item["derived"] for item in window)}


def revenue_growth_inputs(ticker: str, info: dict | None, revenue_history: list[float] | None) -> dict[str, Any]:
    """All three growth readings with the selected one for the ten-year phase-in."""
    info = info or {}
    history = [value for value in (revenue_history or []) if isinstance(value, (int, float))]
    fiscal = history[0] / history[1] - 1 if len(history) >= 2 and history[1] > 0 else None
    quarter = info.get("revenueGrowth") if isinstance(info.get("revenueGrowth"), (int, float)) else None
    try:
        quarters, concept = quarterly_revenue(sec_facts(ticker))
        ttm = {**ttm_growth(quarters), "source": "SEC company facts (10-Q/10-K)", "concept": concept}
    except Exception as exc:  # noqa: BLE001
        ttm = {"state": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    if ttm.get("state") == "AVAILABLE":
        selected, basis = ttm["growth"], f"trailing twelve months to {ttm['latest_quarter_end']} vs the twelve months before (SEC filings)"
    elif fiscal is not None:
        selected, basis = fiscal, "latest filed fiscal year vs the year before (trailing twelve months unavailable)"
    else:
        selected, basis = None, "no filed growth available"
    return {"selected_growth": selected, "basis": basis, "ttm": ttm, "fiscal_year_growth": fiscal, "latest_quarter_yoy": quarter}
