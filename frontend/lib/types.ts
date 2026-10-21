export type StatusTone = "normal" | "watch" | "triggered" | "positive" | "negative" | "muted";

export interface TerminalTableRow {
  [key: string]: string | number;
}

export interface WatchItem {
  label: string;
  value: string;
  change?: string;
  threshold?: string;
  status: string;
  why: string;
  tone: StatusTone;
}

export interface OverviewBriefing {
  asOf: string;
  market: string;
  dataStatus: string;
  reportId: string;
  generated: string;
  sessionId: string;
  cacheAge: string;
  build: string;
  fedState: string;
  terminalStatus: string;
  structure: string;
  summary: string;
  mainTension: string;
  whatChanged: string[];
  watch: WatchItem[];
  commands: string[];
  recentReports: Array<{ id: string; title: string; time: string; status: string }>;
  researchLog: Array<{ time: string; event: string; impact: string }>;
}

export interface CompanyReport {
  ticker: string;
  name: string;
  venue: string;
  currency: string;
  updated: string;
  structuralRead: string;
  summary: string;
  businessEvidence: TerminalTableRow[];
  valuation: TerminalTableRow[];
  positioning: TerminalTableRow[];
  chart: Array<{ period: string; price: number; revenue: number; eps: number; fcf: number }>;
  supportingThesis: string[];
  challengingThesis: string[];
  changeView: string[];
  dataQuality: { source: string; coverage: string; refreshed: string };
}

export interface PrivateAiCompanyReport {
  company: string;
  command: string;
  updated: string;
  dataQuality: string;
  analysisMode: string;
  summary: string;
  scale: TerminalTableRow[];
  adoption: TerminalTableRow[];
  product: TerminalTableRow[];
  infrastructure: TerminalTableRow[];
  capital: TerminalTableRow[];
  valuation: TerminalTableRow[];
  competitors: TerminalTableRow[];
  strengthen: string[];
  weaken: string[];
  finalInterpretation: string;
}

export interface FragilityReport {
  title: string;
  headline: string;
  intro: string;
  decomposition: TerminalTableRow[];
  indexedSeries: Array<{ period: string; price: number; revenue: number; eps: number; fcf: number }>;
  capex: TerminalTableRow[];
  capexBars: Array<{ label: string; capex: number; operatingCashFlow: number }>;
  plumbing: TerminalTableRow[];
  breadth: TerminalTableRow[];
  historical: TerminalTableRow[];
  notClassicBubble: string[];
  dangerTriggers: string[];
}

export interface WatchlistRow {
  category: string;
  metric: string;
  current: string;
  threshold: string;
  change: string;
  status: string;
  why: string;
  tone: StatusTone;
}

export interface CommandItem {
  label: string;
  command: string;
  response?: string;
}

export type ViewKey = "overview" | "company" | "inflation" | "fragility" | "watchlist" | "historical" | "policy" | "liquidity" | "market";
