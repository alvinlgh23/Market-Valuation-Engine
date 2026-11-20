import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MarketsRuntime } from "../../../components/research/MarketsRuntime";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { loadResearchSystem } from "../../../lib/research-server";

const SECTIONS = ["sectors", "breadth", "crowding", "defensive-rotation"];
export const dynamic = "force-dynamic";
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function MarketsSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const response = await loadResearchSystem();
  const system = response.data as unknown as ResearchSystem;
  return <ResearchShell active="markets" dataState="PARTIAL"><MarketsRuntime section={section === "sectors" ? "rotation" : section} initial={system} initialMeta={response.meta} /></ResearchShell>;
}
