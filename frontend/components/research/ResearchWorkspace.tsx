"use client";

import type { ReactNode } from "react";

export function ResearchWorkspace({
  code,
  title,
  ticker,
  children,
  inspector,
  onClose,
  depth = 1,
  inline = false
}: {
  code: string;
  title: string;
  ticker?: string;
  children: ReactNode;
  inspector?: ReactNode;
  onClose: () => void;
  depth?: number;
  inline?: boolean;
}) {
  if (inline && depth === 1) {
    return (
      <div className="research-workspace-layer workspace-inline" role="region" aria-label={`${title} workspace`}>
        <section className="research-workspace">
          <header className="workspace-header">
            <div><span>{code}</span><h2>{title}</h2></div>
            <div>
              <button type="button" onClick={onClose} aria-label={`Close ${title} workspace`}>← Overview</button>
            </div>
          </header>
          <div className={`workspace-body${inspector ? " workspace-with-inspector" : ""}`}>
            <div className="workspace-canvas">{children}</div>
            {inspector ? <aside className="workspace-inspector">{inspector}</aside> : null}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className={`research-workspace-layer workspace-depth-${depth}`} role="dialog" aria-modal="true" aria-label={`${title} workspace`}>
      <section className="research-workspace">
        <header className="workspace-header">
          <div><span>{code}</span><h2>{title}</h2></div>
          <div><small>{ticker ? `${ticker} / ` : ""}DEPTH {depth}</small><button type="button" onClick={onClose} aria-label={`Close ${title} workspace`}>Close <kbd>ESC</kbd></button></div>
        </header>
        <div className={`workspace-body${inspector ? " workspace-with-inspector" : ""}`}>
          <div className="workspace-canvas">{children}</div>
          {inspector ? <aside className="workspace-inspector">{inspector}</aside> : null}
        </div>
      </section>
    </div>
  );
}

export function InspectorRead({ label, children }: { label: string; children: ReactNode }) {
  return <div className="inspector-read"><span>{label}</span><div>{children}</div></div>;
}

export function WorkspaceAction({ children, onClick, secondary = false }: { children: ReactNode; onClick: () => void; secondary?: boolean }) {
  return <button type="button" className={`workspace-action${secondary ? " workspace-action-secondary" : ""}`} onClick={onClick}>{children}<span>→</span></button>;
}
