"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { CompanyResearchViewModel } from "../../lib/company-economics-types";
import { humanize } from "../../lib/companyEconomicsAdapter";
import { ResearchShell, type ResearchDataState } from "../research/ResearchShell";
import { displayStatus } from "../../lib/status-words";
import { CompanyWorkspaces, type CompanyWorkspaceKind } from "./CompanyWorkspaces";
import { ResearchLabel } from "./ResearchPrimitives";
import { ReportMode } from "./ReportMode";
import { JudgmentCard } from "./JudgmentCard";
import { OperationalResearch } from "./OperationalResearch";
import { BottleneckCandidates, candidateBottlenecks, useLiveValuation, useOperating } from "./StoredProfileReads";

function queryState(): { workspace: CompanyWorkspaceKind | null; node: string | null } {
  if (typeof window === "undefined") return { workspace: null, node: null };
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  const valuationViews = ["valuation", "assumptions", "dcf", "reverse-dcf", "sensitivity", "validation"];
  const value = params.get("workspace") ?? (view === "economics" ? "economics" : view === "positioning" ? "thesis" : view && valuationViews.includes(view) ? "valuation" : view === "evidence" ? "evidence" : null);
  const workspace = (["economics", "valuation", "thesis", "financials", "evidence"] as const).find((item) => item === value) ?? null;
  return { workspace, node: params.get("node") };
}

export function CompanyResearchPage({ company, dataState = "FIXTURE", initialWorkspace = null, initialNode = null }: { company: CompanyResearchViewModel; dataState?: ResearchDataState; initialWorkspace?: CompanyWorkspaceKind | null; initialNode?: string | null }) {
  const router = useRouter();
  const [workspace, setWorkspace] = useState<CompanyWorkspaceKind | null>(initialWorkspace);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNode);
  const [reportOpen, setReportOpen] = useState(false);

  const syncFromUrl = useCallback(() => {
    const state = queryState();
    setWorkspace(state.workspace);
    setSelectedNodeId(state.node);
  }, []);

  // Checklist 18.5: one valuation view. The old drawer read a stored structure and showed "Unavailable"
  // next to the live card's numbers; any link to it now opens the full valuation page.
  useEffect(() => {
    if (workspace === "valuation") router.replace(`/valuation/${company.ticker}?view=overview&from=company`);
  }, [workspace, company.ticker, router]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(syncFromUrl);
    window.addEventListener("popstate", syncFromUrl);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("popstate", syncFromUrl);
    };
  }, [syncFromUrl]);

  const closeWorkspace = useCallback(() => {
    if (window.history.state?.researchDepth) {
      window.history.back();
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.delete("workspace");
    url.searchParams.delete("node");
    url.searchParams.delete("view");
    window.history.replaceState({}, "", url);
    setWorkspace(null);
    setSelectedNodeId(null);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (reportOpen) setReportOpen(false);
      else if (workspace) closeWorkspace();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeWorkspace, reportOpen, workspace]);

  function openWorkspace(next: CompanyWorkspaceKind) {
    const url = new URL(window.location.href);
    url.searchParams.set("workspace", next);
    if (["economics", "valuation", "evidence"].includes(next)) url.searchParams.set("view", next);
    url.searchParams.delete("node");
    window.history.pushState({ researchDepth: true }, "", url);
    setWorkspace(next);
    setSelectedNodeId(null);
  }

  function selectNode(nodeId: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("workspace", "economics");
    url.searchParams.set("node", nodeId);
    window.history.replaceState(window.history.state, "", url);
    setSelectedNodeId(nodeId);
  }

  function openEvidence() {
    openWorkspace("evidence");
  }

  function openValuationObject(view = "overview") {
    const query = new URLSearchParams(window.location.search);
    query.set("view", view); query.set("from", "company");
    query.delete("workspace"); query.delete("node");
    router.push(`/valuation/${company.ticker}?${query}`);
  }

  const marketRead = displayStatus(company.raw.market_expectations_comparison.state);
  const liveValuation = useLiveValuation(company.ticker);
  const operating = useOperating(company.ticker);
  const unconfirmed = company.primaryConstraint.constraint === "UNKNOWN";
  const candidates = candidateBottlenecks(company.raw.constraints.candidate_assessments, company.raw.constraints.candidate_constraints);
  const neededNumbers = candidates.map((item) => item.needs).filter((item): item is string => Boolean(item));
  const gapText = neededNumbers.length
    ? `The filings and market data we read have no direct operating numbers (${neededNumbers.join(", ")}), so no bottleneck is confirmed. Financial ratios alone are not used to name one.`
    : company.raw.qualitative_research_reason;
  const growthSummary = company.growthDrivers.map((driver) => driver.label).join(" × ");
  const bottleneckDisplay = operating?.status === "AVAILABLE"
    ? (operating.constraint ? operating.summary : `Filing check clear · ${candidates.length} structural candidates`)
    : unconfirmed
      ? `Not confirmed · ${candidates.length} candidates`
      : company.primaryConstraint.label;

  return (
    <ResearchShell active="company" ticker={company.ticker} dataState={dataState}>
      <div className="company-control-surface">
        <div className="company-crumb-row">
          <Link className="markets-back-link" href="/companies">← Watchlist</Link>
        </div>
        <header className="snapshot-identity">
          <div><span>{company.ticker}</span><h1>{company.name}</h1></div>
          <div className="snapshot-system-meta"><span>Data as of {String(company.asOf).slice(0, 10)}</span><span title={company.raw.validation.status}>Checks: {displayStatus(company.raw.validation.status)}</span></div>
        </header>

        <JudgmentCard key={company.ticker} ticker={company.ticker} />

        <nav className="company-deeper" aria-label="Deeper research">
          <button type="button" className="company-deeper-primary" onClick={() => openValuationObject()}>Valuation &amp; sandbox →</button>
          <button type="button" onClick={() => openWorkspace("economics")}>Economic map</button>
          <button type="button" onClick={() => openWorkspace("financials")}>Financials</button>
          <button type="button" onClick={() => openWorkspace("evidence")}>Evidence <small>{company.evidenceCounts.all}</small></button>
          <button type="button" onClick={() => setReportOpen(true)}>Full report</button>
        </nav>

        {/* Checklist 9.4: the stored research profile sits behind one toggle; the judgment card above is the live read. */}
        <details className="company-details">
        <summary>Research details <small>stored profile · {company.archetype} · built {String(company.asOf).slice(0, 10)}</small></summary>
        <section className="snapshot-question">
          <ResearchLabel>Core economic question</ResearchLabel>
          <h2>{company.coreQuestion}</h2>
        </section>

        {company.raw.data_quality ? <section className="snapshot-quality-strip" aria-label="Company research quality">
          <div title="Business-model route and how sure the classifier is"><span>Business type</span><strong>{company.archetype} · {displayStatus(company.raw.data_quality.classification).toLowerCase()}</strong></div>
          <div title={unconfirmed ? "Filing balance-sheet signals checked; direct operating metrics not in filings" : undefined}><span>Bottleneck</span><strong>{bottleneckDisplay}</strong></div>
          <div title="Live, the same read as the judgment card above"><span>Valuation (live)</span><strong>{liveValuation.axis?.state ?? (liveValuation.loading ? "Loading…" : displayStatus(company.raw.data_quality.valuation))}</strong></div>
          <div><span>Overall research</span><strong>{displayStatus(company.raw.data_quality.overall)}</strong></div>
        </section> : null}

        <section className="snapshot-quality-strip" aria-label="Evidence qualification summary"><div><span>Observed</span><strong>{company.evidenceCounts.observed}</strong></div><div><span>Proxy / inference</span><strong>{company.evidenceCounts.proxy + company.evidenceCounts.inference}</strong></div><div><span>Unverified / stale</span><strong>{company.evidenceCounts.unverified} / {company.evidenceCounts.stale}</strong></div><div><span>Counterevidence</span><strong>{company.evidenceCounts.counter}</strong></div></section>

        {company.raw.qualitative_research_needed ? <section className="snapshot-qualitative-gap" title={company.raw.qualitative_research_reason}><span>WHAT IS MISSING</span><p>{gapText}</p></section> : null}

        <div className="snapshot-research-grid">
          <section className="snapshot-growth snapshot-block">
            <header><span>01</span><strong>Growth Engine</strong><button type="button" onClick={() => openWorkspace("economics")}>Investigate →</button></header>
            <div className="snapshot-equation">{company.growthEquation}</div>
            <p>{growthSummary}</p>
          </section>

          <section className="snapshot-constraint snapshot-block">
            <header><span>02</span><strong>Primary Constraint</strong><button type="button" onClick={() => { openWorkspace("economics"); setTimeout(() => selectNode(company.raw.economic_graph.nodes.find((node) => node.type === "constraint")?.id ?? ""), 0); }}>Inspect →</button></header>
            {operating?.status === "AVAILABLE" ? <><h3>{operating.summary}</h3><p className="snapshot-operating-note">From SEC filings: each figure&apos;s change against sales growth. See the operating signals on the card above.</p></> : unconfirmed ? <BottleneckCandidates candidates={candidates} /> : <><h3>{company.primaryConstraint.label}</h3>
            <dl><div><dt>Binding</dt><dd>{humanize(company.primaryConstraint.constraint_status || "EVIDENCE_INSUFFICIENT")}</dd></div><div><dt>Direction</dt><dd>{humanize(company.primaryConstraint.direction_status || company.primaryConstraint.direction)}</dd></div><div><dt>Evidence</dt><dd>{company.primaryConstraint.basis}</dd></div></dl></>}
          </section>

          <section className="snapshot-read snapshot-block">
            <header><span>03</span><strong>Current Economic Read</strong><button type="button" onClick={() => openWorkspace("thesis")}>Open Thesis →</button></header>
            <p>{company.raw.growth_sustainability.interpretation}</p>
            <small>{company.raw.scaling_economics.interpretation}</small>
          </section>

          <section className="snapshot-valuation snapshot-block">
            <header><span>04</span><strong>Valuation Read</strong><button type="button" onClick={() => openValuationObject()}>Open →</button></header>
            {liveValuation.axis ? <>
              <h3>{liveValuation.axis.state}</h3>
              <p>{liveValuation.axis.evidence[0] ?? liveValuation.axis.missing[0]}</p>
              <small>Live, the same read as the judgment card above.</small>
            </> : <>
              <h3>{liveValuation.loading ? "Loading the live valuation…" : marketRead}</h3>
              <p>{company.raw.market_expectations_comparison.reason}</p>
            </>}
          </section>
        </div>

        <OperationalResearch research={company.raw.operational_research} />
        </details>
      </div>

      <CompanyWorkspaces company={company} workspace={workspace} selectedNodeId={selectedNodeId} onNode={selectNode} onClose={closeWorkspace} onEvidence={openEvidence} />
      {reportOpen ? <ReportMode company={company} onClose={() => setReportOpen(false)} /> : null}
    </ResearchShell>
  );
}
