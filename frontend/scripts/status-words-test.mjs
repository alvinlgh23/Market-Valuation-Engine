import assert from "node:assert/strict";
import fs from "node:fs/promises";
import ts from "typescript";

const source = await fs.readFile(new URL("../lib/status-words.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
const { statusWord, statusTone, displayStatus } = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

// Every availability state the engines emit maps to exactly one of four words.
const expected = {
  Available: ["AVAILABLE", "FULL", "LIVE", "CACHED", "PASSED", "COMPLETED"],
  Partial: ["PARTIAL", "PROVISIONAL", "LIMITED"],
  "Not available": ["UNAVAILABLE", "INSUFFICIENT", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_DATA", "EVIDENCE_INSUFFICIENT", "WITHHELD", "UNKNOWN", "NOT_ANALYZED", "FAILED", "INVALID", "INSUFFICIENT EVIDENCE", ""],
  "Out of date": ["STALE"],
};
for (const [word, states] of Object.entries(expected)) for (const state of states) assert.equal(statusWord(state), word, state);
assert.equal(statusWord("cached"), "Available", "case-insensitive");
assert.equal(new Set(Object.keys(expected).map((word) => word)).size, 4);

// Domain labels are not availability states and keep their meaning.
for (const label of ["WATCH", "TRIGGERED", "FACT", "PROXY", "HIGH", "Narrow Leadership Unwind"]) {
  assert.equal(statusWord(label), null, label);
  assert.equal(statusTone(label), "label", label);
}
assert.equal(displayStatus("WATCH"), "Watch");
assert.equal(displayStatus("US_POLICY"), "US policy");
assert.equal(displayStatus("INSUFFICIENT_EVIDENCE"), "Not available");
assert.equal(statusTone("STALE"), "stale");
console.log("status words: all assertions passed");
