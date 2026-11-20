import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";

const base = process.env.CHAINSTOX_BASE_URL || "http://localhost:3000";
const directory = "artifacts/real-user-acceptance";
await fs.mkdir(directory, { recursive: true });
const api = await fetch(`${base}/api/research?scope=full`);
assert.equal(api.status, 200);
const response = await api.json();
const rows = response.data?.modules?.core_market?.payload?.sectors;
assert.ok(Array.isArray(rows) && rows.length > 0, "Acceptance requires actual cached sector rows");
await fs.writeFile(`${directory}/markets-api.json`, JSON.stringify(response, null, 2));
const htmlResponse = await fetch(`${base}/markets`);
assert.equal(htmlResponse.status, 200);
const html = await htmlResponse.text();
assert.ok(!html.includes("No sector row in this snapshot."), "Bundled empty rows leaked into the Markets server render");
for (const row of rows) assert.ok(html.includes(row.as_of), `${row.ticker} date absent from server HTML`);
await fs.writeFile(`${directory}/markets-server.html`, html);

const browser = await chromium.launch({ headless: true });
const trace = [];
try {
  trace.push({ route: "/markets", stage: "server HTML", coreSnapshotId: response.meta.core_snapshot_id, sectorRows: rows.length });
  const healthcare = rows.find(row => row.ticker === "XLV");
  assert.ok(healthcare);

  const clientPage = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  clientPage.on("response", result => { if (result.url().includes("/api/research")) trace.push({ request: result.url(), status: result.status() }); });
  clientPage.on("pageerror", error => trace.push({ pageError: String(error) }));
  const clientRequest = clientPage.waitForResponse(result => result.url().includes("/api/research?scope=full"), { timeout: 45000 });
  await clientPage.goto(`${base}/markets`, { waitUntil: "domcontentloaded" });
  const loaded = await clientRequest;
  const clientResponse = await loaded.json();
  assert.equal(clientResponse.meta.core_snapshot_id, response.meta.core_snapshot_id, "Browser and direct API selected different core snapshots");
  assert.equal(clientResponse.data.modules.core_market.payload.sectors.length, rows.length);
  await fs.writeFile(`${directory}/markets-browser-api.json`, JSON.stringify(clientResponse, null, 2));
  const clientTable = clientPage.getByRole("region", { name: "Sector rotation table" });
  await clientTable.waitFor({ timeout: 45000 });
  assert.equal(await clientTable.locator("a").count(), rows.length, "Hydrated Markets page lost cached sector rows");
  assert.ok((await clientTable.innerText()).includes(`${(healthcare.rel_6m * 100).toFixed(1)}%`));
  for (const row of rows) {
    const link = clientTable.locator("a").filter({ hasText: `${row.ticker} ·` });
    assert.equal(await link.count(), 1, `Missing ${row.ticker}`);
    assert.ok((await link.innerText()).includes(row.as_of), `${row.ticker} observation date missing`);
  }
  await clientPage.screenshot({ path: `${directory}/markets-client.png`, fullPage: true });
  trace.push({ route: "/markets", stage: "normal browser", sectorRows: await clientTable.locator("a").count() });
  await clientPage.goto(`${base}/markets?sector=semiconductors`, { waitUntil: "domcontentloaded" });
  const snapshot = clientPage.locator(".sector-snapshot-surface");
  await snapshot.waitFor({ timeout: 45000 });
  const semis = rows.find(row => row.ticker === "SMH");
  assert.ok(semis);
  const snapshotText = await snapshot.innerText();
  assert.ok(snapshotText.includes(semis.as_of));
  assert.ok(snapshotText.includes(semis.source));
  assert.ok(snapshotText.includes(`${(semis.rel_6m * 100).toFixed(1)}%`));
  assert.ok(!snapshotText.includes("No sector row in this snapshot."));
  await clientPage.screenshot({ path: `${directory}/semiconductors-client.png`, fullPage: true });
  trace.push({ route: "/markets?sector=semiconductors", observationDate: semis.as_of, source: semis.source, relativeStrength6m: semis.rel_6m });
  await clientPage.goto(`${base}/markets?sector=semiconductors&view=leadership`, { waitUntil: "domcontentloaded" });
  const leadership = clientPage.locator(".sector-leadership-bars");
  await leadership.waitFor({ timeout: 45000 });
  assert.equal(await leadership.locator("i").count(), 0, "Unmeasured company leadership must not draw quantitative bars");
  await clientPage.screenshot({ path: `${directory}/semiconductors-leadership.png`, fullPage: true });
  await fs.writeFile(`${directory}/markets-network-trace.json`, JSON.stringify(trace, null, 2));
  console.log(JSON.stringify(trace));
} finally {
  await browser.close();
}
