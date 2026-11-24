"""Year-on-year change is matched by month, so a missing month cannot stretch it to 13 months."""
import Valuation_model as vm


def series(skip=()):
    rows, level = [], 100.0
    for year in (2024, 2025, 2026):
        for month in range(1, 13):
            level += 0.25
            if (year, month) not in skip and not (year == 2026 and month > 10):
                rows.append((f"{year}-{month:02d}-01", level))
    return rows


def test_yoy_with_complete_months_is_twelve_months():
    rows = series()
    by_month = dict(rows)
    expected = by_month["2026-10-01"] / by_month["2025-10-01"] - 1
    assert abs(vm.latest_yoy(rows, 12)[0] - expected) < 1e-12


def test_missing_october_uses_the_latest_month_with_a_year_ago_match():
    # October 2025 CPI was never published: October 2026 has no year-ago month, so September 2026 is used.
    rows = series(skip={(2025, 10)})
    by_month = dict(rows)
    expected = by_month["2026-09-01"] / by_month["2025-09-01"] - 1
    assert abs(vm.latest_yoy(rows, 12)[0] - expected) < 1e-12
    positional = rows[-1][1] / rows[-13][1] - 1          # the old row-count method spanned 13 months
    assert positional > expected


def test_too_short_is_unavailable():
    assert vm.latest_yoy([("2026-01-01", 1.0)], 12) == (None, None)
