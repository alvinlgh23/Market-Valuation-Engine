import type { ResearchSystem } from "../../../lib/research-system-types";
import { PageDataStatus } from "../../../components/research/DataStatus";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroWorldSurface } from "../../../components/macro/MacroWorldSurface";
import type { MacroWorld } from "../../../lib/macro-types";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function MacroWorldPage() {
  const response = await loadResearchSystem();
  return <ResearchShell active="macro" dataState={researchShellState(response)}><PageDataStatus system={response.data as unknown as ResearchSystem} meta={response.meta} /><MacroWorldSurface world={response.data.world as unknown as MacroWorld} /></ResearchShell>;
}
