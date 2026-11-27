"use client";

import { useEffect, useMemo, useState } from "react";
import { buildEngineChain, type ChainStep } from "../../lib/economic-chain";
import { financialModel, type FinancialModel } from "../../lib/financial-model";
import { obj, str, type ReportData } from "../../lib/report-format";
import { AnnualTable, BalanceTable, QuarterTable, SegmentTable, annualSource, balanceSource, segmentSource } from "../report/FinancialTables";
import { OperatingSignals, type Operating } from "./StoredProfileReads";

// The Economic map and Financials tabs, read from the same stored figures as the downloadable research note.

type Load = { state: "loading" } | { state: "ready"; model: FinancialModel; data: ReportData } | { state: "missing" };

const memo = new Map<string, Promise<ReportData | null>>();
function fetchReportData(ticker: string) {
  if (!memo.has(ticker)) {
    memo.set(ticker, fetch(`/api/report-data/${encodeURIComponent(ticker)}`, { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<ReportData>) : null))
      .catch(() => null)
      .then((d) => { if (!d) memo.delete(ticker); return d; }));
  }
  return memo.get(ticker)!;
}

function useFinancialModel(ticker: string): Load {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  useEffect(() => {
    let active = true;
    fetchReportData(ticker).then((data) => {
      if (active) setLoad(data ? { state: "ready", data, model: financialModel(data) } : { state: "missing" });
    });
    return () => { active = false; };
  }, [ticker]);
  return load;
}

function Pending({ load }: { load: Load }) {
  return <p className="eng-empty">{load.state === "loading" ? "Loading the stored figures…" : "No stored figures for this company yet. Open the Overview to build its card."}</p>;
}

const GLYPH = { supportive: "▲", against: "▼", mixed: "◆", unknown: "○" } as const;

function Step({ step, index, open, onToggle }: { step: ChainStep; index: number; open: boolean; onToggle: () => void }) {
  return <li className={`eng-step tone-${step.tone}${step.missing ? " eng-missing" : ""}`}>
    <button type="button" onClick={onToggle} aria-expanded={open} title={step.how}>
      <span className="eng-n">{String(index + 1).padStart(2, "0")} · {step.title}</span>
      <strong>{step.value}</strong>
      {step.sub ? <small>{step.sub}</small> : null}
      <i aria-hidden="true">{GLYPH[step.tone]}</i>
    </button>
  </li>;
}

export function EngineChainView({ ticker }: { ticker: string }) {
  const load = useFinancialModel(ticker);
  const chain = useMemo(() => (load.state === "ready" ? buildEngineChain(load.model) : null), [load]);
  const [openKey, setOpenKey] = useState<string | null>(null);
  if (load.state !== "ready" || !chain) return <Pending load={load} />;
  const active = chain.steps.find((s) => s.key === openKey) ?? null;
  return <div className="eng-chain-wrap">
    <header className="eng-head">
      <span>{load.model.isBank ? "HOW THE BANK MAKES MONEY" : "HOW THE BUSINESS MAKES MONEY"}</span>
      <h3>Is it enough for what the price assumes?</h3>
      <p>Each step is a reported figure, in order from sales to price; the conclusion is the card&apos;s valuation reading. Tap a step for the full sentence and where the figure comes from.</p>
    </header>
    <ol className="eng-chain">
      {chain.steps.map((step, i) => <Step key={step.key} step={step} index={i} open={openKey === step.key} onToggle={() => setOpenKey(openKey === step.key ? null : step.key)} />)}
    </ol>
    {active ? <div className={`eng-detail tone-${active.tone}`}>
      <b>{active.title}</b>
      <p>{active.sentence}</p>
      <small>How it&apos;s read: {active.how}</small>
    </div> : <div className="eng-sentences">
      {chain.steps.map((s) => <p key={s.key}><b>{s.title}.</b> {s.sentence}</p>)}
    </div>}
    {chain.conclusion ? <section className={`eng-conclusion tone-${chain.conclusion.tone}`}>
      <span>CONCLUSION · FIXED RULES</span>
      <h3><i aria-hidden="true">{GLYPH[chain.conclusion.tone]}</i> {chain.conclusion.title}</h3>
      <p>{chain.conclusion.sentence}</p>
    </section> : null}
    {chain.notInFilings.length ? <p className="eng-foot">Not in the filings: {chain.notInFilings.join(", ")}.</p> : null}
    <p className="eng-foot">A description of the data, not a forecast or a recommendation. Source detail for every figure is in the Evidence tab.</p>
  </div>;
}

function Sheet({ title, source, children }: { title: string; source?: string; children: React.ReactNode }) {
  return <section className="fin-sheet">
    <h4>{title}</h4>
    {children}
    {source ? <p className="fin-src">Source: {source}</p> : null}
  </section>;
}

export function FinancialStatements({ ticker }: { ticker: string }) {
  const load = useFinancialModel(ticker);
  if (load.state !== "ready") return <Pending load={load} />;
  const m = load.model;
  const operating = obj(m.card.operating) as unknown as Operating;
  const quarterName = str(m.quarter.quarter);
  return <div className="fin-statements">
    {str(m.quarter.summary) ? <section className="fin-quarter-summary">
      <span>LATEST QUARTER{quarterName ? ` · ENDED ${new Date(`${quarterName}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }).toUpperCase()}` : ""}</span>
      <h3>{String(m.quarter.summary)}</h3>
    </section> : null}
    {m.years >= 2 ? <Sheet title={`Annual figures (${m.currency}, newest first)`} source={annualSource(m)}><div className="fin-scroll"><AnnualTable m={m} /></div></Sheet> : <p className="eng-empty">Annual figures are not in the stored filings.</p>}
    {!m.isBank ? <Sheet title="Latest quarter against a year earlier" source="Latest quarterly filing; Yahoo Finance estimate for earnings per share."><div className="fin-scroll"><QuarterTable m={m} /></div></Sheet> : null}
    <Sheet title={m.isBank ? "Balance sheet, returns and estimates" : "Balance sheet and estimates"} source={balanceSource(m)}><div className="fin-scroll"><BalanceTable m={m} /></div></Sheet>
    {m.segments.length ? <Sheet title="Company-reported operating measures" source={segmentSource(m.segments)}><div className="fin-scroll"><SegmentTable segments={m.segments} /></div></Sheet> : null}
    {operating && (operating as { signals?: unknown[] }).signals?.length ? <OperatingSignals operating={operating} /> : null}
  </div>;
}
