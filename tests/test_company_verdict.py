"""Checklist P4: company judgment card logic (no network)."""
import datetime as dt

import pandas as pd

import company_verdict as cv
from signal_history import SignalStore, observation


def environment(**directions):
    base = {"semis_cycle": -1, "usd": 1, "long_rates": 0, "volatility": 0, "credit": -1}
    base.update(directions)
    factors = {key: {"state": {1: "Rising", 0: "Flat", -1: "Falling"}[value], "direction": value, "readings": {}} for key, value in base.items()}
    factors["yen_carry"] = {"state": "Stable", "direction": 0, "readings": {"carry_state": "STABLE"}}
    return {"factors": factors, "contradictions": [], "risk_regime": {"regime": "Healthy Rotation"}, "as_of": "2026-11-04"}


def test_macro_axis_counts_only_confirmed_and_skips_downgraded(monkeypatch):
    validation = {"results": {"FABLESS_SEMICONDUCTOR": {
        "semis_cycle": {"status": "CONFIRMED"}, "usd": {"status": "CONFIRMED"}, "volatility": {"status": "CONFIRMED"},
        "long_rates": {"status": "WEAK"}, "yen_carry": {"status": "WEAK"}}}}
    import exposure_map
    monkeypatch.setattr(exposure_map, "load_validation", lambda path=None: validation)
    result = cv.macro_axis("FABLESS_SEMICONDUCTOR", environment())
    assert result["state"] == "Headwind"
    assert result["detail"]["confirmed_headwinds"] == 2 and result["detail"]["confirmed_tailwinds"] == 0
    assert all(row["factor"] != "yen_carry" for row in result["detail"]["exposures"])
    tail = cv.macro_axis("FABLESS_SEMICONDUCTOR", environment(semis_cycle=1, usd=-1))
    assert tail["state"] == "Tailwind"
    validation["results"]["FABLESS_SEMICONDUCTOR"]["usd"]["status"] = "DOWNGRADED"
    assert all(row["factor"] != "usd" for row in cv.macro_axis("FABLESS_SEMICONDUCTOR", environment())["detail"]["exposures"])


def test_carry_switch_fires_only_for_liquidity_sensitive_archetypes(monkeypatch):
    import exposure_map
    monkeypatch.setattr(exposure_map, "load_validation", lambda path=None: {})
    env = environment()
    env["factors"]["yen_carry"]["readings"]["carry_state"] = "UNWIND_RISK"
    assert cv.macro_axis("FABLESS_SEMICONDUCTOR", env)["detail"]["carry_switch"]
    assert cv.macro_axis("UTILITY_INFRASTRUCTURE", env)["detail"]["carry_switch"] is None


def test_flow_axis_requires_persistence(tmp_path):
    store = SignalStore(tmp_path)
    days = pd.bdate_range("2025-01-01", periods=120)
    values = [0.0] * 100 + [0.5] * 20             # last 20 observations in the top bucket
    store.append([observation("sector.XLV.rel_3m", day, value + index * 1e-6, source="t", source_state="BACKFILL") for index, (day, value) in enumerate(zip(days, values))])
    result = cv.flow_axis("LLY", "XLV", "test", store, 0.08, removed={"rel_1m"})
    assert result["state"] == "Money flowing in" and result["detail"]["persistence_of_10"] >= 6
    assert result["detail"]["basis"] == "rel_3m"
    assert "leads XLV by 8.0%" in result["evidence"][1]
    assert cv.flow_axis("LLY", "XLV", "test", store, 0.08, removed={"rel_1m", "rel_3m", "rel_6m"})["state"] == "No informative flow signal"
    flip = SignalStore(tmp_path / "flip")
    flip.append([observation("sector.XLV.rel_3m", day, (0.5 if index % 2 else -0.5) + index * 1e-6, source="t", source_state="BACKFILL") for index, day in enumerate(days)])
    assert cv.flow_axis("LLY", "XLV", "test", flip, None, removed={"rel_1m"})["state"] == "Mixed (not persistent)"
    assert cv.flow_axis("LLY", None, "none", store, None)["state"] == "No sector mapping"


def report(status, **extra):
    base = {"company": {"current_market_price": 100.0}, "discount_rate": {"equity_risk_premium": 0.045, "wacc": 0.09},
            "scenarios": {name: {"fair_value_per_share": value} for name, value in (("bear", 60.0), ("base", 80.0), ("bull", 110.0))},
            "reverse_dcf": {"status": status, **extra}}
    return base


def test_valuation_axis_reads_priced_growth_first():
    converged = cv.valuation_axis(report("CONVERGED", converged=True, required_5y_revenue_cagr=0.30), 0.10, 0.12, -0.008, None)
    assert converged["state"] == "Price implies more growth than observed/consensus"
    above = cv.valuation_axis(report("NO_ECONOMIC_SOLUTION", high_case_value=75.0, low_case_value=20.0), 0.6, 0.7, None, None)
    assert above["state"] == "Price implies growth above what the model can reach"
    below = cv.valuation_axis(report("NO_ECONOMIC_SOLUTION", high_case_value=300.0, low_case_value=150.0), 0.0, 0.0, None, None)
    assert below["state"] == "Price implies contraction beyond the model's floor"
    withheld = cv.valuation_axis({"company": {}, "reverse_dcf": {}, "data_quality": {"reason": "FCFF cannot be reconciled."}}, None, None, None, None)
    assert withheld["state"] == "Fair value withheld" and withheld["missing"] == ["FCFF cannot be reconciled."]
    assert converged["detail"]["fixed_erp"] == 0.045 and converged["detail"]["implied_erp"] == -0.008


def test_withheld_fair_value_says_why_in_plain_words():
    """Checklist 11.5: banks, ADR units and cash-flow checks get an investor-readable reason; the model text stays in detail."""
    bank = cv.valuation_axis({"company": {}, "company_type": "Financial Institution", "reverse_dcf": {},
                              "data_quality": {"status": "INSUFFICIENT_FOR_FAIR_VALUE", "reason": "Debt and interest are operating inputs."}}, None, None, None, None)
    assert bank["missing"][0].startswith("Banks and lenders are valued on book value") and bank["detail"]["model_reason"] == "Debt and interest are operating inputs."
    adr = cv.valuation_axis({"company": {}, "reverse_dcf": {}, "data_quality": {"status": "SECURITY_UNIT_AMBIGUITY", "reason": "TWD vs USD"}}, None, None, None, None)
    assert "ADR" in adr["missing"][0]
    gap = cv.valuation_axis({"company": {}, "reverse_dcf": {}, "data_quality": {"status": "FAILED_FCFF_RECONCILIATION", "missing": ["stock-based compensation"], "reason": "x"}}, None, None, None, None)
    assert "stock-based compensation" in gap["missing"][0] and "zero" in gap["missing"][0]
    mismatch = cv.valuation_axis({"company": {}, "reverse_dcf": {}, "data_quality": {"status": "FAILED_FCFF_RECONCILIATION", "missing": [], "reason": "x"}}, None, None, None, None)
    assert mismatch["missing"][0].startswith("Two independent measures")


def two_base_report(primary_cagr, alternate_cagr):
    shown = report("CONVERGED", converged=True, required_5y_revenue_cagr=primary_cagr)
    shown["data_quality"] = {"status": "CASH_FLOW_MEASURES_DIFFER", "reason": "two measures differ"}
    shown["cash_flow_bases"] = {"gap_pct": 0.28, "operating_profit_base": 9.3e9, "cash_flow_statement_base": 6.7e9,
                                "alternate": {"reverse_dcf": {"status": "CONVERGED", "converged": True, "required_5y_revenue_cagr": alternate_cagr},
                                              "fair_value": {}, "scenarios": {"bear": 50.0, "base": 70.0, "bull": 95.0}}}
    return shown


def test_two_cash_flow_bases_publish_only_a_reading_that_holds_on_both():
    """Checklist 12.1: same reading on both bases -> published with the range and one step less confidence."""
    same = cv.valuation_axis(two_base_report(0.325, 0.386), 0.10, 0.16, None, None)
    assert same["state"] == "Price implies more growth than observed/consensus" and same["confidence"] == "LOW"
    assert "+32.5% to +38.6%" in same["evidence"][0] and "holds on both bases" in same["evidence"][1]
    assert same["detail"]["fair_value"]["base"] == 80.0
    assert same["detail"]["cash_flow_bases"]["fair_value"]["cash_flow_statement"]["base"] == 70.0
    split = cv.valuation_axis(two_base_report(0.147, 0.013), 0.139, 0.159, None, None)
    assert split["state"] == "Depends on which cash-flow measure" and split["confidence"] == "LOW"
    assert split["detail"]["fair_value"] == {} and split["missing"][0].startswith("No single fair value")
    assert "+1.3% to +14.7%" in split["evidence"][0]


def test_next_year_is_the_fiscal_year_still_mostly_ahead():
    today = dt.date(2026, 11, 24)
    # AMAT: the year ending October 2027 has barely started, so it is next year ("0y"), not October 2028.
    assert cv.forward_fiscal_year(dt.date(2027, 10, 25), today) == ("0y", dt.date(2027, 10, 25))
    # AMD: one month of December 2026 is left, so next year is the one ending December 2027 ("+1y").
    assert cv.forward_fiscal_year(dt.date(2026, 12, 27), today) == ("+1y", dt.date(2027, 12, 27))
    # Exactly half a year ahead still counts as the current year; without the year end the old choice stays.
    assert cv.forward_fiscal_year(today + dt.timedelta(days=183), today)[0] == "0y"
    assert cv.forward_fiscal_year(today + dt.timedelta(days=182), today)[0] == "+1y"
    assert cv.forward_fiscal_year(None, today) == ("+1y", None)
    assert cv.forward_fiscal_year(dt.date(2028, 2, 29), dt.date(2028, 2, 1))[1] == dt.date(2029, 2, 28)
    axis = cv.expectations_axis({"eps_trend_next_year": {"current": 1.1, "90daysAgo": 1.0}, "revisions_up_30d": 7, "revisions_down_30d": 0,
                                 "revenue_growth_next_year": 0.393, "analysts_next_year": 30, "forward_fiscal_year_end": "2027-10-25"})
    assert "next fiscal year (fiscal year ending Oct 2027) +39.3%" in axis["evidence"][1]


def test_expectations_and_fundamentals_axes():
    rising = cv.expectations_axis({"eps_trend_next_year": {"current": 1.1, "90daysAgo": 1.0}, "revisions_up_30d": 7, "revisions_down_30d": 0, "revenue_growth_next_year": 0.2, "analysts_next_year": 30})
    assert rising["state"] == "Estimates rising"
    assert cv.expectations_axis({"error": "timeout"})["state"] == "Consensus data unavailable"
    improving = cv.fundamentals_axis({"financial_translation": {"revenue": {"state": "POSITIVE"}, "margin": {"state": "POSITIVE"}, "capital": {"state": "NEGATIVE"}}})
    assert improving["state"] == "Improving"
    assert cv.fundamentals_axis({"financial_translation": {"revenue": {"state": "INSUFFICIENT_EVIDENCE"}}})["state"] == "Trajectory not established"


def test_contradictions_and_catalysts():
    axes = {
        "flow": cv.axis("Money flowing in", direction="weakening", detail={"company_vs_sector_3m": -0.10}),
        "valuation": cv.axis("Price implies growth above what the model can reach"),
        "macro": cv.axis("Headwind"),
        "crowding": cv.axis("High Chase Risk"),
        "expectations": cv.axis("Estimates rising"),
        "fundamentals": cv.axis("Improving"),
    }
    env = {"contradictions": [{"factors": ["liquidity"], "text": "liquidity split"}, {"factors": ["oil"], "text": "oil split"}]}
    found = cv.contradictions(axes, env, {"liquidity"})
    assert any("lags it by 10.0%" in item for item in found)
    assert any("headwind" in item for item in found) and any("crowded" in item for item in found)
    assert "liquidity split" in found and "oil split" not in found
    today = dt.date(2026, 11, 20)
    assert cv.next_catalysts("2026-11-18", {"date": "2026-12-09"}, today) == {"earnings": None, "last_earnings": "2026-11-18", "fomc": "2026-12-09"}
    assert cv.next_catalysts("2027-02-02", None, today)["earnings"] == "2027-02-02"


def test_fomc_parser_returns_the_next_meeting():
    html = ('<h4>2026 FOMC Meetings</h4><div class="fomc-meeting__month"><strong>October</strong></div><div class="fomc-meeting__date">27-28</div>'
            '<div class="fomc-meeting__month"><strong>December</strong></div><div class="fomc-meeting__date">8-9*</div>'
            '<h4>2027 FOMC Meetings</h4><div class="fomc-meeting__month"><strong>January</strong></div><div class="fomc-meeting__date">26-27</div>')
    assert cv.parse_fomc(html, dt.date(2026, 11, 20))["date"] == "2026-12-09"
    assert cv.parse_fomc(html, dt.date(2026, 12, 10))["date"] == "2027-01-27"
    assert cv.parse_fomc("", dt.date(2026, 11, 20))["date"] is None


def test_changes_are_measured_against_the_last_recorded_card(tmp_path):
    store = SignalStore(tmp_path)
    first = {"flow": cv.axis("Neutral"), "macro": cv.axis("Headwind")}
    assert cv.record_verdict("NVDA", first, store, "2026-11-10") == 2
    second = {"flow": cv.axis("Money flowing out"), "macro": cv.axis("Headwind")}
    changes = cv.changes_since_last("NVDA", second, store, "2026-11-20")
    assert changes == [{"axis": "flow", "from": "Neutral", "to": "Money flowing out", "since": "2026-11-10"}]
    assert cv.record_verdict("NVDA", second, store, "2026-11-10") == 0  # append-only


def test_sector_mapping_prefers_engine_candidates():
    assert cv.sector_etf_for("NVDA", "Technology")[0] == "SMH"
    assert cv.sector_etf_for("ZZZZ", "Healthcare")[0] == "XLV"
    assert cv.sector_etf_for("ZZZZ", None)[0] is None


def test_valuation_axis_reads_the_phased_headline():
    base = report("CONVERGED", converged=True, required_5y_revenue_cagr=0.30)
    base["fair_value"] = {"method": "PHASED", "extended_weight": 0.4, "observed_growth": 0.22, "type_cap": 0.18, "phase_in_band": 0.10,
                          "fair_value": {"bear": 70.0, "base": 95.0, "bull": 130.0},
                          "reverse_dcf": {"status": "CONVERGED", "converged": True, "required_5y_revenue_cagr": 0.20}}
    result = cv.valuation_axis(base, 0.22, 0.20, None, None)
    assert result["detail"]["fair_value"] == {"bear": 70.0, "base": 95.0, "bull": 130.0}
    assert result["detail"]["implied_5y_revenue_cagr"] == 0.20 and result["detail"]["ten_year_weight"] == 0.4
    assert "ten-year (40%)" in result["detail"]["notes"][0]


def test_reversed_volatility_is_context_not_a_headwind(monkeypatch):
    """Checklist 10.5: high VIX preceded better returns, so it is shown but not counted."""
    validation = {"results": {"FABLESS_SEMICONDUCTOR": {"volatility": {"status": "CONFIRMED"}, "semis_cycle": {"status": "CONFIRMED"}, "usd": {"status": "CONFIRMED"}}}}
    import exposure_map
    monkeypatch.setattr(exposure_map, "load_validation", lambda path=None: validation)
    monkeypatch.setattr(cv, "reversed_signals", lambda: {"vix_score"})
    result = cv.macro_axis("FABLESS_SEMICONDUCTOR", environment(volatility=1, semis_cycle=1, usd=-1))
    assert result["state"] == "Tailwind"                              # volatility rising would otherwise be a headwind
    assert result["detail"]["confirmed_headwinds"] == 0
    assert any("not counted as a headwind" in line for line in result["detail"]["context_only"])
    monkeypatch.setattr(cv, "reversed_signals", lambda: set())
    assert cv.macro_axis("FABLESS_SEMICONDUCTOR", environment(volatility=1, semis_cycle=1, usd=-1))["detail"]["confirmed_headwinds"] == 1


def test_fx_moves_reports_each_currency_and_none_when_missing(monkeypatch):
    """Checklist 10.9: home-currency moves for a global audience."""
    views = {"EUR": {"home_per_usd_3m_change": 0.064}, "JPY": {"error": "JPY=X history unavailable"}}
    monkeypatch.setattr(cv, "home_currency_view", lambda code: views[code])
    result = cv.fx_moves(("EUR", "JPY"))
    assert result["home_per_usd_change"] == {"EUR": 0.064, "JPY": None}


def test_bank_reading_compares_implied_and_latest_roe():
    """Checklist 12.2."""
    bank = {"status": "AVAILABLE", "price_to_book": 1.54, "latest_roe": 0.057, "implied_roe": 0.218, "cost_of_equity": 0.15, "beta": 2.24, "method": "m"}
    high = cv.valuation_axis({"bank_implied_roe": bank}, None, None, None, None)
    assert high["state"] == "Price implies higher ROE than the bank earns" and "21.8%" in high["evidence"][0]
    assert cv.valuation_axis({"bank_implied_roe": {**bank, "implied_roe": 0.116, "latest_roe": 0.106}}, None, None, None, None)["state"] == "Price roughly matches the bank's ROE"
    assert cv.valuation_axis({"bank_implied_roe": {**bank, "implied_roe": 0.08, "latest_roe": 0.15}}, None, None, None, None)["state"] == "Price implies lower ROE than the bank earns"


def test_adr_figures_convert_to_the_quoted_share():
    """Checklist 12.3: a company-level valuation in TWD is read against the USD ADR price."""
    twd = report("NO_ECONOMIC_SOLUTION", high_case_value=7000.0, low_case_value=1000.0)
    twd["company"]["current_market_price"] = 10_000.0
    twd["unit_bridge"] = {"quote_per_model_share": 0.03}
    axis = cv.valuation_axis(twd, 0.3, 0.25, None, None)
    assert axis["detail"]["price"] == 300.0 and axis["detail"]["fair_value"]["base"] == 80.0 * 0.03
    assert "210.00 vs price 300.00" in axis["evidence"][0]
