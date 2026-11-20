import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";

const base = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = "artifacts/phase8_1";
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  for (const ticker of ["PLTR", "TSM", "NVDA", "AMD", "MSFT", "COST"]) {
    const response = await page.request.get(`${base}/api/research?action=company-open&ticker=${ticker}`);
    assert.equal(response.ok(), true);
    const api = await response.json();
    const live = api.profile?.company_economics;
    assert.ok(live, `${ticker}: real provider profile required, got ${api.status}`);
    assert.equal(live.classification_version, "phase8.1-evidence-authority-v2");
    const nodeIds = live.economic_graph.nodes.map(n => n.id);
    assert.equal(new Set(nodeIds).size, nodeIds.length);
    if (ticker === "TSM") assert.ok(!nodeIds.includes("node_mix") && !nodeIds.includes("wafer_volume"));
    assert.equal(live.constraints.primary_constraint.direction_status, "DIRECTION_UNKNOWN");
    assert.ok(live.evidence_trace.some(e => e.metric === "revenue" && e.type === "FACT"));
    assert.ok(!live.evidence_trace.some(e => e.source_status === "FIXTURE"));
    for (const mode of ["fixture", "provider"]) {
      const query = mode === "fixture" ? "fixture=1&" : "";
      const url = `${base}/company/${ticker}?${query}`;
      await page.goto(url, { waitUntil: "networkidle" });
      await page.getByRole("region", { name: "Operational research", exact: true }).waitFor();
      assert.equal(await page.getByText("Observed Easing", { exact: true }).count(), 0);
      if (mode === "fixture") {
        await page.getByText("Synthetic fixture scaling metrics are illustrative, not observed company economics.").waitFor();
        assert.equal(await page.getByText("Below Supported Economics", { exact: true }).count(), 0);
      } else {
        assert.equal(await page.getByText("Synthetic fixture scaling metrics are illustrative, not observed company economics.").count(), 0);
        assert.equal(await page.getByText("Current price unavailable in fixture").count(), 0);
      }
      await page.screenshot({ path: `${output}/${ticker}-${mode}.png`, fullPage: true });
      const node = live.operational_research.series[0]?.definition.id || "revenue";
      await page.goto(`${url}workspace=economics&node=${node}`, { waitUntil: "networkidle" });
      await page.locator(".workspace-inspector").waitFor();
      if (node !== "revenue") await page.locator(".workspace-inspector").getByText(/Direction: Direction Unknown/).waitFor();
      await page.getByRole("button", { name: "Trace Evidence" }).click();
      await page.getByRole("dialog", { name: "Evidence Trace workspace" }).waitFor();
      const evidence = page.locator(".workspace-evidence-list button");
      assert.ok(await evidence.count() > 0);
      await evidence.first().click();
      await page.getByRole("button", { name: "View Source / Calculation" }).click();
      await page.getByText("Provider / source status", { exact: true }).waitFor();
      if (["PLTR", "TSM"].includes(ticker)) await page.screenshot({ path: `${output}/${ticker}-${mode}-evidence.png`, fullPage: true });
      await page.goto(`${url}workspace=evidence`, { waitUntil: "networkidle" });
      await page.getByRole("dialog", { name: "Evidence Trace workspace" }).waitFor();
      if (mode === "fixture") await page.getByText("Fixture · Synthetic", { exact: true }).first().waitFor();
      else assert.equal(await page.getByText("Fixture · Synthetic", { exact: true }).count(), 0);
      await page.goto(url, { waitUntil: "networkidle" });
      await page.getByRole("button", { name: /Full Report/ }).click();
      const report = page.getByRole("dialog");
      await report.getByText("Operational observations", { exact: true }).waitFor();
      assert.equal(await report.getByText("Observed Easing", { exact: true }).count(), 0);
      if (mode === "fixture") assert.equal(await report.getByText("Below Supported Economics", { exact: true }).count(), 0);
      if (["PLTR", "TSM"].includes(ticker)) await page.screenshot({ path: `${output}/${ticker}-${mode}-report.png`, fullPage: true });
      results.push({ ticker, mode, providerStatus: mode === "provider" ? api.status : null, journey: "PASS" });
    }
  }
  await fs.writeFile(`${output}/journey-results.json`, JSON.stringify(results, null, 2) + "\n");
  console.log(JSON.stringify(results));
} finally { await browser.close(); }
