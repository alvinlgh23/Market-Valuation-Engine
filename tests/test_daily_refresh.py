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
                    steps={"drivers": lambda: [{"ticker": "AAA"}], "events": lambda: {"rows": []}}, score=lambda: {"ok": True},
                    ai_ready=False, market=lambda: {"state": "LIVE", "as_of": "2026-11-26"})
    assert seen == [("AAA", "AAA"), ("BAD", "BAD"), ("CCC", "CCC")]         # progress is written before each step
    assert status["state"] == "DONE" and status["done"] == status["total"] == 7
    assert status["market"] == {"state": "LIVE", "as_of": "2026-11-26"}
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


def test_market_prices_refresh_first_and_a_failure_does_not_stop_the_cards(tmp_path):
    order = []

    def market():
        order.append("market")
        raise RuntimeError("provider down")

    def build(ticker):
        order.append(ticker)
        return {"ticker": ticker}

    status = dr.run(TODAY, directory=tmp_path, tickers=["AAA"], build=build, steps={}, score=lambda: None, ai_ready=False, market=market)
    assert order == ["market", "AAA"]                                    # cards are built after the market snapshot
    assert status["market"] is None and status["cards_done"] == ["AAA"]
    assert status["errors"] == [{"step": "market prices", "error": "RuntimeError: provider down"}]


def test_refresh_market_backs_up_once_a_day_and_keeps_the_last_valid_snapshot(tmp_path, monkeypatch):
    import research_system as rs
    monkeypatch.setattr(rs, "CACHE_DIR", tmp_path / "research")
    rs.save_cache("core-market", {"sectors": [{"ticker": "XLK", "as_of": "2026-11-23"}]})
    monkeypatch.setattr(rs, "record_module", lambda *a, **k: None)
    monkeypatch.setattr(rs, "build_core_market", lambda: {"sectors": []})        # provider returned no sector rows
    result = rs.refresh_market(TODAY, backup_dir=tmp_path / "backups")
    assert result["state"] == "STALE" and result["as_of"] == "2026-11-23"           # last valid snapshot kept
    assert (tmp_path / "backups" / "research-core-market-2026-11-26.json").exists()
    monkeypatch.setattr(rs, "build_core_market", lambda: {"sectors": [{"ticker": "XLK", "as_of": "2026-11-26"}]})
    result = rs.refresh_market(TODAY, backup_dir=tmp_path / "backups")
    assert result["state"] == "LIVE" and result["as_of"] == "2026-11-26"
    backup = json.loads((tmp_path / "backups" / "research-core-market-2026-11-26.json").read_text())
    assert backup["sectors"][0]["as_of"] == "2026-11-23"                            # the day's backup is not overwritten
