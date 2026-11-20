"""Checklist P5: sector flow measurements."""
from unittest.mock import patch

import numpy as np
import pandas as pd

import sector_flow as sf
from signal_history import SignalStore, observation


def frame(seed, days=400, drift=0.0005, volume=1_000_000):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2024-01-01", periods=days)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.01, days)))
    return pd.DataFrame({"Close": close, "Volume": np.full(days, volume, dtype=float)}, index=index)


def test_breadth_counts_members_above_their_averages():
    members = [f"M{i}" for i in range(6)]
    frames = {name: frame(i, drift=0.004) for i, name in enumerate(members[:4])}          # rising names
    frames.update({name: frame(i + 10, drift=-0.004) for i, name in enumerate(members[4:])})  # falling names
    frames["ETF"] = frame(99)
    prepared = sf.prepare(frames)
    day = frames["ETF"].index[-1]
    result = sf.metrics_at("ETF", day, prepared, members)
    assert abs(result["breadth_50"] - 4 / 6) < 1e-9
    assert result["dollar_volume_20d"] > 0
    assert sf.metrics_at("ETF", day, prepared, members[:3])["breadth_50"] is None  # fewer than five names


def test_up_down_volume_ratio():
    index = pd.bdate_range("2025-01-01", periods=30)
    close = np.array([100 + (i % 2) for i in range(30)], dtype=float)   # alternating up and down days
    volume = np.where(np.arange(30) % 2 == 1, 300.0, 100.0)             # heavier on up days
    prepared = sf.prepare({"ETF": pd.DataFrame({"Close": close, "Volume": volume}, index=index)})
    assert abs(sf._at(prepared["ETF"]["updown_volume_20d"], index[-1]) - 3.0) < 1e-9


def test_crowding_rules():
    assert sf.crowding_state(0.9, 0.9, 0.8) == "CROWDED"
    assert sf.crowding_state(0.9, 0.9, 0.1) == "EXTENDED"
    assert sf.crowding_state(0.1, 0.5, 0.2) == "UNLOVED"
    assert sf.crowding_state(0.5, 0.5, 0.5) == "NEUTRAL"
    assert sf.crowding_state(None, 0.9, 0.9) is None


def test_backfill_and_latest_flow(tmp_path):
    store = SignalStore(tmp_path)
    members = [f"M{i}" for i in range(6)]
    frames = {name: frame(i, drift=0.003) for i, name in enumerate(members)}
    frames.update({"ETF": frame(50), "SPY": frame(51)})
    with patch("Valuation_model.SECTOR_ETFS", {"ETF": "Test"}), patch("Valuation_model.SECTOR_CANDIDATES", {"ETF": members}):
        result = sf.backfill(0.5, store, frames=frames)
        again = sf.backfill(0.5, store, frames=frames)
    assert result["state"] == "COMPLETED" and result["written"] > 0 and again["written"] == 0
    days = frames["SPY"].index[-130:]
    store.append([observation("sector.ETF.rel_3m", day, 0.01 * i, source="t", source_state="BACKFILL") for i, day in enumerate(days)])
    latest = sf.latest_sector_flow(store, "ETF")
    assert latest["breadth_50"] >= 0.8 and latest["rs_3m_percentile"] == 1.0
    assert latest["crowding_state"] in {"CROWDED", "EXTENDED"}
    assert latest["rs_persistence_63"] == 1.0
    assert latest["shares_outstanding_change"] is None
