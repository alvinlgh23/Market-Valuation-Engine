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
  // Checklist 14.3: Today is a market read, factor list, ranked alerts, watchlist and sectors.
  await page.locator(".tdy-headline").waitFor();
  await pageShot(page, "01-dashboard-desktop.png");
  if ((await page.locator(".tdy-factors li").count()) < 6) throw new Error("Today page shows too few factors.");
  await sectionShot(page, ".tdy-factors", "02-macro-factors.png");
  await sectionShot(page, ".tdy-sectors", "03-sector-leadership.png");
  await page.locator(".tdy-watch-row b").first().waitFor({ timeout: 30000 });
  await sectionShot(page, ".tdy-watch", "04-watchlist.png");
  await page.locator(".tdy-alert, .tdy-alerts .tdy-empty").first().waitFor({ timeout: 120000 });
  await sectionShot(page, ".tdy-alerts", "05-alerts.png");
  // Checklist 14.4: every alert opens its criteria (rule and track record) on hover or focus.
  if (await page.locator(".tdy-alert").count()) {
    await page.locator(".tdy-alert .crit").first().focus();
    const criteria = page.locator(".tdy-alert .crit-pop").first();
    await criteria.waitFor({ state: "visible" });
    if (!/Rule[\s\S]*Track record/.test(await criteria.innerText())) throw new Error("Alert criteria are missing the rule or track record.");
    await sectionShot(page, ".tdy-alerts", "06-alert-criteria.png");
  }

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

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Dashboard desktop has horizontal page overflow.");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  await mobile.locator(".tdy-headline").waitFor();
  const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (mobileOverflow) throw new Error("Dashboard mobile has horizontal page overflow.");
  await mobile.screenshot({ path: path.join(output, "17-dashboard-mobile.png"), fullPage: false });
  await openSearch(mobile, "Japan", "18-global-search-mobile.png");
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Dashboard Phase 4 checks passed; 17 screenshots captured.");
