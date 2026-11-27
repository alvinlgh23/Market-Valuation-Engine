// The Today exception rule (owner-approved 2026-11-27): which holdings are shown, in which order, at most four.
import assert from "node:assert/strict";
import { focusItems, valueRow, businessColumn, FOCUS_LIMIT } from "../lib/today-model.ts";

const h = (ticker, extra = {}) => ({ ticker, name: null, cardDate: null, agreement: "OUTSIDE", business: "MIXED", short: null, valuation: null, priceChange3m: null, since: null, last5d: null, earnings: null, lastEarnings: null, watch: [], strain: null, aiNote: null, ...extra });
const today = "2026-11-27";

// Nothing qualifies: the calm state.
assert.deepEqual(focusItems([h("A"), h("B")], {}, today, new Set()).items, []);

// Order: changed (company origin, last 7 days) -> disagree (opposed before leaning) -> earnings within 14 days.
const holdings = [
  h("EARN", { earnings: "2026-12-03" }),
  h("LATE", { earnings: "2026-12-20" }),            // 23 days away: not shown
  h("LEAN", { agreement: "LEANS_OPPOSED" }),
  h("OPP", { agreement: "OPPOSED" }),
  h("CHG"),
  h("RULES"),                                        // changed only because the rules changed: not shown
  h("OLD"),                                          // changed 10 days ago: not shown
];
const changes = {
  CHG: [{ axis: "fundamentals", from: "Mixed", to: "Improving", on: "2026-11-25", origin: "COMPANY" }],
  RULES: [{ axis: "valuation", from: "x", to: "y", on: "2026-11-27", origin: "RULES" }],
  OLD: [{ axis: "flow", from: "x", to: "y", on: "2026-11-17", origin: "COMPANY" }],
};
const result = focusItems(holdings, changes, today, new Set());
assert.deepEqual(result.items.map((i) => i.holding.ticker), ["CHG", "OPP", "LEAN", "EARN"]);
assert.deepEqual(result.overflow, []);
assert.equal(result.items[3].earningsIn, 6);

// At most four; the rest are named, not hidden. Core holdings go first within their group.
const many = ["A", "B", "C", "D", "E"].map((t) => h(t, { agreement: "OPPOSED" }));
const capped = focusItems(many, {}, today, new Set(["E"]));
assert.equal(capped.items.length, FOCUS_LIMIT);
assert.equal(capped.items[0].holding.ticker, "E");
assert.deepEqual(capped.overflow, ["D"]);

// Holdings grid placement uses the card's own valuation wording.
assert.equal(valueRow("Price implies less growth than observed/consensus"), "less");
assert.equal(valueRow("Price roughly matches observed/consensus growth"), "inline");
assert.equal(valueRow("Price implies more growth than observed/consensus"), "more");
assert.equal(valueRow("Price implies growth above what the model can reach"), "beyond");
assert.equal(valueRow("Depends on which cash-flow measure"), "none");
assert.equal(valueRow("Price implies higher ROE than the bank earns"), "more");
assert.equal(valueRow(null), "none");
assert.equal(businessColumn("BETTER"), "BETTER");
assert.equal(businessColumn(null), "MIXED");
console.log("Today focus rule: calm state, order, 7/14-day windows, cap of four with overflow, core first, grid placement passed.");
