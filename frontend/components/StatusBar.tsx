export function StatusBar({
  density,
  onToggleDensity,
  fedState,
  cacheAge,
  sources,
  build,
  terminalStatus
}: {
  density: "report" | "terminal";
  onToggleDensity: () => void;
  fedState: string;
  cacheAge: string;
  sources: string;
  build: string;
  terminalStatus: string;
}) {
  return (
    <footer className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-terminal-line bg-terminal-panel2 px-3 py-1 text-[10px] uppercase tracking-[0.06em] text-terminal-muted">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span>FED: <span className="text-terminal-text">{fedState}</span></span>
        <span>30Y: <span className="text-terminal-amber">Above Watch Threshold</span></span>
        <span>Cache: <span className="text-terminal-text">{cacheAge}</span></span>
        <span>Sources: <span className="text-terminal-text">{sources}</span></span>
        <span>Build: <span className="text-terminal-text">{build}</span></span>
        <span>Cmd+K</span>
        <span>Terminal: <span className="text-terminal-green">{terminalStatus}</span></span>
      </div>
      <button onClick={onToggleDensity} className="text-terminal-amber hover:text-terminal-text">
        Density: {density}
      </button>
    </footer>
  );
}
