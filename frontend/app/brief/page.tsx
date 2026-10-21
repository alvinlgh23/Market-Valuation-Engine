import { ResearchShell } from "../../components/research/ResearchShell";
import { FullMarketBrief } from "../../components/research/ObjectResearchSurfaces";
import fixture from "../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../lib/research-system-types";
export default function BriefPage() { const system = fixture as unknown as ResearchSystem; return <ResearchShell active="dashboard" dataState="CACHED"><FullMarketBrief system={system} /></ResearchShell>; }
