"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { axisTone, shortState, TONE_GLYPH } from "../../lib/judgment-tone.mjs";

type Row = { ticker: string; last_card: string | null; axes: Record<string, string>; changed: Array<{ axis: string; from: string; to: string; on: string }> };
const AXES: Array<[string, string]> = [["flow", "Flow"], ["crowding", "Crowd"], ["macro", "Macro"], ["expectations", "Est."], ["fundamentals", "Fund."], ["valuation", "Value"]];

/** Today page (checklist 9.7): the watchlist as a small heatmap; changed cells are outlined. History only, no live request. */
export function WatchlistChanges() {
  const [rows, setRows] = useState<Row[] | null>(null);
  useEffect(() => {
    let active = true;
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then((response) => response.json()).then((body) => { if (active && Array.isArray(body.rows)) setRows(body.rows as Row[]); })
      .catch(() => { if (active) setRows([]); });
    return () => { active = false; };
  }, []);
  if (!rows) return <div className="today-heat today-heat-loading" aria-busy="true" />;
  if (!rows.length) return null;
  const changed = rows.reduce((total, row) => total + row.changed.length, 0);
  return <div className="today-heat" role="table" aria-label="Watchlist heatmap">
    <div className="today-heat-row today-heat-head" role="row"><span />{AXES.map(([key, label]) => <span key={key} role="columnheader">{label}</span>)}</div>
    {rows.map((row) => <Link key={row.ticker} href={`/company/${row.ticker}`} className="today-heat-row" role="row">
      <b role="rowheader">{row.ticker}</b>
      {AXES.map(([key]) => {
        const state = row.axes[key];
        const tone = state ? axisTone(key, state) : "unknown";
        const change = row.changed.find((item) => item.axis === key);
        return <i key={key} role="cell" className={`tone-${tone}${change ? " changed" : ""}`} title={`${row.ticker} · ${key}: ${state ?? "no card"}${change ? ` (was ${change.from})` : ""}`} aria-label={`${key} ${shortState(state)}`}>{change ? TONE_GLYPH[tone] : ""}</i>;
      })}
    </Link>)}
    <small>{changed ? `${changed} changed cell${changed === 1 ? "" : "s"} outlined` : "No change since previous cards"}</small>
  </div>;
}
