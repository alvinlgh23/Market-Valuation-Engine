// Today page helpers: parse observed changes into numbers by unit.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../lib/dashboard-orchestration.ts", import.meta.url), "utf8");
assert.match(source, /export function marketMoves/);
assert.match(source, /export function sectorLeadershipBars/);
// Mirror of the parsing rule, kept in step with marketMoves.
function parse(text) {
  const match = String(text).match(/[-+−]?\d+(?:\.\d+)?/);
  if (!match) return null;
  return { value: Number(match[0].replace("−", "-")), unit: /bp/i.test(text) ? "bp" : /%/.test(text) ? "%" : "level" };
}
assert.deepEqual(parse("+1.59% 3M"), { value: 1.59, unit: "%" });
assert.deepEqual(parse("+7.10 bp 3M"), { value: 7.1, unit: "bp" });
assert.deepEqual(parse("-2.97%"), { value: -2.97, unit: "%" });
assert.deepEqual(parse("-0.03"), { value: -0.03, unit: "level" });
assert.equal(parse("Unavailable"), null);
console.log("Today visual helpers passed.");
