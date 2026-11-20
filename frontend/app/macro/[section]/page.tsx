import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroResearch } from "../../../components/research/ObjectResearchSurfaces";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { MacroRatesRuntime } from "../../../components/macro/MacroRatesRuntime";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

const SECTIONS = ["central-banks", "inflation", "rates", "liquidity", "fx", "risk"];
export const dynamic = "force-dynamic";
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function MacroSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const response = await loadResearchSystem();
  const system = response.data as unknown as ResearchSystem;
  const state = researchShellState(response, section === "inflation" ? "inflation" : "core_market");
  return <ResearchShell active="macro" dataState={state}>{section === "rates" ? <MacroRatesRuntime initial={system} /> : <MacroResearch section={section} system={system} />}</ResearchShell>;
}
