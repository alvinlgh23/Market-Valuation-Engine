"""P20 item 6: the daily background refresh."""
import datetime as dt
import json

import daily_refresh as dr

TODAY = dt.date(2026, 11, 26)


def test_run_builds_every_card_precomputes_and_records_progress(tmp_path):
    seen = []

    def build(ticker):
        seen.append((ticker, dr.read_status(tmp_path)["current"]))
        if ticker == "BAD":
            raise RuntimeError("no data")
        return {"ticker": ticker}

    status = dr.run(TODAY, directory=tmp_path, tickers=["AAA", "BAD", "CCC"], build=build,
                    steps={"drivers": lambda: [{"ticker": "AAA"}], "events": lambda: {"rows": []}}, score=lambda: {"ok": True})
    assert seen == [("AAA", "AAA"), ("BAD", "BAD"), ("CCC", "CCC")]         # progress is written before each step
    assert status["state"] == "DONE" and status["done"] == status["total"] == 6
    assert status["cards_done"] == ["AAA", "CCC"]
    assert status["errors"] == [{"step": "BAD", "error": "RuntimeError: no data"}]   # one failure does not stop the rest
    assert dr.precomputed("drivers", TODAY, tmp_path, tickers=["CCC", "BAD", "AAA"]) == [{"ticker": "AAA"}]
    assert dr.current_status(TODAY, tmp_path)["fresh"] is True


def test_precomputed_results_are_only_used_on_their_day_and_for_the_same_watchlist(tmp_path):
    (tmp_path / "drivers.json").write_text(json.dumps({"data_date": "2026-11-25", "tickers": ["AAA"], "data": [1]}))
    assert dr.precomputed("drivers", TODAY, tmp_path) is None                 # yesterday's: compute live
    (tmp_path / "drivers.json").write_text(json.dumps({"data_date": "2026-11-26", "tickers": ["AAA"], "data": [1]}))
    assert dr.precomputed("drivers", TODAY, tmp_path, tickers=["AAA"]) == [1]
    assert dr.precomputed("drivers", TODAY, tmp_path, tickers=["AAA", "NEW"]) is None   # watchlist edited since
    assert dr.precomputed("fx", TODAY, tmp_path) is None                      # never computed


def test_a_dead_running_process_is_reported_as_failed_and_not_fresh(tmp_path):
    (tmp_path / "status.json").write_text(json.dumps({"state": "RUNNING", "pid": 999999999, "data_date": "2026-11-26"}))
    status = dr.current_status(TODAY, tmp_path)
    assert status["state"] == "FAILED" and status["fresh"] is False
    assert dr.current_status(TODAY, tmp_path / "none") == {"state": "NEVER_RUN", "fresh": False}
