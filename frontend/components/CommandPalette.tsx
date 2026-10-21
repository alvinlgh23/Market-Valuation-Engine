"use client";

import { useEffect } from "react";
import type { CommandItem } from "../lib/types";

const commands: CommandItem[] = [
  { label: "Open Overview", command: "overview" },
  { label: "Open US Inflation Pressure", command: "inflation" },
  { label: "Open Company Report: PLTR", command: "company PLTR" },
  { label: "Open Fragility Lab", command: "fragility" },
  { label: "Open Historical Comparator", command: "historical" },
  { label: "Open Watchlist", command: "watchlist" },
  { label: "Ask: Why does the 30Y yield matter?", command: "ask 30y", response: "The 30Y anchors long-duration discount rates and fiscal stress sensitivity." },
  { label: "Ask: Is this another dot-com bubble?", command: "ask bubble", response: "The current structure has stronger earnings and FCF support, but breadth and valuation gaps require monitoring." }
];

export function CommandPalette({
  open,
  onClose,
  onCommand,
  onResponse
}: {
  open: boolean;
  onClose: () => void;
  onCommand: (command: string) => void;
  onResponse: (response: string) => void;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 p-4">
      <div className="mx-auto mt-20 max-w-2xl border border-terminal-line bg-terminal-panel text-[12px] shadow-2xl shadow-black">
        <div className="border-b border-terminal-line bg-terminal-panel2 px-3 py-2 uppercase tracking-[0.08em] text-terminal-muted">Command Palette</div>
        <div className="max-h-[420px] overflow-y-auto p-2">
          {commands.map((item) => (
            <button
              key={item.label}
              onClick={() => {
                if (item.response) onResponse(item.response);
                onCommand(item.command);
                onClose();
              }}
              className="block w-full border border-transparent px-2 py-2 text-left text-terminal-text hover:border-terminal-line hover:bg-terminal-panel2"
            >
              <span className="text-terminal-amber">MSOS &gt;</span> {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
