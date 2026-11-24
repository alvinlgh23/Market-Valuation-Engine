// Checklist 14.2: proactive alerts for the Today page.
//
// An alert is raised only by a reading the system already makes, with the threshold it already
// uses; nothing here invents a new signal or score. Each alert carries its criteria (the rule,
// what it reads now, the data date) and the scorecard's track record, so the page can say whether
// the condition has ever predicted returns. Most have not, and the alert says so.

export const FACTOR_NAMES = {
  fed_path: "Fed path", long_rates: "US 10Y yield", usd: "US dollar", credit: "Credit", volatility: "Volatility", liquidity: "Liquidity",
  growth: "Growth", inflation: "Inflation", oil: "Oil", semis_cycle: "Chip cycle", yen_carry: "Yen carry"
};

// The rule each factor's state already follows (environment.py), in plain words.
export const FACTOR_RULES = {
  long_rates: "The US 10-year yield's three-month change, ranked against its own three-year history. Above the 67th percentile reads rising, below the 33rd falling.",
  usd: "The dollar index's (DXY) three-month change, ranked against its own three-year history. Above the 67th percentile reads strengthening, below the 33rd weakening.",
  credit: "High-yield bonds (HYG) minus Treasuries (IEF) over three months, ranked against its own three-year history. Below the 33rd percentile reads risk appetite fading.",
  volatility: "The VIX level ranked against its own three-year history. Above the 67th percentile reads elevated, below the 33rd low.",
  growth: "ISM manufacturing PMI. Below 50 and falling over three months reads weakening; above 50 and rising reads improving.",
  inflation: "The US Inflation Pressure Engine's one-to-three-month reading.",
  oil: "WTI crude's three-month change. Above +5% reads rising, below -5% falling.",
  semis_cycle: "Samsung and SK Hynix against KOSPI over three months, ranked within the past year. Below the 33rd percentile reads weakening.",
  fed_path: "Central Bank Compass policy bias (hawkish or dovish) with its three-month move probabilities.",
  liquidity: "Policy liquidity (Central Bank Compass) reads contracting and market liquidity (rates 30%, front-end rates 15%, dollar 25%, curve 10%, credit 20%) is below 40 of 100.",
  yen_carry: "Unwind warning: HIGH when the carry is already unwinding, or two fuel signs plus a trigger; ELEVATED with two fuel signs, or one plus a trigger."
};

export const EXPOSURE_RULE = "The part of each company's three-month price move explained by this factor, from weekly sensitivities fitted on the two years before. Statistical, not causal. Shown at 1 point or more.";
export const CARRY_EXPOSURE_RULE = "Each holding's weekly sensitivity to USD/JPY over two years, times an 8% fall (the August 2024 unwind). A rough size, not a forecast.";
export const MIN_EFFECT = 0.01;
const CARRY_MOVE = -0.08;
const STALE_BUSINESS_DAYS = 2;

const AXIS_NAMES = { macro: "Macro", flow: "Flow", crowding: "Crowding", expectations: "Estimates", fundamentals: "Fundamentals", valuation: "Valuation" };
const AXIS_RULES = {
  expectations: "Estimates rising: next-year EPS estimate up more than 2% over 90 days with more upward than downward revisions in 30 days; falling is the reverse.",
  valuation: "What the price implies (reverse DCF) against consensus growth for the next fiscal year; more than 5 points apart reads higher or lower."
};

const TIER = { macro: 3, carry: 2, liquidity: 1, company: 0 };

function num(value) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function obj(value) { return value && typeof value === "object" ? value : {}; }
export function pct(value, digits = 1) { return `${value >= 0 ? "+" : "−"}${Math.abs(value * 100).toFixed(digits)}%`; }

function percentileText(factor) {
  const value = num(obj(factor.readings).percentile_in_own_history) ?? num(obj(factor.readings).percentile_within_year);
  return value == null ? null : `${Math.round(value * 100)}th percentile`;
}

/** The one figure an alert shows beside its title. */
export function factorFigure(id, factor) {
  const r = obj(factor.readings);
  if (id === "fed_path" && num(r.probability_tightening_3m) != null) return `Hike odds ${Math.round(r.probability_tightening_3m * 100)}%`;
  if (id === "growth" && num(r.ism_pmi) != null) return `PMI ${r.ism_pmi.toFixed(1)}`;
  if (id === "oil" && num(r.change_3m_pct) != null) return `${r.change_3m_pct >= 0 ? "+" : "−"}${Math.abs(r.change_3m_pct).toFixed(1)}% in 3M`;
  return percentileText(factor);
}

function track(factor) {
  const record = obj(factor.track_record);
  return { predictive: record.predictive === true, verdict: record.verdict ?? "NOT_TESTED", text: record.text ?? "Not tested against market returns yet." };
}

/** Each holding's three-month effect from one factor, largest first. */
export function factorEffects(drivers, factor) {
  return (drivers ?? [])
    .map((row) => ({ ticker: row.ticker, value: num(obj(obj(obj(obj(row.attribution).windows)["3M"]).macro_by_factor)[factor]) }))
    .filter((item) => item.value != null && Math.abs(item.value) >= MIN_EFFECT)
    .sort((a, b) => a.value - b.value);
}

function carryHits(drivers) {
  return (drivers ?? [])
    .map((row) => ({ ticker: row.ticker, beta: num(obj(obj(row.attribution).betas).yen_carry) }))
    .filter((item) => item.beta != null)
    .map((item) => ({ ticker: item.ticker, value: item.beta * CARRY_MOVE }))
    .filter((item) => Math.abs(item.value) >= 0.005)
    .sort((a, b) => a.value - b.value);
}

function factorAlert(id, factor, effects, asOf) {
  const hurt = effects.filter((item) => item.value < 0);
  if (!hurt.length) return null;
  const now = [factor.state, factorFigure(id, factor)].filter(Boolean).join(" · ");
  return {
    id: `factor-${id}`, kind: "macro", tone: "against", factor: id,
    title: `${FACTOR_NAMES[id]}: ${factor.state.toLowerCase()}`,
    metric: factorFigure(id, factor) ?? factor.state,
    holdings: hurt.slice(0, 4), more: Math.max(0, hurt.length - 4), holdingsLabel: "3M effect",
    score: Math.abs(hurt[0].value),
    criteria: { rule: FACTOR_RULES[id], now, exposure: EXPOSURE_RULE, asOf: factor.as_of ?? asOf, track: track(factor), notes: factor.notes ?? [] },
    href: "/macro"
  };
}

/**
 * Build the ranked alert list.
 * @param {{ environment?: any, drivers?: any[], summary?: any[] }} input
 */
export function buildAlerts({ environment, drivers, summary } = {}) {
  const factors = obj(environment?.factors);
  const asOf = environment?.as_of ?? null;
  const alerts = [];
  for (const id of Object.keys(FACTOR_NAMES)) {
    const factor = factors[id];
    if (!factor || id === "liquidity" || id === "yen_carry") continue;
    if (factor.direction == null || factor.direction === 0) continue;
    const alert = factorAlert(id, factor, factorEffects(drivers, id), asOf);
    if (alert) alerts.push(alert);
  }
  const carry = factors.yen_carry;
  const warning = obj(obj(carry?.readings).warning);
  if (carry && (warning.level === "ELEVATED" || warning.level === "HIGH")) {
    const hits = carryHits(drivers).filter((item) => item.value < 0);
    const fuel = Array.isArray(warning.fuel) ? warning.fuel : [], trigger = Array.isArray(warning.trigger) ? warning.trigger : [];
    alerts.push({
      id: "yen-carry", kind: "carry", tone: warning.level === "HIGH" ? "against" : "warning", factor: "yen_carry",
      title: `Yen carry unwind warning ${String(warning.level).toLowerCase()}`,
      metric: warning.next_boj_meeting ? `BOJ ${warning.next_boj_meeting} · ${warning.days_to_meeting}d` : `Fuel ${fuel.length}/3 · trigger ${trigger.length}/3`,
      holdings: hits.slice(0, 4), more: Math.max(0, hits.length - 4), holdingsLabel: "if USD/JPY fell 8%",
      score: hits.length ? Math.abs(hits[0].value) : 0.005,
      criteria: { rule: warning.rule ?? FACTOR_RULES.yen_carry, now: `Fuel ${fuel.length}/3, trigger ${trigger.length}/3${fuel.length ? `: ${fuel.join("; ")}` : ""}`,
                  exposure: CARRY_EXPOSURE_RULE, asOf: carry.as_of ?? asOf, track: track(carry), notes: [] },
      href: "/macro"
    });
  }
  const liquidity = factors.liquidity;
  const readings = obj(liquidity?.readings);
  const policy = String(obj(readings.policy_liquidity).label ?? ""), market = String(obj(readings.market_liquidity).label ?? "");
  if (liquidity && readings.relation === "AGREE" && liquidity.direction === -1) {
    alerts.push({
      id: "liquidity", kind: "liquidity", tone: "against", factor: "liquidity",
      title: "Liquidity tight on both measures", metric: `Policy ${policy.toLowerCase()} · market ${market.toLowerCase()}`,
      holdings: [], more: 0, holdingsLabel: null, holdingsNote: "No measured link to your holdings: liquidity has no market proxy to split out of prices.",
      score: 0.004,
      criteria: { rule: FACTOR_RULES.liquidity, now: `Policy: ${policy || "unavailable"}. Market: ${market || "unavailable"}.`, exposure: null,
                  asOf: liquidity.as_of ?? asOf, track: track(liquidity), notes: [] },
      href: "/macro/liquidity"
    });
  }
  for (const row of summary ?? []) {
    for (const change of row.changed ?? []) {
      alerts.push({
        id: `card-${row.ticker}-${change.axis}`, kind: "company", tone: "info", ticker: row.ticker,
        title: `${row.ticker} ${(AXIS_NAMES[change.axis] ?? change.axis).toLowerCase()}: ${String(change.to).toLowerCase()}`,
        metric: `was ${String(change.from).toLowerCase()}`,
        holdings: [], more: 0, holdingsLabel: null, score: 0.003,
        criteria: { rule: AXIS_RULES[change.axis] ?? "The company card's reading for this axis; open the company for its evidence.",
                    now: `${change.from} → ${change.to} on ${change.on}`, exposure: null, asOf: change.on,
                    track: { predictive: false, verdict: "NOT_TESTED", text: "Card readings have not been tested against returns yet." }, notes: [] },
        href: `/company/${row.ticker}`
      });
    }
  }
  // Effects that already happened rank above a scenario, which ranks above an unmeasured condition and card changes.
  return alerts.sort((a, b) => (TIER[b.kind] - TIER[a.kind]) || b.score - a.score);
}

const NOUNS = { fed_path: "the Fed path", long_rates: "the 10-year yield", usd: "the dollar", credit: "credit", volatility: "volatility", liquidity: "liquidity",
  growth: "growth", inflation: "inflation", oil: "oil", semis_cycle: "the chip cycle", yen_carry: "the yen carry trade" };
const COUNT_WORDS = { 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven" };

/** One sentence for the top of the page, built from the alerts, never from a model. */
export function marketRead(alerts, environment) {
  const macro = alerts.filter((item) => item.kind !== "company");
  const regime = obj(environment?.risk_regime).regime;
  const chip = regime ? `Regime: ${String(regime).toLowerCase()}` : null;
  if (!macro.length) {
    return { chip, tone: "mixed", headline: "No macro condition is weighing on your holdings right now.",
             note: alerts.length ? `${alerts.length} company reading${alerts.length === 1 ? "" : "s"} changed since the previous cards.` : "Nothing changed since the previous cards." };
  }
  const names = macro.slice(0, 3).map((item) => NOUNS[item.factor] ?? item.title.toLowerCase());
  const list = names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
  const predictive = macro.filter((item) => item.criteria.track.predictive).length;
  const count = COUNT_WORDS[macro.length] ?? String(macro.length);
  return {
    chip, tone: "against",
    headline: macro.length > 3
      ? `${count} conditions weigh on your holdings, led by ${list}.`
      : `${count} condition${macro.length === 1 ? " weighs" : "s weigh"} on your holdings: ${list}.`,
    note: predictive ? `${predictive} of ${macro.length} has predicted next-month S&P 500 returns in our tests.` : "None of these has predicted next-month S&P 500 returns in our tests: read them as conditions, not forecasts."
  };
}

/** Business days between the data date and today, and whether that is too old to call current. */
export function dataAge(asOf, today) {
  if (!asOf || !today) return { days: null, stale: true };
  const start = new Date(`${String(asOf).slice(0, 10)}T00:00:00Z`), end = new Date(`${String(today).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return { days: null, stale: true };
  let days = 0;
  for (const day = new Date(start); day < end; day.setUTCDate(day.getUTCDate() + 1)) {
    const next = new Date(day); next.setUTCDate(next.getUTCDate() + 1);
    if (next.getUTCDay() !== 0 && next.getUTCDay() !== 6) days += 1;
  }
  return { days, stale: days > STALE_BUSINESS_DAYS };
}
