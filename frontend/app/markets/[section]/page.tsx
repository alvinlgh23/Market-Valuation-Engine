import { notFound } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MarketsRuntime } from "../../../components/research/MarketsRuntime";
import fixture from "../../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../../lib/research-system-types";

const SECTIONS = ["sectors", "breadth", "crowding", "defensive-rotation"];
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function MarketsSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!SECTIONS.includes(section)) notFound();
  const system = fixture as unknown as ResearchSystem;
  return <ResearchShell active="markets" dataState="PARTIAL"><MarketsRuntime section={section === "sectors" ? "rotation" : section} initial={system} /></ResearchShell>;
}
