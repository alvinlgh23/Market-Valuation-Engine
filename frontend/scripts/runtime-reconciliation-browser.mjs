import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";

const base = process.env.CHAINSTOX_BASE_URL || "http://localhost:3001";
const directory = "artifacts/runtime-reconciliation";
await fs.mkdir(directory, { recursive: true });
const browser = await chromium.launch({ headless: true });
const trace = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  page.on("pageerror", error => trace.push({ pageError: String(error) }));
  async function visit(route, name) {
    const received = page.waitForResponse(r => r.url().includes("/api/research?scope=full"), { timeout: 120000 });
    await page.goto(`${base}${route}`, { waitUntil: "networkidle" });
    const response = await received;
    const body = await response.text();
    await fs.writeFile(`${directory}/${name}-api.json`, body);
    const json = JSON.parse(body);
    await page.locator("[data-research-status]").filter({ hasText: json.meta.core_snapshot_id }).waitFor();
    trace.push({ route, request: response.url(), status: response.status(), meta: json.meta });
    return json;
  }
  const markets = await visit("/markets", "after-markets");
  const rows = markets.data.modules.core_market.payload.sectors;
  const table = page.getByRole("region", { name: "Sector rotation table" });
  assert.equal(await table.locator("a").count(), 34);
  for (const row of rows) {
    const link = table.locator("a").filter({ hasText: `${row.ticker} ·` });
    assert.equal(await link.count(), 1, row.ticker);
    await link.getByText(row.name, { exact: false }).first().waitFor();
    assert.ok((await link.innerText()).includes(row.as_of));
  }
  await page.getByText(/Positioning plane unavailable: crowding measurements are missing/).waitFor();
  await page.screenshot({ path: `${directory}/after-markets.png`, fullPage: true });
  const labs = await visit("/labs/fragility", "after-labs");
  assert.equal(labs.meta.core_snapshot_id, markets.meta.core_snapshot_id);
  const sentiment = labs.data.modules.core_market.payload.fragility.consumer_sentiment;
  await page.locator(".object-metric-grid article").filter({ hasText: "Consumer Sentiment" }).first().getByText(sentiment.toFixed(2), { exact: true }).waitFor();
  await page.screenshot({ path: `${directory}/after-labs.png`, fullPage: true });
  const dashboard = await visit("/", "after-dashboard");
  assert.equal(dashboard.meta.core_snapshot_id, markets.meta.core_snapshot_id);
  await page.getByText("Healthcare", { exact: true }).first().waitFor();
  await page.screenshot({ path: `${directory}/after-dashboard.png`, fullPage: true });
  if (process.env.CHAINSTOX_CAPTURE_ONLY === "1") {
    await fs.writeFile(`${directory}/presentation-network-trace.json`, JSON.stringify(trace, null, 2) + "\n");
    console.log(JSON.stringify(trace));
  } else {
  await visit("/markets", "pre-refresh");
  const refreshResponse = page.waitForResponse(r => r.url().includes("refresh=1"), { timeout: 210000 });
  await page.getByRole("button", { name: "Refresh measurements" }).click();
  const refreshed = await refreshResponse;
  const refreshBody = await refreshed.text();
  await fs.writeFile(`${directory}/refresh-api.json`, refreshBody);
  const refresh = JSON.parse(refreshBody);
  trace.push({ route: "refresh", request: refreshed.url(), status: refreshed.status(), meta: refresh.meta, coreState: refresh.data.modules.core_market.state, error: refresh.data.modules.core_market.error, rowCount: refresh.data.modules.core_market.payload?.sectors?.length });
  await page.locator("[data-research-status]").filter({ hasText: /Core snapshot/ }).waitFor();
  assert.ok(await table.locator("a").count() >= 34, "Cached observations must survive failed refresh");
  await page.screenshot({ path: `${directory}/after-refresh.png`, fullPage: true });
  // A real transport failure (browser offline), not a mocked API response.
  await page.context().setOffline(true);
  await page.getByRole("button", { name: "Refresh measurements" }).click();
  await page.locator("[data-research-status]").filter({ hasText: "retaining displayed historical snapshot" }).waitFor();
  assert.ok(await table.locator("a").count() >= 34);
  await page.screenshot({ path: `${directory}/offline-retained.png`, fullPage: true });
  trace.push({ offlineTransport: "PASS", retainedTableRows: await table.locator("a").count() });
  await fs.writeFile(`${directory}/network-trace.json`, JSON.stringify(trace, null, 2) + "\n");
  console.log(JSON.stringify(trace));
  }
} finally { await browser.close(); }
