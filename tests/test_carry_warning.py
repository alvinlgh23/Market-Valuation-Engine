"""Checklist 10.6: yen carry early warning (offline)."""
import datetime as dt

from environment import carry_warning, parse_boj_schedule, us_japan_gap_history

PAGE = """<html><body><h2>2026</h2><table><caption>Table : 2026 Date of MPM Release Schedule Outlook Report</caption>
<tr><td>Jan. 22 (Thurs.), 23 (Fri.)</td><td>Jan. 23 (Fri.)</td><td>Feb. 2 (Mon.)</td></tr>
<tr><td>Apr. 27 (Mon.), 28 (Tues.)</td><td>Apr. 28 (Tues.)</td></tr>
<tr><td>Dec. 17 (Thurs.), 18 (Fri.)</td><td>-</td></tr></table>
<table><caption>Table : 2027 Date of MPM</caption><tr><td>Jan. 21 (Thurs.), 22 (Fri.)</td></tr></table></body></html>"""


def test_schedule_takes_the_decision_day_of_two_day_meetings_only():
    assert parse_boj_schedule(PAGE) == ["2026-01-23", "2026-04-28", "2026-12-18", "2027-01-22"]


GAPS = [("2026-07-01", 2.6), ("2026-08-01", 2.5), ("2026-09-01", 2.4), ("2026-10-01", 2.2)]
TODAY = dt.date(2026, 11, 22)


def test_wide_gap_short_yen_and_near_meeting_is_high():
    warning = carry_warning({"usdjpy_3m": 0.04}, "ACCUMULATING", {"leveraged_net": -40000, "as_of": "2026-11-18"},
                            {"meetings": ["2026-12-18"]}, GAPS, today=TODAY)
    assert warning["level"] == "HIGH"
    assert len(warning["fuel"]) == 3 and len(warning["trigger"]) == 1     # meeting in 26 days is outside 21 days; gap narrowed 0.40
    assert warning["next_boj_meeting"] == "2026-12-18" and warning["days_to_meeting"] == 26


def test_missing_inputs_are_reported_not_assumed():
    warning = carry_warning({}, "STABLE", None, None, [], today=TODAY)
    assert warning["level"] == "UNKNOWN" and warning["complete"] is False
    assert set(warning["missing"]) == {"US-Japan 10Y gap", "CFTC leveraged-fund yen position", "BOJ meeting calendar"}


def test_unwind_under_way_is_high_and_one_fuel_sign_alone_is_low():
    assert carry_warning({"usdjpy_3m": -0.05}, "UNWIND_RISK", None, None, GAPS[:1], today=TODAY)["level"] == "HIGH"
    assert carry_warning({"usdjpy_3m": 0.0}, "STABLE", None, {"meetings": ["2027-03-01"]}, [("2026-10-01", 2.4)], today=TODAY)["level"] == "LOW"


def test_gap_history_reads_the_refreshed_cache():
    history = us_japan_gap_history()
    if history:                     # the cache may be absent on a fresh checkout
        assert all(len(month) == 10 for month, _ in history)
        assert -5 < history[-1][1] < 8


# ---- Checklist 10.8: Fed vs ECB divergence ------------------------------------------------------
from environment import fed_ecb_divergence  # noqa: E402


def test_fed_ecb_gap_and_three_month_change():
    fed = [("2026-07-01", 4.00), ("2026-10-01", 3.75)]
    ecb = [("2026-06-15", 2.00), ("2026-09-20", 2.25)]
    eur = [("2026-07-01", 1.10), ("2026-10-01", 1.155)]
    result = fed_ecb_divergence(fed, ecb, eur)
    assert result["gap_pp"] == 1.5 and result["gap_change_3m_pp"] == -0.5
    assert abs(result["eurusd_3m"] - 0.05) < 1e-9
    assert "narrower by 0.50 pp" in result["text"]
    assert fed_ecb_divergence([], ecb, eur)["status"] == "UNAVAILABLE"
