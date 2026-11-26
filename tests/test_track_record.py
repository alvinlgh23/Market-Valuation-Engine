"""P20 item 5: the valuation reading's track record."""
import datetime as dt

import pandas as pd

import track_record as tr
from signal_history import SignalStore, observation

RICH = "Price implies more growth than observed/consensus"
CHEAP = "Price implies less growth than observed/consensus"


def store_with(tmp_path, rows):
    store = SignalStore(tmp_path)
    store.append(observation(f"verdict.{t}.valuation", d, label=label, source="company_verdict@x", source_state="LIVE") for t, d, label in rows)
    return store


def prices(start, daily):
    days = pd.bdate_range(start, periods=300)
    return pd.DataFrame({"Close": [100.0 * (1 + daily) ** i for i in range(len(days))]}, index=days)


def test_repeated_days_count_once_and_a_new_reading_starts_a_new_run(tmp_path):
    store = store_with(tmp_path, [("AAA", "2026-01-05", RICH), ("AAA", "2026-01-06", RICH), ("AAA", "2026-01-07", CHEAP),
                                  ("BBB", "2026-01-05", "Fair value withheld")])
    runs = tr.spells(store)
    assert [(s["ticker"], s["date"], s["group"]) for s in runs] == [("AAA", "2026-01-05", "RICH"), ("AAA", "2026-01-07", "CHEAP")]


def test_nothing_matured_is_not_tested_and_fetches_no_prices(tmp_path):
    store = store_with(tmp_path, [("AAA", "2026-11-21", RICH)])
    calls = []
    results = tr.score(tr.spells(store), lambda s, p: calls.append(s), dt.date(2026, 11, 26))
    assert calls == []
    first = results["groups"]["RICH"]["horizons"]["1m"]
    assert first == {"matured": 0, "companies": 0, "tested": False, "next_check": "2026-12-22"}   # 21 Nov is a Saturday
    record = tr.for_label(RICH, results)
    assert record["status"] == "NOT_TESTED" and "2026-12-22" in record["text"]
    assert tr.for_label("Fair value withheld", results) is None


def test_matured_runs_are_scored_against_spy_and_tested_only_with_enough_cases(tmp_path):
    rows = [(f"T{i:02d}", "2025-01-06", RICH) for i in range(tr.MIN_SPELLS)]
    store = store_with(tmp_path, rows)
    frames = {"SPY": prices("2025-01-06", 0.001)} | {f"T{i:02d}": prices("2025-01-06", 0.0) for i in range(tr.MIN_SPELLS)}
    results = tr.score(tr.spells(store), lambda s, p: frames[s], dt.date(2026, 11, 26))
    month = results["groups"]["RICH"]["horizons"]["1m"]
    assert month["tested"] and month["matured"] == tr.MIN_SPELLS
    assert abs(month["median_excess"] - (-(1.001 ** 21 - 1))) < 1e-9          # flat stock vs rising SPY
    assert month["share_as_expected"] == 1.0
    assert tr.for_label(RICH, results)["status"] == "TESTED"

    few = tr.score(tr.spells(store_with(tmp_path / "few", rows[:3])), lambda s, p: frames[s], dt.date(2026, 11, 26))
    assert few["groups"]["RICH"]["horizons"]["1m"]["tested"] is False        # three cases are not a test


def test_missing_prices_are_not_counted_as_zero(tmp_path):
    store = store_with(tmp_path, [("AAA", "2025-01-06", RICH)])
    results = tr.score(tr.spells(store), lambda s, p: None, dt.date(2026, 11, 26))
    assert results["groups"]["RICH"]["horizons"]["1m"]["matured"] == 0
    assert "median_excess" not in results["groups"]["RICH"]["horizons"]["1m"]
