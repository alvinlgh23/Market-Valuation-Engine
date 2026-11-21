"""Checklist 7.2: tiers, volatility adjustment and within-tier ranks."""
from unittest.mock import patch

import numpy as np
import pandas as pd

import Valuation_model as vm


def hist(seed, vol, drift, days=251):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"Close": 100 * np.exp(np.cumsum(rng.normal(drift, vol, days)))}, index=pd.bdate_range("2025-01-01", periods=days))


def test_every_sector_etf_has_exactly_one_tier():
    tiers = [ticker for tickers in vm.SECTOR_TIERS.values() for ticker in tickers]
    assert sorted(tiers) == sorted(vm.SECTOR_ETFS) and len(tiers) == len(set(tiers))


def test_volatility_adjustment_divides_by_tracking_volatility():
    spy = hist(1, 0.01, 0.0003)
    row = {"ticker": "XLV", "rel_1m": 0.05, "rel_3m": 0.10, "rel_6m": None}
    fields = vm.vol_adjusted_fields(row, hist(2, 0.012, 0.0005), spy)
    assert fields["tier"] == "GICS_SECTOR"
    assert fields["rel_1m_vol_adj"] > 0 and fields["rel_6m_vol_adj"] is None
    assert fields["vol_adj_score"] is not None


def test_high_volatility_theme_no_longer_tops_a_calmer_peer_on_raw_return():
    spy = hist(1, 0.008, 0.0003)
    histories = {"SPY": spy, "XLV": hist(3, 0.009, 0.0012), "XLP": hist(4, 0.009, 0.0004), "QTUM": hist(5, 0.05, 0.0025), "UFO": hist(6, 0.05, 0.0)}
    etfs = {"XLV": "Healthcare", "XLP": "Staples", "QTUM": "Quantum", "UFO": "Space"}
    with patch.object(vm, "fetch_history", side_effect=lambda ticker, period="1y": histories.get(ticker)), patch.object(vm, "SECTOR_ETFS", etfs):
        rows = {row["ticker"]: row for row in vm.compute_sectors()}
    assert rows["XLV"]["tier"] == "GICS_SECTOR" and rows["QTUM"]["tier"] == "THEME"
    assert {rows["XLV"]["rank_in_tier"], rows["XLP"]["rank_in_tier"]} == {1, 2}
    assert {rows["QTUM"]["rank_in_tier"], rows["UFO"]["rank_in_tier"]} == {1, 2}
    assert "score" in rows["XLV"]  # the original score is still there
