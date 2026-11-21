"""Checklists 7.5/7.6: default valuation next to company-specific spreads and the extended horizon (stop point)."""
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from intrinsic_valuation import build_valuation_report, collect_valuation_data  # noqa: E402

rows = []
for ticker in json.loads(Path("data/watchlist.json").read_text())["tickers"]:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            report = build_valuation_report(ticker, data=collect_valuation_data(ticker))
    except Exception as exc:  # noqa: BLE001
        rows.append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})
        continue
    scenarios = report.get("scenarios") or {}
    default = {name: (scenarios.get(name) or {}).get("fair_value_per_share") for name in ("bear", "base", "bull")}
    rows.append({
        "ticker": ticker, "price": (report.get("company") or {}).get("current_market_price"),
        "default_fair_value": default if scenarios else None,
        "withheld_reason": None if scenarios else (report.get("data_quality") or {}).get("reason"),
        "default_reverse_dcf": (report.get("reverse_dcf") or {}).get("status"),
        "company_spreads": report.get("company_spread_scenarios"),
        "extended_horizon": report.get("extended_horizon"),
    })
Path("data/valuation_parallel_comparison.json").write_text(json.dumps(rows, indent=2, default=str) + "\n")
fmt = lambda values: "withheld" if not values else " / ".join("n/a" if value is None else f"{value:,.0f}" for value in values.values())
for row in rows:
    if "error" in row:
        print(f"{row['ticker']:5} ERROR {row['error'][:80]}")
        continue
    spread = row["company_spreads"] or {}
    ext = row["extended_horizon"] or {}
    spread_text = fmt(spread.get("fair_value")) if spread.get("state") == "COMPUTED" else spread.get("state", "—")
    if spread.get("state") == "COMPUTED":
        spread_text += f"  (growth ±{spread['basis']['growth_spread']:.1%}, margin ±{spread['basis']['margin_spread']:.1%})"
    ext_text = ext.get("state", "—")
    if ext.get("state") == "COMPUTED":
        ext_text = f"{fmt(ext['fair_value'])}  growth {ext['observed_growth']:.0%} > cap {ext['type_cap']:.0%}; reverse {ext['reverse_dcf'].get('status')}; checks {'pass' if ext['checks_passed'] else 'FAIL'}"
    print(f"{row['ticker']:5} price {row['price']}\n      default   {fmt(row['default_fair_value'])}  reverse {row['default_reverse_dcf']}\n      7.5       {spread_text}\n      7.6       {ext_text}")
