import { ResearchShell } from "../../components/research/ResearchShell";
import { MarketsRuntime } from "../../components/research/MarketsRuntime";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function MarketsPage() {
  const response = await loadResearchSystem();
  const system = response.data as unknown as ResearchSystem;
  return <ResearchShell active="markets" dataState={researchShellState(response)}><MarketsRuntime initial={system} initialMeta={response.meta} /></ResearchShell>;
}
