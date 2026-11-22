"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";

// Checklist 10.5: Today leads with what is moving the watchlist (macro or company), not with the risk
// regime, which the scorecard did not find predictive. The regime stays as a small context label.
export function TodayHeadline({ regime, regimeSummary, asOf }: { regime?: string; regimeSummary?: string; asOf?: string | null }) {
  const [rows, setRows] = useState<DriverRow[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((value) => { if (active) setRows(value); }); return () => { active = false; }; }, []);
  const count = (kinds: string[]) => (rows ?? []).filter((row) => kinds.includes(row.reading?.kind ?? "")).length;
  const outside = count(["noise"]), company = count(["company", "fundamentals"]), watch = count(["watch"]), fundamentals = count(["fundamentals"]);
  const movers = (rows ?? []).filter((row) => ["company", "fundamentals"].includes(row.reading?.kind ?? ""));
  return <header className="today-regime today-headline">
    <span>Your watchlist · 3 months</span>
    <h1>{rows ? (rows.length ? `${outside} of ${rows.length} moved with macro, market or sector; ${company} on company news` : "Watchlist drivers unavailable") : "Working out what moved your watchlist…"}</h1>
    <div className="today-headline-chips">
      {watch ? <span>{watch} with some company-specific move</span> : null}
      {fundamentals ? <span className="pd-kind-fundamentals">{fundamentals} with estimates moving the same way</span> : null}
      {movers.map((row) => <Link key={row.ticker} href={`/company/${row.ticker}`} className="today-mover" title={row.reading?.label}>{row.ticker} · {row.reading?.short ?? row.reading?.label}</Link>)}
      {regime ? <span className="today-context" title={`${regimeSummary ?? ""}\nContext only: the regime did not predict returns in the scorecard.`}>Market regime: {regime}</span> : null}
      {asOf ? <small>data {asOf}</small> : null}
    </div>
  </header>;
}
