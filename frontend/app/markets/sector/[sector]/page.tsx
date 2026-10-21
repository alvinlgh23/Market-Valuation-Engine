import { ResearchShell } from "../../../../components/research/ResearchShell";
import { MarketsRuntime } from "../../../../components/research/MarketsRuntime";
import fixture from "../../../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../../../lib/research-system-types";

export default async function SectorPage({ params }: { params: Promise<{ sector: string }> }) {
  const { sector } = await params;
  const system = fixture as unknown as ResearchSystem;
  return <ResearchShell active="markets" dataState="PARTIAL"><MarketsRuntime sector={sector} initial={system} /></ResearchShell>;
}
