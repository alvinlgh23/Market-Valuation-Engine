import { CompanyResearchGateway } from "../../../components/company/CompanyResearchGateway";
import { CompanyResearchPage } from "../../../components/company/CompanyResearchPage";
import type { CompanyWorkspaceKind } from "../../../components/company/CompanyWorkspaces";
import { adaptCompanyEconomics } from "../../../lib/companyEconomicsAdapter";
import { getCompanyResearchFixture } from "../../../lib/data-provider";

export const dynamic = "force-dynamic";

export default async function CompanyPage({
  params,
  searchParams
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ fixture?: string; workspace?: string; view?: string; node?: string }>;
}) {
  const { ticker } = await params;
  const query = await searchParams;
  const valuationViews = ["valuation", "assumptions", "dcf", "reverse-dcf", "sensitivity", "validation"];
  const routeWorkspace = query.workspace ?? (query.view === "economics" ? "economics" : query.view === "positioning" || query.view === "thesis" ? "thesis" : query.view === "financials" ? "financials" : query.view && valuationViews.includes(query.view) ? "valuation" : query.view === "evidence" ? "evidence" : null);
  const initialWorkspace = (["economics", "valuation", "thesis", "financials", "evidence"] as const).find((item) => item === routeWorkspace) ?? null;
  if (query.fixture === "1") {
    const fixture = getCompanyResearchFixture(ticker);
    if (fixture) return <CompanyResearchPage company={adaptCompanyEconomics(fixture)} dataState="FIXTURE" initialWorkspace={initialWorkspace} initialNode={query.node ?? null} />;
  }
  return <CompanyResearchGateway ticker={ticker} initialWorkspace={initialWorkspace as CompanyWorkspaceKind | null} initialNode={query.node ?? null} />;
}
