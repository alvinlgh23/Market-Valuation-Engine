"""Who carries S&P 500 profits, and is the market following them (checklists 15.2, 15.3).

Method (owner-approved 2026-11-24):

- Universe: current S&P 500 members from Wikipedia's list (GICS sector), cached for a week.
  Each GICS sector maps to its SPDR sector ETF.
- Profit: Yahoo "Normalized Income" (net income without unusual items) for each company's own
  fiscal quarters, so non-December fiscal years and one-off gains do not distort the sum.
- Period: each company's latest reported quarter against the same quarter a year earlier
  (within 20 days). Yahoo keeps only 5-7 quarters, so this is a quarter-on-year-ago reading,
  not four full quarters.
- Market driver: the S&P 500's move over the same year is split into profit growth and the
  change in the price paid for those profits (P/E). Profits explain 60% or more of the move:
  profit-led; 40% or less: story-led; between: mixed. When price and profits move in opposite
  directions the multiple did all the moving: story-led.

Missing data never becomes zero: a company without both quarters is left out and counted.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / ".cache" / "market_earnings"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
USER_AGENT = "chainstox-research/1.0"
SECTOR_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Health Care": "XLV", "Consumer Discretionary": "XLY",
              "Consumer Staples": "XLP", "Energy": "XLE", "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
              "Real Estate": "XLRE", "Communication Services": "XLC"}
YEAR_AGO_DAYS, YEAR_AGO_TOLERANCE = 365, 20
PROFIT_LED, STORY_LED = 0.6, 0.4


# ---- pure analysis ---------------------------------------------------------------------------
def year_ago_pair(series: dict[str, float | None]) -> tuple[str, float, str, float] | None:
    """Latest quarter with a value and the quarter about a year before it, or None."""
    points = sorted((dt.date.fromisoformat(day), value) for day, value in series.items()
                    if value is not None and isinstance(value, (int, float)) and math.isfinite(value))
    if not points:
        return None
    latest_day, latest = points[-1]
    earlier = [(day, value) for day, value in points if abs((latest_day - day).days - YEAR_AGO_DAYS) <= YEAR_AGO_TOLERANCE]
    if not earlier:
        return None
    prior_day, prior = earlier[-1]
    return latest_day.isoformat(), latest, prior_day.isoformat(), prior


def profit_breakdown(members: list[dict[str, Any]], incomes: dict[str, dict[str, float | None]], top: int = 10) -> dict[str, Any]:
    """Aggregate profit growth, each sector's share of it, and how many companies carry it."""
    rows, missing = [], []
    for member in members:
        pair = year_ago_pair(incomes.get(member["symbol"]) or {})
        if pair is None:
            missing.append(member["symbol"])
            continue
        quarter, now, prior_quarter, prior = pair
        rows.append({**member, "quarter": quarter, "prior_quarter": prior_quarter, "profit": now, "profit_year_ago": prior, "change": now - prior})
    if not rows:
        return {"status": "UNAVAILABLE", "reason": "No company had both quarters.", "companies": 0, "missing": missing}
    total, total_prior = sum(row["profit"] for row in rows), sum(row["profit_year_ago"] for row in rows)
    growth = total / total_prior - 1 if total_prior > 0 else None
    change = total - total_prior
    sectors: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = sectors.setdefault(row["sector"], {"sector": row["sector"], "etf": SECTOR_ETF.get(row["sector"]), "profit": 0.0, "profit_year_ago": 0.0, "companies": 0})
        item["profit"] += row["profit"]; item["profit_year_ago"] += row["profit_year_ago"]; item["companies"] += 1
    for item in sectors.values():
        item["growth"] = item["profit"] / item["profit_year_ago"] - 1 if item["profit_year_ago"] > 0 else None
        item["share_of_profit"] = item["profit"] / total if total > 0 else None
        item["contribution_pp"] = (item["profit"] - item["profit_year_ago"]) / total_prior if total_prior > 0 else None
        item["share_of_growth"] = (item["profit"] - item["profit_year_ago"]) / change if change > 0 else None
    ranked = sorted(rows, key=lambda row: row["change"], reverse=True)
    carriers, running = [], 0.0
    k50 = k80 = None
    if change > 0:
        for index, row in enumerate(ranked, 1):
            running += row["change"]
            if k50 is None and running >= 0.5 * change:
                k50 = index
            if k80 is None and running >= 0.8 * change:
                k80 = index
                break
    for row in ranked[:top]:
        carriers.append({"symbol": row["symbol"], "name": row["name"], "sector": row["sector"], "etf": SECTOR_ETF.get(row["sector"]),
                         "change": row["change"], "share_of_growth": row["change"] / change if change > 0 else None, "quarter": row["quarter"]})
    biggest = sorted(rows, key=lambda row: row["profit"], reverse=True)[:10]
    quarters = sorted(row["quarter"] for row in rows)
    return {
        "status": "AVAILABLE", "companies": len(rows), "members": len(members), "missing": missing,
        "quarters": {"earliest": quarters[0], "latest": quarters[-1], "median": quarters[len(quarters) // 2]},
        "profit": total, "profit_year_ago": total_prior, "growth": growth,
        "companies_growing": sum(row["change"] > 0 for row in rows),
        "sectors": sorted(sectors.values(), key=lambda item: item["contribution_pp"] or 0, reverse=True),
        "carriers": carriers, "carriers_for_half": k50, "carriers_for_80pct": k80,
        "top10_profit_share": sum(row["profit"] for row in biggest) / total if total > 0 else None,
        "top10_by_profit": [row["symbol"] for row in biggest],
    }


def market_driver(index_change: float | None, profit_growth: float | None) -> dict[str, Any]:
    """Split the index move into profit growth and the change in the multiple (checklist 15.3)."""
    if index_change is None or profit_growth is None or index_change <= -1 or profit_growth <= -1:
        return {"state": "UNAVAILABLE", "label": "Not enough data"}
    multiple = (1 + index_change) / (1 + profit_growth) - 1
    move, profit = math.log(1 + index_change), math.log(1 + profit_growth)
    share = profit / move if move != 0 else None
    if share is None or share < 0:
        state = "STORY_LED"   # price and profits moved in opposite directions: the multiple did all of it
    elif share >= PROFIT_LED:
        state = "PROFIT_LED"
    elif share <= STORY_LED:
        state = "STORY_LED"
    else:
        state = "MIXED"
    labels = {"PROFIT_LED": "Profit-led", "STORY_LED": "Story-led", "MIXED": "Mixed"}
    if state == "PROFIT_LED" and multiple < 0:
        plain = "Prices are following profits: profits grew faster than prices, so investors now pay less for each dollar of profit."
    elif state == "PROFIT_LED":
        plain = "Prices are following profits: most of the rise came from profit growth."
    elif state == "STORY_LED" and index_change > 0:
        plain = "Prices rose faster than profits: investors are paying more for each dollar of profit, a bet on the story."
    elif state == "STORY_LED":
        plain = "Prices moved against profits: the change came from what investors are willing to pay, not from profits."
    else:
        plain = "Prices moved with both profits and a change in what investors pay for them."
    return {"state": state, "label": labels[state], "index_change": index_change, "profit_growth": profit_growth,
            "multiple_change": multiple, "profit_share_of_move": share, "plain": plain,
            "rule": "Profits explain 60% or more of the index move: profit-led; 40% or less: story-led; in between: mixed. "
                    "Price and profits moving in opposite directions: story-led."}


# ---- data (network, cached under .cache/market_earnings) ---------------------------------------
def _read_cache(name: str, max_age_days: float) -> Any | None:
    path = CACHE_DIR / name
    if path.exists() and (dt.datetime.now().timestamp() - path.stat().st_mtime) / 86400 <= max_age_days:
        try:
            return json.loads(path.read_text())
        except ValueError:
            return None
    return None


def _write_cache(name: str, payload: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / name
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, default=str))
    temporary.replace(target)


def parse_members(html: str) -> list[dict[str, Any]]:
    import pandas as pd
    table = pd.read_html(io.StringIO(html))[0]
    seen, members = set(), []
    for _, row in table.iterrows():
        cik = int(row["CIK"])
        if cik in seen:          # one company, two share classes (GOOGL/GOOG): count it once
            continue
        seen.add(cik)
        members.append({"symbol": str(row["Symbol"]), "name": str(row["Security"]), "sector": str(row["GICS Sector"]), "cik": cik})
    return members


def load_members(refresh: bool = False) -> list[dict[str, Any]]:
    cached = None if refresh else _read_cache("members.json", 7)
    if cached:
        return cached
    html = urlopen(Request(WIKI_URL, headers={"User-Agent": USER_AGENT}), timeout=60).read().decode()
    members = parse_members(html)
    _write_cache("members.json", members)
    return members


def _normalized_income(symbol: str) -> tuple[str, dict[str, float | None]]:
    import yfinance as yf
    try:
        frame = yf.Ticker(symbol.replace(".", "-")).quarterly_income_stmt
        if frame is None or "Normalized Income" not in frame.index:
            return symbol, {}
        return symbol, {str(day.date()): (None if value != value else float(value)) for day, value in frame.loc["Normalized Income"].items()}
    except Exception:  # noqa: BLE001
        return symbol, {}


def load_incomes(members: list[dict[str, Any]], today: dt.date, refresh: bool = False) -> dict[str, dict[str, float | None]]:
    name = f"normalized-{today.isoformat()}.json"
    cached = None if refresh else _read_cache(name, 1.5)
    if cached:
        return cached
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        with ThreadPoolExecutor(8) as pool:
            incomes = dict(pool.map(_normalized_income, [member["symbol"] for member in members]))
    _write_cache(name, incomes)
    return incomes


def index_change(start: str, end: str) -> dict[str, Any]:
    import yfinance as yf
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        closes = yf.Ticker("^GSPC").history(start=(dt.date.fromisoformat(start) - dt.timedelta(days=10)).isoformat())["Close"]
    closes.index = closes.index.tz_localize(None)
    first, last = closes[:start], closes[:end]
    if first.empty or last.empty:
        return {"change": None}
    latest = closes.iloc[-1]
    return {"change": float(last.iloc[-1] / first.iloc[-1] - 1), "start": start, "end": end, "since_end": float(latest / last.iloc[-1] - 1),
            "latest_date": str(closes.index[-1].date())}


def build(today: dt.date | None = None, refresh: bool = False) -> dict[str, Any]:
    today = today or dt.date.today()
    try:
        members = load_members(refresh)
        incomes = load_incomes(members, today, refresh)
    except Exception as exc:  # noqa: BLE001
        return {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}
    breakdown = profit_breakdown(members, incomes)
    if breakdown["status"] != "AVAILABLE":
        return breakdown
    end = breakdown["quarters"]["median"]
    start = (dt.date.fromisoformat(end) - dt.timedelta(days=YEAR_AGO_DAYS)).isoformat()
    try:
        move = index_change(start, end)
    except Exception as exc:  # noqa: BLE001
        move = {"change": None, "error": f"{type(exc).__name__}: {exc}"}
    return {**breakdown, "index": move, "driver": market_driver(move.get("change"), breakdown["growth"]), "as_of": today.isoformat(),
            "source": "S&P 500 members: Wikipedia; profits: Yahoo Finance normalized income; index: Yahoo ^GSPC",
            "method": "Each company's latest reported quarter against the same quarter a year earlier."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Refetch members and profits even if today's cache exists.")
    args = parser.parse_args(argv)
    result = build(refresh=args.refresh)
    if args.json:
        print(json.dumps(result, default=str))
    else:
        print(json.dumps({key: result.get(key) for key in ("status", "companies", "growth", "driver", "carriers_for_half")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
