import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// The downloadable research note: prints /report/[ticker] (same data as the site) to an A4 PDF.
export async function GET(request: NextRequest, context: { params: Promise<unknown> }) {
  const raw = (await context.params) as { ticker?: unknown };
  const ticker = String(raw?.ticker ?? "").trim().toUpperCase();
  if (!/^[A-Z0-9.^=-]{1,12}$/.test(ticker) || ticker.startsWith("-")) return NextResponse.json({ error: "Invalid ticker." }, { status: 400 });
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const response = await page.goto(`${request.nextUrl.origin}/report/${encodeURIComponent(ticker)}`, { waitUntil: "load", timeout: 120_000 });
    if (!response || !response.ok()) return NextResponse.json({ error: `No research note for ${ticker}.` }, { status: response?.status() === 404 ? 404 : 502 });
    // The page streams in behind the app's loading placeholder: wait for the note itself and its fonts before printing.
    await page.waitForSelector(".rn-doc", { state: "visible", timeout: 120_000 });
    await page.evaluate(() => document.fonts.ready);
    await page.emulateMedia({ media: "print" });
    const pdf = await page.pdf({
      format: "A4", printBackground: true, preferCSSPageSize: true,
      displayHeaderFooter: true, headerTemplate: "<span></span>",
      footerTemplate: `<div style="width:100%;padding:0 11mm;font-size:6.5pt;color:#5f6873;font-family:Arial,sans-serif;display:flex;justify-content:space-between;border-top:0.5px solid #c9d0d8;padding-top:3px"><span>CHAINSTOX Equity Research · ${ticker}</span><span>See important disclosures at the end of this report. Not investment advice.</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`,
    });
    const day = new Date().toISOString().slice(0, 10);
    return new NextResponse(Buffer.from(pdf), {
      headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="CHAINSTOX_${ticker}_${day}.pdf"`, "Cache-Control": "no-store" },
    });
  } finally {
    await browser.close();
  }
}
