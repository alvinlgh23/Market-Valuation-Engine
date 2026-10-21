import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { LabsSurface } from "../../../components/research/ObjectResearchSurfaces";
import fixture from "../../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../../lib/research-system-types";

const SECTIONS = ["fragility", "historical"];
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function LabsPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const system = fixture as unknown as ResearchSystem;
  return <ResearchShell active="labs" dataState="PARTIAL"><LabsSurface section={section} system={system} /></ResearchShell>;
}
