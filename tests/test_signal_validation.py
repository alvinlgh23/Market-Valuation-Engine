"""Checklist P6: scorecard mechanics on synthetic data."""
import numpy as np
import pandas as pd

import signal_validation as sv


def test_cross_sectional_ic_detects_a_planted_signal_and_rejects_noise():
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2024-01-01", periods=400)
    etfs = [f"E{i}" for i in range(20)]
    signal = pd.DataFrame(rng.normal(size=(400, 20)), index=dates, columns=etfs)
    forward = 0.5 * signal + pd.DataFrame(rng.normal(size=(400, 20)), index=dates, columns=etfs)
    good = sv.cross_sectional(signal, forward, step=21)
    assert good["mean_ic"] > 0.3 and good["t_stat"] > 2 and good["hit_rate"] > 0.6
    noise = sv.cross_sectional(signal, pd.DataFrame(rng.normal(size=(400, 20)), index=dates, columns=etfs), step=21)
    assert abs(noise["mean_ic"]) < 0.15


def test_time_series_and_verdict_rules():
    rng = np.random.default_rng(2)
    index = pd.bdate_range("2020-01-01", periods=2000)
    signal = pd.Series(rng.normal(size=2000), index=index)
    forward = -0.8 * signal + pd.Series(rng.normal(scale=0.3, size=2000), index=index)
    result = {"1M": sv.time_series(signal, forward, 21), "3M": sv.time_series(signal, forward, 63)}
    assert sv.verdict(result) == "REVERSED"
    flat = {"1M": {"mean_ic": 0.01, "t_stat": 0.2, "hit_rate": 0.5}, "3M": {"mean_ic": -0.01, "t_stat": -0.5, "hit_rate": 0.49}}
    assert sv.verdict(flat) == "NO_INFORMATION"
    assert sv.verdict({"1M": {"mean_ic": 0.1, "t_stat": 2.3, "hit_rate": 0.55}, "3M": {"mean_ic": 0.0, "t_stat": 0.1, "hit_rate": 0.5}}) == "INFORMATIVE"
    assert sv.verdict({"1M": {"mean_ic": None, "t_stat": None, "hit_rate": None}}) == "INSUFFICIENT_SAMPLE"


def test_volatility_note_reads_the_scorecard(tmp_path):
    import json
    import environment
    path = tmp_path / "v.json"
    path.write_text(json.dumps({"macro": {"vix_score": {"verdict": "REVERSED"}, "vix_level": {"horizons": {"1M": {"corr": 0.44, "t_stat": 2.8, "samples": 35}}}}}))
    assert "not a forward signal" in environment.volatility_scorecard_note(path)
    path.write_text(json.dumps({"macro": {}}))
    assert environment.volatility_scorecard_note(path) is None
