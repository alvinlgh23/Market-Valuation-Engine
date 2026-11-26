// AI model plan, phase B: the page's what-if formula must keep matching the shared cases the Python port is tested on.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { computeInteractiveFairValue } from "../lib/what-if.mjs";

const cases = JSON.parse(readFileSync(new URL("../../tests/fixtures/what_if_cases.json", import.meta.url), "utf8"));
assert.ok(cases.length >= 7);
for (const { input, expected } of cases) {
  const got = computeInteractiveFairValue(input);
  if (expected === null) assert.equal(got, null);
  else assert.ok(Math.abs(got - expected) < 1e-9 * Math.max(1, Math.abs(expected)), `what-if drifted: ${got} vs ${expected}`);
}
console.log(`what-if parity: ${cases.length} cases match`);
