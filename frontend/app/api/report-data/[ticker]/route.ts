import { NextResponse } from "next/server";
import { loadReportData } from "../../../../lib/report-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// The stored figures behind the research note, as JSON for the Financials and Economic map tabs (same data as the PDF).
// The valuation report is cut to the fields those tabs read; no price chart is fetched.
export async function GET(_request: Request, context: { params: Promise<unknown> }) {
  const raw = (await context.params) as { ticker?: unknown };
  const data = await loadReportData(String(raw?.ticker ?? ""), { chart: false });
  if (!data) return NextResponse.json({ error: "No stored research for this company." }, { status: 404 });
  const v = data.valuation;
  const valuation = v ? {
    company: { currency: v.company.currency, name: v.company.name, as_of: v.company.as_of, current_market_price: v.company.current_market_price },
    historical_base: { diluted_share_history: v.historical_base?.diluted_share_history ?? [] },
    fair_value: v.fair_value ? { method: v.fair_value.method, reverse_dcf: v.fair_value.reverse_dcf } : null,
    reverse_dcf: v.reverse_dcf ? { required_5y_revenue_cagr: v.reverse_dcf.required_5y_revenue_cagr } : null,
  } : null;
  return NextResponse.json({ ...data, valuation }, { headers: { "Cache-Control": "no-store" } });
}
