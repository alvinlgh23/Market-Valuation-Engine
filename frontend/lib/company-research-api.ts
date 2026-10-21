import type { CompanyEconomicsPayload } from "./company-economics-types";

export type CompanyResearchState = "NOT_ANALYZED" | "ANALYZING" | "AVAILABLE" | "PARTIAL" | "INSUFFICIENT_DATA" | "UNSUPPORTED" | "STALE" | "FAILED";

export interface SecurityResolution {
  requested: string;
  ticker: string;
  company_name: string;
  exchange: string;
  currency: string;
  sector: string;
  industry: string;
  quote_type: string;
  business_description: string;
  country: string;
  security_type: string;
  supported: boolean;
  research_state: CompanyResearchState;
  reason: string;
  provider: string;
  as_of: string;
  last_analyzed: string | null;
  error: string | null;
}

export interface RecentCompanyResearch {
  ticker: string;
  name: string;
  last_analyzed: string;
  research_state: CompanyResearchState;
  archetype: string;
  classification_confidence: string;
}

export interface CompanyResolveResponse {
  status: string;
  resolution: SecurityResolution;
  recent_research: RecentCompanyResearch[];
}

export interface CompanyAnalysisResponse {
  status: CompanyResearchState;
  ticker: string;
  profile: CompanyEconomicsPayload | null;
  resolution?: SecurityResolution;
  last_analyzed?: string | null;
  source?: string;
  errors?: string[];
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json() as T & { errors?: string[] };
  if (!response.ok) throw new Error(payload.errors?.[0] ?? `Research bridge returned ${response.status}`);
  return payload;
}

export async function resolveCompany(query: string): Promise<CompanyResolveResponse> {
  const response = await fetch(`/api/research?action=company-resolve&ticker=${encodeURIComponent(query)}`, { cache: "no-store" });
  return readJson<CompanyResolveResponse>(response);
}

export async function openCompany(ticker: string): Promise<CompanyAnalysisResponse> {
  const response = await fetch(`/api/research?action=company-open&ticker=${encodeURIComponent(ticker)}`, { cache: "no-store" });
  return readJson<CompanyAnalysisResponse>(response);
}

export async function analyzeCompany(ticker: string, refresh = false): Promise<CompanyAnalysisResponse> {
  const response = await fetch("/api/research", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ action: "company-analyze", ticker, refresh })
  });
  return readJson<CompanyAnalysisResponse>(response);
}

export async function recentCompanyResearch(): Promise<RecentCompanyResearch[]> {
  const response = await fetch("/api/research?action=company-index", { cache: "no-store" });
  const payload = await readJson<{ recent_research: RecentCompanyResearch[] }>(response);
  return payload.recent_research ?? [];
}
