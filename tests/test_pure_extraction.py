"""Checklist 2.2: the extracted pure functions must reproduce the original engine exactly.

The reference functions below are verbatim copies of compute_sectors and the compute_macro
scoring block as they were before extraction (baseline commit 9ade096). The refactored
engine is run on the same synthetic histories and compared value for value.
"""
import itertools
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import Valuation_model as vm


def synthetic_history(seed, rows, start="2023-01-02", drift=0.0003, vol=0.012, level=100.0):
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, vol, rows)
    closes = level * np.exp(np.cumsum(returns))
    index = pd.bdate_range(start=start, periods=rows)
    return pd.DataFrame({"Close": closes}, index=index)


HISTORIES = {
    "SPY": synthetic_history(1, 251),
    "XLV": synthetic_history(2, 251, drift=0.0008),
    "SMH": synthetic_history(3, 251, vol=0.025),
    "XLE": synthetic_history(4, 251, drift=-0.0004),
    "SHORT": synthetic_history(5, 100),   # too short for 6M relative strength
    "TINY": synthetic_history(6, 15),     # too short for every window
}
ETFS = {"XLV": "Healthcare", "SMH": "Semiconductors", "XLE": "Energy", "SHORT": "Short history", "TINY": "Tiny history", "MISSING": "No history"}


def fake_fetch(ticker, period="1y"):
    frame = HISTORIES.get(ticker)
    return None if frame is None else frame.copy()


def reference_compute_sectors():
    """Verbatim pre-extraction compute_sectors (baseline 9ade096)."""
    rows = []
    for ticker, name in vm.SECTOR_ETFS.items():
        hist = vm.fetch_history(ticker, "1y")
        if hist is None:
            continue

        rel_1m = vm.relative_change(ticker, "SPY", 21)
        rel_3m = vm.relative_change(ticker, "SPY", 63)
        rel_6m = vm.relative_change(ticker, "SPY", 126)
        close = float(hist["Close"].iloc[-1])
        high_252 = float(hist["Close"].tail(252).max())
        breakout = (close / high_252 - 1) if high_252 else None

        momentum_score = (
            vm.score_from_change(rel_1m, True, 0.06) * 0.35
            + vm.score_from_change(rel_3m, True, 0.10) * 0.40
            + vm.score_from_change(rel_6m, True, 0.16) * 0.25
        )
        breakout_score = vm.score_from_change(breakout, True, 0.08)
        score = momentum_score * 0.75 + breakout_score * 0.25

        rows.append({
            "ticker": ticker,
            "name": name,
            "rel_1m": rel_1m,
            "rel_3m": rel_3m,
            "rel_6m": rel_6m,
            "breakout": breakout,
            "score": score,
            "as_of": str(hist.index[-1])[:10],
            "source": "Yahoo Finance / Python sector engine",
            "provider_diagnostic": vm.market_provider_diagnostics().get(f"history:{ticker}:1y", {}),
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def reference_macro_scores(tnx_3m, front_rate_3m, dxy_3m, yield_curve, hyg_ief, vix_level):
    """Verbatim pre-extraction scoring block from compute_macro (baseline 9ade096)."""
    score_from_change = vm.score_from_change
    rate_score = score_from_change(tnx_3m, bullish_when_positive=False, scale=0.12)
    front_rate_score = score_from_change(front_rate_3m, bullish_when_positive=False, scale=0.12)
    usd_score = score_from_change(dxy_3m, bullish_when_positive=False, scale=0.06)
    curve_score = 60 if yield_curve and yield_curve > 0 else 40 if yield_curve and yield_curve < 0 else 50
    vix_score = 75 if vix_level and vix_level < 16 else 60 if vix_level and vix_level < 22 else 35 if vix_level else 50
    credit_score = score_from_change(hyg_ief, bullish_when_positive=True, scale=0.05)

    liquidity_score = (rate_score * 0.30) + (front_rate_score * 0.15) + (usd_score * 0.25) + (curve_score * 0.10) + (credit_score * 0.20)
    risk_score = (vix_score * 0.55) + (credit_score * 0.45)
    macro_score = (liquidity_score * 0.60) + (risk_score * 0.40)
    return liquidity_score, risk_score, macro_score


def test_compute_sectors_matches_pre_extraction_engine_exactly():
    with patch.object(vm, "fetch_history", side_effect=fake_fetch), patch.object(vm, "SECTOR_ETFS", ETFS):
        expected = reference_compute_sectors()
        actual = vm.compute_sectors()
    assert [row["ticker"] for row in actual] == [row["ticker"] for row in expected]
    assert actual == expected  # every field, including None paths, compared with ==


def test_sector_row_from_histories_is_the_engine_row():
    with patch.object(vm, "fetch_history", side_effect=fake_fetch), patch.object(vm, "SECTOR_ETFS", ETFS):
        engine = {row["ticker"]: row for row in vm.compute_sectors()}
    for ticker in ("XLV", "SMH", "SHORT", "TINY"):
        pure = vm.sector_row_from_histories(ticker, ETFS[ticker], HISTORIES[ticker], HISTORIES["SPY"])
        assert pure == {key: engine[ticker][key] for key in pure}


INPUT_GRID = {
    "tnx_3m": [None, -0.2, -0.05, 0.0, 0.03, 0.15],
    "front_rate_3m": [None, -0.1, 0.0, 0.12],
    "dxy_3m": [None, -0.04, 0.0, 0.02, 0.09],
    "yield_curve": [None, -0.005, 0.0, 0.004],
    "hyg_ief": [None, -0.06, 0.0, 0.01],
    "vix_level": [None, 0.0, 12.0, 16.0, 21.9, 22.0, 35.0],
}


def test_macro_scores_match_pre_extraction_formula_exactly():
    keys = list(INPUT_GRID)
    for values in itertools.product(*INPUT_GRID.values()):
        args = dict(zip(keys, values))
        expected = reference_macro_scores(**args)
        actual = vm.macro_scores(**args)
        assert (actual["liquidity_score"], actual["risk_score"], actual["macro_score"]) == expected, args


def test_relative_change_wrapper_matches_pure_form():
    with patch.object(vm, "fetch_history", side_effect=fake_fetch):
        for days in (1, 21, 63, 126, 250, 251, 400):
            assert vm.relative_change("XLV", "SPY", days) == vm.relative_change_from_histories(HISTORIES["XLV"], HISTORIES["SPY"], days)
