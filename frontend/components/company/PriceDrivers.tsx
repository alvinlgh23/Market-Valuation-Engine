// What moved the share price: macro, broad market, sector, or the company itself (checklists 10.2 and 10.3).
// Includes live post-Friday daily bridge so Monday–Thursday surges/drops are never invisible.

export type AttributionWindow = {
  price_change: number; total_log: number;
  parts: { macro: number; market: number; sector: number; company: number };
  macro_by_factor: Record<string, number>; top_macro: { factor: string; value: number } | null; company_z: number | null;
};
export type RecentMove = {
  latest_date?: string;
  since_window_end?: { from: string; to: string; trading_days: number; stock_change: number; spy_change: number } | null;
  last_5d?: { stock_change: number; spy_change: number; vs_spy: number; z_5d: number | null } | null;
};
export type Attribution = {
  status: string; reason?: string; as_of?: string; fit?: { r2: number | null; start: string; end: string };
  factor_labels?: Record<string, string>; windows?: Record<string, AttributionWindow>; recent_move?: RecentMove | null;
};
export type PriceReading = {
  kind: "noise" | "watch" | "company" | "fundamentals" | "unknown" | string; label: string; short?: string; detail: string; confidence: string;
  window: string; price_change?: number; parts?: AttributionWindow["parts"]; company_z?: number | null; low_fit_note?: string | null;
};

const PARTS = [["macro", "Macro"], ["market", "Market"], ["sector", "Sector"], ["company", "Company"]] as const;
const SCALE = 0.5;   // half the bar = a 50% log move

function pct(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  const rounded = Number((value * 100).toFixed(1));
  if (rounded === 0) return "0.0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(1)}%`;
}

export function factorBreakdown(attribution: Attribution | null | undefined, window = "3M"): string {
  const w = attribution?.windows?.[window];
  if (!w) return attribution?.reason ?? "No attribution";
  const factors = Object.entries(w.macro_by_factor).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([id, value]) => `  ${attribution?.factor_labels?.[id] ?? id}: ${pct(value)}`);
  const since = attribution?.recent_move?.since_window_end;
  const recentLine = since ? `Since ${since.from} (to ${since.to}): ${pct(since.stock_change)} vs S&P 500 ${pct(since.spy_change)}` : null;
  return [`${window} price ${pct(w.price_change)}`, `Macro ${pct(w.parts.macro)}`, ...factors, `Market ${pct(w.parts.market)}`, `Sector ${pct(w.parts.sector)}`,
    `Company ${pct(w.parts.company)}${w.company_z == null ? "" : ` (${w.company_z >= 0 ? "+" : ""}${w.company_z.toFixed(1)}x normal range)`}`,
    ...(recentLine ? [recentLine] : []),
    `Fit R² ${attribution?.fit?.r2 == null ? "—" : attribution.fit.r2.toFixed(2)}`].join("\n");
}

/** Diverging stacked bar: pieces that pushed the price down go left of zero, up go right. */
export function DriverBar({ parts, title }: { parts?: AttributionWindow["parts"]; title?: string }) {
  if (!parts) return <span className="pd-bar pd-empty" title={title}>—</span>;
  const segments: { key: string; style: React.CSSProperties }[] = [];
  let down = 0, up = 0;
  for (const [key] of PARTS) {
    const width = Math.min(Math.abs(parts[key]), SCALE) / SCALE * 50;
    if (!width) continue;
    segments.push({ key, style: parts[key] < 0 ? { right: `${50 + down}%`, width: `${width}%` } : { left: `${50 + up}%`, width: `${width}%` } });
    if (parts[key] < 0) down += width; else up += width;
  }
  return <span className="pd-bar" title={title} role="img" aria-label={PARTS.map(([key, label]) => `${label} ${pct(parts[key])}`).join(", ")}>
    <i className="pd-axis" />
    {segments.map(({ key, style }) => <b key={key} className={`pd-seg pd-${key}`} style={style} />)}
  </span>;
}

export function ReadingTag({ reading, compact = false }: { reading?: PriceReading | null; compact?: boolean }) {
  if (!reading) return null;
  return <span className={`pd-tag pd-kind-${reading.kind}`} title={[reading.label, reading.detail, reading.low_fit_note].filter(Boolean).join("\n")}>
    {compact && reading.short ? reading.short : reading.label}{reading.confidence === "LOW" ? <small> · rough</small> : null}
  </span>;
}

export function PriceDriversLegend() {
  return <span className="pd-legend">{PARTS.map(([key, label]) => <span key={key}><b className={`pd-seg pd-${key}`} />{label}</span>)}</span>;
}

/** Top of the judgment card: the one-line reading, the bar, the factor split, and live intra-week move bridge. */
export function PriceDriversPanel({ attribution, reading, lastEarnings }: { attribution?: Attribution | null; reading?: PriceReading | null; lastEarnings?: string | null }) {
  if (!reading) return null;
  const w = attribution?.windows?.["3M"];
  const since = attribution?.recent_move?.since_window_end;
  const last5d = attribution?.recent_move?.last_5d;
  const big5d = last5d && last5d.z_5d != null && Math.abs(last5d.z_5d) >= 1.5;
  return <section className={`pd-panel pd-kind-${reading.kind}`} aria-label="What moved the price">
    <header>
      <span>What moved the price · 3 months{attribution?.as_of ? ` to ${attribution.as_of}` : ""}</span>
      <PriceDriversLegend />
    </header>
    <div className="pd-main">
      <strong className={w && w.price_change < 0 ? "neg" : "pos"}>{pct(w?.price_change)}</strong>
      <DriverBar parts={w?.parts} title={factorBreakdown(attribution)} />
      <ReadingTag reading={reading} />
    </div>
    {w ? <div className="pd-parts">{PARTS.map(([key, label]) => <span key={key}><b className={`pd-seg pd-${key}`} />{label} <em>{pct(w.parts[key])}</em>
      {key === "macro" && w.top_macro ? <small> mainly {(attribution?.factor_labels?.[w.top_macro.factor] ?? w.top_macro.factor).toLowerCase()}</small> : null}</span>)}</div> : <p>{reading.detail}</p>}
    {since && Math.abs(since.stock_change) >= 0.005 ? (
      <div className="pd-recent-bridge">
        <span>Since {since.from} (to {since.to}): <b className={since.stock_change < 0 ? "neg" : "pos"}>{pct(since.stock_change)}</b> vs S&amp;P 500 {pct(since.spy_change)}</span>
        <small>Weekly attribution updates after Friday&apos;s close; live price strip below includes this move.</small>
      </div>
    ) : big5d && last5d ? (
      <div className="pd-recent-bridge">
        <span>Last 5 trading days: <b className={last5d.stock_change < 0 ? "neg" : "pos"}>{pct(last5d.stock_change)}</b> ({pct(last5d.vs_spy)} vs S&amp;P 500){lastEarnings ? ` · last reported ${lastEarnings}` : ""}</span>
      </div>
    ) : null}
    {reading.low_fit_note ? <small className="pd-note">{reading.low_fit_note}</small> : null}
  </section>;
}
