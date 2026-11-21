import { CompanyResearchIndex } from "../../components/company/CompanyResearchIndex";
import { WatchlistTable } from "../../components/company/WatchlistTable";

export default function CompaniesPage() {
  return <CompanyResearchIndex showBenchmarks={process.env.NODE_ENV !== "production"} lead={<WatchlistTable />} />;
}
