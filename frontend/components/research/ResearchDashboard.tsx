"use client";
import Link from "next/link";
import { EnvironmentFactors } from "../macro/EnvironmentFactors";
import { WatchlistChanges } from "./WatchlistChanges";
import { dashboardPriorities, dashboardTensions, marketMoves, sectorLeadershipBars, type MarketMove } from "../../lib/dashboard-orchestration";
import type { ResearchSystem } from "../../lib/research-system-types";
import { statusWord } from "../../lib/status-words";

function pct(value: number, digits = 1) { return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`; }

function Panel({ title, href, children, className = "" }: { title: string; href?: string; children: React.ReactNode; className?: string }) {
  return <section className={`today-panel ${className}`}><header><h2>{title}</h2>{href ? <Link href={href}>Open →</Link> : null}</header>{children}</section>;
}

/** Zero-centred horizontal bars; one scale per call. */
/** `neutral`: direction only (accent up, muted down), for moves that are not good or bad in themselves. */
function DivergingBars({ rows, neutral = false }: { rows: Array<{ key: string; label: string; value: number; text: string; href: string; title?: string }>; neutral?: boolean }) {
  const max = Math.max(...rows.map((row) => Math.abs(row.value)), 1e-9);
  return <div className={`today-bars${neutral ? " neutral" : ""}`}>{rows.map((row) => {
    const width = (Math.abs(row.value) / max) * 50;
    return <Link key={row.key} href={row.href} title={row.title} className="today-bar">
      <span>{row.label}</span>
      <div><i className={row.value < 0 ? "down" : "up"} style={{ width: `${width}%`, left: row.value < 0 ? `${50 - width}%` : "50%" }} /><b /></div>
      <em className={row.value < 0 ? "down" : "up"}>{row.text}</em>
    </Link>;
  })}</div>;
}

function MoveGroups({ moves }: { moves: MarketMove[] }) {
  const units = moves.map((move) => move.unit).filter((unit, index, all) => all.indexOf(unit) === index);
  return <>{units.map((unit) => <div key={unit} className="today-move-group">
    <small>{unit === "level" ? "Other" : unit === "bp" ? "Basis points" : "Percent"}</small>
    <DivergingBars neutral rows={moves.filter((move) => move.unit === unit).map((move) => ({ key: move.label, label: move.label, value: move.value, text: move.text.replace(/\s*3M$/, ""), href: move.href, title: move.note }))} />
  </div>)}</>;
}

/** Checklist 9.7, revised 2026-11-22: Today is charts only; wording lives in tooltips and on the detail pages. */
export function ResearchDashboard({ system }: { system: ResearchSystem; onModule: (module: string) => void }) {
  const sectors = sectorLeadershipBars(system);
  const moves = marketMoves(system);
  const priorities = dashboardPriorities(system);
  const tensions = dashboardTensions(system);
  return <div className="system-dashboard today-visual">
    <header className="today-regime" title={system.dashboard.headline.summary}>
      <span>Risk regime</span>
      <h1>{system.dashboard.headline.state}</h1>
      <small>{system.environment?.as_of ? `data ${system.environment.as_of}` : null}</small>
      <Link href="/brief">Full brief →</Link>
    </header>

    <EnvironmentFactors environment={system.environment} />

    <div className="today-grid">
      <Panel title="Sector leadership · 1M vs SPY" href="/markets" className="today-sectors">
        {sectors.length ? <DivergingBars rows={sectors.map((sector) => ({ key: sector.ticker, label: sector.ticker, value: sector.value, text: pct(sector.value), href: sector.href, title: sector.name }))} /> : <p className="today-empty">No sector readings</p>}
      </Panel>
      <Panel title="Watchlist" href="/companies" className="today-watchlist-panel"><WatchlistChanges /></Panel>
      <Panel title="Market moves" href="/macro" className="today-moves">
        {moves.length ? <MoveGroups moves={moves} /> : <p className="today-empty">No observed moves</p>}
      </Panel>
    </div>

    {priorities.length || tensions.length ? <section className="today-chips" aria-label="Watch items">
      {priorities.slice(0, 6).map((item) => <Link key={`${item.object}-${item.rank}`} href={item.href} title={[item.why, item.current].filter(Boolean).join(" · ")} className="today-chip"><b>{item.object}</b>{item.label}<em>{statusWord(item.state) ?? item.state}</em></Link>)}
      {tensions.map((item) => <Link key={item.id} href={item.href} title={item.interpretation} className="today-chip tension"><b>!</b>{item.stateA} × {item.stateB}</Link>)}
    </section> : null}
  </div>;
}
