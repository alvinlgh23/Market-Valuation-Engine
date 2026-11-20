import type { ResearchSystem } from "./research-system-types";

export type ResearchResponse = { data: ResearchSystem; meta?: { source?: string; data_state?: string; error?: string; fallback?: boolean; core_snapshot_id?: string; empty_reason?: string } };

export function reconcileResearchResponse(previous: ResearchSystem, response: ResearchResponse): ResearchSystem {
  const incoming = response.data;
  const core = incoming.modules.core_market;
  const previousRows = previous.modules.core_market.payload?.sectors;
  const rows = core.payload?.sectors;
  const unexpectedEmpty = Array.isArray(previousRows) && previousRows.length > 0 && (!Array.isArray(rows) || rows.length === 0) && !response.meta?.empty_reason;
  const failed = response.meta?.fallback || response.meta?.data_state === "STALE" || core.error || unexpectedEmpty;
  // Retain the entire prior response on a failed empty refresh, not a mixture
  // of new Dashboard claims and old Markets measurements.
  const keepPrevious = failed && Array.isArray(previousRows) && previousRows.length && (!Array.isArray(rows) || !rows.length);
  const selected = keepPrevious ? previous : incoming;
  if (!failed) return selected;
  return { ...selected, modules: { ...selected.modules, core_market: { ...selected.modules.core_market, state: "STALE" } } };
}
