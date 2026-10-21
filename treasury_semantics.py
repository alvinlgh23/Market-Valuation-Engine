"""Maturity and unit metadata; provider levels are percentage yields."""
import math

MATURITIES = {"2YY=F": "2Y", "^FVX": "5Y", "^IRX": "3M"}


def treasury_curve(long_value, short_value, short_ticker, long_date=None, short_date=None, state="UNKNOWN"):
    short = MATURITIES.get(short_ticker)
    valid = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    aligned = bool(long_date and short_date and long_date == short_date)
    return {
        "value": long_value - short_value if valid(long_value) and valid(short_value) and short else None,
        "label": f"10Y–{short} curve" if short else "Treasury curve unavailable",
        "long_maturity": "10Y", "short_maturity": short,
        "source": f"Yahoo Finance ^TNX / {short_ticker or 'unavailable'}",
        "long_observed_at": long_date, "short_observed_at": short_date,
        "observation_timestamp": long_date if aligned else None,
        "units": "pp", "fallback": short != "2Y",
        "source_state": state,
        "period_alignment": "ALIGNED" if aligned else "MISMATCH" if long_date and short_date else "UNKNOWN",
    }
