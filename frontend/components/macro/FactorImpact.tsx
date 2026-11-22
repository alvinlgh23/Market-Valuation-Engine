"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { loadWatchlistDrivers, type DriverRow as Row } from "../../lib/watchlist-drivers";

// Checklist 10.4: which watchlist companies a macro factor moved over the last three months,
// from the same attribution as the watchlist column (one shared request for every tile).

const MIN_EFFECT = 0.01;   // show companies the factor moved by at least one percentage point
const UNMEASURED: Record<string, string> = { liquidity: "No market proxy; not split out of prices" };

export function FactorImpact({ factor, limit = 3 }: { factor: string; limit?: number }) {
  const [rows, setRows] = useState<Row[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((value) => { if (active) setRows(value); }); return () => { active = false; }; }, []);
  if (UNMEASURED[factor]) return <small className="env-impact env-impact-none">{UNMEASURED[factor]}</small>;
  if (!rows) return <small className="env-impact env-impact-none">Watchlist effect…</small>;
  const effects = rows
    .map((row) => ({ ticker: row.ticker, value: row.attribution?.windows?.["3M"]?.macro_by_factor?.[factor] }))
    .filter((item): item is { ticker: string; value: number } => typeof item.value === "number" && Math.abs(item.value) >= MIN_EFFECT)
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  if (!effects.length) return <small className="env-impact env-impact-none">No watchlist name moved ≥1 pt by this in 3 months</small>;
  const total = effects.length;
  return <div className="env-impact" title={effects.map((item) => `${item.ticker} ${(item.value * 100).toFixed(1)}%`).join("\n")}>
    <span>3M effect on your watchlist</span>
    {effects.slice(0, limit).map((item) => <Link key={item.ticker} href={`/company/${item.ticker}`} className={item.value < 0 ? "down" : "up"}>
      {item.ticker} <b>{item.value >= 0 ? "+" : ""}{(item.value * 100).toFixed(1)}%</b>
    </Link>)}
    {total > limit ? <small>+{total - limit} more</small> : null}
  </div>;
}
