import { ValuationResearchPage } from "../../../components/valuation/ValuationResearchPage";
import { getValuationCompany, getValuationReport, type ValuationView } from "../../../lib/valuation-research";
import { analyzeValuation } from "../../../lib/valuation-service";
import { ResearchShell } from "../../../components/research/ResearchShell";
import Link from "next/link";

export default async function ValuationCompanyPage({
  params,
  searchParams
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ view?: string; from?: string; cell?: string; fixture?: string; refresh?: string }>;
}) {
  const { ticker } = await params;
  const query = await searchParams;
  const fixture = query.fixture === "1" ? getValuationReport(ticker) : null;
  const result = fixture ? null : await analyzeValuation(ticker, { refresh: query.refresh === "1" });
  const report = fixture || result?.report;
  if (!report) return <ResearchShell active="valuation" ticker={ticker.toUpperCase()} dataState="FAILED"><section className="valuation-framework-state"><span>VALUATION / {ticker.toUpperCase()} · {result?.status}</span><h1>Valuation unavailable</h1><p>{result?.meta.error_code} {result?.meta.error || "The security could not be resolved or required financial statement coverage is incomplete."}</p><Link href={`/company/${ticker.toUpperCase()}`}>Open available Company Economics →</Link></section></ResearchShell>;
  const allowed: ValuationView[] = ["overview", "economics-model", "dcf", "assumptions", "reverse-dcf", "sensitivity", "validation", "evidence", "report"];
  const view = allowed.includes(query.view as ValuationView) ? query.view as ValuationView : "overview";
  const dataState = fixture ? "FIXTURE" : result?.meta.data_state === "UNAVAILABLE" ? "FAILED" : result?.meta.data_state || "FAILED";
  return <ValuationResearchPage report={report} company={fixture ? getValuationCompany(ticker) : null} view={view} from={query.from} cell={query.cell} dataState={dataState} />;
}
