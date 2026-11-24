// Checklist 14.2: proactive alerts for the Today page.
//
// An alert is raised only by a reading the system already makes, with the threshold it already
// uses; nothing here invents a new signal or score. Each alert carries its criteria (the rule,
// what it reads now, the data date) and the scorecard's track record, so the page can say whether
// the condition has ever predicted returns. Most have not, and the alert says so.

import { unusualness, versusHistory } from "./plain-words.mjs";

export const FACTOR_NAMES = {
  fed_path: "Fed path", long_rates: "US 10Y yield", usd: "US dollar", credit: "Credit", volatility: "Volatility", liquidity: "Liquidity",
  growth: "Growth", inflation: "Inflation", oil: "Oil", semis_cycle: "Chip cycle", yen_carry: "Yen carry"
};

// The rule each factor's state already follows (environment.py), in plain words.
export const FACTOR_RULES = {
  long_rates: "How far the US 10-year Treasury yield moved over three months, compared with every three-month move in the past three years. A rise bigger than two-thirds of them reads rising; smaller than one-third reads falling.",
  usd: "How far the dollar index (DXY) moved over three months, compared with every three-month move in the past three years. A rise bigger than two-thirds of them reads strengthening; smaller than one-third reads weakening.",
  credit: "How risky company bonds (HYG) did against safe Treasuries (IEF) over three months, compared with the past three years. Worse than two-thirds of that history reads risk appetite fading; better reads improving.",
  volatility: "The VIX, the market's fear gauge, compared with the past three years. Higher than two-thirds of that history reads elevated; lower than one-third reads low.",
  growth: "The ISM manufacturing index, a monthly survey of factories where below 50 means activity is shrinking. Below 50 and falling over three months reads weakening; above 50 and rising reads improving.",
  inflation: "The US Inflation Pressure Engine's reading for the next one to three months.",
  oil: "How much WTI crude oil moved over three months. Up more than 5% reads rising; down more than 5% reads falling.",
  semis_cycle: "Samsung and SK Hynix shares against the Korean market over three months, compared with the past year. Worse than two-thirds of that year reads weakening.",
  fed_path: "The Central Bank Compass reading of the Fed's leaning (toward hikes or cuts) and its odds of a move in the next three months.",
  liquidity: "Policy liquidity (Central Bank Compass) reads contracting, and market liquidity (rates 30%, short-term rates 15%, dollar 25%, yield curve 10%, credit 20%) is below 40 of 100.",
  yen_carry: "Unwind warning: high when the carry trade is already unwinding, or two fuel signs plus a trigger; elevated with two fuel signs, or one plus a trigger."
};

export const EXPOSURE_RULE = "The part of each company's share-price move over the last three months that this factor explains, based on how the stock reacted to it in the two years before. A statistical estimate, not proof of cause. Shown when it is 1 point or more.";
export const CARRY_EXPOSURE_RULE = "How much each holding has moved with the yen over two years, applied to an 8% drop in the dollar against the yen (the size of August 2024). A rough size, not a forecast.";
export const MIN_EFFECT = 0.01;
const CARRY_MOVE = -0.08;
const STALE_BUSINESS_DAYS = 2;

const AXIS_NAMES = { macro: "Macro", flow: "Flow", crowding: "Crowding", expectations: "Estimates", fundamentals: "Fundamentals", valuation: "Valuation" };
const AXIS_RULES = {
  expectations: "Estimates rising: analysts raised next year's earnings-per-share forecast by more than 2% over 90 days, with more raising than cutting in the last 30 days. Falling is the reverse.",
  valuation: "The yearly sales growth the share price assumes, compared with analysts' forecast for the next fiscal year. More than 5 points apart reads higher or lower."
};

const TIER = { macro: 3, carry: 2, liquidity: 1, company: 0 };

function num(value) { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function obj(value) { return value && typeof value === "object" ? value : {}; }
export function pct(value, digits = 1) { return `${value >= 0 ? "+" : "−"}${Math.abs(value * 100).toFixed(digits)}%`; }

function factorPercentile(factor) {
  return num(obj(factor.readings).percentile_in_own_history) ?? num(obj(factor.readings).percentile_within_year);
}

/** Where the reading sits in its own history, as a plain sentence (hover panels). */
export function historySentence(id, factor) {
  const p = factorPercentile(factor);
  return p == null ? null : versusHistory(p, id === "semis_cycle" ? "the past year" : "the past three years");
}

/** The one figure an alert shows beside its title. */
export function factorFigure(id, factor) {
  const r = obj(factor.readings);
  if (id === "fed_path" && num(r.probability_tightening_3m) != null) return `${Math.round(r.probability_tightening_3m * 100)}% chance of a hike`;
  if (id === "growth" && num(r.ism_pmi) != null) return `Factory index ${r.ism_pmi.toFixed(1)}`;
  if (id === "oil" && num(r.change_3m_pct) != null) return `${r.change_3m_pct >= 0 ? "+" : "−"}${Math.abs(r.change_3m_pct).toFixed(1)}% in 3 months`;
  if (id === "yen_carry" && obj(r.warning).level) return `Warning ${String(obj(r.warning).level).toLowerCase()}`;
  return unusualness(factorPercentile(factor));
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

// Factors stay internal (owner 2026-11-24): readers see what is happening, in plain words.
const PLAIN = {
  long_rates: { 1: "Long-term interest rates are rising", "-1": "Long-term interest rates are falling" },
  usd: { 1: "The dollar is getting stronger", "-1": "The dollar is getting weaker" },
  credit: { 1: "Investors are buying risky company bonds", "-1": "Investors are selling risky company bonds" },
  volatility: { 1: "Investors expect big swings", "-1": "Investors expect small swings" },
  growth: { 1: "Factories are picking up", "-1": "Factories are shrinking" },
  inflation: { 1: "Inflation is picking up", "-1": "Inflation is easing" },
  oil: { 1: "Oil prices are rising", "-1": "Oil prices are falling" },
  semis_cycle: { 1: "Chip stocks are leading", "-1": "Chip stocks are lagging" },
  fed_path: { 1: "The Fed is leaning toward higher rates", "-1": "The Fed is leaning toward lower rates" }
};
export function plainTitle(id, factor) {
  return PLAIN[id]?.[String(factor.direction)] ?? `${FACTOR_NAMES[id]}: ${String(factor.state).toLowerCase()}`;
}

function factorAlert(id, factor, effects, asOf) {
  const hurt = effects.filter((item) => item.value < 0);
  if (!hurt.length) return null;
  const now = [`${factor.state}.`, historySentence(id, factor) ?? (factorFigure(id, factor) ? `${factorFigure(id, factor)}.` : null)].filter(Boolean).join(" ");
  return {
    id: `factor-${id}`, kind: "macro", tone: "against", factor: id,
    title: plainTitle(id, factor),
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
      title: `Risk of a sudden yen rebound is ${String(warning.level).toLowerCase()}`,
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
      title: "Money is tight by both measures", metric: `Policy ${policy.toLowerCase()} · market ${market.toLowerCase()}`,
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

const NOUNS = { fed_path: "the Fed", long_rates: "rising long-term rates", usd: "the stronger dollar", credit: "falling risky bonds", volatility: "market fear", liquidity: "tight money",
  growth: "shrinking factories", inflation: "inflation", oil: "oil prices", semis_cycle: "lagging chip stocks", yen_carry: "the yen" };
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
