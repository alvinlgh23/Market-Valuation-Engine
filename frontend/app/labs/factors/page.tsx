import { PageDataStatus } from "../../../components/research/DataStatus";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroOverview } from "../../../components/research/ObjectResearchSurfaces";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

export const dynamic = "force-dynamic";

// Checklist 16: the factor readings the model validates against. Internal: not in the navigation.
export default async function FactorReadingsPage() {
  const response = await loadResearchSystem();
  return <ResearchShell active="labs" dataState={researchShellState(response)}><PageDataStatus system={response.data as unknown as ResearchSystem} meta={response.meta} /><MacroOverview system={response.data as unknown as ResearchSystem} /></ResearchShell>;
}
