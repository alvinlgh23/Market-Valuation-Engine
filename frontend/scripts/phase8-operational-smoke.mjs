import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";

const base = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
await fs.mkdir("artifacts/phase8", { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  for (const ticker of ["PLTR", "TSM", "NVDA", "AMD", "MSFT", "COST"]) {
    await page.goto(`${base}/company/${ticker}?fixture=1`, { waitUntil: "networkidle" });
    const research = page.getByRole("region", { name: "Operational research", exact: true });
    await research.waitFor();
    await page.getByText("Direction Unknown", { exact: true }).first().waitFor();
    assert.equal(await page.getByText("Observed Easing", { exact: true }).count(), 0);
    assert.equal(await page.getByText("Potentially Binding", { exact: true }).count(), 0);
    assert.equal(await page.getByText("Below Supported Economics", { exact: true }).count(), 0);
    if (["PLTR", "TSM", "NVDA"].includes(ticker)) {
      await research.locator("summary").first().click();
      await research.getByText("Observation provenance", { exact: true }).first().click();
      await research.getByText(/documentary_manual/).first().waitFor();
    } else {
      await research.getByText(/Missing company-specific operational evidence/).waitFor();
    }
    if (ticker === "TSM") {
      await research.getByText(/authoritative per-ADR conclusions remain blocked/).waitFor();
      await research.getByText(/Published 2026-03-12/).first().waitFor();
      await research.locator("summary").filter({ hasText: "Advanced technology revenue mix" }).click();
      await research.getByText(/Comparable change: 5 percentage points/).waitFor();
      assert.equal(await research.getByText(/7.2% relative growth/).count(), 0);
    }
    await page.screenshot({ path: `artifacts/phase8/${ticker}.png`, fullPage: true });
  }
  await page.goto(`${base}/company/PLTR?fixture=1&workspace=economics&node=pltr_customers`, { waitUntil: "networkidle" });
  await page.getByRole("region", { name: "Operational research", exact: true }).last().waitFor();
  await page.screenshot({ path: "artifacts/phase8/PLTR-inspector.png", fullPage: true });
  await page.goto(`${base}/company/PLTR?fixture=1`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Full Report/ }).click();
  await page.getByRole("dialog").getByText("Operational observations", { exact: true }).waitFor();
  await page.getByRole("dialog").getByRole("cell", { name: "954", exact: true }).waitFor();
  assert.equal(await page.getByRole("dialog").getByText("Observed Easing", { exact: true }).count(), 0);
  await page.getByRole("button", { name: "Close ×", exact: true }).click();
  await page.getByRole("button", { name: /Open Valuation Open the unified/ }).click();
  await page.waitForURL(/\/valuation\/PLTR/);
  assert.match(page.url(), /fixture=1/);
  console.log("Phase 8: six company snapshots, provenance, missing states, ADR gate, direct map inspector, report and valuation navigation passed.");
} finally {
  await browser.close();
}
