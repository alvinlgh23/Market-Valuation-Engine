export type MacroEvidence = {
  id: string;
  label: string;
  value: string;
  classification: string;
  evidence_type: "FACT" | "PROXY" | "INFERENCE";
  source: string;
  source_path: string;
  period: string | null;
  freshness: string;
  note: string;
};

export type MacroComponent = {
  id: string;
  label: string;
  state: string;
  summary: string;
  confidence: string;
  evidence_ids: string[];
  gaps: string[];
};

export type MacroRegion = {
  id: string;
  name: string;
  available: boolean;
  availability: string;
  framework: string;
  brief: string;
  as_of: string | null;
  freshness: string;
  confidence: string;
  components: MacroComponent[];
  evidence: MacroEvidence[];
  engines: { name: string; role: string; status: string }[];
  watch_conditions: { label: string; threshold: string; current: string; state: string }[];
  engine_specific: Record<string, unknown>;
  gaps: string[];
};

export type MacroTransmission = {
  id: string;
  source: string;
  target: string;
  label: string;
  mechanism: string;
  structural_state: string;
  current_state: string;
  summary: string;
  confidence: string;
  evidence_ids: string[];
  caveat: string;
};

export type MacroWorld = {
  schema_version: string;
  generated_at: string;
  data_state: string;
  supported_regions: string[];
  regions: Record<string, MacroRegion>;
  transmissions: MacroTransmission[];
  evidence_index: Record<string, MacroEvidence>;
  disclaimer: string;
};
