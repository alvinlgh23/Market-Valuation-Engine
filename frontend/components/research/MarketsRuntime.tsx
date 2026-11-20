"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ResearchSystem } from "../../lib/research-system-types";
import { LabsSurface, MarketsResearch, SectorResearch } from "./ObjectResearchSurfaces";
import { ResearchDashboard } from "./ResearchDashboard";
import { reconcileResearchResponse, type ResearchResponse } from "../../lib/research-response";

async function fetchResearch(refresh = false) {
  const response = await fetch(`/api/research?scope=full${refresh ? "&refresh=1" : ""}`, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || !result.data?.modules?.core_market) throw new Error("Research response unavailable.");
  return result as ResearchResponse;
}

function useResearchRuntime(initial: ResearchSystem, initialMeta?: ResearchResponse["meta"]) {
  const [system, setSystem] = useState(initial);
  const current = useRef(initial);
  const snapshotId = useRef(initialMeta?.core_snapshot_id || "bundled snapshot");
  const [message, setMessage] = useState(initialMeta
    ? `${initialMeta.source || "Research"} · Core snapshot ${initialMeta.core_snapshot_id || "unidentified"} · ${Array.isArray(initial.modules.core_market.payload?.sectors) ? initial.modules.core_market.payload.sectors.length : 0} sector rows · ${initial.modules.core_market.state}${initialMeta.error ? ` · ${initialMeta.error}` : " · Response generation is not an observation date."}`
    : "Loading cached research measurements…");
  const accept = useCallback((result: Awaited<ReturnType<typeof fetchResearch>>) => {
      const selected = reconcileResearchResponse(current.current, result);
      const retained = selected.modules.core_market.payload === current.current.modules.core_market.payload && selected.modules.core_market.payload !== result.data.modules.core_market.payload;
      current.current = selected;
      setSystem(selected);
      if (!retained) snapshotId.current = result.meta?.core_snapshot_id || "unidentified";
      const core = selected.modules.core_market;
      const rows = core.payload?.sectors;
      setMessage(`${retained ? "Retained previous snapshot" : result.meta?.source || "Python research"} · Core snapshot ${snapshotId.current} · ${Array.isArray(rows) ? rows.length : 0} sector rows · ${core.state} · ${result.meta?.error || core.error || "Response generation is not an observation date."}`);
  }, []);
  const reject = useCallback((error: unknown) => {
    setSystem(previous => ({ ...previous, modules: { ...previous.modules, core_market: { ...previous.modules.core_market, state: "STALE" } } }));
    setMessage(`Refresh unavailable; retaining displayed historical snapshot: ${error instanceof Error ? error.message : String(error)}`);
  }, []);
  useEffect(() => { let active = true; fetchResearch().then(result => { if (active) accept(result); }).catch(error => { if (active) reject(error); }); return () => { active = false; }; }, [accept, reject]);
  const status = <p role="status" data-research-status>{message} <button onClick={() => { setMessage("Refreshing Python research measurements…"); void fetchResearch(true).then(accept).catch(reject); }}>Refresh measurements</button></p>;
  return { system, status };
}

export function MarketsRuntime({ initial, initialMeta, section = "rotation", sector }: { initial: ResearchSystem; initialMeta?: ResearchResponse["meta"]; section?: string; sector?: string }) {
  const { system, status } = useResearchRuntime(initial, initialMeta);
  return <>{status}{sector ? <SectorResearch sector={sector} system={system} /> : <MarketsResearch section={section} system={system} />}</>;
}

export function LabsRuntime({ initial, section }: { initial: ResearchSystem; section: string }) {
  const { system, status } = useResearchRuntime(initial);
  return <>{status}<p>Snapshot generated {system.generated_at}. Consumer Sentiment observation date is not supplied by this cached record; do not treat snapshot generation as its measurement date.</p><LabsSurface section={section} system={system} /></>;
}

export function DashboardRuntime({ initial, onModule }: { initial: ResearchSystem; onModule: (module: string) => void }) {
  const { system, status } = useResearchRuntime(initial);
  return <>{status}<ResearchDashboard system={system} onModule={onModule} /></>;
}
