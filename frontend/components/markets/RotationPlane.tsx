"use client";

import Link from "next/link";
import type { SectorResearchObject } from "../../lib/market-research";

// The 11 S&P 500 sectors on one plane (moved from the sector page to the Markets overview, 2026-11-27):
// across = 6-month performance against the S&P 500, up = how crowded the sector's positioning is.
// Dots carry your holdings' tickers. Readings come from the sector engine; nothing is recalculated.

const CROWD_Y: Record<string, number> = { crowded: 16, extended: 36, neutral: 58, unloved: 82 };
function crowdY(crowding: string) {
  const key = crowding.toLowerCase();
  return CROWD_Y[key] ?? (key.includes("elevated") ? 26 : key.includes("moderate") ? 50 : 70);
}

export function RotationPlane({ sectors, names, held }: { sectors: SectorResearchObject[]; names: Record<string, string>; held: Record<string, string[]> }) {
  const items = sectors.filter((s) => s.rel6m != null);
  const max = Math.max(0.1, ...items.map((s) => Math.abs(s.rel6m ?? 0)));
  const placed: Array<{ x: number; y: number }> = [];
  return <section className="mkt-plane" aria-label="Sectors by six-month performance and crowding">
    <div className="mkt-plane-area" role="img" aria-label="Sector map">
      <span className="mkt-plane-x">← Lagging the S&amp;P 500 · 6 months · Leading →</span>
      <span className="mkt-plane-y">More crowded ↑</span>
      <i className="mkt-plane-mid" aria-hidden />
      {items.map((s) => {
        const x = Math.max(8, Math.min(92, 50 + ((s.rel6m ?? 0) / max) * 42));
        let y = crowdY(s.crowding);
        let near = placed.filter((p) => Math.abs(p.x - x) < 19 && Math.abs(p.y - y) < 10).length;
        for (let step = 1; near && step < 8; step += 1) { const tryY = Math.max(8, Math.min(90, y + (step % 2 ? 11 : -11) * Math.ceil(step / 2))); if (!placed.some((p) => Math.abs(p.x - x) < 19 && Math.abs(p.y - tryY) < 10)) { y = tryY; near = 0; } }

        placed.push({ x, y });
        const mine = held[s.ticker] ?? [];
        return <Link key={s.ticker} href={`/markets?sector=${s.slug}`} className={`mkt-dot ${(s.rel6m ?? 0) >= 0 ? "up" : "down"}${mine.length ? " held" : ""}`} style={{ left: `${x}%`, top: `${y}%` }}
          title={`${names[s.ticker] ?? s.name}: ${((s.rel6m ?? 0) * 100).toFixed(1)} points vs S&P 500 over 6 months; positioning ${s.crowding.toLowerCase()}${mine.length ? `; your holdings: ${mine.join(", ")}` : ""}`}>
          <b>{names[s.ticker] ?? s.name}</b>{mine.length ? <small>{mine.length > 3 ? `${mine.slice(0, 2).join(" ")} +${mine.length - 2}` : mine.join(" ")}</small> : null}
        </Link>;
      })}
    </div>
    <p className="mkt-plane-note">Across: six-month performance against the S&amp;P 500. Up: positioning (crowded at the top, unloved at the bottom). Industry and theme funds are listed under Themes and assets below.</p>
  </section>;
}
