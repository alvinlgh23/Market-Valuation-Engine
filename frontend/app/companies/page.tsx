import { CompanyResearchIndex } from "../../components/company/CompanyResearchIndex";

export default function CompaniesPage() {
  return <CompanyResearchIndex showBenchmarks={process.env.NODE_ENV !== "production"} />;
}
