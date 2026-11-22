"use client";
import { StatusBadge } from "./StatusBadge";
import { statusWord } from "../../lib/status-words";

import Link from "next/link";
import { WatchlistChanges } from "./WatchlistChanges";
import {
  dashboardChanges,
  dashboardPriorities,
  dashboardStateStrip,
  dashboardTensions,
  marketLeadershipSummary,
  recentCompanyRows
} from "../../lib/dashboard-orchestration";
import type { ResearchSystem } from "../../lib/research-system-types";

function Badge({ state }: { state?: string }) { return <StatusBadge value={state || "UNAVAILABLE"} />; }

function PanelHeader({ code, title, action }: { code: string; title: string; action?: { label: string; href: string } }) {
  return <header className="command-panel-header"><div><span>{code}</span><h2>{title}</h2></div>{action ? <Link href={action.href}>{action.label}</Link> : null}</header>;
}

export function ResearchDashboard({ system }: { system: ResearchSystem; onModule: (module: string) => void }) {
  const states = dashboardStateStrip(system);
  const changes = dashboardChanges(system);
  const priorities = dashboardPriorities(system);
  const tensions = dashboardTensions(system);
  const leaders = marketLeadershipSummary(system);
  const companies = recentCompanyRows(system);
  const watch = system.dashboard.watch_conditions.slice(0, 5);
  const regions = system.dashboard.global_regions.slice(0, 5);

  return <div className="system-dashboard command-center-dashboard">
    {/* Checklist 9.7: the regime as one line; no hero headline or orientation banner. */}
    <header className="today-regime">
      <span>Risk regime</span>
      <h1>{system.dashboard.headline.state}</h1>
      <p>{system.dashboard.headline.summary}</p>
      <Link href="/brief">Full brief →</Link>
    </header>

    <WatchlistChanges />

    <section className="system-state-strip" aria-label="Current market state strip">
      {states.map((item) => <Link href={item.href} key={item.label} title={item.detail}><span>{item.label}</span><strong title={item.state}>{statusWord(item.state) ?? item.state}</strong></Link>)}
    </section>

    <div className="command-center-primary">
      <section className="command-panel what-changed-panel">
        <PanelHeader code="WHAT CHANGED" title="Actual observed changes" />
        <div className="ranked-command-list">{changes.map((item) => { const up = /^\+/.test(item.label), down = /^[-−]/.test(item.label); return <Link href={item.href} key={`${item.object}-${item.rank}`} className="today-move" title={item.why || undefined}><span>{item.object}</span><em className={up ? "up" : down ? "down" : ""} aria-hidden>{up ? "▲" : down ? "▼" : "•"}</em><strong>{item.label}</strong>{item.state !== "Observed market change" ? <Badge state={item.state} /> : null}</Link>; })}</div>
      </section>
      <section className="command-panel priority-panel">
        <PanelHeader code="RESEARCH PRIORITY" title="Where to inspect next" />
        <div className="ranked-command-list compact">{priorities.map((item) => <Link href={item.href} key={`${item.object}-${item.rank}`} title={item.why}><b>{String(item.rank).padStart(2, "0")}</b><div><span>{item.object}</span><strong>{item.label}</strong><small>{item.current}</small></div><Badge state={item.state} /></Link>)}</div>
      </section>
    </div>

    <section className="command-panel tension-panel">
      <PanelHeader code="ACTIVE CROSS-SYSTEM SIGNALS" title="Do not average these away" />
      <div>{tensions.map((item) => <Link href={item.href} key={item.id} title={item.interpretation}><span>{item.objects}</span><strong>{item.stateA}</strong><i>×</i><strong>{item.stateB}</strong><Badge state={item.confidence} /></Link>)}</div>
    </section>

    <div className="command-center-secondary">
      <section className="command-panel macro-snapshot-panel">
        <PanelHeader code="GLOBAL MACRO" title="Regional state preview" action={{ label: "Open World Map →", href: "/macro/world" }} />
        <div className="macro-region-strip">{regions.map((region) => <Link href={String(region.href || "/macro/world")} key={String(region.id)}><span>{region.name}</span><strong>{region.state}</strong><small>{region.availability} / {region.confidence}</small></Link>)}</div>
      </section>
      <section className="command-panel leadership-panel">
        <PanelHeader code="MARKET LEADERSHIP" title="Sector bridge" action={{ label: "Open Sector Rotation →", href: "/markets" }} />
        <div className="leadership-mini-table">{leaders.map((sector) => <Link href={sector.href} key={sector.ticker}><strong>{sector.ticker}<small>{sector.name}</small></strong><span className="today-rs" title="Six-month return relative to SPY"><i style={{ width: `${Math.min(100, Math.abs(sector.rel6mValue ?? 0) * 200)}%` }} className={(sector.rel6mValue ?? 0) >= 0 ? "up" : "down"} /><b>{sector.rel6m}</b></span>{leaders.some((item) => item.breadth !== "Unavailable") ? <span>{sector.breadth}</span> : null}{leaders.some((item) => item.crowding !== "Unavailable") ? <span>{sector.crowding}</span> : null}</Link>)}</div>
      </section>
    </div>

    <div className="command-center-secondary recent-row">
      <section className="command-panel recent-research-panel">
        <PanelHeader code="RECENT RESEARCH" title="Company context" action={{ label: "Resolve Company →", href: "/companies" }} />
        <div className="recent-company-list">{companies.length ? companies.map((company) => <Link href={company.href} key={company.ticker}><strong>{company.ticker}<small>{company.name}</small></strong><span>{company.constraint}</span><span>{company.valuation}</span><Badge state={company.state} /></Link>) : <p>No cached company research yet.</p>}</div>
      </section>
      <section className="command-panel valuation-flag-panel">
        <PanelHeader code="VALUATION FLAGS" title="Recent company valuation reads" action={{ label: "Open Valuation →", href: "/valuation" }} />
        <div className="valuation-flag-list">{system.dashboard.valuation_flags.slice(0, 5).map((flag) => <Link href={`/valuation/${String(flag.ticker || "MSFT")}?from=dashboard`} key={String(flag.ticker)} title={String(flag.reason || "")}><strong>{flag.ticker}</strong><span>{String(flag.state || "UNAVAILABLE").replaceAll("_", " ")}</span></Link>)}</div>
      </section>
    </div>

    <div className="command-center-secondary operations-row">
      <section className="command-panel watch-panel">
        <PanelHeader code="WATCH CONDITIONS" title="Active verification points" />
        <div className="watch-list">{watch.map((item) => <Link href={String(item.href || "/")} key={`${item.module}-${item.label}`}><span>{item.module}</span><strong>{item.label}</strong><small>{item.current} / {item.threshold}</small><Badge state={String(item.state || "WATCH")} /></Link>)}</div>
      </section>
    </div>

    <footer className="system-dashboard-footer"><span>{system.disclaimer}</span></footer>
  </div>;
}
