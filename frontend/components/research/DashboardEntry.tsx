"use client";
import { useRouter } from "next/navigation";

import { DashboardRuntime } from "./MarketsRuntime";
import { ResearchShell, type ResearchDataState } from "./ResearchShell";
import type { ResearchSystem } from "../../lib/research-system-types";
import type { ResearchResponse } from "../../lib/research-response";

const MODULE_ROUTES: Record<string, string> = { macro: "/macro", company: "/companies", inflation: "/macro/inflation", risk: "/macro/risk", rotation: "/markets", historical: "/labs/historical", watchlist: "/" };

export function DashboardEntry({ initial, initialMeta, dataState }: { initial: ResearchSystem; initialMeta: ResearchResponse["meta"]; dataState: ResearchDataState }) {
  const router = useRouter();
  const selectModule = (module: string) => router.push(MODULE_ROUTES[module] ?? "/");
  return <ResearchShell active="dashboard" dataState={dataState} onModule={selectModule}><DashboardRuntime initial={initial} initialMeta={initialMeta} onModule={selectModule} /></ResearchShell>;
}
