"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { displayStatus, statusWord } from "../../lib/status-words";
import { recentCompanyResearch, type RecentCompanyResearch } from "../../lib/company-research-api";
import { sectors } from "../../lib/market-research";
import { ChainstoxBrand } from "./ChainstoxBrand";

export type ResearchDataState = "LIVE" | "CACHED" | "DEMO" | "FIXTURE" | "STALE" | "PARTIAL" | "UNKNOWN" | "INSUFFICIENT" | "INSUFFICIENT_EVIDENCE" | "AVAILABLE" | "FRAMEWORK_REQUIRED" | "NOT_ANALYZED" | "ANALYZING" | "UNSUPPORTED" | "FAILED" | "INSUFFICIENT_DATA";

// Checklist 8.2: three questions instead of one tab per engine. Valuation is reached from each
// company; Labs stays reachable by URL but is not in the top bar. /demo and /brief were deleted (checklist 10.10).
const PRIMARY = [
  ["dashboard", "Today", "/"],
  ["companies", "Watchlist", "/companies"],
  ["markets", "Market context", "/markets"]
] as const;
const TOP_LEVEL: Record<string, string> = { dashboard: "dashboard", overview: "dashboard", company: "companies", companies: "companies", valuation: "companies", macro: "markets", markets: "markets", labs: "markets" };

const CONTEXT: Record<string, readonly (readonly [string, string])[]> = {
  macro: [["Overview", "/macro"], ["World Map", "/macro/world"], ["Central Banks", "/macro/central-banks"], ["Inflation", "/macro/inflation"], ["Rates", "/macro/rates"], ["Liquidity", "/macro/liquidity"], ["FX", "/macro/fx"], ["Risk Regime", "/macro/risk"]],
  markets: [["Sector rotation", "/markets"], ["Macro overview", "/macro"], ["World map", "/macro/world"], ["Central banks", "/macro/central-banks"], ["Inflation", "/macro/inflation"], ["Rates", "/macro/rates"], ["Liquidity", "/macro/liquidity"], ["FX", "/macro/fx"], ["Risk regime", "/macro/risk"]],
  valuation: [["Overview", "/valuation"], ["Assumptions", "/valuation/MSFT?view=assumptions"], ["DCF", "/valuation/MSFT?view=dcf"], ["Reverse DCF", "/valuation/MSFT?view=reverse-dcf"], ["Sensitivity", "/valuation/MSFT?view=sensitivity"], ["Validation", "/valuation/MSFT?view=validation"]],
  labs: [["Historical", "/labs/historical"]]
};

const STATE_HELP: Record<string, string> = {
  LIVE: "Live provider data is being used for this surface.",
  CACHED: "Cached validated research state. Analytical meaning is preserved.",
  DEMO: "Deterministic demo state using existing validated fixtures and cached research.",
  FIXTURE: "Fixture-backed research state for stable reproducible inspection.",
  STALE: "Last-valid data is shown, but freshness is stale.",
  PARTIAL: "Some research coverage exists; gaps remain part of the result.",
  UNKNOWN: "No direction or state has been confirmed by the available evidence.",
  INSUFFICIENT: "Evidence is insufficient for the requested analytical conclusion.",
  INSUFFICIENT_EVIDENCE: "Evidence is insufficient for the requested analytical conclusion.",
  AVAILABLE: "Research object is available.",
  FRAMEWORK_REQUIRED: "A different valuation or analytical framework is required.",
  NOT_ANALYZED: "The object has not been analyzed in this session.",
  ANALYZING: "Research resolution is in progress.",
  UNSUPPORTED: "The object is outside current verified CHAINSTOX coverage.",
  FAILED: "Application or provider failure. Existing cached/fixture routes may remain usable.",
  INSUFFICIENT_DATA: "Provider payload is insufficient for the requested object."
};

function companyContext(ticker: string) {
  const root = `/company/${ticker}`;
  return [["Overview", root], ["Economics", `${root}?view=economics`], ["Positioning", `${root}?view=positioning`], ["Valuation", `${root}?view=valuation`], ["Evidence", `${root}?view=evidence`]] as const;
}

function valuationContext(ticker: string) {
  const root = `/valuation/${ticker}`;
  return [["Overview", root], ["Economics vs Model", `${root}?view=economics-model`], ["DCF", `${root}?view=dcf`], ["Assumptions", `${root}?view=assumptions`], ["Reverse DCF", `${root}?view=reverse-dcf`], ["Sensitivity", `${root}?view=sensitivity`], ["Validation", `${root}?view=validation`], ["Evidence", `${root}?view=evidence`]] as const;
}

/** Thin outline icons for the sidebar (1.5px stroke, 20px box). */
function RailIcon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    dashboard: <><path d="M4 10.5 12 4l8 6.5" /><path d="M6 9v10h12V9" /></>,
    companies: <><path d="M8 6h12M8 12h12M8 18h12" /><circle cx="4.5" cy="6" r=".9" /><circle cx="4.5" cy="12" r=".9" /><circle cx="4.5" cy="18" r=".9" /></>,
    markets: <><circle cx="12" cy="12" r="8" /><path d="M4 12h16M12 4c2.5 2.4 2.5 13.6 0 16M12 4c-2.5 2.4-2.5 13.6 0 16" /></>,
    search: <><circle cx="11" cy="11" r="6" /><path d="m20 20-4.5-4.5" /></>
  };
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export function ResearchShell({
  children,
  active = "dashboard",
  ticker,
  dataState = "FIXTURE",
  demoMode = false
}: {
  children: ReactNode;
  active?: string;
  ticker?: string;
  dataState?: ResearchDataState;
  demoMode?: boolean;
  onModule?: (module: string) => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [recentCompanies, setRecentCompanies] = useState<RecentCompanyResearch[]>([]);
  const routeDemoMode = demoMode;
  const shellState = routeDemoMode ? "DEMO" : dataState;
  const topActive = TOP_LEVEL[active] ?? active;
  const contextual = ticker && active === "valuation" ? valuationContext(ticker) : ticker ? companyContext(ticker) : CONTEXT[active === "valuation" ? "valuation" : topActive] ?? [];
  const moduleResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    const index = [
      ["MODULE", "Dashboard", "/"], ["MODULE", "Macro", "/macro"], ["MODULE", "Inflation", "/macro/inflation"], ["MODULE", "Rates", "/macro/rates"], ["MODULE", "Risk Regime", "/macro/risk"], ["MODULE", "Liquidity", "/macro/liquidity"], ["MODULE", "Valuation", "/valuation"], ["MODULE", "Full Market Brief", "/brief"],
      ["REGION", "Japan", "/macro/world?region=JP"], ["REGION", "South Korea", "/macro/world?region=KR"], ["REGION", "United States", "/macro/world?region=US"], ["REGION", "Euro Area", "/macro/world?region=EURO_AREA"],
      ...sectors.map((sector) => ["SECTOR", sector.name, `/markets?sector=${sector.slug}`] as const),
      ["PRIORITY", "Japan growth pressure", "/macro/world?region=JP"], ["PRIORITY", "Semiconductor breadth", "/markets?sector=semiconductors&view=breadth"], ["PRIORITY", "Risk coverage", "/macro/risk"]
    ] as const;
    return q ? index.filter(([, label]) => label.toLowerCase().includes(q)) : [];
  }, [query]);
  const tickerQuery = moduleResults.length === 0 && /^[A-Za-z][A-Za-z0-9.\-]{0,4}$/.test(query.trim()) ? query.trim().toUpperCase() : null;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "/" && !(event.target instanceof HTMLInputElement)) { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "Escape") { setSearchOpen(false); setMobileNavOpen(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!searchOpen) return;
    recentCompanyResearch().then(setRecentCompanies).catch(() => setRecentCompanies([]));
  }, [searchOpen]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (tickerQuery) { setSearchOpen(false); router.push(`/company/${tickerQuery}`); return; }
    const first = moduleResults[0];
    if (first) { setSearchOpen(false); router.push(first[2]); }
  }

  const currentUrl = `${pathname}${searchParams.size ? `?${searchParams.toString()}` : ""}`;
  return (
    <div className="research-app-shell object-driven-shell rail-shell">
      {/* Checklist 14.1: a quiet icon sidebar instead of the top bar; labels appear on hover. */}
      <aside className="app-rail" aria-label="Primary">
        <ChainstoxBrand compact />
        <nav className={`app-rail-nav${mobileNavOpen ? " open" : ""}`} aria-label="Primary research objects">
          {PRIMARY.map(([key, label, href]) => <Link key={key} className={topActive === key ? "active" : ""} href={href} aria-label={label} data-label={label} onClick={() => setMobileNavOpen(false)}><RailIcon name={key} /></Link>)}
          <button type="button" onClick={() => setSearchOpen(true)} aria-label="Search (⌘K)" data-label="Search  ⌘K"><RailIcon name="search" /></button>
        </nav>
        <div className={`app-rail-state data-state-${shellState.toLowerCase().replaceAll("_", "-")}`} title={`${shellState === "DEMO" || shellState === "FIXTURE" ? displayStatus(shellState) : statusWord(shellState) ?? displayStatus(shellState)}: ${STATE_HELP[shellState] ?? "Current research data state"}`}><i /></div>
      </aside>
      <div className={`research-app-body${contextual.length ? " has-context-nav" : ""}`}>
        {contextual.length ? <aside className="context-research-nav"><div><span>{ticker ? `${ticker} / ${topActive === "valuation" ? "VALUATION" : "COMPANY"}` : `${topActive.toUpperCase()} / RESEARCH`}</span><strong>{ticker ? topActive === "valuation" ? "Valuation object" : "Company workspace" : "Investigation"}</strong></div><nav aria-label={`${topActive} research views`}>{contextual.map(([label, href]) => { const hrefUrl = href.split("?"); const queryView = new URLSearchParams(hrefUrl[1] ?? "").get("view"); const selected = queryView ? pathname === hrefUrl[0] && searchParams.get("view") === queryView : currentUrl === href || (href === pathname && !searchParams.get("view")); return <Link className={selected ? "active" : ""} href={href} key={label}>{label}<span>→</span></Link>; })}</nav></aside> : null}
        <main className="research-app-main">{children}</main>
      </div>
      {searchOpen ? <div className="command-surface-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setSearchOpen(false)}><section className="command-surface" role="dialog" aria-modal="true" aria-label="Global research search"><header><span>GLOBAL SEARCH / RESEARCH COMMAND</span><button type="button" onClick={() => setSearchOpen(false)}>ESC</button></header><form onSubmit={submit}><span>›</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="PLTR, Japan, Semiconductors, Inflation, Valuation" aria-label="Search research" /></form><div className="command-results">{moduleResults.map(([kind, label, href]) => <button key={`${kind}-${label}-${href}`} type="button" onClick={() => { setSearchOpen(false); router.push(href); }}><strong>{kind}</strong><span>{label}</span><small>Open research object</small></button>)}{tickerQuery ? <><button type="button" data-company-resolve={tickerQuery} onClick={() => { setSearchOpen(false); router.push(`/company/${tickerQuery}`); }}><strong>COMPANY</strong><span>{tickerQuery} structured company metadata</span><small>Resolve company research state</small></button><button type="button" data-valuation-resolve={tickerQuery} onClick={() => { setSearchOpen(false); router.push(`/valuation/${tickerQuery}`); }}><strong>VALUATION</strong><span>{tickerQuery} economics, DCF, reverse DCF, sensitivity</span><small>Open valuation object if fixture coverage exists</small></button></> : null}{!query.trim() ? <><div className="command-result-heading"><span>RESEARCH PRIORITY</span><small>Direct investigation routes</small></div>{[["PRIORITY", "Japan growth pressure", "/macro/world?region=JP"], ["PRIORITY", "Semiconductor breadth", "/markets?sector=semiconductors&view=breadth"], ["PRIORITY", "Risk coverage", "/macro/risk"], ["DEMO", "Competition demo path", "/demo"]].map(([kind, label, href]) => <button key={`${kind}-${label}-${href}`} type="button" onClick={() => { setSearchOpen(false); router.push(href); }}><strong>{kind}</strong><span>{label}</span><small>Open priority route</small></button>)}<div className="command-result-heading"><span>RECENT COMPANY RESEARCH</span><small>Previously analyzed - not the supported universe</small></div>{recentCompanies.map((item) => <button key={item.ticker} type="button" onClick={() => { setSearchOpen(false); router.push(`/company/${item.ticker}`); }}><strong>COMPANY · {item.ticker}</strong><span>{item.name}</span><small>{item.research_state.replaceAll("_", " ")}</small></button>)}{!recentCompanies.length ? <p>No on-demand company profiles have been cached yet. Use PLTR, NVDA, MSFT, Japan, or Semiconductors for deterministic coverage.</p> : null}</> : null}{query.trim() && !tickerQuery && !moduleResults.length ? <div className="command-empty-state"><strong>Research coverage unavailable</strong><p>No verified security, sector, macro region, or module matched this query. Try a supported object such as PLTR, NVDA, MSFT, Japan, Singapore, Semiconductors, Inflation, or Valuation.</p></div> : null}</div></section></div> : null}
    </div>
  );
}
