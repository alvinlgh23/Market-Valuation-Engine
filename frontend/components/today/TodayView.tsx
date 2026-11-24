"use client";
import Link from "next/link";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { buildAlerts, dataAge, marketRead, pct, type Alert } from "../../lib/alerts.mjs";
import { axisTone, shortState } from "../../lib/judgment-tone.mjs";
import { sectorLeadershipBars } from "../../lib/dashboard-orchestration";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";
import { CARD_AXES, loadWatchlistSummary, type SummaryRow } from "../../lib/watchlist-summary";
import { Criteria } from "./Criteria";
import { StoryDigest } from "../story/MarketStoryView";

// Checklist 14.3: Today answers one question — what needs my attention — and nothing else.
// Every reading opens its criteria on hover; detail lives on the Macro, Markets and company pages.

const WATCH_AXES = CARD_AXES;
const VISIBLE_ALERTS = 5;

function Card({ title, aside, children, className = "" }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`tdy-card ${className}`}>{title ? <header><h2>{title}</h2>{aside}</header> : null}{children}</section>;
}

function Holdings({ alert }: { alert: Alert }) {
  if (!alert.holdings.length) return alert.holdingsNote ? <p className="tdy-alert-note">{alert.holdingsNote}</p> : null;
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

export function TodayView({ system, status }: { system: ResearchSystem; status?: ReactNode }) {
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  const [summary, setSummary] = useState<SummaryRow[] | null>(null);
  const [showAll, setShowAll] = useState(false);
  useEffect(() => {
    let active = true;
    loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); });
    loadWatchlistSummary().then((rows) => { if (active) setSummary(rows); });
    return () => { active = false; };
  }, []);

  const environment = system.environment;
  const now = useMemo(() => new Date(), []);
  const today = now.toLocaleDateString("en-CA");
  const age = dataAge(environment?.as_of, today);
  const alerts = useMemo(() => buildAlerts({ environment, drivers: drivers ?? [], summary: summary ?? [] }), [environment, drivers, summary]);
  const read = marketRead(alerts, environment);
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

    {age.stale ? <div className="tdy-stale" role="status" suppressHydrationWarning>
      <i aria-hidden="true" />Data is from {environment?.as_of ?? "an unknown date"}{age.days != null ? `, ${age.days} business days ago` : ""}. Alerts describe that date, not today.
    </div> : null}

    <div className="tdy-grid tdy-grid-top">
      <Card className="tdy-read">
        {read.chip ? <span className="tdy-pill">{read.chip}</span> : null}
        <p className="tdy-headline">{loading ? "Reading your holdings…" : read.headline}</p>
        {!loading ? <p className="tdy-sub">{read.note}</p> : null}
      </Card>
      <StoryDigest />
    </div>

    <Card title="Needs your attention" aside={<small>Hover any line for its rule</small>} className="tdy-alerts">
      {loading && !alerts.length ? <p className="tdy-empty">Reading your holdings…</p> : null}
      {!loading && !alerts.length ? <p className="tdy-empty">Nothing needs your attention: no condition is weighing on your holdings and no card changed.</p> : null}
      <ul>{shown.map((alert) => <AlertRow key={alert.id} alert={alert} />)}</ul>
      {alerts.length > VISIBLE_ALERTS ? <button type="button" className="tdy-toggle" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer" : `Show ${alerts.length - VISIBLE_ALERTS} more`}</button> : null}
    </Card>

    <div className="tdy-grid tdy-grid-bottom">
      <Card title="Watchlist" aside={<Link href="/companies">Open</Link>} className="tdy-watch">
        {summary == null ? <p className="tdy-empty">Loading…</p> : <div role="table" aria-label="Watchlist readings">
          <div className="tdy-watch-row tdy-watch-head" role="row"><span role="columnheader">Ticker</span>{WATCH_AXES.map(([, label]) => <span key={label} role="columnheader">{label}</span>)}</div>
          {summary.map((row) => <Link key={row.ticker} href={`/company/${row.ticker}`} className="tdy-watch-row" role="row">
            <b role="rowheader">{row.ticker}</b>
            {WATCH_AXES.map(([key]) => {
              const state = row.axes[key];
              const change = row.changed.find((item) => item.axis === key && item.origin === "COMPANY");
              return <span key={key} role="cell" className={`tone-${state ? axisTone(key, state) : "unknown"}${change ? " changed" : ""}`} title={`${state ?? "No card yet"}${change ? ` (was ${change.from}, changed ${change.on})` : ""}`}>{shortState(state)}</span>;
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
