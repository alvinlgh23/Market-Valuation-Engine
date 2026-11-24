"""Checklist 16-17: the plain-language market story and the scenario gate."""
import datetime as dt

import market_story as ms

DEC9 = dt.date(2026, 12, 9)
FUTURES = {"2026-11": 3.88, "2026-12": 4.07, "2027-01": 4.16, "2027-02": 4.30}


def test_contract_symbols():
    assert ms.contract_symbol("2026-12") == "ZQZ26.CBT"
    assert ms.contract_symbol("2027-01") == "ZQF27.CBT"


def test_fomc_outlook_uses_the_meeting_month_contract():
    outlook = ms.fomc_outlook(DEC9, 3.88, FUTURES)
    # December averages 9 days at 3.88% and 22 days at the new rate: (4.07 - 3.88 x 9/31) / (22/31) = 4.148%
    assert abs(outlook["implied_after"] - 4.1478) < 1e-3
    assert outlook["decision"] == "raise" and outlook["probability_move"] == 1.0
    assert abs(outlook["rate_after_if_move"] - 4.13) < 1e-9
    assert abs(outlook["further_moves"] - (4.30 - outlook["implied_after"]) / 0.25) < 1e-9
    text = ms.fomc_sentence(outlook)
    assert text.startswith("Futures price a near-certain 0.25-point rise on 9 December, from 3.88% to about 4.13%.")
    assert "another rise by February" in text


def test_fomc_outlook_hold_and_missing_data():
    hold = ms.fomc_outlook(DEC9, 3.88, {"2026-11": 3.88, "2026-12": 3.90})
    assert hold["decision"] == "hold" and hold["probability_hold"] > 0.8
    assert "chance on no change" in ms.fomc_sentence(hold)
    assert ms.fomc_outlook(DEC9, 3.88, {"2026-11": 3.88})["status"] == "UNAVAILABLE"
    assert ms.fomc_outlook(None, 3.88, FUTURES)["status"] == "UNAVAILABLE"


def test_inflation_step_against_the_fed_goal():
    above = ms.inflation_step({"current": 3.12, "trend_3m": 0.08, "date": "2026-09-01"})
    assert above["title"] == "Inflation is still above the Fed's goal" and "edged up" in above["text"]
    assert ms.inflation_step({"current": 2.2, "trend_3m": -0.1})["title"] == "Inflation is close to the Fed's goal"
    assert ms.inflation_step({"current": 1.8, "trend_3m": 0.0})["title"] == "Inflation is below the Fed's goal"
    assert ms.inflation_step({"current": None}) is None


def test_volatility_step_notes_tested_pattern_and_checked_link():
    step = ms.volatility_step({"level": 28.4, "median": 16.5, "percentile": 0.95, "as_of": "2026-11-19",
                               "fade": {"days": 38, "share_lower": 0.95, "episodes": 4}},
                              {"verdict": "NO_LINK", "tight_next_vol": 0.125, "other_next_vol": 0.136})
    assert step["title"] == "Investors expect big swings" and "about 8% either way" in step["text"]
    assert [note["tag"] for note in step["notes"]] == ["TESTED", "NO_LINK"]
    assert step["notes"][0]["label"] == "Tested · few cases"
    calm = ms.volatility_step({"level": 14, "median": 16.5, "percentile": 0.2}, None)
    assert calm["title"] == "Investors expect small swings" and calm["notes"] == []


def test_because_only_from_inflation_to_the_fed():
    inputs = {"core_pce": {"current": 3.1, "trend_3m": 0.08}, "fomc": ms.fomc_outlook(DEC9, 3.88, FUTURES),
              "rates": {"tnx_level": 5.05, "long_rates_state": "Rising", "long_rates_words": "rising faster than usual", "dxy_level": 103.9, "dxy_3m": 0.049},
              "vix": {"level": 28.4, "median": 16.5, "percentile": 0.95},
              "market": {"status": "AVAILABLE", "growth": 0.40, "carriers": [], "carriers_for_half": 8,
                         "driver": {"state": "PROFIT_LED", "index_change": 0.14, "plain": "Prices are following profits.", "rule": "r"}},
              "holdings": [{"ticker": "PLTR", "factor": "credit", "value": -0.124}, {"ticker": "V", "factor": "oil", "value": 0.02}],
              "validation": None, "conditions": {}}
    story = ms.build_story(inputs)
    kinds = [(step["id"], step.get("link", {}).get("kind")) for step in story["steps"]]
    assert kinds[0] == ("inflation", "because")
    assert all(kind == "alongside" for _, kind in kinds[1:-1]) and kinds[-1] == ("holdings", None)
    assert story["headline"] == "Rates are going up and investors are nervous, but company profits are still growing fast."
    holdings = next(step for step in story["steps"] if step["id"] == "holdings")
    assert "PLTR −12.4% (risky company bonds falling)" in holdings["text"] and "V" not in [item["ticker"] for item in holdings["holdings"]]


def test_scenario_section_blocks_calls_that_failed_the_gate():
    validation = {"methods": {"analog_sectors": {"verdict": "FAILED", "beat_share": 0.5}, "sector_strength_1m_1m": {"verdict": "FAILED", "beat_share": 0.48}},
                  "conditions": {"hiking=yes,hot=yes,fear=yes": {"months": 6, "episodes": 2, "spy_up_share": 0.67, "all_months_up_share": 0.71},
                                 "hiking=no,hot=no,fear=yes": {"months": 41, "episodes": 8, "spy_up_share": 0.83, "all_months_up_share": 0.70}},
                  "pass_rule": "t >= 2"}
    few = ms.scenario_section(validation, {"hiking": True, "hot": True, "fear": True})
    assert few["passed"] == [] and few["verdict"].startswith("No reliable call on which sectors win next")
    assert "too few to learn from" in few["lesson"]
    context = ms.scenario_section(validation, {"hiking": False, "hot": False, "fear": True})
    assert "83% of the time" in context["lesson"] and context["lesson"].endswith("Context, not a forecast.")
    assert ms.scenario_section(None, {})["status"] == "UNAVAILABLE"
