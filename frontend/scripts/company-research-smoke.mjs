import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.COMPANY_RESEARCH_BASE_URL ?? "http://127.0.0.1:3000";
const tickers = ["PLTR", "NVDA", "MSFT", "JPM", "COST", "TSM"];
const artifacts = path.resolve("artifacts/research-workstation");
await fs.mkdir(artifacts, { recursive: true });
const fixtureCompanyUrl = (ticker, query = "") => `${baseUrl}/company/${ticker}?fixture=1${query ? `&${query}` : ""}`;

const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(8_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

try {
  const directWorkspace = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  observe(directWorkspace);
  const directResponse = await directWorkspace.goto(fixtureCompanyUrl("PLTR", "workspace=evidence"), { waitUntil: "networkidle" });
  if (!directResponse?.ok()) throw new Error(`Direct evidence workspace returned ${directResponse?.status()}`);
  await directWorkspace.getByRole("dialog", { name: /Evidence Trace workspace/i }).waitFor();
  await directWorkspace.close();

  const overview = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  observe(overview);
  await overview.goto(`${baseUrl}/companies`, { waitUntil: "networkidle" });
  await overview.screenshot({ path: path.join(artifacts, "overview.png") });
  await overview.locator("#company-index-ticker").fill("PLTR");
  await overview.screenshot({ path: path.join(artifacts, "company-search.png") });
  await overview.close();

  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  observe(page);
  for (const ticker of tickers) {
    console.log(`Checking ${ticker} snapshot and map`);
    const response = await page.goto(fixtureCompanyUrl(ticker), { waitUntil: "networkidle" });
    if (!response?.ok()) throw new Error(`${ticker} returned ${response?.status()}`);
    const text = await page.locator("body").innerText();
    const normalizedText = text.toLowerCase();
    if (/\b(undefined|null|NaN)\b/.test(text)) throw new Error(`${ticker} leaks an unavailable sentinel`);
    if (/[A-Z]+_[A-Z_]+/.test(text)) throw new Error(`${ticker} leaks a backend enum`);
    if (!normalizedText.includes("growth engine") || !normalizedText.includes("primary constraint") || !normalizedText.includes("current economic read")) throw new Error(`${ticker} snapshot is incomplete`);
    await page.getByRole("button", { name: /Open Economic Map/ }).click();
    await page.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor();
    if ((await page.locator(".economic-node").count()) < 5) throw new Error(`${ticker} map has too few economic nodes`);
    await page.screenshot({ path: path.join(artifacts, `${ticker.toLowerCase()}-economic-map.png`) });
    await page.keyboard.press("Escape");
    await page.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor({ state: "detached" });
  }

  await page.goto(fixtureCompanyUrl("PLTR"), { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(artifacts, "company-level0.png") });
  await page.getByRole("button", { name: /Open Economic Map/ }).click();
  await page.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "economic-map-open.png") });
  await page.locator(".economic-node.node-constraint").first().click();
  await page.locator(".workspace-inspector").getByRole("heading", { name: /Deployment Capacity/i }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "constraint-node-selected.png") });
  await page.getByRole("button", { name: /Trace Evidence/i }).click();
  await page.getByRole("dialog", { name: /Evidence Trace workspace/i }).waitFor();
  await page.locator(".workspace-depth-2 .workspace-canvas .workspace-evidence-list > button").first().click();
  await page.screenshot({ path: path.join(artifacts, "evidence-trace.png") });
  await page.getByRole("button", { name: /View Source \/ Calculation/i }).click();
  await page.getByRole("dialog", { name: /Source & Calculation workspace/i }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "source-trace.png") });
  await page.keyboard.press("Escape");
  await page.getByRole("dialog", { name: /Source & Calculation workspace/i }).waitFor({ state: "detached" });
  await page.goBack();
  await page.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor();
  if (!(await page.locator(".economic-node-selected").count())) throw new Error("Browser back did not preserve the selected economic node");
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: /Open Valuation/ }).click();
  await page.getByRole("heading", { name: /Palantir/i }).waitFor();
  await page.locator(".valuation-research-surface").waitFor();
  await page.screenshot({ path: path.join(artifacts, "valuation-workspace.png") });
  await page.goto(fixtureCompanyUrl("PLTR"), { waitUntil: "networkidle" });

  await page.getByRole("button", { name: /Full Report/i }).click();
  await page.getByRole("dialog", { name: /full company economics report/i }).waitFor();
  if ((await page.locator(".report-section").count()) !== 15) throw new Error("Report mode does not contain 15 sections");
  await page.screenshot({ path: path.join(artifacts, "full-report.png") });
  await page.keyboard.press("Escape");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(fixtureCompanyUrl("PLTR"), { waitUntil: "networkidle" });
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Mobile snapshot has horizontal page overflow");
  await mobile.screenshot({ path: path.join(artifacts, "mobile-company-snapshot.png") });
  await mobile.screenshot({ path: path.join(artifacts, "mobile-navigation.png") });
  await mobile.getByRole("button", { name: /Open Economic Map/ }).click();
  await mobile.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor();
  await mobile.screenshot({ path: path.join(artifacts, "mobile-economic-map.png") });
  await mobile.locator(".economic-node.node-constraint").first().click();
  await mobile.locator(".workspace-inspector").getByRole("heading", { name: /Deployment Capacity/i }).waitFor();
  await mobile.screenshot({ path: path.join(artifacts, "mobile-constraint-inspector.png") });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log(`Research workstation checks passed for ${tickers.join(", ")}`);
