"""Checklist 10.7: Korean chip exports lead (offline)."""
import datetime as dt

import pytest

from environment import semis_cycle
from korea_chip_exports import fetch_korea_chip_exports, latest_month, parse_export_usd, summarise

XML = "<response><header><resultCode>00</resultCode></header><body><items><item><expDlr>1,200</expDlr></item><item><expDlr>300</expDlr></item></items></body></response>"


def test_parse_and_summarise():
    assert parse_export_usd(XML) == 1500
    with pytest.raises(ValueError):
        parse_export_usd("<response><header><resultCode>30</resultCode></header></response>")
    summary = summarise(1500.0, 1000.0, dt.date(2026, 10, 1))
    assert summary["yoy"] == pytest.approx(0.5) and summary["direction"] == 1 and summary["month"] == "2026-10"


def test_latest_month_waits_for_publication():
    assert latest_month(dt.date(2026, 11, 22)) == dt.date(2026, 10, 1)
    assert latest_month(dt.date(2026, 11, 10)) == dt.date(2026, 9, 1)
    assert latest_month(dt.date(2026, 1, 5)) == dt.date(2025, 11, 1)


def test_without_a_key_it_says_so(monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    monkeypatch.delenv("KOREA_CUSTOMS_SERVICE_KEY", raising=False)
    assert fetch_korea_chip_exports(dt.date(2026, 11, 22))["status"] == "NEEDS_KEY"


def test_semis_factor_carries_the_lead():
    kospi = {"sweep": {"results": [{"key": "tech", "detail": {"history": []}}]}}
    lead = summarise(1500.0, 1000.0, dt.date(2026, 10, 1))
    factor = semis_cycle(kospi, lead)
    assert factor["readings"]["leading_exports"]["yoy"] == pytest.approx(0.5)
    assert any("Korean chip exports +50.0%" in note for note in factor["notes"])
