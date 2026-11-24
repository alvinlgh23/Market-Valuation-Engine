"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ResearchSystem } from "../../lib/research-system-types";

export type DataStatusInfo = {
  source: string;
  snapshotId: string;
  state: string;
  retained: boolean;
  error?: string | null;
  refreshing?: boolean;
};

function latestObservation(system: ResearchSystem) {
  const rows = system.modules.core_market.payload?.sectors;
  if (!Array.isArray(rows)) return null;
  return rows.reduce<string | null>((latest, row) => {
    const date = typeof row?.as_of === "string" ? row.as_of : null;
    return date && (!latest || date > latest) ? date : latest;
  }, null);
}

const STATE_WORD: Record<string, string> = { LIVE: "Refreshed", CACHED: "Saved data", STALE: "Out of date", PARTIAL: "Partial", INSUFFICIENT: "Partial", UNAVAILABLE: "No data" };

/** The single place on a page where data provenance is shown. Collapsed by default. */
export function DataStatus({ system, info, onRefresh }: { system: ResearchSystem; info: DataStatusInfo; onRefresh: () => void }) {
  const asOf = latestObservation(system);
  const word = info.error ? "Out of date" : STATE_WORD[String(info.state).toUpperCase()] ?? "Unknown";
  const rows = system.modules.core_market.payload?.sectors;
  return <div className="data-status" data-research-status role="status">
    <details>
      <summary><i className={`data-status-dot data-status-${word.toLowerCase().replaceAll(" ", "-")}`} aria-hidden="true" />{word}{asOf ? ` · market data as of ${asOf}` : ""}</summary>
      <dl>
        <div><dt>Source</dt><dd>{info.retained ? "Retained previous snapshot" : info.source}</dd></div>
        <div><dt>Snapshot</dt><dd>Core snapshot {info.snapshotId}</dd></div>
        <div><dt>Sector rows</dt><dd>{Array.isArray(rows) ? rows.length : 0}</dd></div>
        <div><dt>Generated</dt><dd>{system.generated_at?.replace("T", " ")} (generation time, not an observation date)</dd></div>
        {info.error ? <div><dt>Problem</dt><dd>{info.error}</dd></div> : null}
      </dl>
      <ul aria-label="Module freshness">{system.dashboard.freshness.map((item) => <li key={String(item.module)}><span>{item.module}</span><span>{String(item.state || "UNAVAILABLE")}</span><span>{String(item.as_of || "date unavailable")}</span></li>)}</ul>
    </details>
    <button type="button" onClick={onRefresh} disabled={info.refreshing} aria-label="Refresh measurements">{info.refreshing ? "Refreshing…" : "Refresh"}</button>
  </div>;
}

/** DataStatus for server-rendered pages that do not run the client research runtime. */
export function PageDataStatus({ system, meta }: { system: ResearchSystem; meta?: { source?: string; core_snapshot_id?: string; error?: string; fallback?: boolean } }) {
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(meta?.error ?? null);
  const info: DataStatusInfo = {
    source: meta?.source || "Python research",
    snapshotId: meta?.core_snapshot_id || "unidentified",
    state: meta?.fallback ? "STALE" : system.modules.core_market.state,
    retained: false,
    error,
    refreshing,
  };
  const refresh = () => {
    setRefreshing(true);
    fetch("/api/research?scope=full&refresh=1", { cache: "no-store" })
      .then(async response => { const result = await response.json(); setError(result.meta?.error ?? null); router.refresh(); })
      .catch(failure => setError(`Refresh unavailable; retaining displayed historical snapshot: ${failure instanceof Error ? failure.message : String(failure)}`))
      .finally(() => setRefreshing(false));
  };
  return <DataStatus system={system} info={info} onRefresh={refresh} />;
}
