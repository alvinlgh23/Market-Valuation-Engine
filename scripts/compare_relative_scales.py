"""Checklist 7.3: old absolute quality and heat scores next to the new relative readings, for the watchlist."""
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Valuation_model as vm  # noqa: E402
from company_verdict import sector_etf_for  # noqa: E402
from relative_scales import relative_readings  # noqa: E402

tickers = json.loads(Path("data/watchlist.json").read_text())["tickers"]
with contextlib.redirect_stdout(io.StringIO()):
    own_rows = {row["ticker"]: row for row in vm.company_quality_rows(tickers)}
    heat = {row["ticker"]: row for row in vm.heat_rows(tickers)}
peer_map = {}
for ticker in tickers:
    etf, _ = sector_etf_for(ticker, own_rows[ticker].get("sector"))
    peer_map[ticker] = [name for name in vm.SECTOR_CANDIDATES.get(etf or "", []) if name != ticker]
universe = sorted({name for peers in peer_map.values() for name in peers} | set(tickers))
with contextlib.redirect_stdout(io.StringIO()):
    all_rows = vm.company_quality_rows(universe)
table = []
for ticker in tickers:
    reading = relative_readings(ticker, peer_map[ticker], all_rows)
    table.append({"ticker": ticker, "old_quality_score": own_rows[ticker]["score"], "old_heat": heat[ticker]["heat"], "old_valuation_heat": heat[ticker]["valuation_heat"],
                  "quality_percentile_in_peers": reading["quality"].get("quality_percentile"), "peers": reading["quality"].get("peers"),
                  "price_to_sales": reading["valuation"].get("current"), "price_to_sales_percentile_own_history": reading["valuation"].get("percentile"),
                  "valuation_state": reading["valuation"].get("state"), "detail": reading})
Path("data/relative_scales_comparison.json").write_text(json.dumps(table, indent=2, default=str) + "\n")
fmt = lambda value, spec: "  n/a" if value is None else format(value, spec)
for row in table:
    print(f"{row['ticker']:5} quality {row['old_quality_score']:5.1f} -> peer pct {fmt(row['quality_percentile_in_peers'], '.0%'):>4} ({row['peers']} names) | "
          f"valuation heat {row['old_valuation_heat']:>3} -> P/S {fmt(row['price_to_sales'], '.1f'):>5} at {fmt(row['price_to_sales_percentile_own_history'], '.0%'):>4} of own history")
