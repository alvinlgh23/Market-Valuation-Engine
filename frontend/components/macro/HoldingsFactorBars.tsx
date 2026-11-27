"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { factorExposure } from "../../lib/channel-exposure";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";

/** Your holdings moved by these price-split factors over 3 months (a point or more), as laser bars. */
export function HoldingsFactorBars({ factors, empty, labels }: { factors: string[]; empty?: string; labels?: Record<string, string> }) {
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); }); return () => { active = false; }; }, []);
  if (!drivers) return <p className="ch-quiet">Reading your holdings…</p>;
  const touched = factorExposure(factors, drivers).filter((f) => f.holdings.length);
  if (!touched.length) return <p className="ch-quiet">{empty ?? "None of your holdings moved by a point or more through this over 3 months."}</p>;
  const max = Math.max(0.05, ...touched.flatMap((f) => f.holdings.map((h) => Math.abs(h.value))));
  return <div className="ch-holdings">{touched.map((f) => <div key={f.factor} className="ch-factor">
    <b>{labels?.[f.factor] ?? f.label}</b>
    <div className="ch-bars">{f.holdings.slice(0, 6).map((h) => <Link key={h.ticker} href={`/company/${h.ticker}`} className={h.value < 0 ? "down" : "up"}>
      <span>{h.ticker}</span><i style={{ width: `${(Math.abs(h.value) / max) * 100}%` }} /><em>{`${h.value < 0 ? "−" : "+"}${Math.abs(h.value * 100).toFixed(1)}%`}</em>
    </Link>)}</div>
  </div>)}</div>;
}
