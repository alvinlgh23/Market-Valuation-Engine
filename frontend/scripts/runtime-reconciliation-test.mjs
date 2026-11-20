import assert from "node:assert/strict";
import fs from "node:fs/promises";
import ts from "typescript";

async function moduleUrl(file, replacements = {}) {
  let source = await fs.readFile(new URL(`../lib/${file}`, import.meta.url), "utf8");
  for (const [from, to] of Object.entries(replacements)) source = source.replace(from, to);
  source = source.replace(/^import type .*;$/gm, "");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
  return `data:text/javascript;base64,${Buffer.from(js).toString("base64")}`;
}
const sectorUrl = await moduleUrl("market-research.ts");
const { integrateSectorEngineRows } = await import(sectorUrl);
const { reconcileResearchResponse } = await import(await moduleUrl("research-response.ts"));
const { dashboardStateStrip, marketLeadershipSummary } = await import(await moduleUrl("dashboard-orchestration.ts", { '"./market-research"': JSON.stringify(sectorUrl) }));
// Exact response captured from the normal dev server before this repair.
const response = JSON.parse(await fs.readFile(new URL("../artifacts/runtime-reconciliation/before-api.json", import.meta.url), "utf8"));
const rows = response.data.modules.core_market.payload.sectors;
assert.equal(rows.length, 34);
const mapped = integrateSectorEngineRows(rows, "CACHED");
for (const row of rows) {
  const item = mapped.find(s => s.ticker === row.ticker);
  assert.ok(item, `API ticker silently lost: ${row.ticker}`);
  assert.equal(item.rel6m, row.rel_6m);
  assert.equal(item.lastUpdated, row.as_of);
  assert.equal(item.measurementSource, row.source);
  assert.equal(item.sourceState, "STALE");
  assert.equal(item.breadthRatio, null);
  assert.equal(item.crowding, "Unavailable");
}
assert.equal(dashboardStateStrip(response.data).find(x => x.label === "Leadership").state, rows[0].name);
assert.equal(marketLeadershipSummary(response.data)[0].ticker, rows[0].ticker);
const invalid = integrateSectorEngineRows([{ ...rows[0], validation_status: "FAILED", validation_reason: "Incompatible price basis" }]);
assert.equal(invalid.find(s => s.ticker === rows[0].ticker).rel6m, null);
assert.equal(invalid.find(s => s.ticker === rows[0].ticker).measurementReason, "Incompatible price basis");
assert.equal(invalid.find(s => s.ticker === rows[0].ticker).sourceState, "UNAVAILABLE");
assert.match(invalid.find(s => s.ticker === rows[0].ticker).currentRead, /Measurement withheld: Incompatible price basis/);
const empty = structuredClone(response);
empty.data.modules.core_market.payload.sectors = [];
empty.meta = { fallback: false };
assert.ok(integrateSectorEngineRows([]).every(s => s.rel6m === null && s.measurementReason === "No sector row in this snapshot."));
assert.equal(reconcileResearchResponse(response.data, empty).modules.core_market.payload.sectors.length, 34, "Unjustified empty snapshot cannot erase 34 cached rows");
assert.equal(reconcileResearchResponse(response.data, empty).modules.core_market.state, "STALE");
empty.meta = { fallback: false, empty_reason: "All rows failed model validation" };
assert.equal(reconcileResearchResponse(response.data, empty).modules.core_market.payload.sectors.length, 0, "Justified validated empty snapshot remains explicit");
empty.meta = { fallback: true, error: "Provider refresh failed" };
const retained = reconcileResearchResponse(response.data, empty);
assert.equal(retained.modules.core_market.payload.sectors.length, 34);
assert.equal(retained.modules.core_market.state, "STALE");
assert.equal(retained.dashboard, response.data.dashboard, "Retained claims and metrics share one snapshot");
console.log("Runtime contract: all 34 captured rows retained with dates/source; dashboard lineage, explicit invalid/empty states and failed-refresh retention passed.");

// Checklist 1.6: every API row carries its engine rank, in engine order.
{
  const ranked = integrateSectorEngineRows(rows, "CACHED").filter((sector) => sector.engineRank != null).sort((a, b) => a.engineRank - b.engineRank);
  assert.equal(ranked.length, rows.length);
  assert.deepEqual(ranked.map((sector) => sector.ticker), rows.map((row) => row.ticker.toUpperCase()));
  console.log("Engine rank: table order matches the Python engine ranking for all rows.");
}
