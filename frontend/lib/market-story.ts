// Checklists 15-17: one shared request for the market story, profit breakdown and scenario gate.
export type StoryTag = "FACT" | "MARKET" | "TESTED" | "MEASURED" | "NO_LINK";
export type StoryEvidence = { label: string; value: string; reference: string | null; as_of: string | null; source: string };
export type StoryNote = { tag: StoryTag; label: string; text: string };
export type StoryStep = {
  id: string; tag: StoryTag; title: string; text: string; evidence: StoryEvidence[]; notes?: StoryNote[];
  link?: { kind: "because" | "alongside"; text: string | null }; criteria?: { rule: string };
  holdings?: Array<{ ticker: string; factor: string; value: number }>;
};
export type ScenarioMethod = { name: string; what: string; verdict: string; beat_share: number | null; baseline_share?: number | null };
export type Scenario = { status: string; passed?: string[]; verdict?: string; lesson?: string; methods?: ScenarioMethod[]; rule?: string; generated_on?: string; text?: string };
export type SectorRow = { sector: string; etf: string; profit: number; profit_year_ago: number; companies: number; growth: number | null; share_of_profit: number | null; contribution_pp: number | null; share_of_growth: number | null };
export type Carrier = { symbol: string; name: string; sector: string; etf: string; change: number; share_of_growth: number | null; quarter: string };
export type MarketBreakdown = {
  status: string; reason?: string; companies?: number; members?: number; growth?: number | null; profit?: number; profit_year_ago?: number;
  quarters?: { earliest: string; latest: string; median: string }; sectors?: SectorRow[]; carriers?: Carrier[];
  carriers_for_half?: number | null; carriers_for_80pct?: number | null; companies_growing?: number; top10_profit_share?: number | null; top10_by_profit?: string[];
  driver?: { state: string; label: string; index_change: number; profit_growth: number; multiple_change: number; profit_share_of_move: number | null; plain: string; rule: string };
  index?: { change: number | null; start?: string; end?: string; since_end?: number; latest_date?: string }; source?: string; method?: string;
};
export type MarketStory = {
  status: string; error?: string; as_of?: string;
  story?: { headline: string; steps: StoryStep[]; scenario: Scenario; tags: Record<StoryTag, string> };
  market?: MarketBreakdown; data_dates?: Record<string, string | null>;
};

let shared: Promise<MarketStory> | null = null;
export function loadMarketStory(): Promise<MarketStory> {
  shared ??= fetch("/api/research?action=market-story", { cache: "no-store" })
    .then(async (response) => (await response.json()) as MarketStory)
    .catch((error) => { shared = null; return { status: "FAILED", error: error instanceof Error ? error.message : String(error) }; });
  return shared;
}
