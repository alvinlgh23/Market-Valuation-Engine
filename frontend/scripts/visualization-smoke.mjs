import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.RESEARCH_BASE_URL ?? "http://127.0.0.1:3000";
const artifacts = path.resolve("artifacts/visualization-refactor");
await fs.mkdir(artifacts, { recursive: true });
const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(15_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

async function screenshot(page, name, fullPage = true) { await page.screenshot({ path: path.join(artifacts, name), fullPage }); }

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1050 } });
  observe(page);
  let response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Overview returned ${response?.status()}`);
  await page.getByRole("heading", { name: "Market intelligence" }).waitFor();
  if ((await page.locator(".system-read-grid > a").count()) !== 6) throw new Error("Executive state cards changed unexpectedly");
  if ((await page.locator(".ranked-chart").count()) < 1) throw new Error("Ranked watch visualization missing");
  if ((await page.locator(".diverging-chart section").count()) !== 2) throw new Error("Unlike observed-move units are not separated");
  if ((await page.locator(".heatmap-cell").count()) !== 30) throw new Error("Macro regime matrix is incomplete");
  if ((await page.locator(".coverage-chart button").count()) !== 6) throw new Error("Coverage visualization is incomplete");
  if ((await page.locator(".company-matrix-section").count()) !== 1) throw new Error("Company research matrix surface is missing");
  await screenshot(page, "01-overview-visualizations.png");

  response = await page.goto(`${baseUrl}/macro/world`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`World Macro returned ${response?.status()}`);
  await page.getByRole("heading", { name: "World Macro Map" }).waitFor();
  if ((await page.locator(".macro-map-marker").count()) !== 6) throw new Error("World coverage map marker count changed");
  await screenshot(page, "02-world-macro.png");

  await page.goto(`${baseUrl}/macro/inflation`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Inflation pressure" }).waitFor();
  if ((await page.locator(".inflation-cell").count()) !== 27) throw new Error("Inflation matrix does not expose all 27 indicators");
  await page.locator(".inflation-cell").nth(5).click();
  await page.locator(".inflation-indicator-inspector").waitFor();
  await screenshot(page, "03-us-inflation-matrix.png");

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=SG&detail=currency`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "Singapore macro profile" }).waitFor();
  const neer = page.locator("details").filter({ hasText: "SHADOW S$NEER" });
  await neer.locator("summary").click();
  await neer.locator(".time-series-chart").waitFor();
  if ((await neer.locator(".diverging-chart button").count()) !== 12) throw new Error("NEER contribution chart does not expose all 12 currencies");
  await neer.locator(".diverging-chart button").first().click();
  await screenshot(page, "04-singapore-neer.png");

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=KR&detail=markets`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "South Korea macro profile" }).waitFor();
  const kospi = page.locator("details").filter({ hasText: "KOSPI RESEARCH ENGINE" });
  await kospi.locator("summary").click();
  if ((await kospi.locator(".ranked-chart").count()) !== 3) throw new Error("KOSPI factor/GARCH/export visualizations are incomplete");
  await kospi.getByRole("button", { name: /Tech \/ AI/ }).first().click();
  await kospi.locator(".time-series-chart").waitFor();
  await screenshot(page, "05-south-korea-kospi.png");

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=US&detail=policy`, { waitUntil: "networkidle" });
  const compass = page.locator("details").filter({ hasText: "CENTRAL BANK COMPASS" });
  await compass.locator("summary").click();
  if ((await compass.locator(".ranked-chart-list > button").count()) !== 5) throw new Error("Compass policy block chart is incomplete");
  if ((await compass.locator(".diverging-chart button").count()) !== 7) throw new Error("Compass liquidity contribution chart is incomplete");
  await compass.locator(".ranked-chart-list > button").nth(1).click();
  await compass.locator(".engine-evidence-drill").waitFor();
  await screenshot(page, "06-deep-compass-evidence.png");

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Visualization Overview has page-level mobile overflow");
  await mobile.locator(".ranked-chart").waitFor();
  await mobile.close();
  await page.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Visualization refactor checks passed; six required screenshots captured.");
