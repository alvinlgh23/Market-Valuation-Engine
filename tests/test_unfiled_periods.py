"""Checklist 9.1: fiscal years listed before the annual report is filed are skipped in all statements."""
import numpy as np
import pandas as pd

import intrinsic_valuation as iv

NEW, FY25, FY24 = pd.Timestamp("2026-10-31"), pd.Timestamp("2025-10-31"), pd.Timestamp("2024-10-31")


def frames():
    income = pd.DataFrame({NEW: [np.nan, np.nan, 1.0], FY25: [28.4, 7.0, 1.0], FY24: [27.2, 6.5, 1.0]},
                          index=["Total Revenue", "Operating Income", "Basic Average Shares"])
    cashflow = pd.DataFrame({NEW: [9.0], FY25: [8.0], FY24: [7.5]}, index=["Operating Cash Flow"])
    balance = pd.DataFrame({NEW: [50.0], FY25: [45.0], FY24: [40.0]}, index=["Total Assets"])
    return income, cashflow, balance


def test_partly_filled_new_year_is_dropped_from_every_statement():
    income, cashflow, balance, dropped = iv.drop_unfiled_periods(*frames())
    assert dropped == ["2026-10-31"]
    for frame in (income, cashflow, balance):
        assert list(frame.columns) == [FY25, FY24]
    assert iv._row(income, "Total Revenue") == [28.4, 27.2]
    assert iv._row(cashflow, "Operating Cash Flow") == [8.0, 7.5]   # aligned with income, not FY2026


def test_without_the_skip_the_guard_returns_no_revenue():
    income, _, _ = frames()
    assert iv._row(income, "Total Revenue") == []


def test_filed_statements_are_unchanged():
    income, cashflow, balance = frames()
    income.loc["Total Revenue", NEW] = 30.0
    out = iv.drop_unfiled_periods(income, cashflow, balance)
    assert out[3] == [] and out[0] is income and list(out[1].columns) == [NEW, FY25, FY24]


def test_missing_operating_cash_flow_also_marks_a_period_unfiled():
    income, cashflow, balance = frames()
    income.loc["Total Revenue", NEW] = 30.0
    cashflow.loc["Operating Cash Flow", NEW] = np.nan
    assert iv.drop_unfiled_periods(income, cashflow, balance)[3] == ["2026-10-31"]


def test_none_frames_pass_through():
    assert iv.drop_unfiled_periods(None, None, None) == (None, None, None, [])
