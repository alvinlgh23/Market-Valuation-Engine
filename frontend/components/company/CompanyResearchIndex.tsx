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
      <div className={`company-index-surface${lead ? " has-watchlist-lead" : ""}`}>
        {lead}
        {!lead ? <form className="company-open" onSubmit={submit}><label htmlFor="company-index-ticker">Open a company</label><div><input id="company-index-ticker" autoFocus value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="Ticker, e.g. AMD" /><button type="submit">Open →</button></div></form> : null}
        {!lead && recent.length ? <section className="company-recent" aria-label="Recently analysed"><span>Recent</span>{recent.map((item) => <Link key={item.ticker} href={`/company/${item.ticker}`} title={`${item.name} · ${humanize(item.archetype)}`}>{item.ticker}</Link>)}</section> : null}
        {showBenchmarks ? <details className="company-dev-benchmarks"><summary>DEV / REGRESSION BENCHMARKS</summary><p>Fixture-only architecture examples. These are not the production company universe.</p><div>{BENCHMARKS.map((symbol) => <Link key={symbol} href={`/company/${symbol}?fixture=1`}>{symbol}</Link>)}</div></details> : null}
      </div>
    </ResearchShell>
  );
}
