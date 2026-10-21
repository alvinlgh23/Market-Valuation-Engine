"use client";
import { useCallback, useEffect, useState } from "react";
import type { ResearchSystem } from "../../lib/research-system-types";
import { MarketsResearch, SectorResearch } from "./ObjectResearchSurfaces";

async function fetchResearch(refresh = false) {
  const response = await fetch(`/api/research?scope=full${refresh ? "&refresh=1" : ""}`, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || !result.data?.modules?.core_market) throw new Error("Research response unavailable.");
  return result;
}

export function MarketsRuntime({ initial, section = "rotation", sector }: { initial: ResearchSystem; section?: string; sector?: string }) {
  const [system, setSystem] = useState(initial);
  const [message, setMessage] = useState("Loading cached research measurements…");
  const accept = useCallback((result: Awaited<ReturnType<typeof fetchResearch>>) => {
      const data = result.data as ResearchSystem;
      if (result.meta?.data_state === "STALE") data.modules.core_market.state = "STALE";
      setSystem(data);
      setMessage(`${result.meta?.source || "Python research"} · ${result.meta?.error || "Response cache age is separate from measurement dates shown below."}`);
  }, []);
  const reject = useCallback((error: unknown) => setMessage(`Dynamic measurements unavailable: ${error instanceof Error ? error.message : String(error)}`), []);
  useEffect(() => { let active = true; fetchResearch().then(result => { if (active) accept(result); }).catch(error => { if (active) reject(error); }); return () => { active = false; }; }, [accept, reject]);
  return <><p role="status">{message} <button onClick={() => { setMessage("Refreshing Python research measurements…"); void fetchResearch(true).then(accept).catch(reject); }}>Refresh measurements</button></p>{sector ? <SectorResearch sector={sector} system={system} /> : <MarketsResearch section={section} system={system} />}</>;
}
