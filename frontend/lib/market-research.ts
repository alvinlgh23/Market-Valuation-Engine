export type MarketEvidenceType = "FACT" | "PROXY" | "INFERENCE";
export type SectorStage = "Developing" | "Institutional Momentum" | "Late Momentum" | "Cooling" | "Defensive Rotation" | "Selective" | "Unavailable";

export interface SectorEvidence {
  id: string;
  type: MarketEvidenceType;
  label: string;
  value: string;
  source: string;
  period: string;
  note: string;
}

export interface SectorStructureNode {
  id: string;
  title: string;
  role: string;
  currentState: string;
  description: string;
  companies: string[];
  evidenceIds: string[];
  dataGaps: string[];
}

export interface SectorResearchObject {
  slug: string;
  ticker: string;
  name: string;
  primaryTheme: string;
  currentRead: string;
  rel1m: number | null;
  rel3m: number | null;
  rel6m: number | null;
  breadth: string;
  breadthRatio: number | null;
  crowding: string;
  crowdingBasis: string;
  momentum: string;
  stage: SectorStage;
  heat: string;
  sourceState: "CACHED" | "PARTIAL" | "STRUCTURAL_MODEL_PARTIAL" | "STALE" | "UNAVAILABLE";
  lastUpdated: string;
  leaders: Array<{ ticker: string; name: string; role: string; relativeStrength: number | null; condition: string }>;
  structure: {
    template: string;
    status: "STRUCTURAL" | "STRUCTURAL_MODEL_PARTIAL";
    summary: string;
    nodes: SectorStructureNode[];
    edges: Array<{ from: string; to: string; relationship: string }>;
  };
  evidence: SectorEvidence[];
  dataGaps: string[];
  reportNotes: string[];
}

export const rotationAxis = {
  x: "6M relative strength vs SPY",
  y: "Crowding / extension state",
  reason: "The backend sector engine ranks sectors with 1M/3M/6M relative strength and breakout strength, while sector positioning separates breadth, momentum structure, PE expansion, and crowding risk. The map therefore uses 6M relative strength for leadership and a categorical crowding band for positioning risk."
};

export const sectors: SectorResearchObject[] = [
  {
    slug: "semiconductors",
    ticker: "SMH",
    name: "Semiconductors",
    primaryTheme: "AI Infrastructure",
    currentRead: "Leadership remains intact, but the move is increasingly dependent on AI infrastructure winners and extension should be watched separately from breadth.",
    rel1m: 0.043,
    rel3m: 0.118,
    rel6m: 0.224,
    breadth: "Broad",
    breadthRatio: 0.67,
    crowding: "Elevated proxy-based crowding",
    crowdingBasis: "Relative strength, participation, and price extension are available; direct positioning/options data is unavailable.",
    momentum: "Strong Sector-Wide Acceleration",
    stage: "Institutional Momentum",
    heat: "Warm",
    sourceState: "CACHED",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "NVDA", name: "NVIDIA", role: "AI accelerator design", relativeStrength: 0.31, condition: "Leadership" },
      { ticker: "TSM", name: "Taiwan Semiconductor", role: "Foundry", relativeStrength: 0.24, condition: "Leadership" },
      { ticker: "AVGO", name: "Broadcom", role: "Networking / custom silicon", relativeStrength: 0.21, condition: "Leadership" },
      { ticker: "AMD", name: "Advanced Micro Devices", role: "Chip design", relativeStrength: 0.12, condition: "Participating" },
      { ticker: "MU", name: "Micron", role: "Memory", relativeStrength: 0.1, condition: "Participating" }
    ],
    structure: {
      template: "compute-supply-chain",
      status: "STRUCTURAL",
      summary: "A structural industry map, not a claim that every node is a current bottleneck.",
      nodes: [
        { id: "ai-compute-demand", title: "AI / Compute Demand", role: "Demand Layer", currentState: "Primary theme", description: "End demand that pulls accelerator, networking, memory, and foundry capacity through the chain.", companies: ["NVDA", "AMD", "AVGO"], evidenceIds: ["SMH-E1"], dataGaps: ["Direct hyperscaler capex attribution is not exposed in the current sector fixture."] },
        { id: "chip-design", title: "Chip Design", role: "Design Layer", currentState: "Leadership node", description: "Fabless design captures high-value compute and networking demand before manufacturing handoff.", companies: ["NVDA", "AMD", "AVGO", "MRVL"], evidenceIds: ["SMH-E2"], dataGaps: [] },
        { id: "memory", title: "Memory / HBM", role: "Component Layer", currentState: "Participation broadening", description: "Memory and HBM attach to AI-server demand but have more cyclical pricing sensitivity.", companies: ["MU", "WDC"], evidenceIds: ["SMH-E3"], dataGaps: ["Direct HBM supply-demand data unavailable."] },
        { id: "foundry", title: "Foundry", role: "Manufacturing Layer", currentState: "Structural constraint layer", description: "Advanced-node manufacturing converts design wins into physical supply.", companies: ["TSM"], evidenceIds: ["SMH-E4"], dataGaps: ["Capacity utilization is structural context only in this fixture."] },
        { id: "equipment", title: "Equipment", role: "Capex Layer", currentState: "Second-order leadership", description: "Wafer equipment participates when capex expectations expand across fabs.", companies: ["ASML", "AMAT", "LRCX", "KLAC"], evidenceIds: ["SMH-E5"], dataGaps: [] },
        { id: "advanced-packaging", title: "Advanced Packaging", role: "Constraint / Infrastructure Layer", currentState: "Structurally important; current bottleneck not formally measured", description: "Packaging links accelerators, memory, and foundry output into deployable AI systems.", companies: ["TSM", "NVDA", "AVGO"], evidenceIds: ["SMH-E6"], dataGaps: ["No direct packaging capacity series in current backend output."] }
      ],
      edges: [
        { from: "ai-compute-demand", to: "chip-design", relationship: "pulls demand into" },
        { from: "ai-compute-demand", to: "memory", relationship: "requires" },
        { from: "chip-design", to: "foundry", relationship: "outsources manufacturing to" },
        { from: "memory", to: "advanced-packaging", relationship: "feeds" },
        { from: "foundry", to: "advanced-packaging", relationship: "feeds" },
        { from: "equipment", to: "foundry", relationship: "enables capacity for" }
      ]
    },
    evidence: [
      { id: "SMH-E1", type: "PROXY", label: "6M relative strength", value: "+22.4% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Leadership axis uses backend-compatible relative-strength semantics." },
      { id: "SMH-E2", type: "PROXY", label: "Top company leadership", value: "NVDA / TSM / AVGO", source: "Existing SECTOR_CANDIDATES leadership basket", period: "Current fixture", note: "Company link enters Phase 2 company research." },
      { id: "SMH-E3", type: "PROXY", label: "Breadth", value: "Broad participation", source: "Existing sector_positioning breadth_label semantics", period: "Current fixture", note: "Participation is a proxy, not direct positioning." },
      { id: "SMH-E4", type: "INFERENCE", label: "Foundry role", value: "Structural layer", source: "Declarative SectorStructureTemplate", period: "Static structural context", note: "Structural map is separated from current market state." },
      { id: "SMH-E5", type: "INFERENCE", label: "Equipment role", value: "Capex layer", source: "Declarative SectorStructureTemplate", period: "Static structural context", note: "No operational capex forecast is inferred." },
      { id: "SMH-E6", type: "INFERENCE", label: "Advanced packaging role", value: "Constraint layer", source: "Declarative SectorStructureTemplate", period: "Static structural context", note: "Direct capacity evidence is unavailable." }
    ],
    dataGaps: ["Direct institutional positioning unavailable", "Options positioning unavailable", "Packaging capacity and HBM supply series unavailable"],
    reportNotes: ["CLI equivalents: python model.py sectors; python model.py sector semis", "No sector formula was moved into React."]
  },
  {
    slug: "technology",
    ticker: "XLK",
    name: "Technology",
    primaryTheme: "Platform Growth",
    currentRead: "Technology remains a leadership complex, but it mixes AI infrastructure, software duration, and mega-cap platform exposure.",
    rel1m: 0.021,
    rel3m: 0.074,
    rel6m: 0.151,
    breadth: "Selective",
    breadthRatio: 0.42,
    crowding: "Moderate proxy-based crowding",
    crowdingBasis: "Leadership is positive but less structurally specific than semiconductors.",
    momentum: "Developing Leadership",
    stage: "Developing",
    heat: "Warm",
    sourceState: "CACHED",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "MSFT", name: "Microsoft", role: "Cloud / software platform", relativeStrength: 0.18, condition: "Leadership" },
      { ticker: "AAPL", name: "Apple", role: "Device ecosystem", relativeStrength: 0.05, condition: "Participating" },
      { ticker: "NVDA", name: "NVIDIA", role: "Compute infrastructure", relativeStrength: 0.31, condition: "Leadership" },
      { ticker: "AVGO", name: "Broadcom", role: "Infrastructure silicon", relativeStrength: 0.21, condition: "Leadership" }
    ],
    structure: {
      template: "platform-technology",
      status: "STRUCTURAL_MODEL_PARTIAL",
      summary: "Technology is intentionally broad, so the structure is partial and routes users toward company-level economics.",
      nodes: [
        { id: "platforms", title: "Platforms", role: "Demand Aggregation", currentState: "Large-cap leadership", description: "Operating systems, ecosystems, and cloud platforms aggregate usage and distribution.", companies: ["MSFT", "AAPL"], evidenceIds: ["XLK-E1"], dataGaps: [] },
        { id: "cloud", title: "Cloud Infrastructure", role: "Infrastructure Layer", currentState: "AI-linked", description: "Cloud capex and workloads connect macro liquidity to company scaling economics.", companies: ["MSFT", "ORCL", "NOW"], evidenceIds: ["XLK-E2"], dataGaps: ["Workload-level sector history unavailable."] },
        { id: "software", title: "Software Duration", role: "Long-Duration Cash Flow", currentState: "Rate-sensitive", description: "Software valuation remains sensitive to rates and revenue durability.", companies: ["CRM", "ADBE", "NOW"], evidenceIds: ["XLK-E3"], dataGaps: ["Direct duration decomposition unavailable."] }
      ],
      edges: [
        { from: "platforms", to: "cloud", relationship: "funds / distributes" },
        { from: "cloud", to: "software", relationship: "hosts" }
      ]
    },
    evidence: [
      { id: "XLK-E1", type: "PROXY", label: "6M relative strength", value: "+15.1% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Leadership proxy." },
      { id: "XLK-E2", type: "INFERENCE", label: "Cloud infrastructure role", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "Not current capex evidence." },
      { id: "XLK-E3", type: "INFERENCE", label: "Rate sensitivity", value: "Macro connection prepared", source: "Existing macro transmission concept", period: "Context", note: "Only surfaced as context." }
    ],
    dataGaps: ["Options/positioning unavailable", "Subindustry breadth history unavailable"],
    reportNotes: ["CLI equivalent: python model.py sector tech"]
  },
  {
    slug: "energy",
    ticker: "XLE",
    name: "Energy",
    primaryTheme: "Oil / Cash Flow Discipline",
    currentRead: "Energy is a cyclical hard-asset structure; leadership depends more on commodity prices, production discipline, and refining/services exposure than long-duration growth.",
    rel1m: -0.008,
    rel3m: 0.036,
    rel6m: 0.082,
    breadth: "Selective",
    breadthRatio: 0.36,
    crowding: "Not yet elevated",
    crowdingBasis: "Relative strength is constructive but broad crowding confirmation is not present.",
    momentum: "Early-to-Mid Sector Momentum",
    stage: "Selective",
    heat: "Contained",
    sourceState: "CACHED",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "XOM", name: "Exxon Mobil", role: "Integrated major", relativeStrength: 0.09, condition: "Leadership" },
      { ticker: "CVX", name: "Chevron", role: "Integrated major", relativeStrength: 0.05, condition: "Participating" },
      { ticker: "COP", name: "ConocoPhillips", role: "Upstream", relativeStrength: 0.07, condition: "Participating" },
      { ticker: "SLB", name: "SLB", role: "Oilfield services", relativeStrength: 0.04, condition: "Watch" }
    ],
    structure: {
      template: "hard-asset-energy",
      status: "STRUCTURAL",
      summary: "Energy structure separates commodity price transmission from company balance-sheet/cash-flow expression.",
      nodes: [
        { id: "commodity-price", title: "Oil / Gas Price", role: "Macro Input", currentState: "Primary macro driver", description: "Commodity pricing sets revenue sensitivity for upstream and integrated operators.", companies: ["XOM", "CVX", "COP"], evidenceIds: ["XLE-E1"], dataGaps: ["No live oil curve embedded in current frontend fixture."] },
        { id: "production", title: "Production", role: "Volume Layer", currentState: "Operational driver", description: "Production converts commodity exposure into realized revenue.", companies: ["XOM", "CVX", "COP", "EOG"], evidenceIds: ["XLE-E2"], dataGaps: ["Company production series unavailable."] },
        { id: "refining", title: "Refining / Downstream", role: "Spread Layer", currentState: "Different economics", description: "Refiners depend on crack spreads and demand rather than only upstream prices.", companies: ["MPC", "VLO", "PSX"], evidenceIds: ["XLE-E3"], dataGaps: ["Crack-spread evidence unavailable."] },
        { id: "services", title: "Services", role: "Capex Layer", currentState: "Second-order cyclical", description: "Oilfield services respond to producer capital spending.", companies: ["SLB", "HAL"], evidenceIds: ["XLE-E4"], dataGaps: [] }
      ],
      edges: [
        { from: "commodity-price", to: "production", relationship: "prices output from" },
        { from: "commodity-price", to: "refining", relationship: "affects spreads for" },
        { from: "production", to: "services", relationship: "drives capex demand for" }
      ]
    },
    evidence: [
      { id: "XLE-E1", type: "PROXY", label: "6M relative strength", value: "+8.2% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Sector leadership proxy." },
      { id: "XLE-E2", type: "INFERENCE", label: "Production layer", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "No production forecast inferred." },
      { id: "XLE-E3", type: "INFERENCE", label: "Refining layer", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "Spread data unavailable." },
      { id: "XLE-E4", type: "INFERENCE", label: "Services layer", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "Capex proxy only." }
    ],
    dataGaps: ["Direct commodity curve and crack-spread data unavailable", "Producer capex series unavailable"],
    reportNotes: ["CLI equivalent: python model.py sector energy"]
  },
  {
    slug: "financials",
    ticker: "XLF",
    name: "Financials",
    primaryTheme: "Rates / Credit / Funding",
    currentRead: "Financials are a balance-sheet transmission sector; the key distinction is spread/funding benefit versus credit deterioration risk.",
    rel1m: 0.012,
    rel3m: 0.052,
    rel6m: 0.101,
    breadth: "Broad",
    breadthRatio: 0.58,
    crowding: "Moderate",
    crowdingBasis: "Positive relative strength and participation, but no direct positioning evidence.",
    momentum: "Developing Leadership",
    stage: "Developing",
    heat: "Warm",
    sourceState: "CACHED",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "JPM", name: "JPMorgan Chase", role: "Diversified bank", relativeStrength: 0.13, condition: "Leadership" },
      { ticker: "BAC", name: "Bank of America", role: "Deposit / lending exposure", relativeStrength: 0.08, condition: "Participating" },
      { ticker: "GS", name: "Goldman Sachs", role: "Capital markets", relativeStrength: 0.07, condition: "Participating" },
      { ticker: "V", name: "Visa", role: "Payments", relativeStrength: 0.04, condition: "Quality / steady" }
    ],
    structure: {
      template: "financial-balance-sheet",
      status: "STRUCTURAL",
      summary: "Financials structure is balance-sheet driven, visibly different from semiconductor supply-chain structure.",
      nodes: [
        { id: "funding", title: "Deposits / Funding", role: "Liability Layer", currentState: "Core constraint", description: "Funding cost and deposit stability shape the ability to lend and earn spread.", companies: ["JPM", "BAC", "WFC"], evidenceIds: ["XLF-E1"], dataGaps: ["Bank-level deposit beta not exposed in sector fixture."] },
        { id: "assets", title: "Loans / Assets", role: "Asset Layer", currentState: "Volume driver", description: "Loan growth and asset mix translate funding into revenue opportunity.", companies: ["JPM", "BAC", "WFC"], evidenceIds: ["XLF-E2"], dataGaps: [] },
        { id: "spread", title: "Net Interest Spread", role: "Revenue Mechanism", currentState: "Rates sensitive", description: "Spread captures rates benefit or compression before credit costs.", companies: ["JPM", "BAC"], evidenceIds: ["XLF-E3"], dataGaps: ["Sector-level NIM history unavailable."] },
        { id: "credit", title: "Credit", role: "Risk Layer", currentState: "Falsification risk", description: "Credit losses can offset spread benefit and change the sector read.", companies: ["JPM", "BAC", "GS"], evidenceIds: ["XLF-E4"], dataGaps: ["Direct credit stress series not wired to Markets UI."] }
      ],
      edges: [
        { from: "funding", to: "assets", relationship: "funds" },
        { from: "assets", to: "spread", relationship: "earns" },
        { from: "spread", to: "credit", relationship: "must survive" }
      ]
    },
    evidence: [
      { id: "XLF-E1", type: "PROXY", label: "6M relative strength", value: "+10.1% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Leadership proxy." },
      { id: "XLF-E2", type: "INFERENCE", label: "Balance-sheet structure", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "Not a live NIM calculation." },
      { id: "XLF-E3", type: "INFERENCE", label: "Spread role", value: "Rates-sensitive", source: "SectorStructureTemplate", period: "Context", note: "Macro bridge prepared." },
      { id: "XLF-E4", type: "INFERENCE", label: "Credit risk", value: "Falsification layer", source: "Risk regime context", period: "Context", note: "Sector-specific credit data unavailable." }
    ],
    dataGaps: ["Direct deposit beta unavailable", "Sector-level credit-loss history unavailable"],
    reportNotes: ["CLI equivalent: python model.py sector financials"]
  },
  {
    slug: "healthcare",
    ticker: "XLV",
    name: "Healthcare",
    primaryTheme: "Defensive Growth / Pharma",
    currentRead: "Healthcare is defensive growth: less tied to cyclical demand, more tied to pipeline, reimbursement, and durable demand.",
    rel1m: 0.006,
    rel3m: -0.012,
    rel6m: 0.018,
    breadth: "Narrow",
    breadthRatio: 0.24,
    crowding: "Contained",
    crowdingBasis: "Relative strength is muted; direct positioning data unavailable.",
    momentum: "Base-Building",
    stage: "Selective",
    heat: "Contained",
    sourceState: "STRUCTURAL_MODEL_PARTIAL",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "LLY", name: "Eli Lilly", role: "Pharma growth", relativeStrength: 0.11, condition: "Leadership" },
      { ticker: "UNH", name: "UnitedHealth", role: "Managed care", relativeStrength: -0.02, condition: "Mixed" },
      { ticker: "MRK", name: "Merck", role: "Pharma", relativeStrength: 0.01, condition: "Watch" }
    ],
    structure: {
      template: "defensive-healthcare",
      status: "STRUCTURAL_MODEL_PARTIAL",
      summary: "Partial structure because current backend exposes sector candidates and positioning, not therapy-area economics.",
      nodes: [
        { id: "pharma", title: "Pharma / Pipeline", role: "Innovation Layer", currentState: "Company-specific", description: "Pipeline/product cycles are company-specific and should route to Company Research.", companies: ["LLY", "MRK", "ABBV"], evidenceIds: ["XLV-E1"], dataGaps: ["Therapy-area pipeline data unavailable."] },
        { id: "managed-care", title: "Managed Care", role: "Payment Layer", currentState: "Policy-sensitive", description: "Reimbursement and utilization matter more than commodity or capex cycles.", companies: ["UNH"], evidenceIds: ["XLV-E2"], dataGaps: ["Reimbursement evidence unavailable."] }
      ],
      edges: [{ from: "pharma", to: "managed-care", relationship: "meets payer channel" }]
    },
    evidence: [
      { id: "XLV-E1", type: "PROXY", label: "6M relative strength", value: "+1.8% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Muted leadership proxy." },
      { id: "XLV-E2", type: "INFERENCE", label: "Defensive structure", value: "Partial structural model", source: "SectorStructureTemplate", period: "Static structural context", note: "Unsupported claims are labelled partial." }
    ],
    dataGaps: ["Pipeline and reimbursement data unavailable"],
    reportNotes: ["CLI equivalent: python model.py sector healthcare"]
  },
  {
    slug: "industrials",
    ticker: "XLI",
    name: "Industrials",
    primaryTheme: "Capex / Infrastructure",
    currentRead: "Industrials express capex, transport, aerospace, and equipment cycles rather than a single supply chain.",
    rel1m: 0.009,
    rel3m: 0.028,
    rel6m: 0.064,
    breadth: "Selective",
    breadthRatio: 0.34,
    crowding: "Contained",
    crowdingBasis: "Leadership is present but not broad enough for a crowded read.",
    momentum: "Developing Leadership",
    stage: "Developing",
    heat: "Contained",
    sourceState: "STRUCTURAL_MODEL_PARTIAL",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "CAT", name: "Caterpillar", role: "Equipment", relativeStrength: 0.08, condition: "Leadership" },
      { ticker: "GE", name: "GE Aerospace", role: "Aerospace", relativeStrength: 0.09, condition: "Leadership" },
      { ticker: "RTX", name: "RTX", role: "Aerospace / defense", relativeStrength: 0.05, condition: "Participating" }
    ],
    structure: {
      template: "industrial-capex",
      status: "STRUCTURAL_MODEL_PARTIAL",
      summary: "Partial structure groups industrial demand channels without claiming a single deterministic chain.",
      nodes: [
        { id: "capex", title: "Capex Demand", role: "Demand Layer", currentState: "Primary lens", description: "Equipment and automation respond to corporate and public capex cycles.", companies: ["CAT", "ETN", "DE"], evidenceIds: ["XLI-E1"], dataGaps: [] },
        { id: "aerospace", title: "Aerospace / Defense", role: "Backlog Layer", currentState: "Separate cycle", description: "Backlog and defense spending can diverge from general industrial momentum.", companies: ["GE", "RTX", "LMT"], evidenceIds: ["XLI-E2"], dataGaps: ["Backlog series unavailable."] }
      ],
      edges: [{ from: "capex", to: "aerospace", relationship: "coexists with" }]
    },
    evidence: [
      { id: "XLI-E1", type: "PROXY", label: "6M relative strength", value: "+6.4% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Leadership proxy." },
      { id: "XLI-E2", type: "INFERENCE", label: "Aerospace split", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "No backlog model inferred." }
    ],
    dataGaps: ["Backlog and order series unavailable"],
    reportNotes: ["CLI equivalent: python model.py sector industrials"]
  },
  {
    slug: "utilities",
    ticker: "XLU",
    name: "Utilities",
    primaryTheme: "Defensive / Power Demand",
    currentRead: "Utilities are defensive and regulated; the research question is whether rate pressure is being offset by power-demand and defensive rotation.",
    rel1m: 0.018,
    rel3m: 0.044,
    rel6m: 0.073,
    breadth: "Broad",
    breadthRatio: 0.55,
    crowding: "Moderate defensive crowding",
    crowdingBasis: "Defensive participation is visible, but direct positioning is unavailable.",
    momentum: "Defensive Rerating",
    stage: "Defensive Rotation",
    heat: "Warm",
    sourceState: "CACHED",
    lastUpdated: "2026-08-03",
    leaders: [
      { ticker: "NEE", name: "NextEra Energy", role: "Regulated / renewables", relativeStrength: 0.04, condition: "Participating" },
      { ticker: "CEG", name: "Constellation Energy", role: "Nuclear / power demand", relativeStrength: 0.14, condition: "Leadership" },
      { ticker: "VST", name: "Vistra", role: "Power generation", relativeStrength: 0.16, condition: "Leadership" }
    ],
    structure: {
      template: "regulated-power",
      status: "STRUCTURAL",
      summary: "Utilities structure differs from growth sectors: regulated asset base, rates, and power demand drive the map.",
      nodes: [
        { id: "rates", title: "Rates / Cost of Capital", role: "Macro Constraint", currentState: "Key watch item", description: "Rates affect regulated utility valuation and financing costs.", companies: ["NEE", "SO", "DUK"], evidenceIds: ["XLU-E1"], dataGaps: [] },
        { id: "regulated-assets", title: "Regulated Asset Base", role: "Earnings Base", currentState: "Durability layer", description: "Regulated assets support earnings durability but cap upside.", companies: ["SO", "DUK", "AEP"], evidenceIds: ["XLU-E2"], dataGaps: ["Rate-base growth unavailable."] },
        { id: "power-demand", title: "Power Demand", role: "Growth Layer", currentState: "AI/grid relevance", description: "Electricity demand from data centers can change growth expectations for selected utilities.", companies: ["CEG", "VST", "NEE"], evidenceIds: ["XLU-E3"], dataGaps: ["Direct data-center load evidence unavailable."] }
      ],
      edges: [
        { from: "rates", to: "regulated-assets", relationship: "constrains valuation of" },
        { from: "regulated-assets", to: "power-demand", relationship: "supports investment for" }
      ]
    },
    evidence: [
      { id: "XLU-E1", type: "PROXY", label: "6M relative strength", value: "+7.3% vs SPY", source: "Existing sector rotation field: rel_6m", period: "6M", note: "Defensive leadership proxy." },
      { id: "XLU-E2", type: "INFERENCE", label: "Regulated asset base", value: "Structural", source: "SectorStructureTemplate", period: "Static structural context", note: "No rate-case model inferred." },
      { id: "XLU-E3", type: "INFERENCE", label: "Power demand", value: "Structural growth layer", source: "SectorStructureTemplate", period: "Static structural context", note: "Direct load evidence unavailable." }
    ],
    dataGaps: ["Direct load growth unavailable", "Utility-specific rate-base data unavailable"],
    reportNotes: ["CLI equivalent: python model.py theme utilities"]
  }
];

export function sectorBySlug(slug?: string | null): SectorResearchObject {
  const normalized = (slug || "semiconductors").toLowerCase().replaceAll("_", "-");
  return sectors.find((sector) => sector.slug === normalized || sector.name.toLowerCase() === normalized || sector.ticker.toLowerCase() === normalized) ?? sectors[0];
}

export function percent(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "Unavailable";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

export type SectorEngineRow = { ticker?: string; rel_1m?: number | null; rel_3m?: number | null; rel_6m?: number | null; as_of?: string };

export function integrateSectorEngineRows(rows: SectorEngineRow[] | undefined, state = "UNKNOWN"): SectorResearchObject[] {
  const byTicker = new Map<string, SectorEngineRow>();
  for (const row of Array.isArray(rows) ? rows : []) {
    if (!row || typeof row.ticker !== "string") continue;
    const key = row.ticker.toUpperCase();
    const normalized = { ...row, as_of: typeof row.as_of === "string" && /^\d{4}-\d{2}-\d{2}/.test(row.as_of) && Number.isFinite(Date.parse(row.as_of)) ? row.as_of : undefined };
    const prior = byTicker.get(key);
    if (!prior || (normalized.as_of || "") > (prior.as_of || "")) byTicker.set(key, normalized);
  }
  const finite = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : null;
  return sectors.map((sector) => {
    const row = byTicker.get(sector.ticker);
    const stale = state === "STALE" || (!!row?.as_of && Date.now() - Date.parse(row.as_of) > 7 * 86400_000);
    return {
      ...sector,
      rel1m: finite(row?.rel_1m), rel3m: finite(row?.rel_3m), rel6m: finite(row?.rel_6m),
      breadth: "Unavailable", breadthRatio: null, crowding: "Unavailable", crowdingBasis: "No current positioning measurements supplied.",
      momentum: "Unverified", stage: "Unavailable", heat: "Unavailable",
      currentRead: row ? "Python relative strength is available; broader leadership and crowding conclusions require additional evidence." : "Structural sector map available; dynamic market measurements unavailable.",
      leaders: sector.leaders.map(leader => ({ ...leader, relativeStrength: null, condition: "Structural role; current leadership unverified" })),
      sourceState: !row ? "UNAVAILABLE" : stale ? "STALE" : "PARTIAL",
      lastUpdated: row?.as_of || "Observation date unavailable",
      evidence: sector.evidence.filter(item => !/relative strength|breadth|momentum|crowding/i.test(item.label)),
      reportNotes: ["Structural relationships are declarative. Dynamic numerical fields come only from supplied Python measurements.", `Engine state: ${state}; observation date: ${row?.as_of || "unknown"}.`],
    };
  });
}
