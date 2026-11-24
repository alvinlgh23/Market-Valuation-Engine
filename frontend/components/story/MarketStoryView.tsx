"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Criteria } from "../today/Criteria";
import { loadMarketStory, type MarketBreakdown, type MarketStory, type Scenario, type StoryStep, type StoryTag } from "../../lib/market-story";

// Checklists 15.4, 16, 17: the Macro page is one chain from inflation and the Fed down to profits
// and the reader's holdings. Each step says how sure it is; arrows mean "because" only where the
// link is institutional or tested. Internal factor readings live on /labs/factors.

const TAG_LABEL: Record<StoryTag, string> = { FACT: "Fact", MARKET: "Market expects", TESTED: "Tested", MEASURED: "Measured", NO_LINK: "Checked, no link" };
const TAG_HELP: Record<StoryTag, string> = {
  FACT: "A measured number from an official or market source.",
  MARKET: "The market's own odds, from prices people trade on (futures, the VIX).",
  TESTED: "A pattern that held in our historical data.",
  MEASURED: "Measured on your holdings' own prices.",
  NO_LINK: "A common claim we checked in our data; it did not hold, so we don't use it."
};

function pct(value: number | null | undefined, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? `${value >= 0 ? "+" : "−"}${Math.abs(value * 100).toFixed(digits)}%` : "—";
}
function billions(value: number) { return `$${(value / 1e9).toFixed(0)}B`; }

export function useMarketStory() {
  const [data, setData] = useState<MarketStory | null>(null);
  useEffect(() => { let active = true; loadMarketStory().then((value) => { if (active) setData(value); }); return () => { active = false; }; }, []);
  return data;
}

function Tag({ tag, label }: { tag: StoryTag; label?: string }) {
  return <span className={`story-tag tag-${tag.toLowerCase()}`} title={TAG_HELP[tag]}>{label ?? TAG_LABEL[tag]}</span>;
}

function Step({ step, index, last }: { step: StoryStep; index: number; last: boolean }) {
  const evidence = step.evidence.map((item) => `${item.label}: ${item.value}${item.reference ? ` (${item.reference})` : ""}`).join(". ");
  return <li className={`story-step${last ? " last" : ""} link-${step.link?.kind ?? "end"}`}>
    <span className="story-dot" aria-hidden="true">{index + 1}</span>
    <div className="story-body">
      <Criteria block criteria={{ rule: step.criteria?.rule ?? "", now: evidence || null, asOf: step.evidence.find((item) => item.as_of)?.as_of ?? null, notes: step.evidence.map((item) => item.source).filter(Boolean).slice(0, 1).map((source) => `Source: ${source}`) }}>
        <h3>{step.title}<Tag tag={step.tag} /></h3>
      </Criteria>
      <p>{step.text}</p>
      {step.notes?.map((note) => <p key={note.text} className="story-note"><Tag tag={note.tag} label={note.label} />{note.text}</p>)}
    </div>
    {step.link?.kind === "because" && step.link.text ? <span className="story-because">{step.link.text}</span> : null}
  </li>;
}

export function StoryChain({ data }: { data: MarketStory | null }) {
  if (!data) return <section className="story-card story-loading" aria-busy="true"><p className="story-headline">Reading the market…</p></section>;
  if (data.status !== "OK" || !data.story) return <section className="story-card"><p className="story-headline">The market story is unavailable right now.</p><p className="story-muted">{data.error}</p></section>;
  const { story } = data;
  const dates = data.data_dates ?? {};
  return <section className="story-card" aria-label="The market story">
    <p className="story-kicker">The market story</p>
    <p className="story-headline">{story.headline}</p>
    <ol className="story-chain">{story.steps.map((step, index) => <Step key={step.id} step={step} index={index} last={index === story.steps.length - 1} />)}</ol>
    <p className="story-dates">Data: inflation to {dates.inflation?.slice(0, 7) ?? "—"}, rates and VIX to {dates.rates_and_vix ?? "—"}, futures {dates.futures ?? "—"}, company profits to {dates.profits ?? "—"}. Hover a step for its rule.</p>
  </section>;
}

function SectorBars({ market }: { market: MarketBreakdown }) {
  const rows = (market.sectors ?? []).filter((row) => row.contribution_pp != null);
  const max = Math.max(...rows.map((row) => Math.abs(row.contribution_pp as number)), 1e-9);
  return <div className="story-bars" role="table" aria-label="Share of profit growth by sector">
    {rows.map((row) => {
      const value = row.contribution_pp as number;
      return <div key={row.etf} className="story-bar" role="row" title={`${row.sector}: profits ${pct(row.growth)} from a year earlier across ${row.companies} companies; ${((row.share_of_profit ?? 0) * 100).toFixed(0)}% of all S&P 500 profit.`}>
        <span role="rowheader"><b>{row.etf}</b><small>{row.sector}</small></span>
        <div role="cell"><i className={value < 0 ? "down" : "up"} style={{ width: `${(Math.abs(value) / max) * 100}%` }} /></div>
        <em role="cell" className={value < 0 ? "down" : "up"}>{value >= 0 ? "+" : "−"}{Math.abs(value * 100).toFixed(1)} pts</em>
      </div>;
    })}
  </div>;
}

export function ProfitBreakdown({ data }: { data: MarketStory | null }) {
  const market = data?.market;
  if (!market) return null;
  if (market.status !== "AVAILABLE") return <section className="story-card"><h2>Where the profits come from</h2><p className="story-muted">{market.reason ?? "Unavailable."}</p></section>;
  const driver = market.driver;
  const carriers = market.carriers ?? [];
  const topShare = Math.max(...carriers.map((item) => item.share_of_growth ?? 0), 1e-9);
  return <section className="story-card story-profits" aria-label="Where the profits come from">
    <header><h2>Where the profits come from</h2><Criteria align="right" criteria={{ rule: `${market.method} Profit is net income without one-off items (Yahoo normalized income), so each company is measured on its own fiscal quarters. ${driver?.rule ?? ""}`, now: `${market.companies} of ${market.members} S&P 500 companies had both quarters; the others are left out, not counted as zero.`, asOf: market.quarters?.latest ?? null, notes: [market.source ?? ""] }}><small>How this is measured</small></Criteria></header>
    {driver ? <div className="story-figures">
      <div><span>S&P 500 profits</span><b className={(market.growth ?? 0) < 0 ? "down" : "up"}>{pct(market.growth, 0)}</b><small>latest quarter vs a year earlier</small></div>
      <div><span>S&P 500 index</span><b className={driver.index_change < 0 ? "down" : "up"}>{pct(driver.index_change, 0)}</b><small>same year</small></div>
      <div><span>Price paid per $ of profit</span><b>{pct(driver.multiple_change, 0)}</b><small>{driver.label}</small></div>
    </div> : null}
    <div className="story-split">
      <div>
        <h3>By sector · points of the {pct(market.growth, 0)}</h3>
        <SectorBars market={market} />
      </div>
      <div>
        <h3>{market.carriers_for_half ? `${market.carriers_for_half} companies carry half the growth` : "Biggest contributors"}{market.carriers_for_80pct ? <small> · {market.carriers_for_80pct} carry 80%</small> : null}</h3>
        <ol className="story-carriers">{carriers.map((item) => <li key={item.symbol}>
          <Link href={`/company/${item.symbol}`}><b>{item.symbol}</b><small>{item.name}</small></Link>
          <div><i style={{ width: `${((item.share_of_growth ?? 0) / topShare) * 100}%` }} /></div>
          <em title={`Profit up ${billions(item.change)} on the quarter ending ${item.quarter}`}>{((item.share_of_growth ?? 0) * 100).toFixed(1)}%</em>
        </li>)}</ol>
        {market.companies_growing != null ? <p className="story-muted">{market.companies_growing} of {market.companies} companies grew profits; the ten biggest earners make {((market.top10_profit_share ?? 0) * 100).toFixed(0)}% of all S&P 500 profit.</p> : null}
      </div>
    </div>
  </section>;
}

export function ScenarioGate({ data }: { data: MarketStory | null }) {
  const scenario: Scenario | undefined = data?.story?.scenario;
  if (!scenario) return null;
  return <section className="story-card story-scenario" aria-label="What comes next">
    <header><h2>What comes next</h2><Criteria align="right" criteria={{ rule: `A "likely" call appears only if its method beat chance when replayed month by month since 1999, using only what was known at the time. ${scenario.rule ?? ""}`, now: null, asOf: scenario.generated_on ?? null }}><small>How we decide</small></Criteria></header>
    <p className="story-verdict">{scenario.verdict ?? scenario.text}</p>
    {scenario.lesson ? <p className="story-muted">{scenario.lesson}</p> : null}
    {scenario.methods?.length ? <details className="story-methods"><summary>What we tested</summary><ul>{scenario.methods.map((method) => <li key={method.name}>
      <span>{method.what}</span><b className={method.verdict === "PASSED" ? "up" : "down"}>{method.verdict === "PASSED" ? "Passed" : "Failed"}</b>
      <small>{method.beat_share != null ? `right ${(method.beat_share * 100).toFixed(0)}% of the time${method.baseline_share != null ? ` vs ${(method.baseline_share * 100).toFixed(0)}% for always saying up` : " (50% is chance)"}` : ""}</small>
    </li>)}</ul></details> : null}
  </section>;
}

export function MacroStoryPage() {
  const data = useMarketStory();
  return <div className="story-page">
    <header className="tdy-top"><div><h1>Macro</h1><p>From inflation and the Fed down to profits and your holdings</p></div></header>
    <StoryChain data={data} />
    <ProfitBreakdown data={data} />
    <ScenarioGate data={data} />
  </div>;
}

/** Today page: the story's step titles only, linking to the full chain. */
export function StoryDigest() {
  const data = useMarketStory();
  const steps = data?.story?.steps ?? [];
  return <section className="tdy-card tdy-story">
    <header><h2>The market story</h2><Link href="/macro">Open</Link></header>
    {!data ? <p className="tdy-empty">Reading the market…</p> : null}
    {data && !steps.length ? <p className="tdy-empty">The market story is unavailable right now.</p> : null}
    <ol>{steps.map((step) => <li key={step.id}><Criteria block criteria={{ rule: step.criteria?.rule ?? "", now: step.text, asOf: step.evidence.find((item) => item.as_of)?.as_of ?? null }}><span>{step.title}</span></Criteria><Tag tag={step.tag} /></li>)}</ol>
  </section>;
}
