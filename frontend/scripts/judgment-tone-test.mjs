import assert from "node:assert/strict";
import { axisTone, confidenceDots, percentileWidth } from "../lib/judgment-tone.mjs";

assert.equal(axisTone("macro", "Headwind"), "against");
assert.equal(axisTone("flow", "Money flowing in"), "supportive");
assert.equal(axisTone("crowding", "High Chase Risk"), "against");
assert.equal(axisTone("valuation", "Price implies growth above what the model can reach"), "against");
assert.equal(axisTone("valuation", "Fair value withheld"), "unknown");
assert.equal(axisTone("expectations", "Revisions unavailable"), "unknown");
assert.equal(axisTone("unknown-axis", "Tailwind"), "unknown");
assert.equal(confidenceDots("MODERATE"), 2);
assert.equal(confidenceDots("LOW"), 1);
assert.equal(percentileWidth(0.068), 6.800000000000001);
assert.equal(percentileWidth(1.4), 100);
assert.equal(percentileWidth(null), null);
console.log("Judgment tone mapping passed.");
