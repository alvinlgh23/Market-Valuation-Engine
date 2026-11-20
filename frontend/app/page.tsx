"use client";
import { useRouter } from "next/navigation";

import { DashboardRuntime } from "../components/research/MarketsRuntime";
import { ResearchShell } from "../components/research/ResearchShell";
import fixture from "../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../lib/research-system-types";

export default function Page() {
  const router = useRouter();
  const system = fixture as unknown as ResearchSystem;
  function selectModule(module: string) {
    const routes: Record<string, string> = { macro: "/macro", company: "/companies", inflation: "/macro/inflation", risk: "/macro/risk", rotation: "/markets", historical: "/labs/historical", watchlist: "/" };
    router.push(routes[module] ?? "/");
  }
  return <ResearchShell active="dashboard" dataState="CACHED" onModule={selectModule}><DashboardRuntime initial={system} onModule={selectModule} /></ResearchShell>;
}
