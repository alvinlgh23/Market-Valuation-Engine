import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.CHAINSTOX_BASE_URL || "http://127.0.0.1:3000";
const output = path.resolve("artifacts/universal-company");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });

async function capture(name) {
  await page.screenshot({ path: path.join(output, name), fullPage: false });
}

await page.goto(`${baseUrl}/companies`, { waitUntil: "load" });
await page.locator("#company-index-ticker").fill("AMD");
await capture("01-search-amd.png");

const preview = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
const previewPage = await preview.newPage();
await previewPage.route("**/api/research?action=company-open&ticker=AMD", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ status: "NOT_ANALYZED", ticker: "AMD", profile: null }) }));
await previewPage.route("**/api/research?action=company-resolve&ticker=AMD", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ status: "OK", recent_research: [], resolution: { requested: "AMD", ticker: "AMD", company_name: "Advanced Micro Devices", exchange: "Nasdaq", currency: "USD", sector: "Technology", industry: "Semiconductors", quote_type: "EQUITY", business_description: "", country: "United States", security_type: "EQUITY", supported: true, research_state: "NOT_ANALYZED", reason: "Supported operating security resolved from structured provider metadata.", provider: "SEC submissions and Company Facts", as_of: "2026-08-06", last_analyzed: null, error: null } }) }));
await previewPage.route("**/api/research", async (route) => {
  if (route.request().method() !== "POST") return route.continue();
  await new Promise((resolve) => setTimeout(resolve, 8_000));
  return route.fulfill({ contentType: "application/json", body: JSON.stringify({ status: "FAILED", ticker: "AMD", profile: null, errors: ["Screenshot-only delayed response"] }) });
});
await previewPage.goto(`${baseUrl}/company/AMD`, { waitUntil: "load" });
await previewPage.getByText("COMPANY RESEARCH HAS NOT YET BEEN GENERATED").waitFor();
await previewPage.screenshot({ path: path.join(output, "02-resolved-amd-before-analysis.png") });
await previewPage.getByRole("button", { name: /Analyze Company/ }).click();
await previewPage.getByText("Collecting financial data").waitFor();
await previewPage.screenshot({ path: path.join(output, "03-analyzing-amd.png") });
await preview.close();

await page.goto(`${baseUrl}/company/AMD`, { waitUntil: "load" });
await page.locator(".company-details > summary").click();   // checklist 9.4: the stored profile is folded
await page.getByText("WHAT IS MISSING").waitFor();   // checklist 11.6: plain-language gap
await capture("04-amd-company-snapshot.png");
await page.getByRole("button", { name: /^Economic map$/ }).click();
await page.locator(".research-workspace-layer").waitFor();
await capture("05-amd-economic-map.png");

for (const [ticker, filename] of [["CRM", "06-crm-company-snapshot.png"], ["BAC", "07-bac-company-snapshot.png"], ["WMT", "08-wmt-company-snapshot.png"]]) {
  await page.goto(`${baseUrl}/company/${ticker}?fixture=1`, { waitUntil: "load" });
  await page.locator(".snapshot-identity").waitFor();
  await capture(filename);
}

const unsupported = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
const unsupportedPage = await unsupported.newPage();
await unsupportedPage.route("**/api/research?action=company-open&ticker=SPY", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ status: "NOT_ANALYZED", ticker: "SPY", profile: null }) }));
await unsupportedPage.route("**/api/research?action=company-resolve&ticker=SPY", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ status: "OK", recent_research: [], resolution: { requested: "SPY", ticker: "SPY", company_name: "SPDR S&P 500 ETF Trust", exchange: "NYSE Arca", currency: "USD", sector: "", industry: "Exchange Traded Fund", quote_type: "ETF", business_description: "", country: "United States", security_type: "ETF", supported: false, research_state: "UNSUPPORTED", reason: "Portfolio and holdings research is required; Company Economics is not applied to pooled vehicles.", provider: "Structured company provider", as_of: "2026-08-06", last_analyzed: null, error: null } }) }));
await unsupportedPage.goto(`${baseUrl}/company/SPY`, { waitUntil: "load" });
await unsupportedPage.getByText("SPECIALIZED FRAMEWORK REQUIRED").waitFor();
await unsupportedPage.screenshot({ path: path.join(output, "09-unsupported-etf.png") });
await unsupported.close();

const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
await mobile.goto(`${baseUrl}/companies`, { waitUntil: "load" });
const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
if (overflow > 1) throw new Error(`Company index has ${overflow}px horizontal overflow on mobile.`);

await browser.close();
console.log("Universal company browser checks passed; nine screenshots captured.");
