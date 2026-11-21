"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

type Row = { ticker: string; last_card: string | null; axes: Record<string, string>; changed: Array<{ axis: string; from: string; to: string; on: string }> };
const AXES = [["macro", "Macro"], ["flow", "Money flow"], ["valuation", "Valuation"], ["crowding", "Crowding"], ["expectations", "Expectations"]] as const;

/** Checklist 8.2: the watchlist reads the last recorded card per company (no live data needed to render). */
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
  return <section className="watchlist-table" aria-label="Watchlist">
    <header><h1>Watchlist</h1><p>{"Each company's last judgment card. Companies with changed readings come first. Open a company to build today's card."}</p></header>
    <table>
      <thead><tr><th>Company</th>{AXES.map(([, label]) => <th key={label}>{label}</th>)}<th>Last card</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.ticker} className={row.changed.length ? "changed" : ""}>
        <td><Link href={`/company/${row.ticker}`}>{row.ticker}</Link>{row.changed.length ? <small>{row.changed.length} changed</small> : null}</td>
        {AXES.map(([key]) => <td key={key} title={row.changed.find((item) => item.axis === key) ? `was ${row.changed.find((item) => item.axis === key)?.from}` : undefined}>{row.axes[key] ?? "—"}</td>)}
        <td>{row.last_card ?? "not generated"}</td>
      </tr>)}</tbody>
    </table>
  </section>;
}
