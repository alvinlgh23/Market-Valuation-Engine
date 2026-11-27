"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { factorExposure } from "../../lib/channel-exposure";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";

/** Your holdings moved by these price-split factors over 3 months (a point or more), as laser bars. */
const CARRY_MOVE = -0.08;   // USD/JPY falling 8% (the yen jumping), the same scenario the Today alert uses

/** Scenario, not a measured move: each holding's measured yen-carry sensitivity times an 8% jump in the yen. */
export function carryScenario(drivers: DriverRow[]) {
  return drivers
    .map((d) => ({ ticker: d.ticker, beta: d.attribution?.betas?.yen_carry }))
    .filter((d): d is { ticker: string; beta: number } => typeof d.beta === "number" && Number.isFinite(d.beta))
    .map((d) => ({ ticker: d.ticker, value: d.beta * CARRY_MOVE }))
    .filter((d) => d.value <= -0.005)
    .sort((a, b) => a.value - b.value)
    .slice(0, 4);
}

export function HoldingsFactorBars({ factors, empty, labels, carryScenario: showCarry = false }: { factors: string[]; empty?: string; labels?: Record<string, string>; carryScenario?: boolean }) {
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  useEffect(() => { let active = true; loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); }); return () => { active = false; }; }, []);
  if (!drivers) return <p className="ch-quiet">Reading your holdings…</p>;
  const touched = factorExposure(factors, drivers).filter((f) => f.holdings.length);
  const carryQuiet = showCarry && factors.includes("yen_carry") && !touched.some((f) => f.factor === "yen_carry");
  const scenario = carryQuiet ? carryScenario(drivers) : [];
  const scenarioLine = carryQuiet ? <p className="ch-quiet ch-scenario">{labels?.yen_carry ?? "Yen carry"}: no holding moved a point or more yet.{scenario.length ? ` If the yen jumped 8% (a scenario from each stock's measured sensitivity): ${scenario.map((s) => `${s.ticker} −${Math.abs(s.value * 100).toFixed(1)}%`).join(" · ")}.` : ""}</p> : null;
  if (!touched.length) return scenarioLine ?? <p className="ch-quiet">{empty ?? "None of your holdings moved by a point or more through this over 3 months."}</p>;
  const max = Math.max(0.05, ...touched.flatMap((f) => f.holdings.map((h) => Math.abs(h.value))));
  return <div className="ch-holdings">{scenarioLine}{touched.map((f) => <div key={f.factor} className="ch-factor">
    <b>{labels?.[f.factor] ?? f.label}</b>
    <div className="ch-bars">{f.holdings.slice(0, 6).map((h) => <Link key={h.ticker} href={`/company/${h.ticker}`} className={h.value < 0 ? "down" : "up"}>
      <span>{h.ticker}</span><i style={{ width: `${(Math.abs(h.value) / max) * 100}%` }} /><em>{`${h.value < 0 ? "−" : "+"}${Math.abs(h.value * 100).toFixed(1)}%`}</em>
    </Link>)}</div>
  </div>)}</div>;
}
