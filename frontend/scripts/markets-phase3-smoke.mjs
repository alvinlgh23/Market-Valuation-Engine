import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/markets-phase3");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(30_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 980 }, deviceScaleFactor: 1 });
  observe(page);

  // Since checklist 19.1 /markets opens on the whole market: the 11 sectors against the S&P 500, nothing preselected.
  await page.goto(`${baseUrl}/markets`, { waitUntil: "networkidle" });
  const overview = page.getByRole("region", { name: "Sectors against the S&P 500" });
  await overview.waitFor();
  const sectorLinks = await overview.getByRole("link").count();
  if (sectorLinks !== 11) throw new Error(`Expected 11 sector rows on the market overview, found ${sectorLinks}`);
  await page.getByRole("region", { name: "Themes and assets" }).waitFor();
  await page.screenshot({ path: path.join(output, "00-market-overview.png") });
  await overview.getByRole("link", { name: /Technology/ }).click();
  await page.getByRole("heading", { name: /Where leadership is moving/i }).waitFor();
  await page.getByRole("link", { name: /All sectors/ }).waitFor();
  await page.screenshot({ path: path.join(output, "01-sector-rotation.png") });

  await page.screenshot({ path: path.join(output, "02-full-sector-leaderboard.png") });
  // The rotation map now has points (checklist 5.5) whose labels can overlap; open the sector from the table.
  await page.getByRole("region", { name: "Sector rotation table" }).getByRole("link", { name: /Semiconductors/i }).first().click();
  await page.getByRole("heading", { name: "Semiconductors" }).waitFor();
  await page.screenshot({ path: path.join(output, "03-semiconductors-snapshot.png") });

  await page.getByRole("link", { name: /Explore Sector Structure/i }).click();
  await page.getByRole("heading", { name: /compute-supply-chain/i }).waitFor();
  await page.locator(".sector-structure-workspace").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "04-semiconductors-structure-map.png") });

  await page.getByRole("link", { name: /Advanced Packaging/i }).click();
  await page.getByRole("heading", { name: "Advanced Packaging" }).waitFor();
  await page.locator(".sector-structure-workspace").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "05-semiconductor-node-selected.png") });

  await page.goto(`${baseUrl}/company/NVDA?fixture=1&from=markets&sector=semiconductors`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "NVIDIA", exact: true }).waitFor();
  await page.screenshot({ path: path.join(output, "09-semiconductor-to-nvda.png") });
  await page.goBack();
  await page.getByRole("heading", { name: "Advanced Packaging" }).waitFor();

  await page.goto(`${baseUrl}/markets?sector=semiconductors&view=leadership`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Companies expressing/i }).waitFor();
  await page.screenshot({ path: path.join(output, "06-semiconductor-leadership.png") });

  // The sector breadth view was deleted (checklist 10.10); an old link falls back to the sector snapshot.
  await page.goto(`${baseUrl}/markets?sector=semiconductors&view=breadth`, { waitUntil: "networkidle" });
  await page.getByRole("region", { name: "Semiconductors current market state" }).waitFor();

  // Crowding is measured (checklist P5); either a measured state or Unavailable is valid.

  await page.goto(`${baseUrl}/markets?sector=semiconductors&view=positioning`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /^(Unavailable|Crowded|Extended|Neutral|Unloved)$/ }).first().waitFor();
  await page.screenshot({ path: path.join(output, "08-semiconductor-crowding-positioning.png") });

  for (const [sector, prefix] of [["energy", "10-energy"], ["financials", "12-financials"]]) {
    await page.goto(`${baseUrl}/markets?sector=${sector}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: new RegExp(sector === "energy" ? "Energy" : "Financials", "i") }).waitFor();
    await page.screenshot({ path: path.join(output, `${prefix}-snapshot.png`) });
    await page.goto(`${baseUrl}/markets?sector=${sector}&view=structure`, { waitUntil: "networkidle" });
    await page.locator(".sector-structure-node").first().waitFor();
    await page.locator(".sector-structure-workspace").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, `${Number(prefix.slice(0, 2)) + 1}-${sector}-structure-map.png`) });
  }

  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(`${baseUrl}/markets`, { waitUntil: "networkidle" });
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Markets overview has horizontal page overflow on mobile.");
  await mobile.screenshot({ path: path.join(output, "15-mobile-sector-rotation.png") });
  await mobile.goto(`${baseUrl}/markets?sector=semiconductors&view=structure&node=advanced-packaging`, { waitUntil: "networkidle" });
  await mobile.getByRole("heading", { name: "Advanced Packaging" }).waitFor();
  await mobile.locator(".sector-structure-workspace").scrollIntoViewIfNeeded();
  await mobile.screenshot({ path: path.join(output, "16-mobile-sector-structure.png") });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Markets Phase 3 checks passed; screenshots captured.");
