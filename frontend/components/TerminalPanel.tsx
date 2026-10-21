import type { ReactNode } from "react";

export function TerminalPanel({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="border border-terminal-line bg-terminal-panel">
      {title ? (
        <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-terminal-line bg-terminal-panel2 px-3 py-1">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-terminal-text">{title}</h2>
          {right ? <div className="text-[11px] uppercase text-terminal-muted">{right}</div> : null}
        </div>
      ) : null}
      <div className="p-3">{children}</div>
    </section>
  );
}
