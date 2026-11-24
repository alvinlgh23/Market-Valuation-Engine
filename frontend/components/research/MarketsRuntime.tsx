"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ResearchSystem } from "../../lib/research-system-types";
import { LabsSurface, MarketsResearch, SectorResearch } from "./ObjectResearchSurfaces";
import { TodayView } from "../today/TodayView";
import { reconcileResearchResponse, type ResearchResponse } from "../../lib/research-response";
import { DataStatus, type DataStatusInfo } from "./DataStatus";

async function fetchResearch(refresh = false) {
  const response = await fetch(`/api/research?scope=full${refresh ? "&refresh=1" : ""}`, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || !result.data?.modules?.core_market) throw new Error("Research response unavailable.");
  return result as ResearchResponse;
}

function useResearchRuntime(initial: ResearchSystem, initialMeta?: ResearchResponse["meta"]) {
  const [system, setSystem] = useState(initial);
  const current = useRef(initial);
  const [info, setInfo] = useState<DataStatusInfo>({
    source: initialMeta?.source || "Bundled snapshot",
    snapshotId: initialMeta?.core_snapshot_id || "unidentified",
    state: initial.modules.core_market.state,
    retained: false,
    error: initialMeta?.error ?? null,
  });
  const accept = useCallback((result: Awaited<ReturnType<typeof fetchResearch>>) => {
      const selected = reconcileResearchResponse(current.current, result);
      const retained = selected.modules.core_market.payload === current.current.modules.core_market.payload && selected.modules.core_market.payload !== result.data.modules.core_market.payload;
      current.current = selected;
      setSystem(selected);
      setInfo(previous => ({
        source: result.meta?.source || "Python research",
        snapshotId: retained ? previous.snapshotId : result.meta?.core_snapshot_id || "unidentified",
        state: selected.modules.core_market.state,
        retained,
        error: result.meta?.error || selected.modules.core_market.error || null,
      }));
  }, []);
  const reject = useCallback((error: unknown) => {
    setSystem(previous => ({ ...previous, modules: { ...previous.modules, core_market: { ...previous.modules.core_market, state: "STALE" } } }));
    setInfo(previous => ({ ...previous, state: "STALE", refreshing: false, error: `Refresh unavailable; retaining displayed historical snapshot: ${error instanceof Error ? error.message : String(error)}` }));
  }, []);
  useEffect(() => { let active = true; fetchResearch().then(result => { if (active) accept(result); }).catch(error => { if (active) reject(error); }); return () => { active = false; }; }, [accept, reject]);
  const refresh = () => { setInfo(previous => ({ ...previous, refreshing: true })); void fetchResearch(true).then(accept).catch(reject); };
  const status = <DataStatus system={system} info={info} onRefresh={refresh} />;
  return { system, status };
}

export function MarketsRuntime({ initial, initialMeta, section = "rotation", sector }: { initial: ResearchSystem; initialMeta?: ResearchResponse["meta"]; section?: string; sector?: string }) {
  const { system, status } = useResearchRuntime(initial, initialMeta);
  return <>{status}{sector ? <SectorResearch sector={sector} system={system} /> : <MarketsResearch section={section} system={system} />}</>;
}

export function LabsRuntime({ initial, initialMeta, section }: { initial: ResearchSystem; initialMeta?: ResearchResponse["meta"]; section: string }) {
  const { system, status } = useResearchRuntime(initial, initialMeta);
  return <>{status}<LabsSurface section={section} system={system} /></>;
}

export function DashboardRuntime({ initial, initialMeta }: { initial: ResearchSystem; initialMeta?: ResearchResponse["meta"]; onModule?: (module: string) => void }) {
  const { system, status } = useResearchRuntime(initial, initialMeta);
  return <TodayView system={system} status={status} />;
}
