"""Checklist 2.1-2.3: append-only signal history, backfill and read API."""
import json
import math
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import Valuation_model as vm
import signal_history as sh
from test_pure_extraction import synthetic_history

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    return sh.SignalStore(tmp_path)


def obs(signal_id, day, value=None, label=None, state="LIVE"):
    return sh.observation(signal_id, day, value, label, source="test", source_state=state)


def test_append_is_append_only_and_deduplicates(store):
    assert store.append([obs("macro.x", "2026-01-02", 1.0), obs("macro.x", "2026-01-03", 2.0)]) == 2
    assert store.append([obs("macro.x", "2026-01-03", 99.0), obs("macro.x", "2026-01-04", 3.0)]) == 1
    assert store.series("macro.x") == [("2026-01-02", 1.0), ("2026-01-03", 2.0), ("2026-01-04", 3.0)]


def test_missing_values_are_not_stored_as_zero(store):
    assert obs("macro.x", "2026-01-02", None) is None
    assert obs("macro.x", "2026-01-02", float("nan")) is None
    assert obs("macro.x", None, 1.0) is None
    assert obs("macro.x", "not-a-date", 1.0) is None
    assert store.append([None, obs("risk.regime", "2026-01-02", label="Healthy Rotation")]) == 1
    assert store.series("risk.regime") == []
    assert store.labels("risk.regime") == [("2026-01-02", "Healthy Rotation")]


def test_only_live_and_backfill_rows_are_recorded(store):
    with pytest.raises(ValueError):
        store.append([obs("macro.x", "2026-01-02", 1.0, state="CACHED")])
    assert sh.record_module("core-market", {"sectors": []}, "CACHED", store)["state"] == "SKIPPED"


def test_values_round_trip_exactly(store):
    value = 0.1 + 0.2
    store.append([obs("macro.y", "2026-01-02", value)])
    assert sh.SignalStore(store.directory).series("macro.y")[0][1] == value


def test_read_api(store):
    days = pd.bdate_range("2025-01-01", periods=100)
    store.append([obs("macro.z", day, float(index)) for index, day in enumerate(days)])
    last = str(days[-1].date())
    assert store.latest("macro.z")["value"] == 99.0
    assert store.value_observations_ago("macro.z", 5) == (str(days[-6].date()), 94.0)
    assert store.value_observations_ago("macro.z", 100) is None
    date, value = store.value_days_ago("macro.z", 30, as_of=last)
    assert date <= str((days[-1] - pd.Timedelta(days=30)).date()) and value == days.get_loc(pd.Timestamp(date))
    assert store.percentile("macro.z") == 1.0
    assert store.percentile("macro.z", value=49.5) == 0.5
    assert store.percentile("macro.z", as_of=str(days[30].date())) is None  # fewer than 60 points
    assert store.percentile("macro.z", as_of=str(days[30].date()), min_observations=10) == 1.0
    assert "macro.z" in store.signal_ids("macro.")


def test_core_market_extractor_uses_observation_dates(store):
    payload = json.loads((ROOT / ".cache/research/core-market.json").read_text()) if (ROOT / ".cache/research/core-market.json").exists() else None
    if payload is None:
        pytest.skip("No cached core-market payload in this checkout.")
    observations = sh.observations_from_core_market(payload, "LIVE")
    by_id = {item.signal_id: item for item in observations}
    first = payload["sectors"][0]
    assert by_id[f"sector.{first['ticker']}.rel_6m"].value == first["rel_6m"]
    assert by_id[f"sector.{first['ticker']}.rel_6m"].observation_date == first["as_of"]
    assert by_id["risk.regime"].label == payload["risk"]["regime"]
    assert all(not math.isnan(item.value) for item in observations if item.value is not None)
    assert store.append(observations) == len(observations)
    assert store.append(observations) == 0


def test_kospi_extractor_skips_factors_without_observations():
    payload = {"sweep": {"timestamp": "2026-11-05 09:23 UTC", "results": [
        {"key": "tech", "corr": 0.287, "pval": 0.0, "strength": "Strong", "detail": {"obs": 240}},
        {"key": "foreign_flow", "corr": 0.0, "pval": 1.0, "strength": "No Signal", "detail": {}},
    ], "volatility": {"current_vol": 1.2, "regime": "High"}, "interpretation": {"regime": {"name": "Tech-Sensitive"}}}}
    ids = {item.signal_id for item in sh.observations_from_kospi(payload, "LIVE")}
    assert "kospi.factor.tech.corr" in ids
    assert not any("foreign_flow" in item for item in ids)


def test_trailing_window_mirrors_one_year_fetch():
    frame = synthetic_history(7, 900, start="2023-01-02")
    cutoff = frame.index[700]
    window = sh.trailing_window(frame, cutoff)
    assert window.index[-1] == cutoff
    assert window.index[0] > cutoff - pd.Timedelta(days=365)
    assert sh.trailing_window(frame, frame.index[0] - pd.Timedelta(days=1)) is None


def test_backfill_cutoff_equals_live_engine_on_the_same_window():
    """A backfilled date must equal compute_sectors run on that date's 1y window."""
    long = {ticker: synthetic_history(seed, 800, start="2023-01-02") for seed, ticker in enumerate(["SPY", "XLV", "SMH", "XLE"], start=11)}
    cutoff = long["SPY"].index[650]
    windows = {ticker: sh.trailing_window(frame, cutoff) for ticker, frame in long.items()}
    etfs = {"XLV": "Healthcare", "SMH": "Semiconductors", "XLE": "Energy"}
    with patch.object(vm, "fetch_history", side_effect=lambda ticker, period="1y": windows.get(ticker)), patch.object(vm, "SECTOR_ETFS", etfs):
        live = {row["ticker"]: row for row in vm.compute_sectors()}
        backfilled = {item.signal_id: item for item in sh.backfill_observations_at(cutoff, long)}
    for ticker in etfs:
        for key in ("rel_1m", "rel_3m", "rel_6m", "breakout", "score"):
            item = backfilled.get(f"sector.{ticker}.{key}")
            assert item is not None and item.value == live[ticker][key], (ticker, key)


def test_backfill_writes_each_cutoff_once(store):
    long = {ticker: synthetic_history(seed, 700, start="2023-01-02") for seed, ticker in enumerate(["SPY", "XLV"], start=21)}
    with patch.object(vm, "SECTOR_ETFS", {"XLV": "Healthcare"}):
        first = sh.backfill(0.25, store, histories=long)
        second = sh.backfill(0.25, store, histories=long)
    assert first["state"] == "COMPLETED" and first["written"] > 0
    assert second["written"] == 0
    rel = store.series("sector.XLV.rel_6m")
    assert len(rel) == first["cutoffs"]
    assert {row["source_state"] for row in store.rows("sector.XLV.rel_6m")} == {"BACKFILL"}
    assert store.labels("risk.regime")  # risk regime recomputed per cutoff


def test_record_module_never_raises(store, monkeypatch):
    monkeypatch.setitem(sh.EXTRACTORS, "kospi", lambda payload, state: (_ for _ in ()).throw(RuntimeError("boom")))
    result = sh.record_module("kospi", {"sweep": {}}, "LIVE", store)
    assert result["state"] == "FAILED" and "boom" in result["error"]
