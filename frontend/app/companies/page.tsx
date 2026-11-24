import { CompanyResearchIndex } from "../../components/company/CompanyResearchIndex";
import { WatchlistTable } from "../../components/company/WatchlistTable";

export default function CompaniesPage() {
  return <CompanyResearchIndex showBenchmarks={process.env.CHAINSTOX_SHOW_DEV === "1"} lead={<WatchlistTable />} />;
}
