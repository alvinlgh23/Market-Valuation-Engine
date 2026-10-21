import assert from "node:assert/strict";
import fs from "node:fs/promises";
import ts from "typescript";

const adapterSource = await fs.readFile(new URL("../lib/research-visualization-adapter.ts", import.meta.url), "utf8");
const stripped = adapterSource.replace(/^import type .*;$/gm, "");
const output = ts.transpileModule(stripped, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
const adapter = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
const system = JSON.parse(await fs.readFile(new URL("../lib/fixtures/research-system.json", import.meta.url), "utf8"));

const neer = system.modules.neer.payload;
const contributions = adapter.normalizeNeerContributions(neer);
assert.equal(contributions.length, 12, "all twelve NEER currencies map into the contribution chart");
assert.ok(contributions.every((item) => Number.isFinite(item.value)), "NEER contributions remain typed numeric values");
assert.ok(contributions.every((item) => item.scaleGroup === "neer-contribution"), "NEER contributions share only their defensible unit scale");
assert.equal(adapter.normalizeNeerHistory(neer).points.length, 299, "real cached NEER history remains available");

const kospi = system.modules.kospi.payload;
const factors = adapter.normalizeKospiFactors(kospi);
assert.equal(factors.length, 5, "all KOSPI studies map into the factor visual");
assert.equal(factors.filter((item) => item.confidence === "OBSERVED").length, 4, "the missing foreign-flow study stays insufficient");
const volatility = adapter.normalizeKospiVolatility(kospi);
assert.equal(volatility.length, 2, "GARCH current and sample-average values map into a comparison");
assert.ok(volatility.every((item) => Number.isFinite(item.magnitude)), "GARCH values stay numeric");

assert.equal(system.market_transmission.coverage.source_state, "CACHED", "last-valid research is distinguished from live data");
assert.equal(system.market_transmission.risk.coverage_status, "INSUFFICIENT", "risk gate remains categorical");

console.log("Macro coverage and specialist-engine mapping tests passed.");
