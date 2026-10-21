"use client";

import { useCallback, useEffect, useState } from "react";
import { adaptCompanyEconomics, humanize } from "../../lib/companyEconomicsAdapter";
import { analyzeCompany, openCompany, resolveCompany, type CompanyResearchState, type SecurityResolution } from "../../lib/company-research-api";
import type { CompanyEconomicsPayload } from "../../lib/company-economics-types";
import { ResearchShell, type ResearchDataState } from "../research/ResearchShell";
import { CompanyResearchPage } from "./CompanyResearchPage";
import type { CompanyWorkspaceKind } from "./CompanyWorkspaces";

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
    } catch (caught) {
      setState("FAILED");
      setError(caught instanceof Error ? caught.message : "Company research could not be opened.");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (state !== "ANALYZING") return;
    const timer = window.setInterval(() => setProgress((index) => Math.min(index + 1, STEPS.length - 1)), 900);
    return () => window.clearInterval(timer);
  }, [state]);

  async function analyze(refresh = false) {
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
  }

  if (profile) return <CompanyResearchPage company={adaptCompanyEconomics(profile)} dataState={shellState(state)} initialWorkspace={initialWorkspace} initialNode={initialNode} />;

  return (
    <ResearchShell active="company" ticker={symbol} dataState={shellState(state)}>
      <div className="company-on-demand-state">
        {loading ? <section className="company-loading-state"><i /><span>Resolving company research state</span></section> : null}
        {!loading && resolution ? (
          <section className="company-resolved-preview">
            <header><span>SECURITY RESOLUTION / {resolution.security_type}</span><b>{humanize(state)}</b></header>
            <h1>{resolution.company_name}</h1>
            <p>{resolution.ticker} · {[resolution.exchange, resolution.currency, resolution.country].filter(Boolean).join(" · ")}</p>
            <dl><div><dt>Sector</dt><dd>{resolution.sector || "Unavailable"}</dd></div><div><dt>Industry</dt><dd>{resolution.industry || "Unavailable"}</dd></div><div><dt>Quote type</dt><dd>{resolution.quote_type || "Unavailable"}</dd></div><div><dt>Research state</dt><dd>{humanize(state)}</dd></div></dl>
            <article><strong>{resolution.supported ? "COMPANY RESEARCH HAS NOT YET BEEN GENERATED" : "SPECIALIZED FRAMEWORK REQUIRED"}</strong><p>{resolution.reason}</p></article>
            {state === "ANALYZING" ? <div className="company-analysis-progress page-progress" aria-live="polite">{STEPS.map((step, index) => <div key={step} className={index < progress ? "complete" : index === progress ? "active" : "pending"}><i />{step}</div>)}</div> : null}
            {state !== "ANALYZING" && resolution.supported ? <button className="company-analyze-action" type="button" onClick={() => analyze(false)}>Analyze Company <i>→</i></button> : null}
          </section>
        ) : null}
        {!loading && error ? <section className="company-failed-state"><span>APPLICATION / PROVIDER FAILURE</span><h1>{symbol}</h1><p>{error}</p><article><strong>What remains usable</strong><small>Fixture-backed company examples, Macro, Markets, Dashboard, and benchmark Valuation routes remain available. This is separate from analytical states such as INSUFFICIENT_EVIDENCE or FRAMEWORK_REQUIRED.</small></article><button type="button" onClick={load}>Retry Resolution</button></section> : null}
      </div>
    </ResearchShell>
  );
}
