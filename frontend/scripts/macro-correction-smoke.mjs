import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.MACRO_BASE_URL ?? "http://127.0.0.1:3000";
const artifacts = path.resolve("artifacts/macro-correction");
await fs.mkdir(artifacts, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];
function observe(page) {
  page.setDefaultTimeout(15_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}
async function open(page, route) {
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`${route} returned ${response?.status()}`);
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  observe(page);

  // Checklist 16: the factor tiles and engine detail moved from /macro to the internal /labs/factors page.
  await open(page, "/labs/factors");
  await page.locator(".env-factors").waitFor();
  if (await page.locator(".macro-overview-surface .object-metric-grid").count()) throw new Error("Macro Overview still contains the generic metric grid");
  await page.getByRole("heading", { name: "US Treasury structure" }).waitFor();
  // Since checklist 1.1 Macro renders current data, not the August fixture. The curve is drawn
  // only when 2Y/10Y/30Y share an observation date; otherwise the rates card shows its
  // explicit coverage fallback. Either is valid; a blank card is not.
  const curve = page.getByRole("img", { name: /Treasury curve with 2Y, 10Y/ });
  const curveFallback = page.locator(".rates-card .macro-coverage-fallback");
  await curve.or(curveFallback).first().waitFor();
  await page.getByText(/\d+\/\d+ configured drivers available\./).first().waitFor();
  await page.screenshot({ path: path.join(artifacts, "01-macro-overview.png"), fullPage: true });
  await page.locator(".macro-market-transmission").screenshot({ path: path.join(artifacts, "02-market-transmission.png") });

  const japanMarker = page.getByRole("button", { name: "Open Japan macro profile" });   // Singapore removed 2026-11-22
  await japanMarker.hover();
  await page.getByText("JAPAN", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Brazil not available" }).hover();
  await page.getByText("No verified CHAINSTOX macro engine currently covers this economy.").waitFor();

  await open(page, "/macro/world");
  await page.getByRole("heading", { name: "World Macro Map" }).waitFor();
  if ((await page.locator(".macro-region-index > button").count()) !== 4) throw new Error("World map must list four supported economies (Singapore removed 2026-11-22)");
  await page.screenshot({ path: path.join(artifacts, "03-world-map.png"), fullPage: true });

  await open(page, "/macro/world?region=JP");
  await page.getByRole("complementary", { name: "Japan macro profile" }).waitFor();
  await page.locator(".macro-engine-detail > summary").filter({ hasText: "CENTRAL BANK COMPASS" }).click();
  await page.getByText("SPECIALIZED POLICY MODEL", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "07-japan-selected.png"), fullPage: true });

  await open(page, "/macro/world?region=KR");
  await page.getByRole("complementary", { name: "South Korea macro profile" }).waitFor();
  await page.getByRole("button", { name: "Open KOSPI" }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "08-south-korea-selected.png"), fullPage: true });
  await page.locator("#kospi-workspace > summary").click();
  if ((await page.locator("#kospi-workspace .macro-engine-visual").count()) !== 3) throw new Error("KOSPI workspace must expose factor, volatility and export visuals");
  if ((await page.locator("#kospi-workspace .macro-engine-visual").nth(0).locator(".ranked-chart-list > button").count()) !== 5) throw new Error("KOSPI factor visual must expose five studies");
  if ((await page.locator("#kospi-workspace .macro-engine-visual").nth(1).locator(".ranked-chart-list > button").count()) !== 2) throw new Error("GARCH visual must compare current and average volatility");
  await page.locator("#kospi-workspace .macro-engine-visual").nth(0).screenshot({ path: path.join(artifacts, "09-kospi-factors.png") });

  for (const region of ["US", "EURO_AREA"]) {
    await open(page, `/macro/world?region=${region}`);
    const name = region === "US" ? "United States" : "Euro Area";
    await page.getByRole("complementary", { name: `${name} macro profile` }).waitFor();
    await page.getByRole("button", { name: "Open Policy" }).click();
    await page.locator(".macro-component-detail").waitFor();
  }

  // 2026-11-27: the graph became "Channels -> holdings"; a channel's detail opens from the map (filler sections removed).
  await open(page, "/macro/world?mode=transmission");
  await page.getByRole("heading", { name: "Channels → your holdings" }).waitFor();
  await open(page, "/macro/world?mode=regions&edge=jp-us-yen-carry");
  await page.getByRole("complementary", { name: /Yen carry → US risk assets transmission detail/ }).waitFor();
  await page.getByText("Structural chain", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "10-transmission-workspace.png"), fullPage: true });

  // 2026-11-27: Risk regime lives on Market conditions; the old URL redirects to its section.
  await open(page, "/macro/risk");
  await page.waitForURL(/\/macro\/conditions#regime/);
  await page.locator("#regime .display-h").waitFor();
  for (const [old, target] of [["/macro/rates", "#rates"], ["/macro/fx", "#fx"], ["/macro/liquidity", "#liquidity"], ["/macro/central-banks", "#central-banks"]]) {
    await open(page, old);
    await page.locator(target).waitFor();
  }
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await open(mobile, "/labs/factors");
  await mobile.locator(".env-factors").waitFor();
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Mobile Macro Overview has horizontal overflow");
  await mobile.screenshot({ path: path.join(artifacts, "11-mobile-macro.png"), fullPage: true });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Macro correction checks passed; 8 requested screenshots captured.");
