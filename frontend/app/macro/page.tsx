import { ResearchShell } from "../../components/research/ResearchShell";
import { MacroStoryPage } from "../../components/story/MarketStoryView";
import { loadResearchSystem, researchShellState } from "../../lib/research-server";

export const dynamic = "force-dynamic";

// Checklist 15.4 / 16: Macro is the market story. The factor tiles and engine detail moved to /labs/factors.
export default async function MacroPage() {
  const response = await loadResearchSystem();
  return <ResearchShell active="macro" dataState={researchShellState(response)}><MacroStoryPage /></ResearchShell>;
}
