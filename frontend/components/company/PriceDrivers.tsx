// What moved the share price: macro, broad market, sector, or the company itself (checklists 10.2 and 10.3).
// Data comes from price_attribution.py via the judgment card; nothing is computed here except layout.

export type AttributionWindow = {
  price_change: number; total_log: number;
  parts: { macro: number; market: number; sector: number; company: number };
  macro_by_factor: Record<string, number>; top_macro: { factor: string; value: number } | null; company_z: number | null;
};
export type Attribution = {
  status: string; reason?: string; as_of?: string; fit?: { r2: number | null; start: string; end: string };
  factor_labels?: Record<string, string>; windows?: Record<string, AttributionWindow>;
};
export type PriceReading = {
  kind: "noise" | "watch" | "company" | "fundamentals" | "unknown" | string; label: string; detail: string; confidence: string;
  window: string; price_change?: number; parts?: AttributionWindow["parts"]; company_z?: number | null; low_fit_note?: string | null;
};

const PARTS = [["macro", "Macro"], ["market", "Market"], ["sector", "Sector"], ["company", "Company"]] as const;
const SCALE = 0.5;   // half the bar = a 50% log move

function pct(value: number | null | undefined) { return value == null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`; }

export function factorBreakdown(attribution: Attribution | null | undefined, window = "3M"): string {
  const w = attribution?.windows?.[window];
  if (!w) return attribution?.reason ?? "No attribution";
  const factors = Object.entries(w.macro_by_factor).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([id, value]) => `  ${attribution?.factor_labels?.[id] ?? id}: ${pct(value)}`);
  return [`${window} price ${pct(w.price_change)}`, `Macro ${pct(w.parts.macro)}`, ...factors, `Market ${pct(w.parts.market)}`, `Sector ${pct(w.parts.sector)}`,
    `Company ${pct(w.parts.company)}${w.company_z == null ? "" : ` (${w.company_z >= 0 ? "+" : ""}${w.company_z.toFixed(1)}x normal range)`}`,
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

export function ReadingTag({ reading }: { reading?: PriceReading | null }) {
  if (!reading) return null;
  return <span className={`pd-tag pd-kind-${reading.kind}`} title={[reading.detail, reading.low_fit_note].filter(Boolean).join("\n")}>
    {reading.label}{reading.confidence === "LOW" ? <small> · rough</small> : null}
  </span>;
}

export function PriceDriversLegend() {
  return <span className="pd-legend">{PARTS.map(([key, label]) => <span key={key}><b className={`pd-seg pd-${key}`} />{label}</span>)}</span>;
}

/** Top of the judgment card: the one-line reading, the bar, and the factor split. */
export function PriceDriversPanel({ attribution, reading }: { attribution?: Attribution | null; reading?: PriceReading | null }) {
  if (!reading) return null;
  const w = attribution?.windows?.["3M"];
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
    {reading.low_fit_note ? <small className="pd-note">{reading.low_fit_note}</small> : null}
  </section>;
}
