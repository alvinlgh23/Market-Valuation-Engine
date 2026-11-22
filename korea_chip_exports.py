"""Korean semiconductor exports as a lead for the chip cycle (checklist 10.7).

Korea Customs item-trade data (HS 8541 + 8542, monthly, US dollars) via data.go.kr, the same
endpoint the KOSPI engine uses. Needs DATA_GO_KR_SERVICE_KEY (or KOREA_CUSTOMS_SERVICE_KEY);
without it the result says so instead of guessing. Korean chip exports are a widely watched early
read on memory and foundry demand; this project has not yet validated the lead in its scorecard.
"""
from __future__ import annotations

import datetime as dt
import os
import xml.etree.ElementTree as ET
from typing import Any

ITEMTRADE_URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"
HS_CODES = ("8541", "8542")


def service_key() -> str | None:
    return os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("KOREA_CUSTOMS_SERVICE_KEY")


def latest_month(today: dt.date | None = None) -> dt.date:
    """Previous-month data is published around the 15th; use two months back before the 18th."""
    today = today or dt.date.today()
    back = 1 if today.day >= 18 else 2
    year, month = today.year, today.month - back
    while month <= 0:
        month += 12
        year -= 1
    return dt.date(year, month, 1)


def parse_export_usd(xml_text: str) -> float | None:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode")
    if code and code != "00":
        raise ValueError(f"Korea Customs returned result code {code}")
    values = [item.findtext("expDlr") for item in root.findall(".//item")]
    numbers = [float(str(value).replace(",", "")) for value in values if value and str(value).strip()]
    return sum(numbers) if numbers else None


def month_exports(month: dt.date, key: str, timeout: int = 12) -> float | None:
    import requests
    total = 0.0
    for hs in HS_CODES:
        response = requests.get(ITEMTRADE_URL, params={"serviceKey": key, "strtYymm": month.strftime("%Y%m"), "endYymm": month.strftime("%Y%m"), "hsSgn": hs}, timeout=timeout)
        response.raise_for_status()
        value = parse_export_usd(response.text)
        if value is None:
            return None
        total += value
    return total


def summarise(current: float | None, year_ago: float | None, month: dt.date) -> dict[str, Any]:
    growth = None if current is None or not year_ago else current / year_ago - 1
    return {"status": "AVAILABLE" if growth is not None else "UNAVAILABLE", "month": month.isoformat()[:7],
            "exports_usd": current, "year_ago_usd": year_ago, "yoy": growth,
            "direction": None if growth is None else 1 if growth > 0.05 else -1 if growth < -0.05 else 0,
            "source": "Korea Customs item trade (HS 8541+8542) via data.go.kr",
            "note": "Widely watched early read on chip demand; the lead is not yet validated in this project's scorecard."}


def fetch_korea_chip_exports(today: dt.date | None = None) -> dict[str, Any]:
    key = service_key()
    month = latest_month(today)
    if not key:
        return {"status": "NEEDS_KEY", "month": month.isoformat()[:7],
                "note": "Set DATA_GO_KR_SERVICE_KEY (free at data.go.kr) to read monthly Korean chip exports."}
    year_ago = dt.date(month.year - 1, month.month, 1)
    return summarise(month_exports(month, key), month_exports(year_ago, key), month)
