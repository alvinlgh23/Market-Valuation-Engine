import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroWorldSurface } from "../../../components/macro/MacroWorldSurface";
import systemFixture from "../../../lib/fixtures/research-system.json";
import type { MacroWorld } from "../../../lib/macro-types";

export default function MacroWorldPage() {
  return <ResearchShell active="macro" dataState="CACHED"><MacroWorldSurface world={systemFixture.world as unknown as MacroWorld} /></ResearchShell>;
}
