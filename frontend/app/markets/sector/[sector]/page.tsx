import { ResearchShell } from "../../../../components/research/ResearchShell";
import { MarketsRuntime } from "../../../../components/research/MarketsRuntime";
import type { ResearchSystem } from "../../../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function SectorPage({ params }: { params: Promise<{ sector: string }> }) {
  const { sector } = await params;
  const response = await loadResearchSystem();
  return <ResearchShell active="markets" dataState={researchShellState(response)}><MarketsRuntime sector={sector} initial={response.data as unknown as ResearchSystem} initialMeta={response.meta} /></ResearchShell>;
}
