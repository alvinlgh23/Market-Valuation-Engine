import { ResearchShell } from "../../components/research/ResearchShell";
import { FullMarketBrief } from "../../components/research/ObjectResearchSurfaces";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function BriefPage() {
  const response = await loadResearchSystem();
  return <ResearchShell active="dashboard" dataState={researchShellState(response)}><FullMarketBrief system={response.data as unknown as ResearchSystem} /></ResearchShell>;
}
