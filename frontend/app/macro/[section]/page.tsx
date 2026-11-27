import { PageDataStatus } from "../../../components/research/DataStatus";
import { notFound, redirect } from "next/navigation";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { InflationView } from "../../../components/macro/InflationView";
import type { ResearchSystem } from "../../../lib/research-system-types";
import { loadMacroEvidence } from "../../../lib/macro-evidence-server";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

// 2026-11-27: the macro menu has five pages. Rates, Liquidity, FX and Risk regime live on Market conditions;
// Central banks lives on the World map. Old links redirect to the matching section, so none break.
const REDIRECTS: Record<string, string> = {
  rates: "/macro/conditions#rates",
  liquidity: "/macro/conditions#liquidity",
  fx: "/macro/conditions#fx",
  risk: "/macro/conditions#regime",
  "central-banks": "/macro/world#central-banks",
};
const SECTIONS = ["inflation", ...Object.keys(REDIRECTS)];
export const dynamic = "force-dynamic";
export function generateStaticParams() { return SECTIONS.map((section) => ({ section })); }
export default async function MacroSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (REDIRECTS[section]) redirect(REDIRECTS[section]);
  if (section !== "inflation") notFound();
  const [response, evidence] = await Promise.all([loadResearchSystem(), loadMacroEvidence()]);
  const system = response.data as unknown as ResearchSystem;
  return <ResearchShell active="macro" dataState={researchShellState(response, "inflation")}><PageDataStatus system={system} meta={response.meta} /><InflationView system={system} breakeven={evidence.breakeven10y} /></ResearchShell>;
}
