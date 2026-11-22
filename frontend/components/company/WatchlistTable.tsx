"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { axisTone, shortState, TONE_GLYPH, TONE_LABEL } from "../../lib/judgment-tone.mjs";

type Row = { ticker: string; last_card: string | null; axes: Record<string, string>; changed: Array<{ axis: string; from: string; to: string; on: string }> };
const AXES = [["flow", "Money flow"], ["crowding", "Crowding"], ["macro", "Macro"], ["expectations", "Expectations"], ["fundamentals", "Fundamentals"], ["valuation", "Valuation"]] as const;

/** Checklists 8.2, 9.6: company x axis grid of the last recorded card (history only, no live request). */
export function WatchlistTable() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (!active) return; if (Array.isArray(body.rows)) setRows(body.rows as Row[]); else setError(body.error || "Watchlist unavailable."); })
      .catch((failure) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, []);
  if (error) return <p className="watchlist-note">Watchlist unavailable: {error}</p>;
  if (!rows) return <p className="watchlist-note">Loading the watchlist…</p>;
  const changedCount = rows.filter((row) => row.changed.length).length;
  return <section className="watchlist-grid" aria-label="Watchlist">
    <header>
      <h1>Watchlist</h1>
      <div className="wl-legend">{(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}<span className="wl-changed-key">changed since last card</span></div>
    </header>
    {changedCount ? <p className="wl-summary">{changedCount} of {rows.length} companies changed since their previous card.</p> : null}
    <div className="wl-table" role="table">
      <div className="wl-row wl-head" role="row"><span role="columnheader">Company</span>{AXES.map(([, label]) => <span role="columnheader" key={label}>{label}</span>)}<span role="columnheader">Card</span></div>
      {rows.map((row) => <Link href={`/company/${row.ticker}`} className="wl-row" role="row" key={row.ticker}>
        <span role="cell" className="wl-ticker">{row.ticker}</span>
        {AXES.map(([key, label]) => {
          const state = row.axes[key];
          const tone = state ? axisTone(key, state) : "unknown";
          const change = row.changed.find((item) => item.axis === key);
          return <span role="cell" key={key} className={`wl-cell tone-${tone}${change ? " changed" : ""}`} title={`${label}: ${state ?? "no card"}${change ? ` (was ${change.from})` : ""}`}>
            <em aria-hidden>{TONE_GLYPH[tone]}</em>{shortState(state)}
          </span>;
        })}
        <span role="cell" className="wl-date">{row.last_card ?? "—"}</span>
      </Link>)}
    </div>
  </section>;
}
