"use client";

import { useCallback, useEffect, useState } from "react";
import { adaptCompanyEconomics, humanize } from "../../lib/companyEconomicsAdapter";
import { analyzeCompany, openCompany, resolveCompany, type CompanyResearchState, type SecurityResolution } from "../../lib/company-research-api";
import type { CompanyEconomicsPayload } from "../../lib/company-economics-types";
import { ResearchShell, type ResearchDataState } from "../research/ResearchShell";
import { CompanyResearchPage } from "./CompanyResearchPage";
import type { CompanyWorkspaceKind } from "./CompanyWorkspaces";

// Companies outside the watchlist build on first open (owner-approved 2026-11-27): structured Yahoo and SEC data
// only, no AI calls, about 5-20 seconds, then stored so the next open is instant.
const STEPS = ["Resolving company", "Collecting financial data", "Classifying business model", "Building economic architecture", "Evaluating scaling constraints", "Preparing valuation context"];

function shellState(state: CompanyResearchState): ResearchDataState {
  return state;
}

export function CompanyResearchGateway({ ticker, initialWorkspace = null, initialNode = null }: { ticker: string; initialWorkspace?: CompanyWorkspaceKind | null; initialNode?: string | null }) {
  const symbol = ticker.trim().toUpperCase();
  const [profile, setProfile] = useState<CompanyEconomicsPayload | null>(null);
  const [resolution, setResolution] = useState<SecurityResolution | null>(null);
  const [state, setState] = useState<CompanyResearchState>("NOT_ANALYZED");
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (refresh: boolean) => {
    setState("ANALYZING");
    setProgress(0);
    setError(null);
    try {
      const result = await analyzeCompany(symbol, refresh);
      setState(result.status);
      if (result.profile) setProfile(result.profile);
      else setError(result.errors?.[0] ?? "The deterministic pipeline returned no profile.");
    } catch (caught) {
      setState("FAILED");
      setError(caught instanceof Error ? caught.message : "Company analysis failed.");
    }
  }, [symbol]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cached = await openCompany(symbol);
      if (cached.profile) {
        setProfile(cached.profile);
        setState(cached.status);
        return;
      }
      const resolved = await resolveCompany(symbol);
      setResolution(resolved.resolution);
      setState(resolved.resolution.research_state);
      if (resolved.resolution.supported && resolved.resolution.research_state === "NOT_ANALYZED") void runAnalysis(false);
    } catch (caught) {
      setState("FAILED");
      setError(caught instanceof Error ? caught.message : "Company research could not be opened.");
    } finally {
      setLoading(false);
    }
  }, [symbol, runAnalysis]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (state !== "ANALYZING") return;
    const timer = window.setInterval(() => setProgress((index) => Math.min(index + 1, STEPS.length - 1)), 900);
    return () => window.clearInterval(timer);
  }, [state]);

  if (profile) return <CompanyResearchPage company={adaptCompanyEconomics(profile)} dataState={shellState(state)} initialWorkspace={initialWorkspace} initialNode={initialNode} />;

  return (
    <ResearchShell active="company" ticker={symbol} dataState={shellState(state)}>
      <div className="company-on-demand-state">
        {loading ? <section className="company-loading-state"><i /><span>Resolving company research state</span></section> : null}
        {!loading && resolution ? (
          <section className="company-resolved-preview">
            <header><span>SECURITY RESOLUTION / {resolution.security_type}</span><b>{resolution.security_type === "REIT" ? "Partial readings" : humanize(state)}</b></header>
            <h1>{resolution.company_name}</h1>
            <p>{resolution.ticker} · {[resolution.exchange, resolution.currency, resolution.country].filter(Boolean).join(" · ")}</p>
            <dl><div><dt>Sector</dt><dd>{resolution.sector || "Unavailable"}</dd></div><div><dt>Industry</dt><dd>{resolution.industry || "Unavailable"}</dd></div><div><dt>Quote type</dt><dd>{resolution.quote_type || "Unavailable"}</dd></div><div><dt>Research state</dt><dd>{resolution.security_type === "REIT" ? "Partial readings" : humanize(state)}</dd></div></dl>
            {state === "ANALYZING" ? <article><strong>BUILDING THIS COMPANY&apos;S PAGE</strong><p>First visit only: collecting filings and market data (about 20 seconds). The page is stored afterwards and opens instantly.</p></article>
              : resolution.security_type === "REIT" ? <ReitReadings ticker={symbol} />
              : <article><strong>{resolution.supported ? "COMPANY RESEARCH HAS NOT YET BEEN GENERATED" : "SPECIALIZED FRAMEWORK REQUIRED"}</strong><p>{resolution.reason}</p></article>}
            {state === "ANALYZING" ? <div className="company-analysis-progress page-progress" aria-live="polite">{STEPS.map((step, index) => <div key={step} className={index < progress ? "complete" : index === progress ? "active" : "pending"}><i />{step}</div>)}</div> : null}
            {state !== "ANALYZING" && resolution.supported ? <button className="company-analyze-action" type="button" onClick={() => void runAnalysis(false)}>Build this page <i>→</i></button> : null}
          </section>
        ) : null}
        {!loading && error ? <section className="company-failed-state"><span>APPLICATION / PROVIDER FAILURE</span><h1>{symbol}</h1><p>{error}</p><article><strong>What remains usable</strong><small>Fixture-backed company examples, Macro, Markets, Dashboard, and benchmark Valuation routes remain available. This is separate from analytical states such as INSUFFICIENT_EVIDENCE or FRAMEWORK_REQUIRED.</small></article><button type="button" onClick={load}>Retry Resolution</button></section> : null}
      </div>
    </ResearchShell>
  );
}

// REITs: the value of a property trust rests on its property cash flow (FFO), which the model does not measure yet.
// Until it does, show the readings that do apply (price, money flow, macro, estimates, business) and say so plainly.
type ReitAxis = { state?: string; evidence?: string[] };
type ReitCard = { axes?: Record<string, ReitAxis>; conclusion?: { sentences?: string[] }; generated_on?: string };
const REIT_AXES: Array<[string, string]> = [["fundamentals", "Business"], ["expectations", "Analyst estimates"], ["flow", "Money flow"], ["crowding", "Crowding"], ["macro", "Macro"]];

function ReitReadings({ ticker }: { ticker: string }) {
  const [card, setCard] = useState<ReitCard | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const get = (action: string) => fetch(`/api/research?action=${action}&ticker=${encodeURIComponent(ticker)}`).then((r) => r.json()).then((d: { card?: ReitCard | null }) => d.card ?? null);
    get("company-verdict-cached").then((saved) => { if (active && saved?.axes) setCard(saved); })
      .catch(() => undefined)
      .then(() => get("company-verdict"))
      .then((live) => { if (active && live?.axes) setCard(live); else if (active) setFailed((prev) => prev || !live); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [ticker]);
  return <div className="reit-readings">
    <article><strong>REIT VALUATION ISN&apos;T MODELLED YET</strong><p>A property trust is valued on its property cash flow (FFO), which CHAINSTOX does not measure yet, so there is no fair-value reading. The readings below still apply.</p></article>
    {card?.conclusion?.sentences?.length ? <p className="reit-lead">{card.conclusion.sentences.filter((line) => !/valuation reading/i.test(line)).join(" ")}</p> : null}
    {card?.axes ? <dl className="reit-axes">{REIT_AXES.filter(([key]) => card.axes?.[key]?.state).map(([key, label]) => <div key={key}><dt>{label}</dt><dd><b>{card.axes![key].state}</b>{card.axes![key].evidence?.[0] ? <small>{card.axes![key].evidence![0]}</small> : null}</dd></div>)}</dl>
      : failed ? <p className="reit-lead">The readings could not be built right now.</p> : <p className="reit-lead">Building the readings (about 15 seconds)…</p>}
  </div>;
}
