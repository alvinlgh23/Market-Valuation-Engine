import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/phase7");
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const research = await page.request.get(`${baseUrl}/api/research?scope=full`);
  assert.equal(research.ok(), true, `research API returned ${research.status()}`);
  const researchBody = await research.json();
  const sectors = researchBody.data?.modules?.core_market?.payload?.sectors;
  assert.equal(Array.isArray(sectors), true, "research API must expose a sector array");

  const smh = sectors.find((row) => row.ticker === "SMH");
  await page.goto(`${baseUrl}/markets?sector=semiconductors`, { waitUntil: "networkidle" });
  // Data source and date are shown in the header ("Saved data · market data as of …" or live).
  await page.getByText(/(Saved|Live) data · market data as of \d{4}-\d{2}-\d{2}/i).first().waitFor();
  if (smh && Number.isFinite(smh.rel_6m)) {
    const value = `${smh.rel_6m > 0 ? "+" : ""}${(smh.rel_6m * 100).toFixed(1)}%`;
    await page.getByText(value, { exact: true }).first().waitFor();
  } else {
    await page.getByText("Unavailable", { exact: true }).first().waitFor();
  }
  await page.screenshot({ path: path.join(output, "01-live-markets.png"), fullPage: true });

  for (const ticker of ["PLTR", "NVDA", "TSM"]) {
    // Company operating disclosures (with binding status, direction and counterevidence) live in the Evidence tab.
    await page.goto(`${baseUrl}/company/${ticker}?fixture=1&workspace=evidence`, { waitUntil: "networkidle" });
    const disclosures = page.locator("details.ev-operational");
    await disclosures.locator("summary").first().click();
    const research = disclosures.getByRole("region", { name: "Operational research", exact: true });
    await research.locator("details > summary").first().click();
    await research.getByText(/Binding: .* · Direction: Direction Unknown/).first().waitFor();
    assert.equal(await page.getByText("Observed Easing", { exact: true }).count(), 0);
    await research.getByText(/^Counterevidence:/).first().waitFor();
  }

  await page.goto(`${baseUrl}/company/PLTR?fixture=1&workspace=evidence`, { waitUntil: "networkidle" });
  await page.getByText(/Evidence Trace/i).first().waitFor();
  await page.locator(".workspace-evidence-list button").filter({ hasText: "Customers" }).first().click();
  await page.getByRole("button", { name: "View Source / Calculation" }).click();
  await page.getByText("Provider / source status", { exact: true }).waitFor();
  await page.getByText("Observed / retrieved", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(output, "02-evidence-provenance.png"), fullPage: true });

  console.log(JSON.stringify({ sectors: sectors.length, smh: smh?.rel_6m ?? null, companies: ["PLTR", "NVDA", "TSM"], provenance: "visible" }));
} finally {
  await browser.close();
}
