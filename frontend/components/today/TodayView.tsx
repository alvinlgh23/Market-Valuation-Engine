"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { attentionItems, buildAlerts, dataAge, marketRead, pct, type Alert } from "../../lib/alerts.mjs";
import { axisTone, shortState } from "../../lib/judgment-tone.mjs";
import { sectorLeadershipBars } from "../../lib/dashboard-orchestration";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";
import { CARD_AXES, cellLabel, loadWatchlistSummary, resetWatchlistLoaders, type SummaryRow } from "../../lib/watchlist-summary";
import { refreshLine, useDailyRefresh } from "../../lib/daily-refresh";
import { loadWatchlistEvents, type WatchlistEvents } from "../../lib/watchlist-events";
import { Criteria } from "./Criteria";
import { StoryDigest } from "../story/MarketStoryView";

// Checklist 14.3 / 18.14: Today answers what needs attention next, then explains why holdings moved.
const WATCH_AXES = CARD_AXES;
const COMPACT_AXIS_HEADER: Record<string, string> = {
  flow: "Flow",
  crowding: "Crowd",
  macro: "Macro",
  expectations: "Est.",
  fundamentals: "Fund.",
  valuation: "Value"
};
const VISIBLE_ALERTS = 5;

function Card({ title, aside, children, className = "" }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`tdy-card ${className}`}>{title ? <header><h2>{title}</h2>{aside}</header> : null}{children}</section>;
}

function Holdings({ alert }: { alert: Alert }) {
  if (!alert.holdings?.length) return alert.holdingsNote ? <p className="tdy-alert-note">{alert.holdingsNote}</p> : null;
  return <div className="tdy-holdings">
    {alert.holdings.map((item) => <Link key={item.ticker} href={`/company/${item.ticker}`} className="tdy-chip">{item.ticker} <b className={item.value < 0 ? "down" : "up"}>{pct(item.value)}</b></Link>)}
    {alert.more ? <span className="tdy-more">+{alert.more} more</span> : null}
    {alert.holdingsLabel ? <span className="tdy-more">{alert.holdingsLabel}</span> : null}
  </div>;
}

function AlertRow({ alert }: { alert: Alert }) {
  return <li className={`tdy-alert tone-${alert.tone}`}>
    <Criteria criteria={alert.criteria} block>
      <div className="tdy-alert-head">
        <Link href={alert.href}><i aria-hidden="true" />{alert.title}</Link>
        <span className="tdy-metric">{alert.metric}</span>
      </div>
    </Criteria>
    <Holdings alert={alert} />
  </li>;
}

function compactCellText(label: string) {
  return label.replace(/^Beyond model · /, ">").replace(/^Beyond model$/, "Beyond");
}


// P20 item 11: the product's core answer first - for each holding, does the price agree with the business?
const AGREEMENT: Record<string, { label: string; order: number; tone: string }> = {
  OPPOSED: { label: "Price and business disagree", order: 0, tone: "opposed" },
  ALIGNED: { label: "Price and business agree", order: 1, tone: "aligned" },
  OUTSIDE: { label: "Moved with outside forces", order: 2, tone: "outside" },
  UNCLEAR: { label: "No clear reading", order: 3, tone: "unclear" },
};

function HoldingVerdicts({ summary }: { summary: SummaryRow[] | null }) {
  if (!summary) return <section className="tdy-card tdy-verdicts" aria-label="Your holdings"><header><h2>Your holdings</h2></header><p className="tdy-muted">Reading your holdings…</p></section>;
  const rows = summary.filter((row) => row.conclusion?.agreement)
    .sort((a, b) => (AGREEMENT[a.conclusion!.agreement]?.order ?? 9) - (AGREEMENT[b.conclusion!.agreement]?.order ?? 9) || a.ticker.localeCompare(b.ticker));
  if (!rows.length) return null;
  const opposed = rows.filter((row) => row.conclusion!.agreement === "OPPOSED").length;
  const outside = rows.filter((row) => row.conclusion!.agreement === "OUTSIDE").length;
  return <section className="tdy-card tdy-verdicts" aria-label="Your holdings: price against business">
    <header>
      <h2>Your holdings: price against business</h2>
      <small>{opposed ? `${opposed} where the price and the filings point opposite ways` : "No holding where price and business disagree"}{outside ? ` · ${outside} moved mostly with outside forces` : ""}</small>
    </header>
    <ul>{rows.map((row) => {
      const c = row.conclusion!, meta = AGREEMENT[c.agreement] ?? AGREEMENT.UNCLEAR, short = c.short ?? null;
      return <li key={row.ticker}><Link href={`/company/${row.ticker}`}>
        <b>{row.ticker}</b>
        <span className={`tdy-agree is-${meta.tone}`}>{meta.label}</span>
        <span className="tdy-verdict-line">{[short?.business, short?.price, short?.value].filter(Boolean).join(" · ") || "Open the card for the full reading"}</span>
      </Link></li>;
    })}</ul>
    <p className="tdy-muted">Fixed rules on the filings, analysts&apos; estimates and what moved the price. A description, not a forecast or a recommendation.</p>
  </section>;
}

export function TodayView({ system, status }: { system: ResearchSystem; status?: ReactNode }) {
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  const [summary, setSummary] = useState<SummaryRow[] | null>(null);
  const [events, setEvents] = useState<WatchlistEvents | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  // P20 item 6: when today's background refresh finishes, read its precomputed results again.
  const refresh = useDailyRefresh(useCallback(() => { resetWatchlistLoaders(); setReloadKey((key) => key + 1); }, []));
  const refreshNote = refreshLine(refresh);

  useEffect(() => {
    let active = true;
    loadWatchlistEvents().then((value) => { if (active) setEvents(value); });
    loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); });
    loadWatchlistSummary().then((rows) => { if (active) setSummary(rows); });
    return () => { active = false; };
  }, [reloadKey]);

  const environment = system.environment;
  const now = useMemo(() => new Date(), []);
  const today = now.toLocaleDateString("en-CA");
  const age = dataAge(environment?.as_of, today);
  const alerts = useMemo(() => buildAlerts({ environment, drivers: drivers ?? [], summary: summary ?? [] }), [environment, drivers, summary]);
  const read = marketRead(alerts, environment);
  const attention = useMemo(() => attentionItems({ events: events ?? undefined, summary: summary ?? [], environment, today }), [events, summary, environment, today]);
  const loading = drivers == null || summary == null;
  const shown = showAll ? alerts : alerts.slice(0, VISIBLE_ALERTS);
  const sectors = sectorLeadershipBars(system, 4);

  return <div className="tdy">
    <header className="tdy-top">
      <div>
        <h1>Today</h1>
        <p suppressHydrationWarning>{now.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" })}</p>
      </div>
      <div className="tdy-top-right">{status}</div>
    </header>

    {refreshNote ? <div className={`data-refresh tone-${refreshNote.tone}`} role="status"><i aria-hidden="true" />{refreshNote.text}</div> : null}

    {age.stale ? <div className="tdy-stale" role="status" suppressHydrationWarning>
      <i aria-hidden="true" />Data is from {environment?.as_of ?? "an unknown date"}{age.days != null ? `, ${age.days} business days ago` : ""}. Alerts describe that date, not today.
    </div> : null}


    <HoldingVerdicts summary={summary} />

    <div className="tdy-grid tdy-grid-top">
      <Card className="tdy-read">
        {read.chip ? <span className="tdy-pill">{read.chip}</span> : null}
        <p className="tdy-headline">{loading ? "Reading your holdings…" : read.headline}</p>
        {!loading ? <p className="tdy-sub">{read.note}</p> : null}
      </Card>
      <StoryDigest />
    </div>

    <Card title="Needs your attention" aside={<small>Scheduled events, changed readings and tested patterns</small>} className="tdy-alerts tdy-attention">
      {events == null || summary == null ? <p className="tdy-empty">Checking your holdings&apos; calendar…</p> : null}
      {events != null && summary != null && !attention.length ? <p className="tdy-empty">Nothing needs your attention: no earnings or Fed decision in the next three weeks, and no reading changed.</p> : null}
      <ul>{attention.map((item) => <AlertRow key={item.id} alert={item} />)}</ul>
    </Card>

    <Card title="Why your holdings moved · last 3 months" aside={<small>Explains the past; not a forecast</small>} className="tdy-alerts tdy-moved">
      {loading && !alerts.length ? <p className="tdy-empty">Reading your holdings…</p> : null}
      {!loading && !alerts.length ? <p className="tdy-empty">No macro condition moved your holdings by a point or more.</p> : null}
      <ul>{shown.map((alert) => <AlertRow key={alert.id} alert={alert} />)}</ul>
      {alerts.length > VISIBLE_ALERTS ? <button type="button" className="tdy-toggle" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer" : `Show ${alerts.length - VISIBLE_ALERTS} more`}</button> : null}
    </Card>

    <div className="tdy-grid tdy-grid-bottom">
      <Card title="Watchlist" aside={<Link href="/companies">Open &amp; edit</Link>} className="tdy-watch">
        {summary == null ? <p className="tdy-empty">Loading…</p> : <div role="table" aria-label="Watchlist readings">
          <div className="tdy-watch-row tdy-watch-head" role="row"><span role="columnheader">Ticker</span>{WATCH_AXES.map(([key, label]) => <span key={key} role="columnheader" title={label}>{COMPACT_AXIS_HEADER[key] ?? label}</span>)}</div>
          {summary.map((row) => <Link key={row.ticker} href={`/company/${row.ticker}`} className="tdy-watch-row" role="row">
            <b role="rowheader">{row.ticker}</b>
            {WATCH_AXES.map(([key, fullLabel]) => {
              const state = row.axes[key];
              const change = row.changed.find((item) => item.axis === key && item.origin === "COMPANY");
              const rawText = cellLabel(shortState(state), key, row);
              return <span key={key} role="cell" className={`tone-${state ? axisTone(key, state) : "unknown"}${change ? " changed" : ""}`} title={`${fullLabel}: ${state ?? "No card yet"}${change ? ` (was ${change.from}, changed ${change.on})` : ""}`}>{compactCellText(rawText)}</span>;
            })}
          </Link>)}
        </div>}
      </Card>
      <Card title="Sectors · 1M vs S&P 500" aside={<Link href="/markets">Open</Link>} className="tdy-sectors">
        {sectors.length ? <ul>{sectors.map((sector) => <li key={sector.ticker}><Link href={sector.href} title={sector.name}><span>{sector.ticker}</span><small>{sector.name}</small><b className={sector.value < 0 ? "down" : "up"}>{pct(sector.value)}</b></Link></li>)}</ul> : <p className="tdy-empty">No sector readings</p>}
      </Card>
    </div>
  </div>;
}
