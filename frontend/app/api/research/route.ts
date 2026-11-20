import { runPythonJson, runtimeError, PythonRuntimeError } from "../../../lib/python-runtime";
import { NextRequest, NextResponse } from "next/server";
import { analyzeValuation, type ValuationOverrides } from "../../../lib/valuation-service";
import { loadResearchSystem } from "../../../lib/research-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function runCompany(command: "resolve" | "analyze" | "open" | "index", ticker?: string, refresh = false) {
  if (ticker && (!/^[A-Za-z0-9 .^=-]{1,100}$/.test(ticker) || ticker.startsWith("-"))) throw new PythonRuntimeError("INVALID_INPUT", "Invalid company query.");
  const args = ["-B", "company_research.py", command, ...(ticker ? [ticker] : []), ...(refresh ? ["--refresh"] : [])];
  const result = await runPythonJson<Record<string, unknown>>(args, 120_000);
  if (!result || typeof result !== "object" || Array.isArray(result) || (command === "resolve" && !result.resolution) || (command === "index" && !Array.isArray(result.recent_research)) || (["open", "analyze"].includes(command) && typeof result.status !== "string")) throw new PythonRuntimeError("INVALID_JSON", "Malformed company research payload.");
  return result;
}

export async function GET(request: NextRequest) {
  const action = request.nextUrl.searchParams.get("action");
  if (action === "valuation-analyze") {
    const ticker = request.nextUrl.searchParams.get("ticker")?.trim();
    if (!ticker) return NextResponse.json({ status: "PROVIDER_ERROR", report: null, meta: { data_state: "UNAVAILABLE", source: "VALIDATION", error: "Ticker is required." } }, { status: 400 });
    const result = await analyzeValuation(ticker, { refresh: request.nextUrl.searchParams.get("refresh") === "1" });
    return NextResponse.json(result, { status: result.status === "PROVIDER_ERROR" ? 502 : 200 });
  }
  if (action?.startsWith("company-")) {
    const ticker = request.nextUrl.searchParams.get("ticker")?.trim();
    const command = action.replace("company-", "") as "resolve" | "open" | "index";
    if (!(["resolve", "open", "index"] as const).includes(command)) return NextResponse.json({ status: "FAILED", errors: ["Unsupported company research action."] }, { status: 400 });
    if (command !== "index" && !ticker) return NextResponse.json({ status: "FAILED", errors: ["Ticker is required."] }, { status: 400 });
    try {
      return NextResponse.json(await runCompany(command, ticker));
    } catch (error) {
      return NextResponse.json({ status: "FAILED", profile: null, runtime_error: runtimeError(error), errors: [runtimeError(error).message] }, { status: 502 });
    }
  }
  const refresh = request.nextUrl.searchParams.get("refresh") === "1";
  const scope = request.nextUrl.searchParams.get("scope") || "full";
  if (action || !["full", "dashboard", "world"].includes(scope)) return NextResponse.json({ status: "FAILED", runtime_error: { code: "UNSUPPORTED_ACTION", message: "Unsupported research action or scope." } }, { status: 400 });
  const result = await loadResearchSystem(refresh);
  const full = result.data;
  return NextResponse.json({ data: scope === "dashboard" ? full.dashboard : scope === "world" ? full.world : full, meta: result.meta });
}

export async function POST(request: NextRequest) {
  let body: { action?: string; ticker?: string; refresh?: boolean; overrides?: ValuationOverrides };
  try {
    body = await request.json() as typeof body;
  } catch {
    return NextResponse.json({ status: "FAILED", errors: ["A JSON request body is required."] }, { status: 400 });
  }
  if (!body || typeof body.ticker !== "string" || !body.ticker.trim() || !["company-analyze", "valuation-analyze"].includes(body.action || "")) {
    return NextResponse.json({ status: "FAILED", errors: ["A supported action and ticker are required."] }, { status: 400 });
  }
  if (body.action === "valuation-analyze") {
    const result = await analyzeValuation(body.ticker, { refresh: Boolean(body.refresh), overrides: body.overrides });
    return NextResponse.json(result, { status: result.status === "PROVIDER_ERROR" ? 502 : 200 });
  }
  try {
    return NextResponse.json(await runCompany("analyze", body.ticker.trim(), Boolean(body.refresh)));
  } catch (error) {
    return NextResponse.json({ status: "FAILED", ticker: body.ticker.trim().toUpperCase(), profile: null, runtime_error: runtimeError(error), errors: [runtimeError(error).message] }, { status: 502 });
  }
}
