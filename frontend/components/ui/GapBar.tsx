// The gap bar: CHAINSTOX's signature graphic (design system v2, 2026-11-27). Always two real numbers from the card -
// what the price assumes (orange dot) and what the business shows (green band) - never a combined score.
// Growth: five-year sales growth the price requires vs analysts' and past growth once faded.
// Banks: return on equity the price assumes vs what the bank earns. Above the model's reach: named, not drawn.

export type GapInput = {
  implied: number | null; refLow: number | null; refHigh: number | null;
  impliedRoe?: number | null; latestRoe?: number | null;
  priceToMax?: number | null; valuationState?: string | null;
};

function pct(v: number, digits = 0, signed = true) {
  const r = Number((v * 100).toFixed(digits));
  return r === 0 ? "0%" : `${r < 0 ? "−" : signed ? "+" : ""}${Math.abs(r).toFixed(digits)}%`;
}

export function gapMode(g: GapInput): "growth" | "roe" | "beyond" | "none" {
  if (g.implied != null && g.refLow != null && g.refHigh != null) return "growth";
  if (g.impliedRoe != null && g.latestRoe != null) return "roe";
  if (g.priceToMax != null && /model can reach/i.test(g.valuationState ?? "")) return "beyond";
  return "none";
}

export function GapBar({ gap, compact = false, label = true }: { gap: GapInput; compact?: boolean; label?: boolean }) {
  const mode = gapMode(gap);
  if (mode === "beyond") return <div className={`gapbar gapbar-beyond${compact ? " compact" : ""}`}>
    <div className="gapbar-track"><span className="gapbar-off">{gap.priceToMax!.toFixed(1)}× the model&apos;s best case →</span></div>
    {label ? <p className="gapbar-label"><b className="gp">Price</b> above anything the cash-flow model reaches</p> : null}
  </div>;
  if (mode === "none") return <div className={`gapbar gapbar-none${compact ? " compact" : ""}`}>
    <div className="gapbar-track"><span className="gapbar-off muted">{/cash-flow/i.test(gap.valuationState ?? "") ? "No single reading: depends on the cash-flow measure" : "No valuation reading"}</span></div>
  </div>;

  const price = mode === "growth" ? gap.implied! : gap.impliedRoe!;
  const lo = mode === "growth" ? gap.refLow! : gap.latestRoe!;
  const hi = mode === "growth" ? gap.refHigh! : gap.latestRoe!;
  const min = Math.min(0, price, lo);
  const max = Math.max(mode === "growth" ? 0.5 : 0.3, Math.ceil((Math.max(price, hi) + 0.05) * 10) / 10);
  const x = (v: number) => ((v - min) / (max - min)) * 100;
  const edge = price > hi ? hi : price < lo ? lo : price;
  const left = Math.min(x(price), x(edge)), width = Math.abs(x(price) - x(edge));
  const tone = price > hi ? "over" : price < lo ? "under" : "inline";
  const unit = mode === "growth" ? "/yr" : "";
  const roe = mode === "roe";
  const shows = Math.abs(hi - lo) >= 0.005 ? `${pct(lo)} to ${pct(hi)}` : pct(lo, roe ? 1 : 0, !roe);
  return <div className={`gapbar tone-${tone}${compact ? " compact" : ""}`} role="img"
    aria-label={`${mode === "growth" ? "Sales growth" : "Return on equity"} the price assumes ${pct(price, 1)}${unit}; the business shows ${shows}${unit}`}>
    <div className="gapbar-track">
      {min < 0 ? <i className="gapbar-zero" style={{ left: `${x(0)}%` }} /> : null}
      <i className="gapbar-band" style={{ left: `${x(lo)}%`, width: `${Math.max(1.2, x(hi) - x(lo))}%` }} />
      {width > 0.3 ? <i className="gapbar-line" style={{ left: `${left}%`, width: `${width}%` }} /> : null}
      <i className="gapbar-dot" style={{ left: `${x(price)}%` }} />
    </div>
    {label ? <p className="gapbar-label">
      <span><b className="gp">{mode === "growth" ? "Price assumes" : "Price assumes ROE"}</b> {pct(price, roe ? 1 : 0, !roe)}{unit}</span>
      <span><b className="gb">{mode === "growth" ? "Business shows" : "Bank earns"}</b> {shows}{unit}</span>
    </p> : null}
  </div>;
}
