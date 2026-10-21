"use client";

import type { ViewKey } from "../lib/types";

const moduleGroups: Array<{ title: string; items: Array<{ key?: ViewKey; label: string; command?: string }> }> = [
  { title: "Overview", items: [{ key: "overview", label: "Daily Briefing", command: "overview" }] },
  {
    title: "Policy",
    items: [
      { key: "policy", label: "Fed", command: "policy" },
      { label: "ECB" },
      { label: "BOJ" }
    ]
  },
  {
    title: "Markets",
    items: [
      { key: "liquidity", label: "Liquidity", command: "liquidity" },
      { key: "market", label: "Rotation", command: "market" },
      { key: "company", label: "Companies", command: "company PLTR" },
      { key: "inflation", label: "US Inflation", command: "inflation" }
    ]
  },
  {
    title: "Labs",
    items: [
      { key: "fragility", label: "Fragility", command: "fragility" },
      { key: "historical", label: "Historical", command: "historical" }
    ]
  },
  {
    title: "Tools",
    items: [
      { key: "watchlist", label: "Watchlist", command: "watchlist" },
      { label: "Settings" }
    ]
  }
];

export function SidebarNav({ active, onSelect }: { active: ViewKey; onSelect: (key: ViewKey, command: string) => void }) {
  return (
    <nav className="border-r border-terminal-line bg-terminal-panel p-2 text-[12px] uppercase tracking-[0.06em] text-terminal-muted">
      <div className="mb-2 border-b border-terminal-line pb-2 text-[10px] text-terminal-faint">Research Modules</div>
      <div className="space-y-3">
        {moduleGroups.map((group) => (
          <div key={group.title}>
            <div className="mb-1 text-[10px] font-semibold text-terminal-text">{group.title}</div>
            <div className="space-y-0.5">
              {group.items.map((module) =>
                module.key && module.command ? (
                  <button
                    key={module.label}
                    onClick={() => onSelect(module.key as ViewKey, module.command as string)}
                    className={`block w-full border border-transparent px-2 py-1 text-left normal-case hover:border-terminal-line hover:text-terminal-text ${
                      active === module.key ? "border-terminal-line bg-terminal-panel2 text-terminal-amber" : ""
                    }`}
                  >
                    {module.label}
                  </button>
                ) : (
                  <div key={module.label} className="px-2 py-1 normal-case text-terminal-faint">
                    {module.label}
                  </div>
                )
              )}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
