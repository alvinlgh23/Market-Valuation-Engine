"use client";

import Link from "next/link";
import { useProView } from "../../lib/view-mode";
import type { LiquidityScore, ResearchSystem } from "../../lib/research-system-types";
import type { MacroEvidence, ScoreTest } from "../../lib/macro-evidence-server";
import { YieldCurveChart } from "../charts/AnalyticalCharts";
import { CoverageFallback, driverDatum } from "./MacroOverviewSurface";
import { HoldingsFactorBars } from "./HoldingsFactorBars";

// Market conditions (2026-11-27): Risk regime, Rates, Liquidity and Dollar & Yen on one page. Plain language by
// default for everyday investors; "Pro view" shows the technical names and detail. Readings come from the existing
// engines; the plain words are display labels for the same readings, nothing is recalculated.

type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === "object" && !Array.isArray(v) ? (v as Json) : {});
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const lower = (v: unknown) => String(v ?? "").replace(/_/g, " ").toLowerCase();
const pct = (v: number, d = 1) => `${v < 0 ? "−" : "+"}${Math.abs(v * 100).toFixed(d)}%`;

/** Plain names for the regime and the cross-asset rows (display labels of the risk engine's own readings). */
const REGIME_PLAIN: Record<string, string> = {
  "Narrow Leadership Unwind": "The few big winners are falling; the rest of the market is holding up",
  "Healthy Rotation": "Money is moving between sectors, without broad stress",
  "Broad Risk-Off": "Investors are selling almost everything risky",
  "Liquidity / Inflation Stress": "Tight money and inflation are weighing on markets",
  "No Dominant Stress": "No clear stress across markets",
};
const ROW_PLAIN: Record<string, string> = {
  "Cap-weight market": "Big stocks (S&P 500)", "Equal-weight breadth": "The average stock", "Momentum leadership": "Recent winners",
  "Semiconductor leadership": "Chip stocks", "Defensive sectors": "Safe sectors", "Global equities": "Stocks worldwide",
  "Switzerland defensive proxy": "Swiss stocks", "Credit conditions": "Company bonds", "Volatility": "Fear gauge (VIX)",
  "Treasury hedge behavior": "US government bonds", "Gold behavior": "Gold", "USD stress": "US dollar",
};
/** Rows where "up" is bad for stocks (fear, a dollar squeeze) are coloured the other way; hedges stay neutral. */
const ROW_TONE: Record<string, "inverse" | "neutral"> = { "Volatility": "inverse", "USD stress": "inverse", "Treasury hedge behavior": "neutral", "Gold behavior": "neutral" };
function rowClass(label: string, value: number) {
  const tone = ROW_TONE[label];
  if (tone === "neutral") return "flat";
  const good = tone === "inverse" ? value < 0 : value >= 0;
  return good ? "up" : "down";
}
const FACTOR_PLAIN: Record<string, string> = { long_rates: "Long-term interest rates", fed_path: "Expected Fed rate moves", usd: "The US dollar", yen_carry: "Yen borrowing trade" };

function Tested({ test, what }: { test: ScoreTest; what: string }) {
  if (!test.verdict) return null;
  const weak = test.verdict !== "PREDICTIVE";
  return <p className={`mc-tested${weak ? " weak" : ""}`}><b>{weak ? "Checked" : "Tested"}</b>
    {weak ? `In our data, ${what} didn't tell us where the S&P 500 went next month. Read it as how things are now, not a forecast.` : `In our data, ${what} came before moves in the S&P 500.`}</p>;
}

/** "SPY 20D -6.84%; vs market +4.89%" -> -0.0684 (the first 20-day move in the engine's evidence text). */
function twentyDay(text: string): number | null {
  const m = text.match(/20D\s*([+-−]?\d+(?:\.\d+)?)%/);
  return m ? Number(m[1].replace("−", "-")) / 100 : null;
}

export function MarketConditions({ system, evidence }: { system: ResearchSystem; evidence: MacroEvidence }) {
  const [pro, setPro] = useProView();
  const core = obj(system.modules.core_market.payload);
  const risk = obj(core.risk);
  const regime = String(risk.published_regime ?? risk.regime ?? "No regime published");
  const rows = (Array.isArray(risk.evidence) ? risk.evidence : []).map((r) => (Array.isArray(r) ? r.map(String) : [])).filter((r) => r.length >= 3);
  const bars = rows.map(([label, state, text]) => ({ label, state, text, value: twentyDay(text) })).filter((r) => r.value != null);
  const maxBar = Math.max(0.05, ...bars.map((b) => Math.abs(b.value!)));
  const samples = evidence.regimeSamples[regime];

  const t = system.market_transmission;
  const curve = t.rates.current_curve.flatMap((m) => { const tenor = m.key === "us_2y" ? 2 : m.key === "us_10y" ? 10 : m.key === "us_30y" ? 30 : null; return tenor === null ? [] : [{ label: m.label.replace("US ", ""), tenorYears: tenor, value: m.raw_value }]; });
  const ten = t.rates.metrics.find((m) => m.key === "us_10y"), two = t.rates.metrics.find((m) => m.key === "us_2y");
  const spread = t.rates.metrics.find((m) => m.key.startsWith("us_10y_") && m.unit === "pp");
  const real = t.rates.metrics.find((m) => m.key === "us_10y_real");
  const tenMove = t.rates.moves.find((m) => m.key === "us_10y_3m");

  const liq = obj(obj(system.environment?.factors?.liquidity).readings);
  const policy = obj(liq.policy_liquidity), market = obj(liq.market_liquidity) as LiquidityScore & Json;
  const disagree = liq.relation === "DIFFERENT" || liq.relation === "OPPOSITE";
  const drivers = t.liquidity.drivers.flatMap((d) => { const datum = driverDatum(d); return datum ? [datum] : []; });

  const fxMetrics = (t.fx as { metrics?: typeof t.fx.moves }).metrics ?? [];
  // Plain view: every bar is the dollar's move against that currency (EUR/USD inverted), so up = stronger dollar.
  const VS: Record<string, string> = { DXY: "Major currencies (index)", "USD/JPY": "Japanese yen", "EUR/USD": "Euro", "USD/KRW": "Korean won", "USD/CNY": "Chinese yuan" };
  const fxBars = fxMetrics.filter((m) => m.unit === "% 3M" && m.raw_value != null).map((m) => ({
    key: m.key, label: pro ? m.label : VS[m.label] ?? m.label,
    value: (pro || !m.label.startsWith("EUR/") ? m.raw_value! : -m.raw_value!) / 100,
  }));
  const fxMax = Math.max(0.03, ...fxBars.map((b) => Math.abs(b.value)));
  const fxLevels = fxMetrics.filter((m) => m.unit === "index" || m.unit === "FX rate");
  const fxDate = fxMetrics.find((m) => m.date)?.date ?? null;
  const dxy3m = fxMetrics.find((m) => m.key === "dxy_3m");
  const carry = obj(system.environment?.factors?.yen_carry);
  const carryR = obj(carry.readings), warning = obj(carryR.warning);

  return <div className={`mc${pro ? " mc-pro" : ""}`}>
    <header className="mc-top">
      <div>
        <h1>Market conditions</h1>
        <p>{pro ? "Risk regime, rates, liquidity and FX: the readings, what markets price, which holdings each moved, and our own test results." : "How markets feel right now, and which of your holdings that touched. Plain words first; switch to Pro view for the technical detail."}</p>
      </div>
      <div className="mc-mode" role="group" aria-label="View">
        <button type="button" aria-pressed={!pro} className={!pro ? "on" : ""} onClick={() => setPro(false)}>Plain</button>
        <button type="button" aria-pressed={pro} className={pro ? "on" : ""} onClick={() => setPro(true)}>Pro view</button>
      </div>
    </header>

    <section id="regime" className="mc-hero glow-card" aria-label="Risk regime">
      <span className="mc-kicker">{pro ? `Risk regime · ${lower(risk.confidence)} confidence · last 20 trading days` : "The market mood · last 20 trading days"}</span>
      <h2 className="display-h">{pro ? regime : REGIME_PLAIN[regime] ?? regime}</h2>
      {pro && typeof risk.summary === "string" ? <p className="mc-lede">{risk.summary}</p> : null}
      {bars.length ? <div className="mc-xbars">{bars.map((b) => <div key={b.label} className={rowClass(b.label, b.value!)} title={b.text}>
        <span>{pro ? b.label : ROW_PLAIN[b.label] ?? b.label}</span><small>{lower(b.state)}</small>
        <div className="mc-xtrack"><i style={{ width: `${(Math.abs(b.value!) / maxBar) * 50}%`, [b.value! < 0 ? "right" : "left"]: "50%" } as React.CSSProperties} /></div>
        <em>{pct(b.value!)}</em>
      </div>)}</div> : null}
      <p className="mc-tested weak"><b>Checked</b>{samples != null && samples < 10
        ? `This mood has only shown up ${samples} separate time${samples === 1 ? "" : "s"} in our record, too few to say what usually follows. It describes now; it isn't a forecast.`
        : "Market moods in our record haven't reliably told us where the S&P 500 went next. It describes now; it isn't a forecast."}</p>
    </section>

    <div className="mc-grid">
      <section id="rates" className="mc-card" aria-label="Interest rates">
        <header><h3>{pro ? "Rates" : "Interest rates"}</h3>{pro && spread?.raw_value != null ? <span className="mc-pill">10Y–2Y {spread.raw_value >= 0 ? "+" : "−"}{Math.round(Math.abs(spread.raw_value) * 100)} bps</span> : null}</header>
        <div className="mc-big">
          <div><small>{pro ? "US 10Y" : "10-year US government rate"}</small><b>{ten?.formatted_value ?? "—"}</b>{tenMove?.raw_value != null ? <em>{pro ? `${tenMove.raw_value >= 0 ? "+" : "−"}${Math.abs(tenMove.raw_value).toFixed(0)} bps in 3M` : `${tenMove.raw_value >= 0 ? "up" : "down"} ${Math.abs(tenMove.raw_value / 100).toFixed(2)} points in 3 months`}</em> : null}</div>
          <div><small>{pro ? "US 2Y" : "2-year rate"}</small><b>{two?.formatted_value ?? "—"}</b></div>
        </div>
        {!pro ? <p className="mc-plain">Higher long-term rates make future profits worth less today, which tends to weigh most on fast-growing companies.</p> : null}
        {pro ? <>
          {curve.length >= 2 ? <YieldCurveChart points={curve} asOf={t.rates.current_curve[0]?.date ?? t.rates.last_valid_as_of} source={t.rates.current_curve[0]?.source} /> : null}
          <div className="mc-stats">
            {t.rates.moves.map((m) => <div key={m.key}><small>{m.label}, 3M</small><b>{m.raw_value != null ? `${m.raw_value >= 0 ? "+" : "−"}${Math.abs(m.raw_value).toFixed(0)} bps` : "—"}</b></div>)}
            {real ? <div><small>10Y real yield</small><b>{real.formatted_value}</b></div> : null}
          </div>
        </> : null}
        <span className="ch-sub">Your holdings moved by rates · 3 months</span>
        <HoldingsFactorBars factors={["long_rates", "fed_path"]} labels={pro ? undefined : FACTOR_PLAIN} />
        <Tested test={evidence.rates} what={pro ? "the rates score" : "interest rates"} />
        <Link className="mc-link" href="/macro/world#central-banks">What markets expect from the Fed →</Link>
      </section>

      <section id="liquidity" className="mc-card" aria-label="Money conditions">
        <header><h3>{pro ? "Liquidity" : "Money conditions"}</h3>{disagree ? <span className="mc-pill warn">{pro ? "Policy and market disagree" : "Mixed signals"}</span> : null}</header>
        <div className="mc-big">
          <div><small>{pro ? "Policy liquidity (Compass)" : "What the central bank is doing"}</small><b>{String(policy.label ?? t.liquidity.state ?? "—")}</b>{pro && num(policy.score) != null ? <em>{Math.round(num(policy.score)!)} / 100 · {String(policy.drivers_available ?? t.liquidity.available_drivers)} of {String(policy.drivers_expected ?? t.liquidity.expected_drivers)} inputs</em> : null}</div>
          <div><small>{pro ? "Market liquidity (price-based)" : "What markets are feeling"}</small><b>{String(market.label ?? "—")}</b>{pro && num(market.score) != null ? <em>{Math.round(num(market.score)!)} / 100</em> : null}</div>
        </div>
        {!pro ? <p className="mc-plain">{disagree ? "The central bank isn't squeezing money supply, but markets feel tight anyway, mainly from high rates and nervous investors." : "Central-bank policy and market conditions point the same way."}</p> : null}
        {pro && drivers.length ? <><span className="ch-sub">Driver contributions to the policy score (points)</span><div className="mc-fxbars">{drivers.map((d) => {
          const max = Math.max(5, ...drivers.map((x) => Math.abs(x.value ?? 0)));
          const v = d.value ?? 0;
          return <div key={d.id} className={v < 0 ? "down" : "up"} title={d.context}>
            <span>{d.label}</span>
            <div className="mc-xtrack"><i style={{ width: `${(Math.abs(v) / max) * 50}%`, [v < 0 ? "right" : "left"]: "50%" } as React.CSSProperties} /></div>
            <em>{v === 0 ? "0" : `${v > 0 ? "+" : "−"}${Math.abs(v).toFixed(0)}`}</em>
          </div>;
        })}</div></> : null}
        <Tested test={evidence.liquidity} what={pro ? "the liquidity score" : "money conditions"} />
      </section>

      <section id="fx" className="mc-card mc-wide" aria-label="Dollar and yen">
        <header><h3>{pro ? "Dollar & yen" : "The dollar and the yen"}</h3>{typeof carry.state === "string" ? <span className={`mc-pill${warning.level === "HIGH" ? " warn" : ""}`}>{pro ? `Yen carry: ${lower(carry.state)}` : `Yen borrowing trade: ${lower(carry.state)}`}</span> : null}</header>
        <div className="mc-fx">
          <div>
            {dxy3m?.raw_value != null && !pro ? <div className="mc-big"><div><small>US dollar against major currencies, 3 months</small><b>{`${dxy3m.raw_value >= 0 ? "+" : "−"}${Math.abs(dxy3m.raw_value).toFixed(1)}%`}</b><em>{dxy3m.raw_value >= 0 ? "a stronger dollar" : "a weaker dollar"}</em></div></div> : null}
            <span className="ch-sub">{pro ? `3M change${fxDate ? ` to ${fxDate}` : ""}` : `The dollar against each currency, 3 months${fxDate ? ` to ${fxDate}` : ""}`}</span>
            {fxBars.length ? <div className="mc-fxbars">{fxBars.map((b) => <div key={b.key} className={b.value < 0 ? "down" : "up"}>
              <span>{b.label}</span>
              <div className="mc-xtrack"><i style={{ width: `${(Math.abs(b.value) / fxMax) * 50}%`, [b.value < 0 ? "right" : "left"]: "50%" } as React.CSSProperties} /></div>
              <em>{pct(b.value)}</em>
            </div>)}</div> : <p className="ch-quiet">No fresh currency moves.</p>}
            {pro && fxLevels.length ? <div className="mc-levels">{fxLevels.map((m) => <span key={m.key}><small>{m.label}</small><b>{m.formatted_value}</b></span>)}</div> : null}
            {!pro ? <p className="mc-plain">A stronger dollar shrinks what US companies earn abroad once it&apos;s converted back into dollars.</p> : null}
          </div>
          <div>
            {!pro ? <p className="mc-plain">Some investors borrow cheap yen to buy US stocks. When that trade unwinds, they sell, which can hit popular stocks.</p> : <dl className="mc-carry">
              {num(carryR.usdjpy_level) != null ? <div><dt>USD/JPY</dt><dd>{num(carryR.usdjpy_level)!.toFixed(2)}</dd></div> : null}
              {num(carryR.us_jp_10y_spread_pp) != null ? <div><dt>US–JP 10Y spread</dt><dd>{num(carryR.us_jp_10y_spread_pp)!.toFixed(2)} pp</dd></div> : null}
              {num(carryR.boj_normalization_probability) != null ? <div><dt>BOJ normalisation probability</dt><dd>{Math.round(num(carryR.boj_normalization_probability)! * 100)}%</dd></div> : null}
              {num(carryR.vix_level) != null ? <div><dt>VIX</dt><dd>{num(carryR.vix_level)!.toFixed(1)}</dd></div> : null}
              {num(carryR.cftc_leveraged_net_jpy_contracts) != null ? <div><dt>CFTC leveraged net JPY</dt><dd>{num(carryR.cftc_leveraged_net_jpy_contracts)!.toLocaleString("en-US")}</dd></div> : null}
            </dl>}
            <span className="ch-sub">Your holdings moved by the dollar and the yen trade · 3 months</span>
            <HoldingsFactorBars factors={["usd", "yen_carry"]} labels={pro ? undefined : FACTOR_PLAIN} carryScenario={warning.level === "HIGH"} />
          </div>
        </div>
      </section>
    </div>

    {pro ? <details className="mc-coverage"><summary>Data coverage and sources</summary>
      <CoverageFallback title="Rates" coverage={t.rates} reason="Treasury yields: Yahoo Finance closes; real yield: FRED via Central Bank Compass." />
      <CoverageFallback title="Liquidity" coverage={t.liquidity} reason="Policy liquidity: Central Bank Compass drivers; market liquidity: price-based score." />
      <CoverageFallback title="Dollar / FX" coverage={t.fx} reason="Daily closes from Yahoo Finance; regional year-on-year changes from Central Bank Compass." />
      {typeof risk.publication_rule === "string" ? <p className="mc-rule">Risk regime: {risk.publication_rule}</p> : null}
    </details> : null}
  </div>;
}
