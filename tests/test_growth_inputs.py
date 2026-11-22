"""Checklist 9.2: trailing-12-month growth from SEC quarters, and the parallel phase-in candidate."""
import datetime as dt
from unittest.mock import patch

import growth_inputs as gi
import intrinsic_valuation as iv
from test_intrinsic_valuation import fixture_data, fixture_rates

TODAY = dt.date(2026, 11, 22)


def q(start, end, val, form="10-Q", filed="2026-11-01"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


def facts(rows, concept="Revenues"):
    return {"facts": {"us-gaap": {concept: {"units": {"USD": rows}}}}}


QUARTERS = [("2024-10-01", "2024-12-31"), ("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"), ("2025-07-01", "2025-09-30"),
            ("2025-10-01", "2025-12-31"), ("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-30"), ("2026-07-01", "2026-09-30")]


def test_ttm_is_latest_four_quarters_over_the_four_before():
    rows = [q(start, end, 100.0 + 10 * index) for index, (start, end) in enumerate(QUARTERS)]
    quarters, concept = gi.quarterly_revenue(facts(rows))
    result = gi.ttm_growth(quarters, today=TODAY)
    assert concept == "Revenues" and result["state"] == "AVAILABLE"
    assert abs(result["growth"] - ((160 + 170 + 140 + 150) / (100 + 110 + 120 + 130) - 1)) < 1e-12
    assert result["latest_quarter_end"] == "2026-09-30"


def test_fourth_quarter_is_derived_from_the_fiscal_year():
    rows = [q(start, end, 100.0) for start, end in QUARTERS if end not in ("2024-12-31", "2025-12-31")]
    rows += [q("2025-01-01", "2025-12-31", 450.0, form="10-K"), q("2024-01-01", "2024-12-31", 400.0, form="10-K"),
             q("2024-01-01", "2024-03-31", 100.0), q("2024-04-01", "2024-06-30", 100.0), q("2024-07-01", "2024-09-30", 100.0)]
    quarters, _ = gi.quarterly_revenue(facts(rows))
    by_end = {item["end"]: item for item in quarters}
    assert by_end["2025-12-31"]["derived"] and by_end["2025-12-31"]["value"] == 150.0
    assert by_end["2024-12-31"]["value"] == 100.0


def test_latest_filing_wins_for_a_restated_quarter():
    rows = [q(start, end, 100.0) for start, end in QUARTERS] + [q("2026-07-01", "2026-09-30", 140.0, filed="2026-11-20")]
    quarters, _ = gi.quarterly_revenue(facts(rows))
    assert quarters[0]["value"] == 140.0


def test_stale_gapped_and_short_histories_are_not_used():
    old = [q(start.replace("202", "201"), end.replace("202", "201"), 100.0) for start, end in QUARTERS]
    assert gi.ttm_growth(gi.quarterly_revenue(facts(old))[0], today=TODAY)["state"] == "STALE"
    gapped = [q(start, end, 100.0) for start, end in QUARTERS if end != "2025-06-30"]
    assert gi.ttm_growth(gi.quarterly_revenue(facts(gapped))[0], today=TODAY)["state"] in {"GAP", "INSUFFICIENT_HISTORY"}
    assert gi.ttm_growth([], today=TODAY)["state"] == "INSUFFICIENT_HISTORY"


def test_fallback_is_the_filed_fiscal_year_with_its_basis():
    with patch("growth_inputs.sec_facts", side_effect=LookupError("not an SEC filer")):
        result = gi.revenue_growth_inputs("TSM", {"revenueGrowth": 0.5}, [131.6, 100.0])
    assert abs(result["selected_growth"] - 0.316) < 1e-12 and "fiscal year" in result["basis"]
    assert result["latest_quarter_yoy"] == 0.5 and result["ttm"]["state"] == "UNAVAILABLE"


def report_for(data):
    with patch("intrinsic_valuation._market_rates", return_value=fixture_rates()):
        return iv.build_valuation_report("TEST", data=data)


def test_candidate_uses_ttm_growth_and_leaves_the_headline_alone():
    data = fixture_data(); data["info"]["revenueGrowth"] = 0.53   # one noisy quarter
    data["growth_inputs"] = {"selected_growth": 0.08, "basis": "test"}
    report = report_for(data)
    candidate = report["fair_value_ttm_candidate"]
    assert candidate["state"] == "COMPUTED" and candidate["default"] is False
    assert candidate["method"] == "FIVE_YEAR" and candidate["extended_weight"] == 0.0   # 8% is under the 18% cap
    assert report["fair_value"]["method"] == "PHASED" and report["fair_value"]["extended_weight"] == 1.0
    assert candidate["fair_value"] == report["fair_value"]["five_year"]


def test_candidate_not_computed_without_growth_inputs():
    assert report_for(fixture_data())["fair_value_ttm_candidate"]["state"] == "NOT_COMPUTED"
