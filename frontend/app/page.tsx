import { DashboardEntry } from "../components/research/DashboardEntry";
import type { ResearchSystem } from "../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../lib/research-server";

export const dynamic = "force-dynamic";

export default async function Page() {
  const response = await loadResearchSystem();
  return <DashboardEntry initial={response.data as unknown as ResearchSystem} initialMeta={response.meta} dataState={researchShellState(response)} />;
}
