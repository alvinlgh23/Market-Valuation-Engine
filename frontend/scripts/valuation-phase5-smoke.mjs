import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/valuation-phase5");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];

function observe(page) {
  page.setDefaultTimeout(10_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

async function shot(page, name, selector) {
  if (selector) {
    const locator = page.locator(selector).first();
    await locator.scrollIntoViewIfNeeded();
    await locator.screenshot({ path: path.join(output, name) });
    return;
  }
  await page.screenshot({ path: path.join(output, name), fullPage: false });
}

async function goto(page, url, heading) {
  await page.goto(`${baseUrl}${url}`, { waitUntil: "networkidle" });
  if (heading) await page.getByRole("heading", typeof heading === "string" ? { name: heading, exact: true } : { name: heading }).first().waitFor();
}

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 980 }, deviceScaleFactor: 1 });
  observe(page);

  await goto(page, "/valuation", /Intrinsic valuation/i);
  await shot(page, "01-valuation-search.png");

  await goto(page, "/valuation/MSFT?fixture=1", /Microsoft/i);
  await shot(page, "02-msft-valuation-snapshot.png");
  await shot(page, "03-fair-value-range.png", ".valuation-range-surface");
  await goto(page, "/valuation/MSFT?view=economics-model&fixture=1", /Observed economics vs model assumptions/i);
  await shot(page, "04-economics-vs-model.png", ".valuation-triad");
  await shot(page, "05-economics-model-market-triad.png", ".valuation-triad-table");
  await goto(page, "/valuation/MSFT?view=dcf&fixture=1", /Operating base and period consistency/i);
  await shot(page, "06-msft-dcf-workspace.png");
  await shot(page, "07-historical-base.png", ".valuation-section");
  await shot(page, "08-fcff-reconciliation.png", ".fcff-reconciliation");
  await shot(page, "09-forecast.png", ".forecast-table");
  await shot(page, "10-discount-rate-inspector.png", ".discount-terminal");
  await shot(page, "11-terminal-value.png", ".discount-terminal");
  await shot(page, "12-scenario-comparison.png", ".scenario-table");
  await goto(page, "/valuation/MSFT?view=reverse-dcf&fixture=1", /Converged/i);
  await shot(page, "13-reverse-dcf.png", ".reverse-dcf-workspace");
  await goto(page, "/valuation/PLTR?view=reverse-dcf&fixture=1", /above what even 50% first-year sales growth can justify/i);
  await shot(page, "14-reverse-dcf-no-solution.png", ".reverse-dcf-workspace");
  await goto(page, "/valuation/MSFT?view=sensitivity&fixture=1", /WACC × Terminal Growth/i);
  await shot(page, "15-sensitivity-matrix.png", ".sensitivity-workspace");
  await goto(page, "/valuation/MSFT?view=sensitivity&cell=1-2&fixture=1", /WACC × Terminal Growth/i);
  await shot(page, "16-sensitivity-cell-inspector.png", ".sensitivity-inspector");
  await goto(page, "/valuation/MSFT?view=validation&fixture=1", /Passed/i);
  await shot(page, "17-validation-workspace.png", ".validation-workspace");
  await goto(page, "/valuation/MSFT?view=evidence&fixture=1", /Good/i);
  await shot(page, "18-data-quality-fallback-inspector.png", ".valuation-workspace-page");
  await goto(page, "/valuation/GOOG?fixture=1", /Alphabet/i);
  await shot(page, "19-goog-valuation.png");
  // The company page keeps loading its judgment card, so wait for the page, not for a quiet network.
  await page.goto(`${baseUrl}/company/PLTR?fixture=1`, { waitUntil: "load", timeout: 60000 });
  await page.getByRole("heading", { name: "Palantir Technologies", exact: true }).first().waitFor();
  await page.getByRole("button", { name: /Valuation & sandbox/i }).first().click();   // the company page opens valuation from this button
  await page.waitForURL(/\/valuation\/PLTR/);
  await page.getByRole("heading", { name: /Palantir/ }).first().waitFor();
  await shot(page, "20-pltr-valuation-from-company-economics.png");
  // Banks load the card's return-on-equity reading, so wait for the page rather than a quiet network.
  await page.goto(`${baseUrl}/valuation/JPM?fixture=1`, { waitUntil: "load", timeout: 60000 });
  await page.getByRole("heading", { name: /JPMorgan/i }).first().waitFor({ timeout: 60000 });
  await shot(page, "21-framework-required-state.png", ".valuation-framework-state");
  await goto(page, "/valuation/MSFT?view=report&fixture=1", /MSFT intrinsic valuation/i);
  await shot(page, "22-full-report.png");

  const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (desktopOverflow) throw new Error("Valuation desktop has horizontal page overflow.");
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  await goto(mobile, "/valuation/MSFT?fixture=1", /Microsoft/i);
  const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (mobileOverflow) throw new Error("Valuation mobile snapshot has horizontal page overflow.");
  await mobile.screenshot({ path: path.join(output, "23-mobile-valuation-snapshot.png"), fullPage: false });
  await goto(mobile, "/valuation/PLTR?view=reverse-dcf&fixture=1", /above what even 50% first-year sales growth can justify/i);
  await mobile.screenshot({ path: path.join(output, "24-mobile-reverse-dcf.png"), fullPage: false });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Valuation Phase 5 checks passed; 24 screenshots captured.");
