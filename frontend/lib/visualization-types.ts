export type EvidenceState = "FACT" | "PROXY" | "INFERENCE" | string;

export type QuantitativeDatum = {
  id: string;
  label: string;
  value: number;
  unit: string;
  date?: string | null;
  status?: string;
  confidence?: string;
  evidenceId?: string;
  source?: string;
  context?: string;
  scaleGroup?: string;
};

export type RankedResearchItem = {
  id: string;
  rank: number;
  label: string;
  group: string;
  status: string;
  current?: string;
  threshold?: string;
  reason?: string;
  href?: string;
  magnitude?: number;
  unit?: string;
};

export type TimeSeriesPoint = {
  date: string;
  value: number | null;
  comparison?: number | null;
};

export type TimeSeriesDefinition = {
  id: string;
  label: string;
  unit: string;
  points: TimeSeriesPoint[];
  comparisonLabel?: string;
  source?: string;
};

export type HeatmapCell = {
  id: string;
  row: string;
  column: string;
  state: string;
  confidence: string;
  coverage?: string;
  href?: string;
  evidenceIds?: string[];
};

export type CoverageItem = {
  id: string;
  label: string;
  state: string;
  asOf?: string | null;
  available?: number;
  total?: number;
  detail: string;
};

export type CompanyMatrixRow = {
  ticker: string;
  name: string;
  archetype: string;
  growthDirection: string;
  growthConfidence: string;
  constraint: string;
  constraintDirection: string;
  scaling: string;
  valuation: string;
  confidence: string;
  href: string;
};

export type TransmissionNode = { id: string; label: string; x: number; y: number };
export type TransmissionEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  state: string;
  evidenceType: EvidenceState;
  confidence: string;
  evidenceIds: string[];
};
