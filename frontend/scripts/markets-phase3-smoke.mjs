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
  // Map view (2026-11-27): the 11 sectors on one plane, opened from the overview.
  await page.getByRole("tab", { name: "Map", exact: true }).click();
  await page.getByRole("region", { name: "Sectors by six-month performance and crowding" }).waitFor();
  await page.screenshot({ path: path.join(output, "01-sector-map-view.png") });
  await page.getByRole("tab", { name: "Heatmap", exact: true }).click();

  // The sector page (rebuilt 2026-11-27): hero, your holdings, money flow, industries inside, written industry map.
  await page.getByRole("region", { name: "Sectors against the S&P 500" }).getByRole("link", { name: /Technology/ }).click();
  await page.getByRole("heading", { name: "Technology", exact: true }).waitFor();
  await page.getByRole("link", { name: /All sectors/ }).waitFor();
  await page.getByRole("heading", { name: /Your holdings in this sector/ }).waitFor();
  await page.getByRole("heading", { name: /Industries inside it/ }).waitFor();
  await page.screenshot({ path: path.join(output, "02-technology-sector.png"), fullPage: true });
  if (await page.getByText("Full Report").count()) throw new Error("The raw-JSON Full Report must not appear on the sector page.");

  await page.getByRole("link", { name: /Semiconductors/ }).first().click();
  await page.getByRole("heading", { name: "Semiconductors", exact: true }).waitFor();
  await page.getByRole("link", { name: /Part of Technology/ }).waitFor();
  await page.getByRole("heading", { name: /How this industry works/ }).waitFor();
  if (await page.getByText(/compute-supply-chain|fixture/i).count()) throw new Error("Engine slugs or fixture wording leaked onto the sector page.");
  await page.screenshot({ path: path.join(output, "03-semiconductors-sector.png"), fullPage: true });

  // Old deep links (report, structure, leadership) still land on the sector page, never on raw JSON.
  for (const view of ["report", "structure", "leadership", "breadth", "positioning"]) {
    await page.goto(`${baseUrl}/markets?sector=semiconductors&view=${view}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Semiconductors", exact: true }).waitFor();
    if (await page.locator("pre").count()) throw new Error(`view=${view} rendered raw JSON.`);
  }

  // Sectors without a written industry map show none; readable slugs resolve.
  await page.goto(`${baseUrl}/markets?sector=communication-services`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Communication", exact: true }).waitFor();
  if (await page.getByRole("heading", { name: /How this industry works/ }).count()) throw new Error("Communication has no written industry map; none should show.");
  for (const [sector, heading] of [["energy", "Energy"], ["financials", "Financials"]]) {
    await page.goto(`${baseUrl}/markets?sector=${sector}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: heading, exact: true }).waitFor();
    await page.getByRole("heading", { name: /How this industry works/ }).waitFor();
  }

  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(`${baseUrl}/markets`, { waitUntil: "networkidle" });
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Markets overview has horizontal page overflow on mobile.");
  await mobile.screenshot({ path: path.join(output, "15-mobile-sector-rotation.png") });
  await mobile.goto(`${baseUrl}/markets?sector=semiconductors`, { waitUntil: "networkidle" });
  await mobile.getByRole("heading", { name: "Semiconductors", exact: true }).waitFor();
  if (await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)) throw new Error("Sector page has horizontal page overflow on mobile.");
  await mobile.screenshot({ path: path.join(output, "16-mobile-sector-page.png") });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Markets Phase 3 checks passed; screenshots captured.");
