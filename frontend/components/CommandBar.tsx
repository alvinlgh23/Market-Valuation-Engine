"use client";

import { FormEvent, useState } from "react";

export function CommandBar({ command, onCommand, onPalette }: { command: string; onCommand: (command: string) => void; onPalette: () => void }) {
  const [value, setValue] = useState(command);
  const [history, setHistory] = useState(["overview", "inflation", "company PLTR", "fragility"]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (value.trim()) {
      setHistory((items) => [value.trim(), ...items.filter((item) => item !== value.trim())].slice(0, 4));
    }
    onCommand(value);
  }

  const hint = ["overview", "inflation", "cpi", "inflation-pressure", "company PLTR", "fragility", "historical", "watchlist"].find(
    (item) => item.startsWith(value) && item !== value
  );

  return (
    <div className="border-b border-terminal-line bg-terminal-bg px-3 py-2">
      <form onSubmit={submit} className="flex min-h-8 items-center gap-2 text-[13px]">
        <span className="shrink-0 text-terminal-amber">MSOS &gt;</span>
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="min-w-0 flex-1 bg-transparent text-terminal-text outline-none placeholder:text-terminal-faint"
          placeholder="inflation"
          spellCheck={false}
        />
        {hint ? <span className="hidden text-[11px] text-terminal-faint sm:inline">tab: {hint}</span> : null}
        <button type="button" onClick={onPalette} className="border border-terminal-line px-2 py-1 text-[10px] uppercase text-terminal-muted hover:text-terminal-text">
          Cmd+K
        </button>
      </form>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[10px] uppercase tracking-[0.08em] text-terminal-faint">
        <span>Recent:</span>
        {history.map((item) => (
          <button key={item} onClick={() => setValue(item)} className="text-terminal-muted hover:text-terminal-amber">
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}
