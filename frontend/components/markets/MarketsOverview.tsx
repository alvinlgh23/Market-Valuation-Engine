"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { holdingsBySector } from "../../lib/sector-holdings";
import { loadTodayHoldings } from "../../lib/today-client";
import { RotationPlane } from "./RotationPlane";
import { sectorSentence, type SectorResearchObject } from "../../lib/market-research";

// Checklist 19.2: Markets opens on the whole market - the 11 GICS sectors against the S&P 500 - with
// no sector preselected. Theme and asset ETFs (semiconductors, uranium, gold...) sit below as a second tier.

export const GICS_SECTORS = ["XLK", "XLC", "XLY", "XLP", "XLV", "XLF", "XLE", "XLI", "XLB", "XLU", "XLRE"];
const GICS_NAME: Record<string, string> = {
  XLK: "Technology", XLC: "Communication", XLY: "Consumer discretionary", XLP: "Consumer staples", XLV: "Health care", XLF: "Financials",
  XLE: "Energy", XLI: "Industrials", XLB: "Materials", XLU: "Utilities", XLRE: "Real estate"
};
type Horizon = "rel1m" | "rel3m" | "rel6m";
const HORIZONS: Array<[Horizon, string]> = [["rel1m", "1 month"], ["rel3m", "3 months"], ["rel6m", "6 months"]];

function pts(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? `${value >= 0 ? "+" : "−"}${Math.abs(value * 100).toFixed(1)}` : "—";
}

function tone(value: number | null | undefined) {
  if (typeof value !== "number") return "flat";
  if (value > 0.03) return "up-strong"; if (value > 0) return "up";
  if (value < -0.03) return "down-strong"; return "down";
}

export function MarketsOverview({ sectorList, asOf }: { sectorList: SectorResearchObject[]; asOf?: string | null }) {
  const [horizon, setHorizon] = useState<Horizon>("rel1m");
  const [view, setView] = useState<"heat" | "map">("heat");
  const [held, setHeld] = useState<Record<string, string[]>>({});
  useEffect(() => { let active = true; loadTodayHoldings().then((d) => { if (active && d) setHeld(holdingsBySector(d.holdings)); }); return () => { active = false; }; }, []);
  const gics = GICS_SECTORS.map((ticker) => sectorList.find((item) => item.ticker === ticker)).filter((item): item is SectorResearchObject => !!item);
  const themes = sectorList.filter((item) => !GICS_SECTORS.includes(item.ticker) && item[horizon] != null)
    .sort((a, b) => (b[horizon] ?? 0) - (a[horizon] ?? 0));
  const ranked = [...gics].sort((a, b) => (b[horizon] ?? -9) - (a[horizon] ?? -9));
  const leaders = ranked.slice(0, 2).map((item) => GICS_NAME[item.ticker].toLowerCase());
  const laggards = ranked.slice(-2).map((item) => GICS_NAME[item.ticker].toLowerCase());
  const label = HORIZONS.find(([key]) => key === horizon)?.[1];
  return <div className="mkt">
    <header className="tdy-top">
      <div><h1>Markets</h1><p>How the 11 sectors of the S&amp;P 500 did against the index{asOf ? ` · data to ${asOf}` : ""}</p></div>
      <div className="mkt-horizons" role="tablist" aria-label="Period">{HORIZONS.map(([key, text]) => <button key={key} type="button" role="tab" aria-selected={horizon === key} className={horizon === key ? "active" : ""} onClick={() => setHorizon(key)}>{text}</button>)}</div>
    </header>
    {ranked.length ? <p className="mkt-read">Over {label}, {leaders.join(" and ")} led the S&amp;P 500; {laggards.join(" and ")} lagged it.</p> : null}
    <div className="mkt-viewswitch" role="tablist" aria-label="View">
      <button type="button" role="tab" aria-selected={view === "heat"} className={view === "heat" ? "on" : ""} onClick={() => setView("heat")}>Heatmap</button>
      <button type="button" role="tab" aria-selected={view === "map"} className={view === "map" ? "on" : ""} onClick={() => setView("map")}>Map</button>
    </div>
    {view === "heat" ? <section className="mkt-heat" aria-label="Sectors against the S&P 500">
      {ranked.map((sector) => { const mine = held[sector.ticker] ?? []; return <Link key={sector.ticker} href={`/markets?sector=${sector.slug}`} className={`mkt-tile ${tone(sector[horizon])}`} title={sectorSentence(sector)}>
        <span>{GICS_NAME[sector.ticker]}</span>
        <b>{pts(sector[horizon])}</b>
        <small>{sector.ticker} · points vs S&amp;P 500</small>
        <em className="mkt-held">{mine.length ? <>{mine.slice(0, mine.length > 4 ? 3 : 4).map((t) => <i key={t}>{t}</i>)}{mine.length > 4 ? <i className="more">+{mine.length - 3}</i> : null}</> : null}</em>
      </Link>; })}
    </section> : <RotationPlane sectors={gics} names={GICS_NAME} held={held} />}
    <section className="tdy-card mkt-themes" aria-label="Themes and assets">
      <header><h2>Themes and assets</h2><small>Narrower ETFs, against the S&amp;P 500 · {label}</small></header>
      <ul>{themes.map((item) => <li key={item.ticker}><Link href={`/markets?sector=${item.slug}`}>
        <span><b>{item.ticker}</b><small>{item.name}</small></span>
        <span className="mkt-track"><i className={tone(item[horizon])} style={{ width: `${Math.min(50, Math.abs((item[horizon] ?? 0) * 100) * 2)}%`, [(item[horizon] ?? 0) < 0 ? "right" : "left"]: "50%" }} /></span>
        <em className={(item[horizon] ?? 0) >= 0 ? "up" : "down"}>{pts(item[horizon])}</em>
      </Link></li>)}</ul>
    </section>
  </div>;
}
