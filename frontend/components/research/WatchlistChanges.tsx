"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { axisTone, shortState, TONE_GLYPH } from "../../lib/judgment-tone.mjs";

type Row = { ticker: string; last_card: string | null; changed: Array<{ axis: string; from: string; to: string; on: string }> };
const AXIS_LABEL: Record<string, string> = { macro: "Macro", flow: "Money flow", valuation: "Valuation", crowding: "Crowding", expectations: "Expectations", fundamentals: "Fundamentals" };

/** Checklist 9.7: what changed on the watchlist since each company's previous card (history only). */
export function WatchlistChanges() {
  const [rows, setRows] = useState<Row[] | null>(null);
  useEffect(() => {
    let active = true;
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then((response) => response.json()).then((body) => { if (active && Array.isArray(body.rows)) setRows(body.rows as Row[]); })
      .catch(() => { if (active) setRows([]); });
    return () => { active = false; };
  }, []);
  if (!rows) return null;
  const changes = rows.flatMap((row) => row.changed.map((change) => ({ ...change, ticker: row.ticker })));
  return <section className="today-watchlist" aria-label="Watchlist changes">
    <header><span>Watchlist</span><Link href="/companies">Open grid →</Link></header>
    {changes.length ? <div>{changes.map((change) => {
      const tone = axisTone(change.axis, change.to);
      return <Link key={`${change.ticker}-${change.axis}`} href={`/company/${change.ticker}`} className={`today-change tone-${tone}`} title={`${change.from} → ${change.to} (${change.on})`}>
        <b>{change.ticker}</b><span>{AXIS_LABEL[change.axis] ?? change.axis}</span><em aria-hidden>{TONE_GLYPH[tone]}</em>{shortState(change.from)} → {shortState(change.to)}
      </Link>;
    })}</div> : <p>No company changed since its previous card.</p>}
  </section>;
}
