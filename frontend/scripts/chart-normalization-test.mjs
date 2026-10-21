import assert from "node:assert/strict";
import fs from "node:fs/promises";
import ts from "typescript";

const source = await fs.readFile(new URL("../lib/chart-normalization-core.ts", import.meta.url), "utf8");
const stripped = source.replace(/^import type .*;$/gm, "");
const output = ts.transpileModule(stripped, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
const core = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);

assert.deepEqual(core.normalizeTimeSeriesPoints([]), [], "missing series remains empty");
assert.deepEqual(core.normalizeTimeSeriesPoints([{ date: "2026-01-01", value: 2 }]), [{ date: "2026-01-01", value: 2 }], "single observation is retained");
assert.deepEqual(core.normalizeTimeSeriesPoints([{ date: "2026-Q1", value: 1 }, { date: "2026-04-01", value: 2 }, { date: "", value: 3 }, { date: "2026-05", value: Number.NaN }]), [{ date: "2026-Q1", value: 1 }, { date: "2026-04-01", value: 2 }], "mixed frequency labels are preserved and invalid points are removed");

const groups = core.groupDivergingData([
  { id: "a", label: "A", value: -2, unit: "%", scaleGroup: "percent" },
  { id: "b", label: "B", value: 3, unit: "%", scaleGroup: "percent" },
  { id: "c", label: "C", value: -0.2, unit: "pp", scaleGroup: "points" },
  { id: "bad", label: "Bad", value: Number.NaN, unit: "%", scaleGroup: "percent" },
]);
assert.equal(groups.length, 2, "unlike units are separated");
assert.deepEqual(groups[0].map((item) => item.value), [-2, 3], "negative values retain sign");
assert.equal(core.coveragePercent(23, 27), 23 / 27 * 100);
assert.equal(core.coveragePercent(undefined, 27), null, "missing numerator remains categorical");
assert.equal(core.coveragePercent(1, 0), null, "zero denominator never creates completeness");

console.log("Chart normalization edge-case tests passed.");
