// Channels -> holdings (2026-11-27): the factor mapping, the 1-point threshold and the card line.
import assert from "node:assert/strict";
import { channelExposure, exposureLine, CHANNEL_FACTORS } from "../lib/channel-exposure.ts";

const d = (ticker, f) => ({ ticker, attribution: { factor_labels: { usd: "US dollar", semis_cycle: "Semiconductor cycle", yen_carry: "Yen carry" }, windows: { "3M": { macro_by_factor: f } } } });
const drivers = [d("AMD", { semis_cycle: -0.176, usd: -0.079, yen_carry: 0.009 }), d("NVDA", { semis_cycle: -0.065, usd: -0.013 }), d("NET", { yen_carry: -0.002 })];

assert.deepEqual(Object.keys(CHANNEL_FACTORS).sort(), ["jp-us-yen-carry", "us-eu-rate-fx", "us-jp-rate-fx", "us-kr-dollar-kospi"]);
const kr = channelExposure("us-kr-dollar-kospi", drivers);
assert.deepEqual(kr.map((f) => f.factor), ["semis_cycle"]);                              // one family per channel
assert.deepEqual(channelExposure("us-eu-rate-fx", drivers).map((f) => f.factor), ["usd"]);
assert.deepEqual(channelExposure("us-jp-rate-fx", drivers).map((f) => f.factor), ["long_rates", "fed_path"]);
assert.deepEqual(kr[0].holdings.map((h) => h.ticker), ["AMD", "NVDA"]);                 // biggest first
const carry = channelExposure("jp-us-yen-carry", drivers);
assert.equal(carry[0].holdings.length, 0);                                               // 0.9 and 0.2 points: under the threshold
assert.match(exposureLine("jp-us-yen-carry", drivers), /none of your holdings/);
assert.match(exposureLine("us-kr-dollar-kospi", drivers), /^Your holdings, 3 months: AMD −17\.6% · NVDA −6\.5%$/);  // each ticker once
assert.equal(exposureLine("us-kr-dollar-kospi", null), "Reading your holdings…");
console.log("Channels: mapping, threshold, ordering and card line passed.");
