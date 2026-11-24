import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { LabsRuntime } from "../../../components/research/MarketsRuntime";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

const SECTIONS = ["historical"];   // fragility deleted (checklist 10.10)
export const dynamic = "force-dynamic";
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function LabsPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const response = await loadResearchSystem();
  return <ResearchShell active="labs" dataState={researchShellState(response)}><LabsRuntime section={section} initial={response.data as unknown as ResearchSystem} initialMeta={response.meta} /></ResearchShell>;
}
