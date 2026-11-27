// Watchlist Compare (2026-11-27): the price-gap sort value and missing values always last.
import assert from "node:assert/strict";
import { priceGap, sortHoldings, COLUMNS } from "../lib/compare-model.ts";

const base = { implied: null, refLow: null, refHigh: null, priceToMax: null, impliedRoe: null, latestRoe: null, move3m: null, macroPart: null,
  eps90: null, revUp: null, revDown: null, qSales: null, sectorEtf: null, sectorRel: null, dist200: null, psPercentile: null, psState: null, states: {} };
const c = (extra) => ({ ...base, ...extra, states: { ...base.states, ...(extra.states ?? {}) } });

assert.ok(Math.abs(priceGap(c({ implied: 0.36, refLow: 0.40, refHigh: 0.47 })) - (0.36 - 0.435)) < 1e-9);          // NVDA: below what is shown
assert.ok(Math.abs(priceGap(c({ impliedRoe: 0.202, latestRoe: 0.167 })) - 0.035) < 1e-9);                          // JPM
assert.equal(priceGap(c({ priceToMax: 4.9, states: { valuation: "Price implies growth above what the model can reach" } })), 14.9);
assert.equal(priceGap(c({ priceToMax: 1.06, states: { valuation: "Depends on which cash-flow measure" } })), null);   // TSM: no single reading

const h = (ticker, compare) => ({ ticker, compare });
const rows = [h("A", c({ eps90: 0.1 })), h("B", c({})), h("C", c({ eps90: -0.05 })), h("D", c({ eps90: 0.3 }))];
assert.deepEqual(sortHoldings(rows, "eps", -1).map((r) => r.ticker), ["D", "A", "C", "B"]);
assert.deepEqual(sortHoldings(rows, "eps", 1).map((r) => r.ticker), ["C", "A", "D", "B"]);                          // missing stays last
assert.equal(COLUMNS.length, 8);
assert.equal(COLUMNS.find((col) => col.key === "sales").cell(c({}), {}).text, "—");
console.log("Compare: price gap (growth, bank, beyond model, split reading), sort both ways with missing last passed.");
