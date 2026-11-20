import { ResearchShell } from "../../components/research/ResearchShell";
import { MacroOverview } from "../../components/research/ObjectResearchSurfaces";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function MacroPage() {
  const response = await loadResearchSystem();
  return <ResearchShell active="macro" dataState={researchShellState(response)}><MacroOverview system={response.data as unknown as ResearchSystem} /></ResearchShell>;
}
