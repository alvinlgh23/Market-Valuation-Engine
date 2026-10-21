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
  if ((await page.locator(".macro-map-marker").count()) !== 6) throw new Error("Expected five supported map markers plus one unsupported marker");
  if ((await page.locator(".macro-region-index > button").count()) !== 5) throw new Error("Expected five supported economy list rows");
  await page.screenshot({ path: path.join(artifacts, "macro-world-map.png"), fullPage: true });

  const regions = [
    ["United States", "us-selected.png"],
    ["Japan", "japan-selected.png"],
    ["Singapore", "singapore-selected.png"],
    ["South Korea", "south-korea-selected.png"],
    ["Euro Area", "euro-area-selected.png"],
  ];
  for (const [name, file] of regions) {
    await page.getByRole("button", { name: `Open ${name} macro profile` }).press("Enter");
    await page.getByRole("complementary", { name: `${name} macro profile` }).waitFor();
    await page.screenshot({ path: path.join(artifacts, file), fullPage: true });
    if (name === "Singapore") {
      await page.getByRole("button", { name: /FX/ }).click();
      await page.getByText("Shadow S$NEER basket").waitFor();
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

  await page.getByRole("tab", { name: "Transmission" }).click();
  await page.getByRole("heading", { name: "Cross-border transmission" }).waitFor();
  await page.screenshot({ path: path.join(artifacts, "transmission-mode.png"), fullPage: true });
  await page.getByRole("button", { name: /JP → US/ }).click();
  await page.getByRole("complementary", { name: /Yen carry → US risk assets transmission detail/ }).waitFor();
  await page.getByText("A transmission channel is not proof").waitFor();
  await page.screenshot({ path: path.join(artifacts, "japan-us-edge-selected.png"), fullPage: true });

  await page.goto(`${baseUrl}/macro/world?mode=regions&region=SG&detail=currency`, { waitUntil: "networkidle" });
  await page.getByRole("complementary", { name: "Singapore macro profile" }).waitFor();
  await page.getByText("Shadow S$NEER basket").waitFor();
  await page.goBack();
  await page.getByRole("complementary", { name: /Yen carry → US risk assets transmission detail/ }).waitFor();
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  observe(mobile);
  response = await mobile.goto(`${baseUrl}/macro/world`, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Mobile macro route returned ${response?.status()}`);
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error("Mobile macro page has horizontal overflow");
  await mobile.getByText("Supported economy index").waitFor();
  await mobile.screenshot({ path: path.join(artifacts, "mobile-macro-map.png"), fullPage: true });
  await mobile.getByRole("button", { name: "Open Singapore macro profile" }).click();
  await mobile.getByRole("complementary", { name: "Singapore macro profile" }).waitFor();
  await mobile.keyboard.press("Escape");
  await mobile.getByRole("complementary", { name: "Singapore macro profile" }).waitFor({ state: "detached" });
  await mobile.close();
} finally {
  await browser.close();
}

if (errors.length) throw new Error(errors.join("\n"));
console.log("Macro world checks passed; 10 requested screenshots captured.");
