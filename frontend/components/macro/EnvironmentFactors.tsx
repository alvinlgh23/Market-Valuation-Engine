import type { EnvironmentFactor, EnvironmentLayer } from "../../lib/research-system-types";
import { FactorImpact } from "./FactorImpact";

const ORDER: Array<[string, string]> = [["fed_path", "Fed path"], ["long_rates", "US 10Y yield"], ["usd", "US dollar"], ["credit", "Credit"], ["volatility", "Volatility"], ["liquidity", "Liquidity"],
  ["growth", "Growth"], ["inflation", "Inflation"], ["oil", "Oil"], ["semis_cycle", "Chip cycle"], ["yen_carry", "Yen carry"]];

function num(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function obj(value: unknown) { return (value && typeof value === "object" ? value : {}) as Record<string, unknown>; }

/** Neutral 0-100 track: macro factors have no good or bad end, so there is no colour scale. */
function Track({ label, value, right }: { label: string; value: number | null; right?: string }) {
  if (value == null) return null;
  const position = Math.max(0, Math.min(100, value * 100));
  return <div className="env-track"><span>{label}</span><div><i style={{ left: `${position}%` }} /></div><b>{right ?? `${Math.round(position)}th pct`}</b></div>;
}

function FactorVisual({ id, factor }: { id: string; factor: EnvironmentFactor }) {
  const r = factor.readings;
  if (num(r.percentile_in_own_history) != null) return <Track label="vs own history" value={num(r.percentile_in_own_history)} />;
  if (id === "semis_cycle") return <Track label="within year" value={num(r.percentile_within_year)} />;
  if (id === "liquidity") {
    const policy = obj(r.policy_liquidity), market = obj(r.market_liquidity);
    // Checklist 10.5: the 0-100 scores failed the scorecard (not significant), so only their states are shown.
    return <div className="env-states">{[["Policy", policy], ["Market", market]].map(([label, item]) => { const state = (item as Record<string, unknown>).label; return state ? <span key={String(label)}><small>{String(label)}</small>{String(state)}</span> : null; })}<small className="env-untested">Scores not validated against returns</small></div>;
  }
  if (id === "fed_path") {
    const tighten = num(r.probability_tightening_3m), ease = num(r.probability_easing_3m);
    if (tighten == null || ease == null) return null;
    const hold = Math.max(0, 1 - tighten - ease);
    return <div className="env-split" title={`Next 3 months: tighten ${Math.round(tighten * 100)}%, hold ${Math.round(hold * 100)}%, ease ${Math.round(ease * 100)}% (${String(r.probability_model ?? "model")})`}>
      <div><i className="ease" style={{ flexGrow: ease }} /><i className="hold" style={{ flexGrow: hold }} /><i className="tighten" style={{ flexGrow: tighten }} /></div>
      <small><span>Ease {Math.round(ease * 100)}%</span><span>Tighten {Math.round(tighten * 100)}%</span></small>
    </div>;
  }
  if (id === "growth" && num(r.ism_pmi) != null) {
    const pmi = num(r.ism_pmi) as number;
    return <Track label="ISM PMI (50 = flat)" value={(pmi - 40) / 20} right={pmi.toFixed(1)} />;
  }
  if (id === "oil" && num(r.change_3m_pct) != null) return <div className="env-figure"><b>{(num(r.change_3m_pct) as number) >= 0 ? "+" : ""}{(num(r.change_3m_pct) as number).toFixed(1)}%</b><span>3 months · WTI {String(r.wti ?? "—")}</span></div>;
  if (id === "yen_carry") {
    // Checklist 10.6: early warning = fuel (why the trade is crowded) + trigger (what could close it).
    const w = obj(r.warning);
    const fuel = Array.isArray(w.fuel) ? (w.fuel as string[]) : [], trigger = Array.isArray(w.trigger) ? (w.trigger as string[]) : [];
    const missing = Array.isArray(w.missing) ? (w.missing as string[]) : [];
    const level = String(w.level ?? "UNKNOWN");
    return <div className="env-carry">
      <div className={`env-carry-level level-${level.toLowerCase()}`} title={String(w.rule ?? "")}>Unwind warning: <b>{level.toLowerCase()}</b>{missing.length ? <small> · incomplete</small> : null}</div>
      <div className="env-carry-signs">
        <span title={fuel.join("\n") || "No fuel signs"}>Fuel {fuel.length}/3</span>
        <span title={trigger.join("\n") || "No trigger signs"}>Trigger {trigger.length}/3</span>
        <span>{w.next_boj_meeting ? `BOJ ${String(w.next_boj_meeting)} (${String(w.days_to_meeting)}d)` : "BOJ date unavailable"}</span>
      </div>
      {num(r.usdjpy_level) != null ? <small>USD/JPY {(num(r.usdjpy_level) as number).toFixed(1)} · US–JP 10Y gap {num(w.us_jp_gap_pp)?.toFixed(2) ?? "—"} pp{num(w.gap_change_3m_pp) != null ? ` (${(num(w.gap_change_3m_pp) as number) >= 0 ? "+" : ""}${(num(w.gap_change_3m_pp) as number).toFixed(2)} in 3M)` : ""}</small> : null}
      {missing.length ? <small className="env-untested">Missing: {missing.join(", ")}</small> : null}
    </div>;
  }
  return null;
}

/** Checklist 9.7: every environment factor as a tile with its state, direction and one small chart. */
export function EnvironmentFactors({ environment }: { environment?: EnvironmentLayer }) {
  if (!environment?.factors) return null;
  const tiles = ORDER.filter(([id]) => environment.factors[id]);
  if (!tiles.length) return null;
  return <section className="env-factors" aria-label="Macro factors">
    <header><span>Factors</span><small>as of {environment.as_of ?? "—"} · arrows show direction, not good or bad</small></header>
    <div>{tiles.map(([id, label]) => {
      const factor = environment.factors[id];
      const glyph = factor.direction === 1 ? "▲" : factor.direction === -1 ? "▼" : "◆";
      return <article key={id} title={[factor.source, ...factor.notes].join(" · ")}>
        <span>{label}</span>
        <strong><em aria-hidden>{glyph}</em>{factor.state}</strong>
        <FactorVisual id={id} factor={factor} />
        <FactorImpact factor={id} />
      </article>;
    })}</div>
    {environment.contradictions?.length ? <footer>{environment.contradictions.map((item) => <span key={item.text}>! {item.text}</span>)}</footer> : null}
  </section>;
}
