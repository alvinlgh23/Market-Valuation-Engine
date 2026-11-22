import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.RESEARCH_BASE_URL ?? "http://127.0.0.1:3000";
const artifacts = path.resolve("artifacts/research-capability-audit");
await fs.mkdir(artifacts, { recursive: true });
const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(12_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

async function shot(page, name, fullPage = false) {
  await page.screenshot({ path: path.join(artifacts, name), fullPage });
}

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  observe(page);
  let response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Dashboard returned ${response?.status()}`);
  await page.locator(".today-regime h1").waitFor();
  if ((await page.locator(".env-factors article").count()) < 6) throw new Error("Today page does not show the macro factor tiles");
  if ((await page.locator(".today-chips .today-chip").count()) < 4) throw new Error("Today page watch items are under-populated");
  await shot(page, "01-dashboard.png", true);

  response = await page.goto(`${baseUrl}/macro/world`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Macro returned ${response?.status()}`);
  await page.getByRole("heading", { name: "World Macro Map" }).waitFor();
  await shot(page, "02-macro-world-map.png", true);

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=SG&detail=currency`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "Singapore macro profile" }).waitFor();
  await shot(page, "03-singapore-brief.png", true);
  const neer = page.locator("details").filter({ hasText: "SHADOW S$NEER" });
  await neer.locator("summary").click();
  await neer.locator(".time-series-chart").waitFor();
  if ((await neer.locator(".diverging-chart button").count()) !== 12) throw new Error("NEER does not show all 12 FX components");
  await shot(page, "04-singapore-neer-fx-workspace.png", true);

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=JP&detail=policy`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "Japan macro profile" }).waitFor();
  await shot(page, "05-japan-brief.png", true);

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=KR&detail=markets`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "South Korea macro profile" }).waitFor();
  await shot(page, "06-korea-brief.png", true);
  const kospi = page.locator("details").filter({ hasText: "KOSPI RESEARCH ENGINE" });
  await kospi.locator("summary").click();
  if ((await kospi.locator(".ranked-chart").count()) !== 3) throw new Error("KOSPI factor, GARCH, and export visualizations are incomplete");
  if ((await kospi.locator(".ranked-chart").first().locator("button").count()) !== 5) throw new Error("KOSPI does not show all five factors");
  if ((await kospi.locator(".ranked-chart").nth(1).locator("button").count()) !== 2) throw new Error("KOSPI GARCH comparison is incomplete");
  if ((await kospi.locator(".ranked-chart").nth(2).locator("button").count()) < 6) throw new Error("KOSPI export structure is incomplete");

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=US&detail=policy`, { waitUntil: "networkidle" });
  const compass = page.locator("details").filter({ hasText: "CENTRAL BANK COMPASS" });
  await compass.locator("summary").click();
  if ((await compass.locator(".ranked-chart-list > button").count()) !== 5) throw new Error("Compass does not expose five policy blocks");
  if ((await compass.locator(".diverging-chart button").count()) !== 7) throw new Error("Compass does not expose seven liquidity drivers");
  await shot(page, "07-central-bank-workspace.png", true);

  await page.goto(`${baseUrl}/macro/world?mode=transmission`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Cross-border transmission" }).waitFor();
  await shot(page, "08-transmission-map.png", true);

  await page.goto(`${baseUrl}/company/PLTR?fixture=1`, { waitUntil: "networkidle" });
  await page.locator(".company-details > summary").click();   // checklist 9.4: the stored profile is folded
  await page.getByText("Current economic read").waitFor();
  await shot(page, "09-company-snapshot.png", true);
  await page.getByRole("button", { name: /^Economic map$/ }).click();
  await page.getByRole("dialog", { name: /Economic Map workspace/i }).waitFor();
  await shot(page, "10-economic-map.png");

  const api = await page.request.get(`${baseUrl}/api/research?scope=dashboard`);
  if (!api.ok()) throw new Error(`Research API returned ${api.status()}`);
  const apiPayload = await api.json();
  if (apiPayload.data.reads.length !== 6) throw new Error("Research API dashboard contract is incomplete");

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  await mobile.locator(".today-regime h1").waitFor();
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Mobile dashboard has horizontal overflow");
  await shot(mobile, "11-mobile-dashboard.png", true);
  await mobile.close();
  await page.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Integrated research capability checks passed; 11 requested screenshots captured.");
