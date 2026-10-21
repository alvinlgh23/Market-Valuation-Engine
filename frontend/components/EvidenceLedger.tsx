import { TerminalPanel } from "./TerminalPanel";

export function EvidenceLedger({ supporting, challenging }: { supporting: string[]; challenging: string[] }) {
  return (
    <TerminalPanel title="Evidence Ledger">
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="mb-2 text-[10px] uppercase tracking-[0.08em] text-terminal-green">Supporting thesis</div>
          <ul className="space-y-1 text-[12px] text-terminal-text">
            {supporting.map((item) => (
              <li key={item}>+ {item}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-2 text-[10px] uppercase tracking-[0.08em] text-terminal-amber">Challenging thesis</div>
          <ul className="space-y-1 text-[12px] text-terminal-text">
            {challenging.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </TerminalPanel>
  );
}
