import { notFound } from "next/navigation";
import { ResearchNote } from "../../../components/report/ResearchNote";
import { loadReportData } from "../../../lib/report-data";

export const dynamic = "force-dynamic";

// The research note as a page; /api/report/[ticker] prints this page to the downloadable PDF.
export default async function ReportPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const data = await loadReportData(ticker);
  if (!data) notFound();
  return <ResearchNote data={data} />;
}
