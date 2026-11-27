import { PageDataStatus } from "../../../components/research/DataStatus";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MarketConditions } from "../../../components/macro/MarketConditions";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { loadMacroEvidence } from "../../../lib/macro-evidence-server";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

export const dynamic = "force-dynamic";

export default async function MarketConditionsPage() {
  const [response, evidence] = await Promise.all([loadResearchSystem(), loadMacroEvidence()]);
  const system = response.data as unknown as ResearchSystem;
  return <ResearchShell active="macro" dataState={researchShellState(response, "core_market")}>
    <PageDataStatus system={system} meta={response.meta} />
    <MarketConditions system={system} evidence={evidence} />
  </ResearchShell>;
}
