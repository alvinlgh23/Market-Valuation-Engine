import { ResearchShell } from "../../components/research/ResearchShell";
import { MacroOverview } from "../../components/research/ObjectResearchSurfaces";
import systemFixture from "../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../lib/research-system-types";

export default function MacroPage() {
  const system = systemFixture as unknown as ResearchSystem;
  return <ResearchShell active="macro" dataState="CACHED"><MacroOverview system={system} /></ResearchShell>;
}
