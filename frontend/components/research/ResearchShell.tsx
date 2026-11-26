"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { displayStatus, statusWord } from "../../lib/status-words";
import { recentCompanyResearch, type RecentCompanyResearch } from "../../lib/company-research-api";
import { sectors } from "../../lib/market-research";
import { ChainstoxBrand } from "./ChainstoxBrand";

const GICS_SEARCH: Array<[string, string]> = [["Technology", "technology"], ["Communication services", "xlc"], ["Consumer discretionary", "xly"], ["Consumer staples", "xlp"],
  ["Health care", "healthcare"], ["Financials", "financials"], ["Energy", "energy"], ["Industrials", "industrials"], ["Materials", "xlb"], ["Utilities", "utilities"], ["Real estate", "xlre"]];
const GICS_SLUGS = new Set(GICS_SEARCH.map(([, slug]) => slug));

export type ResearchDataState = "LIVE" | "CACHED" | "DEMO" | "FIXTURE" | "STALE" | "PARTIAL" | "UNKNOWN" | "INSUFFICIENT" | "INSUFFICIENT_EVIDENCE" | "AVAILABLE" | "FRAMEWORK_REQUIRED" | "NOT_ANALYZED" | "ANALYZING" | "UNSUPPORTED" | "FAILED" | "INSUFFICIENT_DATA";

// Checklist 8.2: three questions instead of one tab per engine. Valuation is reached from each
// company; Labs stays reachable by URL but is not in the top bar. /demo and /brief were deleted (checklist 10.10).
const PRIMARY = [
  ["dashboard", "Today", "Today", "/"],
  ["companies", "Watchlist", "Watchlist", "/companies"],
  ["markets", "Market context", "Markets", "/markets"]
] as const;
const TOP_LEVEL: Record<string, string> = { dashboard: "dashboard", overview: "dashboard", company: "companies", companies: "companies", valuation: "companies", macro: "markets", markets: "markets", labs: "markets" };

const CONTEXT: Record<string, readonly (readonly [string, string])[]> = {
  markets: [["Sector rotation", "/markets"], ["Market story", "/macro"], ["World map", "/macro/world"], ["Central banks", "/macro/central-banks"], ["Inflation", "/macro/inflation"], ["Rates", "/macro/rates"], ["Liquidity", "/macro/liquidity"], ["FX", "/macro/fx"], ["Risk regime", "/macro/risk"]],
  valuation: [["Overview", "/valuation"]],
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
  return [
    ["Overview", root],
    ["Economics", `${root}?view=economics`],
    ["Positioning", `${root}?view=positioning`],
    ["Financials", `${root}?view=financials`],
    ["Valuation", `/valuation/${ticker}?view=overview&from=company`],
    ["Evidence", `${root}?view=evidence`],
  ] as const;
}

function valuationContext(ticker: string) {
  const root = `/valuation/${ticker}`;
  return [[`← ${ticker} company page`, `/company/${ticker}`], ["Overview", root], ["What the price assumes", `${root}?view=reverse-dcf`], ["Business vs model", `${root}?view=economics-model`], ["Cash-flow model", `${root}?view=dcf`], ["Assumptions", `${root}?view=assumptions`], ["What-if table", `${root}?view=sensitivity`], ["Checks", `${root}?view=validation`], ["Evidence", `${root}?view=evidence`]] as const;
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
  const [tickerMatches, setTickerMatches] = useState<Array<{ ticker: string; name: string }>>([]);
  const [tickerFetchedFor, setTickerFetchedFor] = useState("");
  const routeDemoMode = demoMode;
  const shellState = routeDemoMode ? "DEMO" : dataState;
  const topActive = TOP_LEVEL[active] ?? active;
  const contextual = ticker && active === "valuation" ? valuationContext(ticker) : ticker ? companyContext(ticker) : CONTEXT[active === "valuation" ? "valuation" : topActive] ?? [];
  const moduleResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    const themes = q.length >= 2
      ? sectors.filter((s) => !GICS_SLUGS.has(s.slug) && !GICS_SLUGS.has(s.ticker.toLowerCase())).map((s) => ["THEME", `${s.name} (${s.ticker})`, `/markets?sector=${s.slug}`] as const)
      : [];
    const index = [
      ["MODULE", "Today dashboard", "/"], ["MODULE", "Macro · Market story", "/macro"], ["MODULE", "Inflation", "/macro/inflation"], ["MODULE", "Rates", "/macro/rates"], ["MODULE", "Risk Regime", "/macro/risk"], ["MODULE", "Liquidity", "/macro/liquidity"], ["MODULE", "Valuation", "/valuation"],
      ["REGION", "Japan", "/macro/world?region=JP"], ["REGION", "South Korea", "/macro/world?region=KR"], ["REGION", "United States", "/macro/world?region=US"], ["REGION", "Euro Area", "/macro/world?region=EURO_AREA"],
      // Checklist 19.3: the 11 GICS sectors first; theme ETFs also match when explicitly searched.
      ...GICS_SEARCH.map(([name, slug]) => ["SECTOR", name, `/markets?sector=${slug}`] as const),
      ...themes,
      ["PRIORITY", "Japan growth pressure", "/macro/world?region=JP"], ["PRIORITY", "All sectors", "/markets"], ["PRIORITY", "Risk coverage", "/macro/risk"]
    ] as const;
    return q ? index.filter(([, label]) => label.toLowerCase().includes(q)) : [];
  }, [query]);

  useEffect(() => {
    const trimmed = query.trim();
    if (!searchOpen || !trimmed) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      fetch(`/api/research?action=ticker-search&q=${encodeURIComponent(trimmed)}`, { cache: "no-store" })
        .then((r) => r.json())
        .then((body) => {
          if (cancelled) return;
          setTickerMatches(Array.isArray(body.results) ? body.results.slice(0, 6) : []);
          setTickerFetchedFor(trimmed);
        })
        .catch(() => {
          if (cancelled) return;
          setTickerMatches([]);
          setTickerFetchedFor(trimmed);
        });
    }, 60);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [searchOpen, query]);

  const trimmedQuery = query.trim();
  const upperQuery = trimmedQuery.toUpperCase();
  const activeTickerMatches = searchOpen && trimmedQuery ? tickerMatches : [];
  const activeFetchedFor = searchOpen && trimmedQuery ? tickerFetchedFor : "";
  const exactCompany = activeTickerMatches.find((item) => item.ticker === upperQuery);
  const rawTickerFallback = activeTickerMatches.length === 0
    && (activeFetchedFor !== trimmedQuery ? moduleResults.length === 0 && /^[A-Za-z][A-Za-z0-9.\-]{0,4}$/.test(trimmedQuery) : /^[A-Z][A-Z0-9.\-]{0,4}$/.test(trimmedQuery))
    ? upperQuery : null;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "/" && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "Escape") { setSearchOpen(false); setMobileNavOpen(false); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, []);

  useEffect(() => {
    if (!searchOpen) return;
    recentCompanyResearch().then(setRecentCompanies).catch(() => setRecentCompanies([]));
  }, [searchOpen]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (exactCompany) { setSearchOpen(false); router.push(`/company/${exactCompany.ticker}`); return; }
    if (activeTickerMatches[0] && trimmedQuery.length <= 5 && moduleResults.length === 0) { setSearchOpen(false); router.push(`/company/${activeTickerMatches[0].ticker}`); return; }
    if (activeTickerMatches[0] && activeTickerMatches[0].ticker.startsWith(upperQuery) && upperQuery.length <= 4) { setSearchOpen(false); router.push(`/company/${activeTickerMatches[0].ticker}`); return; }
    if (rawTickerFallback) { setSearchOpen(false); router.push(`/company/${rawTickerFallback}`); return; }
    const first = moduleResults[0];
    if (first) { setSearchOpen(false); router.push(first[2]); return; }
    if (activeTickerMatches[0]) { setSearchOpen(false); router.push(`/company/${activeTickerMatches[0].ticker}`); }
  }

  const currentUrl = `${pathname}${searchParams.size ? `?${searchParams.toString()}` : ""}`;
  return (
    <div className="research-app-shell object-driven-shell rail-shell">
      {/* Primary navigation rail with visible micro-labels for zero-guesswork clarity */}
      <aside className="app-rail" aria-label="Primary">
        <ChainstoxBrand compact />
        <nav className={`app-rail-nav${mobileNavOpen ? " open" : ""}`} aria-label="Primary research objects">
          {PRIMARY.map(([key, label, shortLabel, href]) => (
            <Link key={key} className={topActive === key ? "active" : ""} href={href} aria-label={label} title={label} onClick={() => setMobileNavOpen(false)}>
              <RailIcon name={key} />
              <small className="app-rail-label">{shortLabel}</small>
            </Link>
          ))}
          <button type="button" onClick={() => setSearchOpen(true)} aria-label="Search (⌘K)" title="Search (⌘K)">
            <RailIcon name="search" />
            <small className="app-rail-label">Search</small>
          </button>
        </nav>
        <div className={`app-rail-state data-state-${shellState.toLowerCase().replaceAll("_", "-")}`} title={`${shellState === "DEMO" || shellState === "FIXTURE" ? displayStatus(shellState) : statusWord(shellState) ?? displayStatus(shellState)}: ${STATE_HELP[shellState] ?? "Current research data state"}`}><i /></div>
      </aside>
      <div className={`research-app-body${contextual.length ? " has-context-nav" : ""}`}>
        {contextual.length ? <aside className="context-research-nav"><div><span>{ticker ? `${ticker} / ${active === "valuation" ? "VALUATION" : "COMPANY"}` : `${active === "macro" ? "MACRO" : active === "labs" ? "INTERNAL" : topActive.toUpperCase()} / RESEARCH`}</span><strong>{ticker ? active === "valuation" ? "Valuation object" : "Company workspace" : "Investigation"}</strong></div><nav aria-label={`${topActive} research views`}>{contextual.map(([label, href]) => { const hrefUrl = href.split("?"); const queryView = new URLSearchParams(hrefUrl[1] ?? "").get("view"); const viewParam = searchParams.get("view"); const selected = queryView ? pathname === hrefUrl[0] && viewParam === queryView : currentUrl === href || (href === pathname && (!viewParam || viewParam === "overview")); return <Link className={selected ? "active" : ""} href={href} key={label}>{label}{label.startsWith("←") ? null : <span>→</span>}</Link>; })}</nav></aside> : null}
        <main className="research-app-main">{children}</main>
      </div>
      {searchOpen ? <div className="command-surface-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setSearchOpen(false)}><section className="command-surface" role="dialog" aria-modal="true" aria-label="Global research search"><header><span>GLOBAL SEARCH / RESEARCH COMMAND</span><button type="button" onClick={() => setSearchOpen(false)}>ESC</button></header><form onSubmit={submit}><span>›</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); setSearchOpen(false); } }} placeholder="Ticker or company (NVDA, CAT, Visa, Apple), sector, or macro topic" aria-label="Search research" /></form><div className="command-results">{activeTickerMatches.length ? <><div className="command-result-heading"><span>COMPANIES</span><small>Listed equities</small></div>{activeTickerMatches.map((item) => <button key={`co-${item.ticker}`} type="button" data-company-resolve={item.ticker} onClick={() => { setSearchOpen(false); router.push(`/company/${item.ticker}`); }}><strong>COMPANY · {item.ticker}</strong><span>{item.name}</span><small>Open judgment card</small></button>)}{exactCompany ? <button type="button" data-valuation-resolve={exactCompany.ticker} onClick={() => { setSearchOpen(false); router.push(`/valuation/${exactCompany.ticker}`); }}><strong>VALUATION · {exactCompany.ticker}</strong><span>{exactCompany.name} — DCF, reverse DCF &amp; sandbox</span><small>Open valuation workspace</small></button> : null}</> : null}{rawTickerFallback ? <><button type="button" data-company-resolve={rawTickerFallback} onClick={() => { setSearchOpen(false); router.push(`/company/${rawTickerFallback}`); }}><strong>COMPANY</strong><span>{rawTickerFallback} structured company metadata</span><small>Resolve company research state</small></button><button type="button" data-valuation-resolve={rawTickerFallback} onClick={() => { setSearchOpen(false); router.push(`/valuation/${rawTickerFallback}`); }}><strong>VALUATION</strong><span>{rawTickerFallback} economics, DCF, reverse DCF, sensitivity</span><small>Open valuation workspace</small></button></> : null}{moduleResults.length ? <><div className="command-result-heading"><span>SECTORS, REGIONS &amp; TOPICS</span><small>Market context</small></div>{moduleResults.map(([kind, label, href]) => <button key={`${kind}-${label}-${href}`} type="button" onClick={() => { setSearchOpen(false); router.push(href); }}><strong>{kind}</strong><span>{label}</span><small>Open research view</small></button>)}</> : null}{!trimmedQuery ? <><div className="command-result-heading"><span>RESEARCH PRIORITY</span><small>Direct investigation routes</small></div>{[["PRIORITY", "Market story", "/macro"], ["PRIORITY", "Japan growth pressure", "/macro/world?region=JP"], ["PRIORITY", "All sectors", "/markets"], ["PRIORITY", "Risk coverage", "/macro/risk"]].map(([kind, label, href]) => <button key={`${kind}-${label}-${href}`} type="button" onClick={() => { setSearchOpen(false); router.push(href); }}><strong>{kind}</strong><span>{label}</span><small>Open priority route</small></button>)}<div className="command-result-heading"><span>RECENT COMPANY RESEARCH</span><small>Previously analyzed</small></div>{recentCompanies.map((item) => <button key={item.ticker} type="button" onClick={() => { setSearchOpen(false); router.push(`/company/${item.ticker}`); }}><strong>COMPANY · {item.ticker}</strong><span>{item.name}</span><small>{item.research_state.replaceAll("_", " ")}</small></button>)}{!recentCompanies.length ? <p>No on-demand company profiles have been cached yet. Type any ticker, company name, sector or topic.</p> : null}</> : null}{trimmedQuery && !activeTickerMatches.length && !rawTickerFallback && !moduleResults.length ? <div className="command-empty-state"><strong>Research coverage unavailable</strong><p>No listed security, sector, macro region, or topic matched &ldquo;{trimmedQuery}&rdquo;. Try a ticker or company name (e.g. NVDA, CAT, Apple), a region (Japan, Euro Area), or a sector (Technology, Semiconductors, Energy).</p></div> : null}</div></section></div> : null}
    </div>
  );
}
