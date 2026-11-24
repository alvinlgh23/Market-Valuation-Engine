"""Checklist 17: the scenario gate's helpers."""
import scenario_validation as sv


def test_episodes_counts_separate_runs():
    assert sv.episodes([True, True, False, True, False, False, True, True]) == 3
    assert sv.episodes([False, False]) == 0


def test_verdict_needs_t_of_two_and_beating_the_baseline():
    assert sv.verdict(2.4, None) == "PASSED"
    assert sv.verdict(0.4, None) == "FAILED"
    assert sv.verdict(None, None) == "INSUFFICIENT_SAMPLE"
    assert sv.verdict(2.4, 0.70, baseline_share=0.74) == "FAILED"


def test_link_test_separates_a_real_link_from_noise():
    signal = list(range(30))
    linked = sv.link_test(signal, [2 * x + (1 if x % 2 else -1) for x in signal])
    assert linked["verdict"] == "LINKED" and linked["corr"] > 0.99
    noise = sv.link_test(signal, [1, -1, 2, -2, 0, 1, -1, 2, -2, 0] * 3)
    assert noise["verdict"] == "NO_LINK"
    assert sv.link_test([1, 2], [1, 2])["verdict"] == "INSUFFICIENT_SAMPLE"
