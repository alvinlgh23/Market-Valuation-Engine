"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";

// Owner request 2026-11-22 (follow-up to checklist 10.5): Market context also leads with what macro did to
// the watchlist, not with the risk regime, which the scorecard did not find predictive.
export function MarketContextHeadline({ regime, regimeSummary }: { regime?: string; regimeSummary?: string }) {
  const [rows, setRows] = useState<DriverRow[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((value) => { if (active) setRows(value); }); return () => { active = false; }; }, []);
  const totals = new Map<string, { label: string; total: number; names: { ticker: string; value: number }[] }>();
  for (const row of rows ?? []) {
    for (const [factor, value] of Object.entries(row.attribution?.windows?.["3M"]?.macro_by_factor ?? {})) {
      const entry = totals.get(factor) ?? { label: row.attribution?.factor_labels?.[factor] ?? factor, total: 0, names: [] };
      entry.total += Math.abs(value);
      entry.names.push({ ticker: row.ticker, value });
      totals.set(factor, entry);
    }
  }
  const top = Array.from(totals.values()).sort((a, b) => b.total - a.total)[0];
  const names = top ? top.names.filter((item) => Math.abs(item.value) >= 0.01).sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 4) : [];
  return <header className="today-regime today-headline">
    <span>Macro and your watchlist · 3 months</span>
    <h1>{!rows ? "Working out which macro factor moved your watchlist…" : top ? `Biggest macro push on your watchlist: ${top.label.toLowerCase()}` : "No macro factor split available for the watchlist"}</h1>
    <div className="today-headline-chips">
      {names.map((item) => <Link key={item.ticker} href={`/company/${item.ticker}`} className="today-mover" title={`${top?.label}: ${(item.value * 100).toFixed(1)}% of the 3-month move`}>
        {item.ticker} {item.value >= 0 ? "+" : ""}{(item.value * 100).toFixed(1)}%
      </Link>)}
      {regime ? <span className="today-context" title={`${regimeSummary ?? ""}\nContext only: the regime did not predict returns in the scorecard.`}>Market regime: {regime}</span> : null}
    </div>
  </header>;
}
