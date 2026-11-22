import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/dashboard-phase4");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(10_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

async function sectionShot(page, selector, filename) {
  const locator = page.locator(selector).first();
  await locator.scrollIntoViewIfNeeded();
  await locator.screenshot({ path: path.join(output, filename) });
}

async function pageShot(page, filename) {
  await page.screenshot({ path: path.join(output, filename), fullPage: false });
}

async function openSearch(page, query, filename) {
  await page.keyboard.press("Meta+K");
  await page.getByRole("dialog", { name: /Global research search/i }).waitFor();
  if (query) await page.getByLabel("Search research").fill(query);
  await page.screenshot({ path: path.join(output, filename), fullPage: false });
  await page.keyboard.press("Escape");
}

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 980 }, deviceScaleFactor: 1 });
  observe(page);

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator(".today-regime h1").waitFor();
  await pageShot(page, "01-dashboard-desktop.png");
  await sectionShot(page, ".what-changed-panel", "02-what-changed.png");
  await sectionShot(page, ".priority-panel", "03-research-priority.png");
  await sectionShot(page, ".tension-panel", "04-cross-system-signals.png");
  await sectionShot(page, ".macro-snapshot-panel", "05-global-macro-snapshot.png");
  await sectionShot(page, ".leadership-panel", "06-market-leadership.png");
  await sectionShot(page, ".recent-research-panel", "07-recent-company-research.png");
  await sectionShot(page, ".operations-row", "08-data-freshness-watch-conditions.png");

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await openSearch(page, "", "09-global-search-default.png");
  await openSearch(page, "Japan", "10-search-japan.png");
  await openSearch(page, "Semiconductors", "11-search-semiconductors.png");
  await openSearch(page, "PLTR", "12-search-pltr.png");

  await page.goto(`${baseUrl}/macro/world?region=JP`, { waitUntil: "networkidle" });
  await page.getByText(/Japan/i).first().waitFor();
  await pageShot(page, "13-dashboard-to-japan-deep-link.png");

  await page.goto(`${baseUrl}/markets?sector=semiconductors`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Semiconductors/i }).waitFor();
  await pageShot(page, "14-dashboard-to-semiconductors.png");

  await page.goto(`${baseUrl}/company/PLTR`, { waitUntil: "networkidle" });
  await page.locator("body").waitFor();
  await pageShot(page, "15-dashboard-to-pltr.png");

  await page.goto(`${baseUrl}/brief`, { waitUntil: "networkidle" });
  await page.locator("body").waitFor();
  await pageShot(page, "16-full-market-brief.png");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Dashboard desktop has horizontal page overflow.");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  await mobile.locator(".today-regime h1").waitFor();
  const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (mobileOverflow) throw new Error("Dashboard mobile has horizontal page overflow.");
  await mobile.screenshot({ path: path.join(output, "17-dashboard-mobile.png"), fullPage: false });
  await openSearch(mobile, "Japan", "18-global-search-mobile.png");
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Dashboard Phase 4 checks passed; 18 screenshots captured.");
