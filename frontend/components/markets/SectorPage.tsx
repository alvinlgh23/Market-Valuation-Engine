"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { sectorSentence, type SectorFlowRow, type SectorResearchObject } from "../../lib/market-research";
import { GICS_PARENT, holdingsForFund } from "../../lib/sector-holdings";
import { loadTodayHoldings } from "../../lib/today-client";
import type { TodayHolding } from "../../lib/today-model";
import { useProView } from "../../lib/view-mode";
import { GICS_NAME, pts } from "./MarketsOverview";

// One sector, rebuilt around the sector you clicked (owner-approved 2026-11-27): how it did against the S&P 500,
// which of your holdings sit in it, whether money and participation backed the move, and - only where one is
// written - a descriptive map of how the industry works. Every number comes from the sector engine and
// sector_flow.py; nothing is recalculated here. The old raw-JSON "Full report" view is gone.

const HORIZONS: Array<["rel1m" | "rel3m" | "rel6m", string]> = [["rel1m", "1 month"], ["rel3m", "3 months"], ["rel6m", "6 months"]];
const CROWD_PLAIN: Record<string, string> = {
  CROWDED: "Crowded: most of its big stocks are rising, trading is heavy and it has led for months. Late money is piling in.",
  EXTENDED: "Getting stretched: two of the three crowding signs are showing.",
  NEUTRAL: "Normal: no sign of a crowd chasing it or of investors deserting it.",
  UNLOVED: "Unloved: few of its big stocks are rising and it has lagged for months. Investors have moved elsewhere.",
};

function share(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? Math.round(value * 100) : null;
}

function flowLines(flow: SectorFlowRow | undefined, pro: boolean) {
  if (!flow) return [];
  const lines: Array<[string, string]> = [];
  const b50 = share(flow.breadth_50), b200 = share(flow.breadth_200);
  if (b50 != null) lines.push(["Participation", pro
    ? `breadth_50 ${b50}%${b200 != null ? ` · breadth_200 ${b200}%` : ""} (${flow.breadth_basis ?? "top holdings"})`
    : `${b50}% of its biggest stocks are above their 50-day average${b200 != null ? `; ${b200}% above their 200-day average` : ""}.`]);
  const dv = share(flow.dollar_volume_percentile);
  if (dv != null) lines.push(["Trading activity", pro
    ? `20-day dollar volume, percentile in own history: ${dv}`
    : `Trading in the fund is heavier than on ${dv} of every 100 days in its record.`]);
  const ud = flow.updown_volume_20d;
  if (typeof ud === "number" && Number.isFinite(ud)) lines.push(["Buying vs selling", pro
    ? `Up-day / down-day volume, 20 days: ${ud.toFixed(2)}`
    : ud >= 1.15 ? `More shares traded on up days than down days over the last 20 days (${ud.toFixed(2)} to 1).`
      : ud <= 0.87 ? `More shares traded on down days than up days over the last 20 days (${ud.toFixed(2)} to 1).`
        : `Trading was about even between up and down days over the last 20 days.`]);
  return lines;
}

export function SectorPage({ sector, sectorList }: { sector: SectorResearchObject & { flow?: SectorFlowRow }; sectorList: SectorResearchObject[] }) {
  const [pro, setPro] = useProView();
  const [holdings, setHoldings] = useState<TodayHolding[] | null>(null);
  useEffect(() => { let active = true; loadTodayHoldings().then((d) => { if (active) setHoldings(d?.holdings ?? []); }); return () => { active = false; }; }, []);

  const name = GICS_NAME[sector.ticker] ?? sector.name;
  const parent = GICS_PARENT[sector.ticker] && GICS_PARENT[sector.ticker] !== sector.ticker ? sectorList.find((s) => s.ticker === GICS_PARENT[sector.ticker]) : undefined;
  const children = sectorList.filter((s) => s.ticker !== sector.ticker && GICS_PARENT[s.ticker] === sector.ticker && s.rel1m != null);
  const mine = holdings ? holdingsForFund(holdings, sector.ticker) : [];
  const flow = sector.flow;
  const crowd = flow?.crowding_state ? String(flow.crowding_state).toUpperCase() : null;
  const lines = flowLines(flow, pro);
  const nodes = sector.structure.nodes;

  return <div className="sec">
    <div className="markets-crumb-row"><Link className="markets-back-link" href="/markets">← All sectors</Link>{parent ? <Link className="markets-back-link" href={`/markets?sector=${parent.slug}`}>Part of {GICS_NAME[parent.ticker] ?? parent.name} →</Link> : null}</div>
    <header className="sec-hero glow-card">
      <div className="sec-hero-top">
        <span className="sec-kicker">{sector.ticker} · {GICS_NAME[sector.ticker] ? "S&P 500 sector" : "industry / theme fund"}{sector.lastUpdated && /^\d{4}-/.test(sector.lastUpdated) ? ` · data to ${sector.lastUpdated}` : ""}</span>
        <div className="mc-mode" role="group" aria-label="View">
          <button type="button" aria-pressed={!pro} className={!pro ? "on" : ""} onClick={() => setPro(false)}>Plain</button>
          <button type="button" aria-pressed={pro} className={pro ? "on" : ""} onClick={() => setPro(true)}>Pro view</button>
        </div>
      </div>
      <h1 className="display-h">{name}</h1>
      <p className="sec-sentence">{sectorSentence(sector)}</p>
      <div className="sec-nums">{HORIZONS.map(([key, label]) => { const v = sector[key]; return <div key={key} className={v == null ? "" : v >= 0 ? "up" : "down"}><span>{label}</span><b>{pts(v)}</b><small>points vs S&amp;P 500</small></div>; })}</div>
    </header>

    <section className="tdy-card sec-card">
      <h2>Your holdings in this {GICS_NAME[sector.ticker] ? "sector" : "fund's area"}</h2>
      {holdings == null ? <p className="sec-quiet">Loading your watchlist…</p>
        : mine.length ? <div className="sec-holdings">{mine.map((h) => <Link key={h.ticker} href={`/company/${h.ticker}?from=markets&sector=${sector.slug}`}><b>{h.ticker}</b><span>{h.name ?? ""}</span>{h.short?.business ? <small>{h.short.business}</small> : null}</Link>)}</div>
          : <p className="sec-quiet">None of your watchlist companies are in this {GICS_NAME[sector.ticker] ? "sector" : "fund's area"}.</p>}
    </section>

    {lines.length || crowd ? <section className="tdy-card sec-card">
      <h2>Is money backing the move?</h2>
      {crowd ? <p className={`sec-crowd ${crowd.toLowerCase()}`}>{pro ? `Crowding state: ${crowd} (breadth, dollar-volume and 3M relative-strength percentiles)` : CROWD_PLAIN[crowd] ?? crowd}</p> : null}
      <dl className="sec-flow">{lines.map(([label, text]) => <div key={label}><dt>{label}</dt><dd>{text}</dd></div>)}</dl>
      {pro && flow?.as_of ? <p className="sec-quiet">Flow measurements as of {flow.as_of}. Breadth uses about 10 top holdings, not the full constituent list.</p> : null}
    </section> : null}

    {children.length ? <section className="tdy-card sec-card">
      <h2>Industries inside it</h2>
      <div className="sec-children">{children.map((c) => <Link key={c.ticker} href={`/markets?sector=${c.slug}`} className={(c.rel1m ?? 0) >= 0 ? "up" : "down"}><span>{c.name}</span><b>{pts(c.rel1m)}</b><small>{c.ticker} · 1 month</small></Link>)}</div>
    </section> : null}

    {nodes.length ? <section className="tdy-card sec-card">
      <h2>How this industry works</h2>
      <p className="sec-quiet">A written description of the industry&apos;s parts, not a measurement.</p>
      <ol className="sec-chain">{nodes.map((n) => <li key={n.id}><b>{n.title}</b>{pro ? <small>{n.role}</small> : null}<span>{n.description}</span><em>{n.companies.slice(0, 5).map((t) => <Link key={t} href={`/company/${t}?from=markets&sector=${sector.slug}`}>{t}</Link>)}</em></li>)}</ol>
    </section> : null}
  </div>;
}
