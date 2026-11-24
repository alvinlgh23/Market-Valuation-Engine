"use client";
import { useState, type ReactNode } from "react";

export type CriteriaContent = {
  rule: string;
  now?: string | null;
  exposure?: string | null;
  asOf?: string | null;
  track?: { predictive: boolean; verdict: string; text: string } | null;
  notes?: string[];
};

function trackBadge(track: NonNullable<CriteriaContent["track"]>) {
  if (track.predictive) return <em className="crit-badge tested">Tested</em>;
  if (track.verdict === "NOT_TESTED") return <em className="crit-badge untested">Not tested</em>;
  return <em className="crit-badge condition">Condition, not a forecast</em>;
}

/**
 * Checklist 14.4: any reading can show how it was judged. Hover or keyboard focus opens a small
 * panel with the rule, what it reads now, how holdings are linked, the data date and the track record.
 */
export function Criteria({ children, criteria, align = "left", block = false }: { children: ReactNode; criteria: CriteriaContent; align?: "left" | "right"; block?: boolean }) {
  // Checklist 18.10: open upwards when the panel would run off the bottom of the screen.
  const [up, setUp] = useState(false);
  const place = (event: { currentTarget: HTMLElement }) => {
    const box = event.currentTarget.getBoundingClientRect();
    setUp(window.innerHeight - box.bottom < 340 && box.top > window.innerHeight - box.bottom);
  };
  return <span className={`crit${block ? " crit-block" : ""}${up ? " crit-up" : ""}`} tabIndex={0} onMouseEnter={place} onFocus={place}>
    <span className="crit-trigger">{children}</span>
    <span className={`crit-pop crit-${align}`} role="tooltip">
      <span className="crit-row"><small>Rule</small><span>{criteria.rule}</span></span>
      {criteria.now ? <span className="crit-row"><small>Now</small><span>{criteria.now}</span></span> : null}
      {criteria.exposure ? <span className="crit-row"><small>Holdings</small><span>{criteria.exposure}</span></span> : null}
      {criteria.track ? <span className="crit-row"><small>Track record</small><span>{trackBadge(criteria.track)}{criteria.track.text}</span></span> : null}
      {criteria.notes?.length ? <span className="crit-row"><small>Note</small><span>{criteria.notes[0]}</span></span> : null}
      {criteria.asOf ? <span className="crit-foot">Data as of {criteria.asOf}</span> : null}
    </span>
  </span>;
}
