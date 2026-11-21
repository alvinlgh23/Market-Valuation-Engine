"""Checklist 7.2: overall engine rank against the new within-tier volatility-adjusted rank."""
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Valuation_model as vm  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    rows = vm.compute_sectors()
table = [{"overall_rank": index, "ticker": row["ticker"], "name": row["name"], "tier": row["tier"], "rank_in_tier": row["rank_in_tier"],
          "score": row["score"], "rel_3m": row["rel_3m"], "rel_3m_vol_adj": row.get("rel_3m_vol_adj"), "vol_adj_score": row.get("vol_adj_score"), "as_of": row["as_of"]}
         for index, row in enumerate(rows, 1)]
Path("data/sector_tier_comparison.json").write_text(json.dumps(table, indent=2) + "\n")
for tier in vm.TIER_ORDER:
    print(tier)
    for item in sorted((row for row in table if row["tier"] == tier), key=lambda row: row["rank_in_tier"] or 99):
        print(f"  #{item['rank_in_tier']}  {item['ticker']:5} {item['name'][:28]:28} overall #{item['overall_rank']:<3} 3M {item['rel_3m']:+.1%}  3M/vol {item['rel_3m_vol_adj']:+.2f}")
