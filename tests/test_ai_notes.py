"""AI model plan, phase B: review notes and the write-up keep only what passes the checks, and never touch a reading."""
import copy
import datetime as dt
import json

import ai_checks
import company_verdict as cv
import company_writeup as cw
import daily_refresh as dr
import filing_reviewer as fr

TODAY = dt.date(2026, 11, 26)
FILING = ("Revenue increased 26% compared with the prior year, driven by advertising. Operating margin declined primarily due to "
          "a legal accrual of $4.0 billion recorded in the quarter. We expect capital expenditures to remain elevated through next year "
          "as we expand data center capacity.")
SOURCE = {"text": FILING, "form": "10-Q", "period": "2026-09-30", "filing_date": "2026-10-30", "url": "https://sec.example/x"}

CARD = {"ticker": "META", "name": "Meta", "generated_on": "2026-11-26",
        "axes": {"fundamentals": {"state": "Deteriorating", "detail": {"quarterly": {"revenue_yoy": 0.26, "margin_change": -0.2}}},
                 "expectations": {"state": "Estimates stable or mixed", "detail": {}},
                 "valuation": {"state": "Price implies more growth than observed/consensus",
                               "detail": {"price": 609.89, "implied_5y_revenue_cagr": 0.25, "growth_band": {"consensus_2y_faded": 0.13, "history_3y_faded": 0.11}}},
                 "macro": {"state": "No confirmed exposure has a current reading", "evidence": []}},
        "price_reading": {"price_change": 0.021, "parts": {"macro": -0.185, "company": 0.212}, "kind": "watch"},
        "conclusion": {"sentences": ["The business is getting weaker."]},
        "what_if_inputs": {"headline_base": 521.0, "report": {
            "assumptions": [{"name": "year_1_revenue_growth", "value": 0.2}, {"name": "year_5_fcff_margin", "value": 0.3}, {"name": "wacc", "value": 0.1},
                            {"name": "terminal_growth", "value": 0.025}, {"name": "annual_dilution", "value": 0.001}],
            "historical_base": {"latest_annual_revenue": 230000, "fcff_margin": 0.25, "cash": 60000, "debt": 30000, "diluted_shares": 2600},
            "fair_value": {}}}}


class FakeGateway:
    def __init__(self, reply, ready=True):
        self.reply, self.ready, self.calls = reply, ready, []

    def role_status(self, role):
        return {"ready": self.ready, "reason": "role is off" if not self.ready else None}

    def chat(self, role, messages, **kwargs):
        self.calls.append(role)
        if self.reply is None:
            return {"status": "UNAVAILABLE", "reason": "rate limited (429)"}
        return {"status": "OK", "text": json.dumps(self.reply), "model": "nemotron-test", "provider": "openrouter"}


def test_review_keeps_quoted_notes_and_drops_invented_quotes_and_numbers(tmp_path):
    reply = {"notes": [
        {"axis": "fundamentals", "note": "The margin drop includes a one-off legal accrual of $4.0 billion.",
         "quote": "Operating margin declined primarily due to a legal accrual of $4.0 billion recorded in the quarter."},
        {"axis": "fundamentals", "note": "Management says demand is collapsing.", "quote": "Demand is collapsing across all regions this year."},
        {"axis": "valuation", "note": "Sales grew 31% last quarter.", "quote": "Revenue increased 26% compared with the prior year, driven by advertising."}]}
    result = fr.review(copy.deepcopy(CARD), gateway=FakeGateway(reply), source=SOURCE, today=TODAY, directory=tmp_path)
    assert result["status"] == "OK" and [n["note"] for n in result["notes"]] == ["The margin drop includes a one-off legal accrual of $4.0 billion."]
    reasons = [d["reason"] for d in result["dropped"]]
    assert "quote not found in the filing" in reasons and any(r.startswith("numbers not in the card or the quote: 31%") for r in reasons)
    assert result["model"] == "nemotron-test" and fr.load_review("META", TODAY, tmp_path)["notes"] == result["notes"]


def test_review_is_unavailable_without_the_role_and_writes_nothing(tmp_path):
    result = fr.review(copy.deepcopy(CARD), gateway=FakeGateway({}, ready=False), source=SOURCE, today=TODAY, directory=tmp_path)
    assert result["status"] == "UNAVAILABLE" and not list(tmp_path.iterdir())
    failed = fr.review(copy.deepcopy(CARD), gateway=FakeGateway(None), source=SOURCE, today=TODAY, directory=tmp_path)
    assert failed["status"] == "UNAVAILABLE" and failed["reason"] == "rate limited (429)"


def good_writeup(**changes):
    reply = {"business": "Sales rose 26% from a year earlier, but the operating margin fell 20 points.",
             "price": "The price rose 2.1% in three months; the company's own part was +21.2% while macro pulled the other way.",
             "macro": "Credit conditions weighed on the price; the card does not count that link as confirmed.",
             "management": [{"point": "Management expects heavy investment to continue.",
                             "quote": "We expect capital expenditures to remain elevated through next year as we expand data center capacity."},
                            {"point": "Management promised a buyback.", "quote": "We will buy back shares aggressively next quarter."}],
             "scenario": {"growth": 0.15, "margin": 0.28, "discount_rate": 0.1, "reason": "Growth fades faster as the price assumes 25% a year."}}
    reply.update(changes)
    return reply


def test_writeup_keeps_checked_parts_values_the_scenario_with_python_and_drops_bad_quotes(tmp_path):
    result = cw.write(copy.deepcopy(CARD), gateway=FakeGateway(good_writeup()), source=SOURCE, today=TODAY, directory=tmp_path)
    assert result["status"] == "OK" and len(result["management"]) == 1
    assert "management quote not found in the filing" in result["dropped"]
    from valuation_what_if import what_if
    expected = what_if(CARD["what_if_inputs"]["report"], growth=0.15, margin=0.28, wacc=0.1, headline_base=521.0)["value"]
    assert abs(result["scenario"]["value"] - expected) < 1e-9 and abs(result["scenario"]["base_value"] - 521.0) < 1e-6
    assert cw.load_writeup("META", TODAY, tmp_path)["model"] == "nemotron-test"


def test_a_writeup_with_an_invented_number_is_rejected_whole(tmp_path):
    result = cw.write(copy.deepcopy(CARD), gateway=FakeGateway(good_writeup(business="Sales rose 40% from a year earlier.")),
                      source=SOURCE, today=TODAY, directory=tmp_path)
    assert result["status"] == "REJECTED" and "40%" in result["reason"]
    assert cw.load_writeup("META", TODAY, tmp_path) is None            # the card keeps its rule-built sentences


def test_scenario_outside_bounds_is_dropped_not_valued(tmp_path):
    result = cw.write(copy.deepcopy(CARD), gateway=FakeGateway(good_writeup(scenario={"growth": 0.9, "margin": 0.3, "discount_rate": 0.1, "reason": "x"})),
                      source=SOURCE, today=TODAY, directory=tmp_path)
    assert result["scenario"] is None and "scenario assumptions missing or outside sensible bounds" in result["dropped"]


def test_ai_results_never_change_a_reading(tmp_path, monkeypatch):
    card = copy.deepcopy(CARD)
    before = json.dumps({k: card[k] for k in ("axes", "conclusion", "price_reading")}, sort_keys=True)
    fr.review(card, gateway=FakeGateway({"notes": []}), source=SOURCE, today=TODAY, directory=tmp_path / "r")
    cw.write(card, gateway=FakeGateway(good_writeup()), source=SOURCE, today=TODAY, directory=tmp_path / "w")
    monkeypatch.setattr(fr, "REVIEW_DIR", tmp_path / "r")
    monkeypatch.setattr(cw, "WRITEUP_DIR", tmp_path / "w")
    monkeypatch.setattr(fr.load_review, "__defaults__", (None, tmp_path / "r"))
    monkeypatch.setattr(cw.load_writeup, "__defaults__", (None, tmp_path / "w"))
    cv.attach_ai(card, TODAY)
    assert card["ai"]["writeup"]["business"].startswith("Sales rose 26%")
    assert json.dumps({k: card[k] for k in ("axes", "conclusion", "price_reading")}, sort_keys=True) == before


def test_daily_refresh_runs_the_ai_step_per_card_only_when_switched_on(tmp_path):
    seen = []
    status = dr.run(TODAY, directory=tmp_path, tickers=["AAA", "BBB"], build=lambda t: {"ticker": t}, steps={}, score=lambda: None,
                    ai=lambda card: seen.append(card["ticker"]), ai_ready=True)
    assert seen == ["AAA", "BBB"] and status["total"] == 5 and status["done"] == 5
    seen.clear()
    dr.run(TODAY, directory=tmp_path, tickers=["AAA"], build=lambda t: {"ticker": t}, steps={}, score=lambda: None,
           ai=lambda card: seen.append(card["ticker"]), ai_ready=False)
    assert seen == []


def test_json_replies_in_code_fences_are_read_and_anything_else_is_rejected():
    assert ai_checks.parse_json_reply('```json\n{"notes": []}\n```') == {"notes": []}
    assert ai_checks.parse_json_reply("Sure! Here are the notes.") is None
