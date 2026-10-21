"use client";
import { useRouter } from "next/navigation";

import { ResearchDashboard } from "../../components/research/ResearchDashboard";
import { ResearchShell } from "../../components/research/ResearchShell";
import fixture from "../../lib/fixtures/research-system.json";
import type { ResearchSystem } from "../../lib/research-system-types";

export default function DemoPage() {
  const router = useRouter();
  const system = fixture as unknown as ResearchSystem;
  function selectModule(module: string) {
    const routes: Record<string, string> = { macro: "/macro?demo=1", company: "/companies?demo=1", inflation: "/macro/inflation?demo=1", risk: "/macro/risk?demo=1", rotation: "/markets?demo=1", historical: "/labs/historical?demo=1", watchlist: "/demo" };
    router.push(routes[module] ?? "/demo");
  }
  return <ResearchShell active="dashboard" dataState="DEMO" demoMode onModule={selectModule}><ResearchDashboard system={system} onModule={selectModule} /></ResearchShell>;
}
