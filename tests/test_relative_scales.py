"""Checklist 7.3: relative quality and valuation readings."""
import datetime as dt

import numpy as np
import pandas as pd

import relative_scales as rs


def test_peer_percentiles_need_five_names():
    rows = [{"ticker": f"P{i}", "score": 50 + i, "rev_growth": 0.1 * i} for i in range(6)]
    result = rs.peer_quality_percentiles("P5", rows)
    assert result["quality_percentile"] == 1.0 and result["state"] == "AVAILABLE"
    thin = rs.peer_quality_percentiles("P2", rows[:3])
    assert thin["quality_percentile"] is None and thin["state"] == "INSUFFICIENT_SAMPLE"
    assert rs.peer_quality_percentiles("ZZZ", rows)["state"] == "UNAVAILABLE"


def test_price_to_sales_uses_only_public_revenue():
    days = pd.bdate_range("2022-01-03", periods=900)
    close = pd.Series(np.linspace(10, 30, 900), index=days)
    revenue = {dt.date(2021, 12, 31): 100.0, dt.date(2022, 12, 31): 200.0, dt.date(2023, 12, 31): 300.0, dt.date(2024, 12, 31): 400.0}
    history = dict(rs.price_to_sales_history(close, revenue, shares=10))
    assert "2022-03-01" not in history                                                   # FY2021 public only from 2022-03-16
    assert history["2022-04-01"] == close[pd.Timestamp("2022-04-01")] * 10 / 100.0
    assert history["2023-03-01"] == close[pd.Timestamp("2023-03-01")] * 10 / 100.0   # FY2022 not yet public on 1 March
    assert history["2023-04-03"] == close[pd.Timestamp("2023-04-03")] * 10 / 200.0
    result = rs.valuation_percentile("X", close, revenue, 10)
    assert result["state"] == "AVAILABLE" and 0 <= result["percentile"] <= 1
    assert rs.valuation_percentile("X", close, dict(list(revenue.items())[:2]), 10)["state"] == "INSUFFICIENT_HISTORY"
