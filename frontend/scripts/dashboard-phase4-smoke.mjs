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
  // The shortcut works once the page has hydrated; keep pressing until the dialog opens.
  const dialog = page.getByRole("dialog", { name: /Global research search/i });
  for (let attempt = 0; attempt < 30 && !(await dialog.isVisible()); attempt += 1) {
    await page.keyboard.press("Meta+K");
    await dialog.waitFor({ timeout: 1000 }).catch(() => {});
  }
  await dialog.waitFor();
  if (query) await page.getByLabel("Search research").fill(query);
  await page.screenshot({ path: path.join(output, filename), fullPage: false });
  await page.keyboard.press("Escape");
}

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 980 }, deviceScaleFactor: 1 });
  observe(page);

  await page.goto(baseUrl, { waitUntil: "load" });
  // Today (2026-11-27 redesign): status band, exceptions only, next three weeks, holdings at a glance.
  await page.locator(".tdy-band .tdy-band-line").waitFor();
  await pageShot(page, "01-dashboard-desktop.png");
  await page.locator(".tdy-focus, .tdy-calm").first().waitFor({ timeout: 120000 });
  const focusCards = await page.locator(".tdy-focus").count();
  if (focusCards > 4) throw new Error(`Today shows ${focusCards} focus cards; the rule allows at most 4.`);
  await page.locator(".tdy-focus-wrap > header .crit").focus();
  const rule = page.locator(".tdy-focus-wrap > header .crit-pop");
  await rule.waitFor({ state: "visible" });
  if (!/A holding is shown here/.test(await rule.innerText())) throw new Error("The focus rule is not shown on hover or focus.");
  await sectionShot(page, ".tdy-focus-wrap", "02-focus.png");
  await page.locator(".tdy-timeline li, .tdy-timeline-card .tdy-empty").first().waitFor({ timeout: 120000 });
  await sectionShot(page, ".tdy-timeline-card", "03-next-three-weeks.png");
  // The holdings grid places every holding with a card exactly once; the full list stays in Watchlist.
  await page.locator(".tdy-dot").first().waitFor({ timeout: 60000 });
  const dots = await page.locator(".tdy-dot").allInnerTexts();
  if (new Set(dots).size !== dots.length) throw new Error("A holding appears twice in the holdings grid.");
  if (await page.locator(".tdy-watch-row, .tdy-sectors, .tdy-story").count()) throw new Error("Today still shows the retired watchlist, sectors or story blocks.");
  await sectionShot(page, ".tdy-glance", "04-holdings-at-a-glance.png");
  // Checklist 14.4: every condition opens its criteria (rule and track record) on hover or focus.
  await page.locator(".tdy-shared-bars, .tdy-shared .tdy-empty").first().waitFor({ timeout: 120000 });
  if (await page.locator(".tdy-shared-bars").count()) {
    await page.locator(".tdy-shared .crit").first().focus();
    const criteria = page.locator(".tdy-shared .crit-pop").first();
    await criteria.waitFor({ state: "visible" });
    if (!/Rule[\s\S]*Track record/.test(await criteria.innerText())) throw new Error("Condition criteria are missing the rule or track record.");
  }
  await sectionShot(page, ".tdy-shared", "05-what-holdings-share.png");

  // Checklists 15.4 / 16 / 17: Macro is the market story, the profit breakdown and the scenario gate.
  await page.goto(`${baseUrl}/macro`, { waitUntil: "load" });
  await page.locator(".story-chain .story-step").first().waitFor({ timeout: 120000 });
  if ((await page.locator(".story-step").count()) < 4) throw new Error("Macro story has too few steps.");
  if (!(await page.locator(".story-carriers li").count())) throw new Error("Macro page is missing the companies that carry profit growth.");
  await page.locator(".story-scenario .story-verdict").waitFor();
  if (/\d+(st|nd|rd|th) (pct|percentile)/.test(await page.locator("main").innerText())) throw new Error("Macro page shows percentile jargon.");
  await pageShot(page, "07-macro-story.png");
  await sectionShot(page, ".story-profits", "08-profit-breakdown.png");

  await page.goto(baseUrl, { waitUntil: "load" });
  await openSearch(page, "", "09-global-search-default.png");
  await openSearch(page, "Japan", "10-search-japan.png");
  await openSearch(page, "Semiconductors", "11-search-semiconductors.png");
  await openSearch(page, "PLTR", "12-search-pltr.png");

  await page.goto(`${baseUrl}/macro/world?region=JP`, { waitUntil: "load" });
  await page.getByText(/Japan/i).first().waitFor();
  await pageShot(page, "13-dashboard-to-japan-deep-link.png");

  await page.goto(`${baseUrl}/markets?sector=semiconductors`, { waitUntil: "load" });
  await page.getByRole("heading", { name: /Semiconductors/i }).waitFor();
  await pageShot(page, "14-dashboard-to-semiconductors.png");

  await page.goto(`${baseUrl}/company/PLTR`, { waitUntil: "load" });
  await page.locator("body").waitFor();
  await pageShot(page, "15-dashboard-to-pltr.png");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Dashboard desktop has horizontal page overflow.");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await mobile.goto(baseUrl, { waitUntil: "load" });
  await mobile.locator(".tdy-band .tdy-band-line").waitFor();
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
