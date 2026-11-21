"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { recentCompanyResearch, type RecentCompanyResearch } from "../../lib/company-research-api";
import { humanize } from "../../lib/companyEconomicsAdapter";
import { ResearchShell } from "../research/ResearchShell";

const BENCHMARKS = ["PLTR", "NVDA", "MSFT", "JPM", "COST", "TSM"];

export function CompanyResearchIndex({ showBenchmarks, lead }: { showBenchmarks: boolean; lead?: ReactNode }) {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [recent, setRecent] = useState<RecentCompanyResearch[]>([]);
  useEffect(() => { recentCompanyResearch().then(setRecent).catch(() => setRecent([])); }, []);
  function submit(event: FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (/^[A-Z][A-Z0-9.\-]{0,9}$/.test(symbol)) router.push(`/company/${symbol}`);
  }
  return (
    <ResearchShell active="companies" dataState="CACHED">
      <div className="company-index-surface">
        {lead}
        <header><span>COMPANIES / ON-DEMAND RESEARCH</span><h1>Universal Company Research</h1><p>Resolve any supported equity ticker, classify its economic structure, and build an evidence-traceable profile. No pre-indexed universe is required.</p></header>
        <form onSubmit={submit}><label htmlFor="company-index-ticker">Ticker or company</label><div><input id="company-index-ticker" autoFocus value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="AMD" /><button type="submit">Resolve Company →</button></div><small>Version 1 prioritizes direct ticker resolution. Company-name lookup is not inferred.</small></form>
        <section className="company-index-recent"><header><span>RECENT RESEARCH</span><small>Previously analyzed profiles — not the supported universe</small></header>{recent.length ? recent.map((item) => <Link key={item.ticker} href={`/company/${item.ticker}`}><strong>{item.ticker}</strong><span>{item.name}</span><small>{humanize(item.archetype)}</small><b>{humanize(item.research_state)}</b></Link>) : <p>No on-demand profiles have been generated yet.</p>}</section>
        {showBenchmarks ? <details className="company-dev-benchmarks"><summary>DEV / REGRESSION BENCHMARKS</summary><p>Fixture-only architecture examples. These are not the production company universe.</p><div>{BENCHMARKS.map((symbol) => <Link key={symbol} href={`/company/${symbol}?fixture=1`}>{symbol}</Link>)}</div></details> : null}
      </div>
    </ResearchShell>
  );
}
