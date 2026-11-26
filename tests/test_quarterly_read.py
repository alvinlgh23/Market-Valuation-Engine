"""Checklist 15.5: the latest quarterly report, read with fixed rules."""
import quarterly_read as q

QUARTERS = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]


def rows(values, quarters=QUARTERS):
    return dict(zip(quarters, values))


def test_health_rules():
    assert q.health(10.0, -5.0, 20.0, False)["state"] == "STRONG"           # net cash
    assert q.health(10.0, 30.0, 20.0, False)["state"] == "STRONG"           # 1.5x
    assert q.health(10.0, 60.0, 20.0, False)["state"] == "FAIR"             # 3x
    assert q.health(10.0, 100.0, 20.0, False)["state"] == "WEAK"            # 5x
    assert q.health(-1.0, -5.0, 20.0, False)["state"] == "WEAK"             # negative free cash flow
    assert q.health(10.0, 5.0, -1.0, False)["state"] == "WEAK"              # net debt with no positive EBITDA
    assert q.health(10.0, 5.0, 20.0, True)["state"] == "NOT_APPLICABLE"
    assert q.health(None, 5.0, 20.0, False)["state"] == "UNKNOWN"


def test_change_rules():
    assert q.change(0.05, 0.02)["state"] == "IMPROVING"
    assert q.change(0.05, None)["state"] == "IMPROVING"
    assert q.change(-0.05, 0.0)["state"] == "DETERIORATING"
    assert q.change(0.05, -0.02)["state"] == "MIXED"
    assert q.change(0.01, 0.005)["state"] == "NO_CHANGE"
    assert q.change(None, None)["state"] == "UNKNOWN"


def test_read_builds_the_quarter_from_statements():
    income = {"Total Revenue": rows([100, 100, 100, 100, 110, 115, 125]),
              "Operating Income": rows([10, 10, 10, 10, 12, 13, 15]),
              "EBITDA": rows([15, 15, 15, 15, 17, 18, 20])}
    cashflow = {"Free Cash Flow": rows([5, 5, 5, 5, 6, 7, 8])}
    balance = {"Total Debt": rows([50] * 7), "Cash And Cash Equivalents": rows([20] * 7)}
    result = q.read(income, cashflow, balance, {"epsActual": 1.1, "epsEstimate": 1.0, "surprisePercent": 0.1})
    assert result["quarter"] == "2026-09-30"
    assert abs(result["revenue_yoy"] - 0.25) < 1e-12 and abs(result["revenue_yoy_prior_quarter"] - 0.15) < 1e-12
    assert abs(result["revenue_acceleration"] - 0.10) < 1e-12
    assert abs(result["margin_change"] - (0.12 - 0.10)) < 1e-12
    assert result["fcf_ttm"] == 5 + 6 + 7 + 8 and result["ebitda_ttm"] == 15 + 17 + 18 + 20 and result["net_debt"] == 30
    assert result["health"]["state"] == "STRONG" and result["change"]["state"] == "IMPROVING"
    assert result["summary"].startswith("Quarter to Sep 2026: sales +25% from a year earlier, faster than last quarter's +15%")
    assert "beat forecasts by 10%" in result["summary"]


def test_missing_data_is_not_zero():
    assert q.read({}, {}, {})["status"] == "UNAVAILABLE"
    short = q.read({"Total Revenue": rows([100, 110], ["2025-09-30", "2026-09-30"])}, {}, {})
    assert short["fcf_ttm"] is None and short["health"]["state"] == "UNKNOWN"
    assert short["revenue_acceleration"] is None and short["change"]["state"] == "UNKNOWN"


def test_four_quarters_must_be_consecutive():
    gap = [(q.series({"x": {"2024-03-31": 1}}, "x")[0][0], 1.0)]
    assert q.last_four(gap) is None
    points = q.series({"x": {"2024-03-31": 1, "2024-09-30": 1, "2025-03-31": 1, "2025-09-30": 1}}, "x")
    assert q.last_four(points) is None     # spread over 18 months



def test_a_fast_grower_easing_is_not_deteriorating():
    """18.21: 55% -> 50% is a 5-point slowdown but under a fifth of 55%; 10% -> 6% still counts."""
    assert abs(q.growth_threshold(0.55) - 0.11) < 1e-12
    assert q.change(-0.05, 0.0, prior_growth=0.55)["state"] == "NO_CHANGE"
    assert q.change(-0.12, 0.0, prior_growth=0.55)["state"] == "DETERIORATING"
    assert q.change(-0.04, 0.0, prior_growth=0.10)["state"] == "DETERIORATING"
    assert q.change(-0.04, 0.0)["state"] == "DETERIORATING"     # no prior growth: the 3-point floor


def test_an_outsized_eps_gap_is_flagged_not_read_as_a_beat():
    """Walkthrough 2026-11-26: CRM's $5.90 against $3.27 came with a jump in reported EPS - a one-off, not the business."""
    income = {"Total Revenue": rows([100, 100, 100, 100, 110, 115, 125])}
    result = q.read(income, {}, {}, {"epsActual": 5.9, "epsEstimate": 3.27, "surprisePercent": 0.8036})
    assert result["eps_surprise_outsized"] is True
    assert "beat forecasts" not in result["summary"] and "($5.90 against $3.27)" in result["summary"]
    assert q.read(income, {}, {}, {"epsActual": 1.1, "epsEstimate": 1.0, "surprisePercent": 0.1})["eps_surprise_outsized"] is False
