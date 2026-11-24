// Checklist 14.2: alert rules for the Today page.
import assert from "node:assert/strict";
import { buildAlerts, dataAge, marketRead } from "../lib/alerts.mjs";

const weak = { predictive: false, verdict: "WEAK", text: "Has not reliably predicted next-month S&P 500 returns (r = -0.17, t = -1.0, 35 months)." };
const environment = {
  as_of: "2026-11-04",
  risk_regime: { regime: "Narrow Leadership Unwind" },
  factors: {
    credit: { state: "Risk appetite fading", direction: -1, readings: { percentile_in_own_history: 0.15 }, notes: [], as_of: "2026-11-04", track_record: weak },
    volatility: { state: "Normal", direction: 0, readings: { percentile_in_own_history: 0.59 }, notes: [], track_record: weak },
    usd: { state: "Strengthening", direction: 1, readings: { percentile_in_own_history: 0.78 }, notes: [], track_record: weak },
    oil: { state: "Rising", direction: 1, readings: { change_3m_pct: 21.6 }, notes: [] },
    liquidity: { state: "Policy: Liquidity Contracting · Market: Tight", direction: -1, notes: [], track_record: weak,
                 readings: { relation: "AGREE", policy_liquidity: { label: "Liquidity Contracting" }, market_liquidity: { label: "Tight" } } },
    yen_carry: { state: "Stable", direction: 0, notes: [], readings: { warning: { level: "ELEVATED", fuel: ["gap wide", "funds short yen"], trigger: [], next_boj_meeting: "2026-12-18", days_to_meeting: 24, rule: "HIGH: ... ELEVATED: ..." } } }
  }
};
const drivers = [
  { ticker: "PLTR", attribution: { windows: { "3M": { macro_by_factor: { credit: -0.124, usd: 0.02, volatility: -0.05 } } }, betas: { yen_carry: 0.1 } } },
  { ticker: "AMD", attribution: { windows: { "3M": { macro_by_factor: { credit: -0.004, usd: -0.061 } } }, betas: { yen_carry: 1.6 } } },
  { ticker: "V", attribution: { windows: { "3M": { macro_by_factor: { oil: 0.016 } } } } }
];
const summary = [{ ticker: "MSFT", changed: [{ axis: "expectations", from: "Estimates rising", to: "Estimates stable or mixed", on: "2026-11-24" }] }];

const alerts = buildAlerts({ environment, drivers, summary });
const ids = alerts.map((item) => item.id);
// Credit is outside its middle band and cost PLTR 12.4 points: the top alert.
assert.equal(ids[0], "factor-credit");
assert.deepEqual(alerts[0].holdings, [{ ticker: "PLTR", value: -0.124 }]);
assert.equal(alerts[0].metric, "Unusual");
assert.match(alerts[0].criteria.now, /^Risk appetite fading\. Lower than 85 of every 100 readings in the past three years\.$/);
assert.ok(!JSON.stringify(alerts).match(/\d+(st|nd|rd|th) (pct|percentile)/), "no percentile jargon in alerts");
assert.equal(alerts[0].criteria.track.predictive, false);
// The dollar only lists the holding it hurt; AMD's -0.4 point credit effect is below the 1-point floor.
assert.deepEqual(alerts.find((item) => item.id === "factor-usd").holdings, [{ ticker: "AMD", value: -0.061 }]);
// Volatility is in its middle band, so no alert even though it moved PLTR; oil only helped, so no alert.
assert.ok(!ids.includes("factor-volatility") && !ids.includes("factor-oil"));
// Yen carry: elevated warning, sized by each holding's yen sensitivity times an 8% fall.
const carry = alerts.find((item) => item.id === "yen-carry");
assert.equal(carry.tone, "warning");
assert.equal(carry.holdings[0].ticker, "AMD");
assert.ok(Math.abs(carry.holdings[0].value - -0.128) < 1e-9);
assert.equal(carry.metric, "BOJ 2026-12-18 · 24d");
// Liquidity: both measures tight, with no measured holding link.
const liquidity = alerts.find((item) => item.id === "liquidity");
assert.equal(liquidity.holdings.length, 0);
assert.match(liquidity.holdingsNote, /No measured link/);
// Card changes come after the macro conditions.
assert.equal(ids[ids.length - 1], "card-MSFT-expectations");
assert.equal(alerts[alerts.length - 1].title, "MSFT estimates: estimates stable or mixed");

// Liquidity that disagrees between policy and market raises no alert.
const split = structuredClone(environment);
split.factors.liquidity.readings.relation = "DIFFERENT";
assert.ok(!buildAlerts({ environment: split, drivers, summary: [] }).some((item) => item.id === "liquidity"));

// Market read: built from the alerts, and honest that none of them forecasts.
const read = marketRead(alerts, environment);
assert.equal(read.chip, "Regime: narrow leadership unwind");
assert.equal(read.headline, "Four conditions weigh on your holdings, led by credit, the dollar and the yen carry trade.");
assert.equal(marketRead(alerts.slice(0, 2), environment).headline, "Two conditions weigh on your holdings: credit and the dollar.");
// Factors without a percentile show their own figure, not the state again.
const growth = buildAlerts({ environment: { factors: { growth: { state: "Weakening", direction: -1, readings: { ism_pmi: 47.9 }, notes: [] } } },
  drivers: [{ ticker: "CAT", attribution: { windows: { "3M": { macro_by_factor: { growth: -0.025 } } } } }] });
assert.equal(growth[0].metric, "Factory index 47.9");
assert.match(read.note, /^None of these has predicted/);
const calm = marketRead(buildAlerts({ environment: { factors: {} }, drivers: [], summary }), {});
assert.equal(calm.headline, "No macro condition is weighing on your holdings right now.");
assert.equal(calm.chip, null);

// Data age in business days: 4 Nov to 24 Nov 2026 is 14 business days; Friday to Monday is one.
assert.deepEqual(dataAge("2026-11-04", "2026-11-24"), { days: 14, stale: true });
assert.deepEqual(dataAge("2026-11-20", "2026-11-23"), { days: 1, stale: false });
assert.deepEqual(dataAge(null, "2026-11-24"), { days: null, stale: true });
console.log("Alert rules passed.");

// Plain words for a reading's place in its own history.
const { unusualness, versusHistory, historyLabel } = await import("../lib/plain-words.mjs");
assert.equal(unusualness(0.5), "Typical");
assert.equal(unusualness(0.69), "Slightly unusual");
assert.equal(unusualness(0.15), "Unusual");
assert.equal(unusualness(0.97), "Extreme");
assert.equal(unusualness(null), null);
assert.equal(versusHistory(0.69), "Higher than 69 of every 100 readings in the past three years.");
assert.equal(versusHistory(0.15, "the past year"), "Lower than 85 of every 100 readings in the past year.");
assert.equal(historyLabel(0.9, "price"), "Expensive for its history");
assert.equal(historyLabel(0.25, "strength"), "Weaker than usual");
assert.equal(historyLabel(0.5), "About usual");
console.log("Plain-word rules passed.");
