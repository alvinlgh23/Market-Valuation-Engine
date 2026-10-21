import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroResearch } from "../../../components/research/ObjectResearchSurfaces";
import fixture from "../../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { MacroRatesRuntime } from "../../../components/macro/MacroRatesRuntime";

const SECTIONS = ["central-banks", "inflation", "rates", "liquidity", "fx", "risk"];
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function MacroSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const system = fixture as unknown as ResearchSystem;
  const state = section === "inflation" ? system.modules.inflation.state : system.modules.core_market.state;
  return <ResearchShell active="macro" dataState={state as never}>{section === "rates" ? <MacroRatesRuntime initial={system} /> : <MacroResearch section={section} system={system} />}</ResearchShell>;
}
