"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { COLUMNS, sortHoldings, type Tone } from "../../lib/compare-model";
import { loadTodayHoldings } from "../../lib/today-client";
import { GapBar, gapMode } from "../ui/GapBar";
import type { TodayHolding } from "../../lib/today-model";

// Watchlist Compare: every holding side by side by number. Click a heading to sort (again to reverse).

const TONE_WORD: Record<Tone, string> = { supportive: "works for the company", against: "works against the company", mixed: "mixed", unknown: "no reading" };

export function CompareTable({ reloadKey, core }: { reloadKey: number; core: Record<string, string> }) {
  const [holdings, setHoldings] = useState<TodayHolding[] | null>(null);
  const [sort, setSort] = useState<{ key: string; direction: 1 | -1 }>({ key: "price", direction: -1 });
  useEffect(() => {
    let active = true;
    loadTodayHoldings().then((data) => { if (active) setHoldings(data?.holdings ?? []); });
    return () => { active = false; };
  }, [reloadKey]);
  const rows = useMemo(() => (holdings ? sortHoldings(holdings, sort.key, sort.direction) : []), [holdings, sort]);
  if (!holdings) return <p className="cmp-empty">Reading the stored cards…</p>;
  if (!holdings.length) return <p className="cmp-empty">No stored cards yet; they are built by the daily update.</p>;
  const toggle = (key: string) => setSort((s) => (s.key === key ? { key, direction: s.direction === 1 ? -1 : 1 } : { key, direction: -1 }));
  return <div className="cmp">
    <p className="cmp-legend">
      <span><i className="tone-supportive" />works for the company</span>
      <span><i className="tone-against" />works against it</span>
      <span><i className="tone-mixed" />mixed</span>
      <span className="cmp-legend-note">Dots are each card&apos;s own reading on that measure. Click a heading to sort.</span>
    </p>
    <div className="cmp-scroll">
      <table className="cmp-table">
        <thead><tr>
          <th scope="col" className="cmp-sticky">Company</th>
          {COLUMNS.map((c) => <th scope="col" key={c.key} aria-sort={sort.key === c.key ? (sort.direction === 1 ? "ascending" : "descending") : "none"}>
            <button type="button" onClick={() => toggle(c.key)} title={c.hint}>{c.label}<i aria-hidden>{sort.key === c.key ? (sort.direction === 1 ? "↑" : "↓") : "↕"}</i></button>
          </th>)}
        </tr></thead>
        <tbody>{rows.map((h) => <tr key={h.ticker}>
          <th scope="row" className="cmp-sticky"><Link href={`/company/${h.ticker}`}>{core[h.ticker] === "core" ? <em title="Core holding">★</em> : null}<b>{h.ticker}</b><small>{h.name}</small></Link></th>
          {COLUMNS.map((c) => {
            if (!h.compare) return <td key={c.key}>—</td>;
            const cell = c.cell(h.compare, h);
            // Colour by sign only where there is no reading dot; otherwise the dot alone carries the tone.
            const signClass = cell.tone || cell.sign == null ? "" : cell.sign < -0.0005 ? " down" : cell.sign > 0.0005 ? " up" : "";
            if (cell.text === "—") return <td key={c.key}><span className="cmp-val cmp-na">—</span>{cell.sub ? <small>{cell.sub}</small> : null}</td>;
            if (c.key === "price") return <td key={c.key} className="cmp-price" title={c.label}>
              <span className="cmp-val">{cell.tone && cell.tone !== "unknown" ? <i className={`cmp-dot tone-${cell.tone}`} aria-hidden /> : null}{cell.text}</span>
              {cell.sub ? <small>{cell.sub}</small> : null}
              {gapMode({ ...h.compare, valuationState: h.compare.states.valuation }) !== "none" && gapMode({ ...h.compare, valuationState: h.compare.states.valuation }) !== "beyond" ? <GapBar gap={{ ...h.compare, valuationState: h.compare.states.valuation }} compact label={false} /> : null}
            </td>;
            return <td key={c.key} title={cell.tone ? `${c.label}: ${TONE_WORD[cell.tone]}${c.axis && h.compare.states[c.axis] ? ` (${h.compare.states[c.axis]})` : ""}` : c.label}>
              <span className={`cmp-val${signClass}`}>{cell.tone && cell.tone !== "unknown" ? <i className={`cmp-dot tone-${cell.tone}`} aria-hidden /> : null}{cell.text}</span>
              {cell.sub ? <small>{cell.sub}</small> : null}
            </td>;
          })}
        </tr>)}</tbody>
      </table>
    </div>
    <p className="cmp-foot">From each company&apos;s stored judgment card; hover a heading for how it is measured. A side-by-side description, not a ranking or a recommendation.</p>
  </div>;
}
