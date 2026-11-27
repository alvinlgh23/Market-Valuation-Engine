import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.MACRO_WORLD_BASE_URL ?? "http://127.0.0.1:3000";
const artifacts = path.resolve("artifacts/macro-world");
await fs.mkdir(artifacts, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];
function observe(page) {
  page.setDefaultTimeout(10_000);
  page.on("console", (message) => message.type() === "error" && errors.push(`console: ${message.text()}`));
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  observe(page);
  let response = await page.goto(`${baseUrl}/macro/world`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Macro route returned ${response?.status()}`);
  await page.getByRole("heading", { name: "World Macro Map" }).waitFor();
  // Singapore was removed on 2026-11-22 (owner decision: global audience); four modelled economies remain.
  if ((await page.locator(".macro-map-marker").count()) !== 5) throw new Error("Expected four supported map markers plus one unsupported marker");
  if ((await page.locator(".macro-region-index > button").count()) !== 4) throw new Error("Expected four modelled economy cards");
  await page.screenshot({ path: path.join(artifacts, "macro-world-map.png"), fullPage: true });

  let japanDetail = "";
  const regions = [
    ["United States", "us-selected.png"],
    ["Japan", "japan-selected.png"],
    ["South Korea", "south-korea-selected.png"],
    ["Euro Area", "euro-area-selected.png"],
  ];
  for (const [name, file] of regions) {
    await page.getByRole("button", { name: `Open ${name} macro profile` }).press("Enter");
    await page.getByRole("complementary", { name: `${name} macro profile` }).waitFor();
    await page.screenshot({ path: path.join(artifacts, file), fullPage: true });
    if (name === "Japan") {
      await page.getByRole("button", { name: /^Policy / }).click();
      await page.waitForURL(/detail=/);
      japanDetail = new URL(page.url()).searchParams.get("detail");
    }
    if (name === "South Korea") {
      await page.getByRole("button", { name: /Policy NOT AVAILABLE/ }).click();
      await page.getByText("No Bank of Korea policy model is integrated.").waitFor();
    }
    await page.keyboard.press("Escape");
  }

  const unavailable = page.getByRole("button", { name: "Brazil not available" });
  await unavailable.focus();
  await page.screenshot({ path: path.join(artifacts, "unsupported-country-hover.png"), fullPage: true });
  await unavailable.click();
  await page.getByRole("status").getByText("NOT AVAILABLE", { exact: true }).waitFor();

  // The Mechanism Graph was replaced by "Channels -> holdings" (2026-11-27): each channel with the holdings it moved.
  await page.getByRole("tab", { name: "Channels → holdings" }).click();
  await page.getByRole("heading", { name: "Channels → your holdings" }).waitFor();
  if ((await page.locator(".ch-row").count()) !== 4) throw new Error("Expected four cross-border channels");
  await page.locator(".ch-bars a, .ch-quiet").first().waitFor({ timeout: 60000 });
  await page.screenshot({ path: path.join(artifacts, "channels-to-holdings.png"), fullPage: true });
  await page.getByRole("tab", { name: "World & Channels" }).click();
  await page.locator(".macro-channel-card").filter({ hasText: "Yen carry" }).click();
  await page.getByRole("complementary", { name: /Yen carry → US risk assets transmission detail/ }).waitFor();
  await page.getByText("A transmission channel is not proof").waitFor();
  await page.screenshot({ path: path.join(artifacts, "japan-us-edge-selected.png"), fullPage: true });

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=JP&detail=${japanDetail}`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "Japan macro profile" }).waitFor();
  await page.locator(".macro-component-nav button.active").filter({ hasText: /^Policy/ }).waitFor();
  await page.goBack();
  await page.getByRole("complementary", { name: /Yen carry → US risk assets transmission detail/ }).waitFor();
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  response = await mobile.goto(`${baseUrl}/macro/world`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Mobile macro route returned ${response?.status()}`);
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Mobile macro page has horizontal overflow");
  await mobile.getByRole("heading", { name: "Economies we model" }).waitFor();
  await mobile.screenshot({ path: path.join(artifacts, "mobile-macro-map.png"), fullPage: true });
  await mobile.getByRole("button", { name: "Open Japan macro profile" }).click();
  await mobile.getByRole("complementary", { name: "Japan macro profile" }).waitFor();
  await mobile.keyboard.press("Escape");
  await mobile.getByRole("complementary", { name: "Japan macro profile" }).waitFor({ state: "detached" });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Macro world checks passed; 9 screenshots captured.");
