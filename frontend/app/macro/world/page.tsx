import type { ResearchSystem } from "../../../lib/research-system-types";
import { PageDataStatus } from "../../../components/research/DataStatus";
import { ResearchShell } from "../../../components/research/ResearchShell";
import { MacroWorldSurface, type FxPair } from "../../../components/macro/MacroWorldSurface";
import type { MacroWorld } from "../../../lib/macro-types";
import { loadResearchSystem, researchShellState } from "../../../lib/research-server";

export const dynamic = "force-dynamic";

type Search = Promise<Record<string, string | string[] | undefined>>;
const one = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value) ?? "";

/** Stored FX pairs (USD/KRW, EUR/USD...) recorded by the daily refresh; empty when absent. */
function fxPairs(data: unknown): Record<string, FxPair> {
  const macro = (data as { modules?: { core_market?: { payload?: { macro?: { fx_pairs?: unknown } } } } })?.modules?.core_market?.payload?.macro;
  return macro?.fx_pairs && typeof macro.fx_pairs === "object" ? macro.fx_pairs as Record<string, FxPair> : {};
}

export default async function MacroWorldPage({ searchParams }: { searchParams: Search }) {
  const query = await searchParams;
  const response = await loadResearchSystem();
  return <ResearchShell active="macro" dataState={researchShellState(response)}><PageDataStatus system={response.data as unknown as ResearchSystem} meta={response.meta} /><MacroWorldSurface world={response.data.world as unknown as MacroWorld} fxPairs={fxPairs(response.data)} initial={{ mode: one(query.mode), region: one(query.region), detail: one(query.detail), edge: one(query.edge) }} /></ResearchShell>;
}
