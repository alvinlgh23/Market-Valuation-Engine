"use client";

import Link from "next/link";
import { useState } from "react";
import {
  dashboardChanges,
  dashboardPriorities,
  dashboardStateStrip,
  dashboardTensions,
  marketLeadershipSummary,
  recentCompanyRows
} from "../../lib/dashboard-orchestration";
import type { ResearchSystem } from "../../lib/research-system-types";

function stateClass(value: string) { return value.toLowerCase().replaceAll(" ", "-").replaceAll("/", "-").replaceAll("_", "-"); }
function Badge({ state }: { state?: string }) { const value = state || "UNAVAILABLE"; return <span className={`system-badge system-badge-${stateClass(value)}`}>{value}</span>; }
function timestamp(value: string) { return value.replace("T", " ").replace(/([+-]\d\d:\d\d|Z)$/, " UTC"); }

function PanelHeader({ code, title, action }: { code: string; title: string; action?: { label: string; href: string } }) {
  return <header className="command-panel-header"><div><span>{code}</span><h2>{title}</h2></div>{action ? <Link href={action.href}>{action.label}</Link> : null}</header>;
}

export function ResearchDashboard({ system }: { system: ResearchSystem; onModule: (module: string) => void }) {
  const [showOrientation, setShowOrientation] = useState(true);
  const states = dashboardStateStrip(system);
  const changes = dashboardChanges(system);
  const priorities = dashboardPriorities(system);
  const tensions = dashboardTensions(system);
  const leaders = marketLeadershipSummary();
  const companies = recentCompanyRows(system);
  const freshness = system.dashboard.freshness.slice(0, 7);
  const watch = system.dashboard.watch_conditions.slice(0, 5);
  const regions = system.dashboard.global_regions.slice(0, 5);

  function dismissOrientation() {
    setShowOrientation(false);
  }

  return <div className="system-dashboard command-center-dashboard">
    <header className="command-center-hero">
      <div>
        <span>CHAINSTOX / RESEARCH COMMAND CENTER</span>
        <h1>What matters now?</h1>
        <p>{system.dashboard.headline.summary}</p>
      </div>
      <aside>
        <Badge state="CACHED" />
        <strong>{system.dashboard.headline.state}</strong>
        <small>Generated {timestamp(system.generated_at)}</small>
        <Link href="/brief">Open Full Market Brief →</Link>
      </aside>
    </header>

    {showOrientation ? <section className="product-orientation-panel" aria-label="First-time CHAINSTOX orientation">
      <div>
        <span>PRODUCT ORIENTATION</span>
        <strong>CHAINSTOX maps economic mechanisms from global policy to company valuation.</strong>
        <p>Start with what changed, inspect the mechanism, then open evidence and validation before forming an interpretation.</p>
      </div>
      <nav aria-label="Research starting points">
        <Link href="/macro/world">Macro Map</Link>
        <Link href="/markets?sector=semiconductors">Markets</Link>
        <Link href="/company/PLTR?fixture=1">Company</Link>
        <Link href="/valuation/PLTR">Valuation</Link>
      </nav>
      <button type="button" onClick={dismissOrientation} aria-label="Dismiss product orientation">Dismiss</button>
    </section> : null}

    <section className="system-state-strip" aria-label="Current market state strip">
      {states.map((item) => <Link href={item.href} key={item.label}><span>{item.label}</span><strong>{item.state}</strong><small>{item.detail}</small></Link>)}
    </section>

    <div className="command-center-primary">
      <section className="command-panel what-changed-panel">
        <PanelHeader code="WHAT CHANGED" title="Actual observed changes" />
        <div className="ranked-command-list">{changes.map((item) => <Link href={item.href} key={`${item.object}-${item.rank}`}><b>{String(item.rank).padStart(2, "0")}</b><div><span>{item.object}</span><strong>{item.label}</strong><p>{item.why}</p><small>{item.current}</small></div><Badge state={item.state} /></Link>)}</div>
      </section>
      <section className="command-panel priority-panel">
        <PanelHeader code="RESEARCH PRIORITY" title="Where to inspect next" />
        <div className="ranked-command-list compact">{priorities.map((item) => <Link href={item.href} key={`${item.object}-${item.rank}`}><b>{String(item.rank).padStart(2, "0")}</b><div><span>{item.object}</span><strong>{item.label}</strong><p>{item.why}</p><small>{item.current}</small></div><Badge state={item.state} /></Link>)}</div>
      </section>
    </div>

    <section className="command-panel tension-panel">
      <PanelHeader code="ACTIVE CROSS-SYSTEM SIGNALS" title="Do not average these away" />
      <div>{tensions.map((item) => <Link href={item.href} key={item.id}><span>{item.objects}</span><strong>{item.stateA}</strong><i>×</i><strong>{item.stateB}</strong><p>{item.interpretation}</p><Badge state={item.confidence} /></Link>)}</div>
    </section>

    <div className="command-center-secondary">
      <section className="command-panel macro-snapshot-panel">
        <PanelHeader code="GLOBAL MACRO" title="Regional state preview" action={{ label: "Open World Map →", href: "/macro/world" }} />
        <div className="macro-region-strip">{regions.map((region) => <Link href={String(region.href || "/macro/world")} key={String(region.id)}><span>{region.name}</span><strong>{region.state}</strong><small>{region.availability} / {region.confidence}</small></Link>)}</div>
      </section>
      <section className="command-panel leadership-panel">
        <PanelHeader code="MARKET LEADERSHIP" title="Sector bridge" action={{ label: "Open Sector Rotation →", href: "/markets" }} />
        <div className="leadership-mini-table">{leaders.map((sector) => <Link href={sector.href} key={sector.ticker}><strong>{sector.ticker}<small>{sector.name}</small></strong><span>{sector.rel6m}</span><span>{sector.breadth}</span><span>{sector.crowding}</span></Link>)}</div>
      </section>
    </div>

    <div className="command-center-secondary recent-row">
      <section className="command-panel recent-research-panel">
        <PanelHeader code="RECENT RESEARCH" title="Company context" action={{ label: "Resolve Company →", href: "/companies" }} />
        <div className="recent-company-list">{companies.length ? companies.map((company) => <Link href={company.href} key={company.ticker}><strong>{company.ticker}<small>{company.name}</small></strong><span>{company.constraint}</span><span>{company.valuation}</span><Badge state={company.state} /></Link>) : <p>No cached company research yet.</p>}</div>
      </section>
      <section className="command-panel valuation-flag-panel">
        <PanelHeader code="VALUATION FLAGS" title="Recent company valuation reads" action={{ label: "Open Valuation →", href: "/valuation" }} />
        <div className="valuation-flag-list">{system.dashboard.valuation_flags.slice(0, 5).map((flag) => <Link href={`/valuation/${String(flag.ticker || "MSFT")}?from=dashboard`} key={String(flag.ticker)}><strong>{flag.ticker}</strong><span>{String(flag.state || "UNAVAILABLE").replaceAll("_", " ")}</span><small>{String(flag.reason || "Open valuation context.")}</small></Link>)}</div>
      </section>
    </div>

    <div className="command-center-secondary operations-row">
      <section className="command-panel freshness-panel">
        <PanelHeader code="DATA FRESHNESS" title="Compact coverage" />
        <div className="freshness-grid">{freshness.map((item) => <article key={String(item.module)}><span>{item.module}</span><Badge state={String(item.state || "UNAVAILABLE")} /><small>{String(item.as_of || "Timestamp unavailable")}</small></article>)}</div>
      </section>
      <section className="command-panel watch-panel">
        <PanelHeader code="WATCH CONDITIONS" title="Active verification points" />
        <div className="watch-list">{watch.map((item) => <Link href={String(item.href || "/")} key={`${item.module}-${item.label}`}><span>{item.module}</span><strong>{item.label}</strong><small>{item.current} / {item.threshold}</small><Badge state={String(item.state || "WATCH")} /></Link>)}</div>
      </section>
    </div>

    <footer className="system-dashboard-footer"><span>{system.disclaimer}</span><span>DASHBOARD → PRIORITY → MECHANISM → EVIDENCE</span></footer>
  </div>;
}
