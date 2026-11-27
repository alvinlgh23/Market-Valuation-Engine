// The Market view's 1-month vs 3-month sentence on the shapes found in the 13 watchlist cards (2026-11-27).
import assert from "node:assert/strict";
import { concentration } from "../lib/market-words.ts";

assert.match(concentration(-0.405, -0.415), /almost all of the move came in the last month/);          // NVDA
assert.match(concentration(-0.238, -0.237), /almost all/);                                              // TSM: 0.1 point apart
assert.match(concentration(-0.273, -0.135), /more than the −13\.5%.*gave back gains/);                  // CRM
assert.match(concentration(0.12, 0.05), /more than.*made up losses/);
assert.match(concentration(-0.127, 0.021), /went the other way/);                                       // META
assert.match(concentration(-0.074, 0.005), /went the other way/);                                       // MSFT: 3M under 1 point
assert.match(concentration(-0.063, -0.112), /spread across/);                                           // JPM
assert.match(concentration(0.059, 0.074), /most of the move came in the last month/);                  // LLY
assert.match(concentration(-0.01, -0.2), /little of it came in the last month/);
assert.equal(concentration(0.002, -0.004), null);                                                       // both flat: no sentence
assert.equal(concentration(null, -0.2), null);
console.log("Market view sentences: same direction, near-equal, larger last month, opposite, flat and missing cases passed.");
