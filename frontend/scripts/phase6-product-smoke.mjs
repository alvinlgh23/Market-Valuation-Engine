import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/phase6-product");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(12_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

async function screenshot(page, filename) {
  await page.screenshot({ path: path.join(output, filename), fullPage: false });
}

async function noHorizontalOverflow(page, label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error(`${label} has horizontal page overflow.`);
}

async function openSearch(page, query, filename) {
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByRole("dialog", { name: /Global research search/i }).waitFor();
  if (query) await page.getByLabel("Search research").fill(query);
  await screenshot(page, filename);
  await page.keyboard.press("Escape");
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1 });
  observe(page);

  await page.goto(`${baseUrl}/demo`, { waitUntil: "networkidle" });
  await page.getByText("DETERMINISTIC DEMO").first().waitFor();
  await page.getByText(/CHAINSTOX maps economic mechanisms/i).first().waitFor();
  await screenshot(page, "01-demo-dashboard-orientation.png");
  await noHorizontalOverflow(page, "Demo dashboard");

  await openSearch(page, "", "02-global-search-priority-demo.png");
  await openSearch(page, "Atlantis", "03-global-search-unsupported.png");

  await page.goto(`${baseUrl}/macro/world?mode=transmission&edge=jp-us-yen-carry&demo=1`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Cross-border transmission/i }).waitFor();
  await page.getByText(/Japan|Yen|Carry/i).first().waitFor();
  await screenshot(page, "04-demo-japan-us-transmission.png");
  await noHorizontalOverflow(page, "Japan-US transmission");

  await page.goto(`${baseUrl}/markets?sector=semiconductors&view=structure&demo=1`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Semiconductors/i }).waitFor();
  await screenshot(page, "05-demo-semiconductor-structure.png");

  await page.goto(`${baseUrl}/company/PLTR?fixture=1&view=economics&demo=1`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Palantir/i }).first().waitFor();
  await screenshot(page, "06-demo-company-economics.png");

  await page.goto(`${baseUrl}/valuation/PLTR?view=reverse-dcf&from=demo&demo=1&fixture=1`, { waitUntil: "networkidle" });
  await page.getByText("MARKET-IMPLIED EXPECTATIONS").first().waitFor();
  await screenshot(page, "07-demo-valuation-reverse-dcf.png");

  await page.goto(`${baseUrl}/company/NOTAREALTICKER`, { waitUntil: "networkidle" });
  await page.locator("body").waitFor();
  await screenshot(page, "08-company-failure-or-resolution-state.png");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(`${baseUrl}/demo`, { waitUntil: "networkidle" });
  await mobile.getByText("DETERMINISTIC DEMO").first().waitFor();
  await noHorizontalOverflow(mobile, "Mobile demo dashboard");
  await screenshot(mobile, "09-mobile-demo-dashboard.png");
  await openSearch(mobile, "Atlantis", "10-mobile-search-unsupported.png");
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Phase 6 product polish checks passed; 10 screenshots captured.");
