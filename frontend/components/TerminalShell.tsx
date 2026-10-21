"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import type { ViewKey, WatchItem } from "../lib/types";
import { CommandBar } from "./CommandBar";
import { CommandPalette } from "./CommandPalette";
import { RightRail } from "./RightRail";
import { SidebarNav } from "./SidebarNav";
import { StatusBar } from "./StatusBar";
import { TerminalHeader } from "./TerminalHeader";

export function TerminalShell({
  active,
  command,
  asOf,
  region,
  dataStatus,
  session,
  cacheAge,
  build,
  fedState,
  terminalStatus,
  watch,
  children,
  onNavigate
}: {
  active: ViewKey;
  command: string;
  asOf: string;
  region: string;
  dataStatus: string;
  session: string;
  cacheAge: string;
  build: string;
  fedState: string;
  terminalStatus: string;
  watch: WatchItem[];
  children: ReactNode;
  onNavigate: (key: ViewKey, command: string) => void;
}) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [density, setDensity] = useState<"report" | "terminal">("report");
  const [mockResponse, setMockResponse] = useState("");
  const [mobileModulesOpen, setMobileModulesOpen] = useState(false);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function routeCommand(value: string) {
    const v = value.toLowerCase();
    const directTicker = value.trim().toUpperCase();
    const companyMatch = value.trim().match(/^company\s+([a-z.]+)$/i);
    if (/^[A-Z][A-Z0-9.\-]{0,9}$/.test(directTicker)) {
      window.location.href = `/company/${directTicker}`;
      return;
    }
    if (companyMatch) {
      window.location.href = `/company/${companyMatch[1].toUpperCase()}`;
      return;
    }
    if (v === "inflation" || v === "cpi" || v.includes("inflation-pressure")) onNavigate("inflation", "inflation");
    else if (v.includes("company")) onNavigate("company", "company PLTR");
    else if (v.includes("fragility") || v.includes("historical")) onNavigate(v.includes("historical") ? "historical" : "fragility", value);
    else if (v.includes("watchlist")) onNavigate("watchlist", "watchlist");
    else if (v.includes("policy")) onNavigate("policy", "policy");
    else if (v.includes("liquidity")) onNavigate("liquidity", "liquidity");
    else if (v.includes("market")) onNavigate("market", "market");
    else onNavigate("overview", "overview");
  }

  return (
    <div className="min-h-screen bg-terminal-bg p-0 font-mono text-terminal-text md:p-3">
      <div className="mx-auto flex min-h-screen max-w-[1500px] flex-col border-terminal-line bg-terminal-bg md:min-h-[calc(100vh-1.5rem)] md:border">
        <TerminalHeader mode="REPORT" asOf={asOf} region={region} session={session} dataStatus={dataStatus} />
        <CommandBar key={command} command={command} onCommand={routeCommand} onPalette={() => setPaletteOpen(true)} />
        <div className="grid flex-1 grid-cols-1 overflow-hidden md:grid-cols-[170px_minmax(0,1fr)_230px]">
          <div className="hidden md:block">
            <SidebarNav active={active} onSelect={onNavigate} />
          </div>
          <main className={`overflow-y-auto ${density === "terminal" ? "p-2" : "p-3"} space-y-3`}>
            <div className="md:hidden">
              <button
                onClick={() => setMobileModulesOpen((open) => !open)}
                className="flex w-full items-center justify-between border border-terminal-line bg-terminal-panel px-3 py-2 text-left text-[11px] uppercase tracking-[0.08em] text-terminal-muted"
              >
                <span>Modules / {active}</span>
                <span className="text-terminal-amber">{mobileModulesOpen ? "close" : "open"}</span>
              </button>
              {mobileModulesOpen ? (
                <div className="border-x border-b border-terminal-line">
                  <SidebarNav
                    active={active}
                    onSelect={(key, nextCommand) => {
                      onNavigate(key, nextCommand);
                      setMobileModulesOpen(false);
                    }}
                  />
                </div>
              ) : null}
            </div>
            {mockResponse ? (
              <div className="border border-terminal-line bg-terminal-panel px-3 py-2 text-[12px] text-terminal-amber">MOCK RESPONSE: {mockResponse}</div>
            ) : null}
            {children}
          </main>
          <div className="hidden md:block">
            <RightRail watch={watch} />
          </div>
        </div>
        <StatusBar
          density={density}
          onToggleDensity={() => setDensity(density === "report" ? "terminal" : "report")}
          fedState={fedState}
          cacheAge={cacheAge}
          sources={dataStatus}
          build={build}
          terminalStatus={terminalStatus}
        />
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onCommand={routeCommand} onResponse={setMockResponse} />
    </div>
  );
}
