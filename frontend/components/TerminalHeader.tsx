export function TerminalHeader({
  mode,
  asOf,
  region,
  session,
  dataStatus
}: {
  mode: string;
  asOf: string;
  region: string;
  session: string;
  dataStatus: string;
}) {
  return (
    <header className="border-b border-terminal-line bg-terminal-panel2 px-3 py-2 uppercase tracking-[0.08em]">
      <div className="grid gap-2 text-[11px] md:grid-cols-[220px_1fr] md:items-center">
        <div>
          <div className="text-[13px] font-semibold tracking-[0.06em] text-terminal-text">Market Structure OS</div>
          <div className="mt-0.5 text-[10px] text-terminal-muted">Research Terminal</div>
        </div>
        <div className="grid gap-x-5 gap-y-1 text-[10px] text-terminal-muted sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <span className="text-terminal-faint">Region:</span> <span className="text-terminal-text">{region}</span>
          </div>
          <div>
            <span className="text-terminal-faint">Research Session:</span> <span className="text-terminal-text">{session}</span>
          </div>
          <div>
            <span className="text-terminal-faint">Mode:</span> <span className="text-terminal-text">{mode}</span>
          </div>
          <div>
            <span className="text-terminal-faint">As Of:</span> <span className="text-terminal-text">{asOf}</span>
          </div>
          <div>
            <span className="text-terminal-faint">Data:</span> <span className="text-terminal-amber">{dataStatus}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
