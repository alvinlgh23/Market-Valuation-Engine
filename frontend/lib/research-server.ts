import { createHash } from "node:crypto";
import { statSync } from "node:fs";
import path from "node:path";
import fixture from "./fixtures/research-system.json";
import { PythonRuntimeError, runPythonJson, runtimeError } from "./python-runtime";

let memoryCache: { at: number; value: typeof fixture } | null = null;
let researchInflight: Promise<typeof fixture> | null = null;
const CACHE_MS = 15 * 60 * 1000;
const REFRESH_TIMEOUT_MS = 15 * 60 * 1000;

function coreSnapshotId(system: typeof fixture) {
  return createHash("sha256").update(JSON.stringify(system.modules.core_market.payload)).digest("hex").slice(0, 16);
}

/** When the daily refresh writes a new market snapshot, the in-memory copy is out of date at once. */
function marketSnapshotTime(): number {
  try { return statSync(path.resolve(process.cwd(), "..", ".cache", "research", "core-market.json")).mtimeMs; } catch { return 0; }
}

export async function loadResearchSystem(refresh = false) {
  let full: typeof fixture;
  let source = "BUNDLED_LAST_VALID";
  if (memoryCache && !refresh && Date.now() - memoryCache.at < CACHE_MS && marketSnapshotTime() <= memoryCache.at) {
    full = memoryCache.value;
    source = "MEMORY_CACHE";
  } else {
    try {
      if (!researchInflight) {
        const args = ["-B", "research_system.py", "full", "--json", ...(refresh ? ["--live"] : [])];
        // A live refresh re-downloads every market, inflation and KOSPI series and takes several minutes;
        // the 3-minute default meant it was always stopped before it could save anything.
        researchInflight = runPythonJson<typeof fixture>(args, refresh ? REFRESH_TIMEOUT_MS : undefined).finally(() => { researchInflight = null; });
      }
      full = await researchInflight;
      if (!full?.modules?.core_market || !full.dashboard || !full.world) throw new PythonRuntimeError("INVALID_JSON", "Malformed research payload.");
      const incomingRows = full.modules.core_market.payload?.sectors;
      const priorRows = memoryCache?.value.modules.core_market.payload?.sectors;
      if (Array.isArray(priorRows) && priorRows.length > 0 && (!Array.isArray(incomingRows) || incomingRows.length === 0)) {
        throw new PythonRuntimeError("INVALID_JSON", "Refresh returned zero sector rows without a validated reason; retaining the prior dated snapshot.");
      }
      memoryCache = { at: Date.now(), value: full };
      source = refresh ? "LIVE_REFRESH" : "PYTHON_CACHE";
    } catch (error) {
      const last = memoryCache?.value ?? fixture;
      const failure = runtimeError(error);
      return { data: last, meta: { source: memoryCache ? "MEMORY_CACHE" : source, core_snapshot_id: coreSnapshotId(last), data_state: "STALE", fallback: true, runtime_error: failure, error: failure.message } };
    }
  }
  return { data: full, meta: { source, core_snapshot_id: coreSnapshotId(full), fallback: false, generated_at: full.generated_at } };
}

export type LoadedResearch = Awaited<ReturnType<typeof loadResearchSystem>>;

/** One data state for the page shell, derived from the same response every page renders. */
export function researchShellState(response: LoadedResearch, module: "core_market" | "inflation" = "core_market") {
  if (response.meta.fallback) return "STALE" as const;
  const state = String(response.data.modules[module]?.state ?? "UNKNOWN").toUpperCase();
  return (["LIVE", "CACHED", "STALE", "PARTIAL", "INSUFFICIENT", "UNAVAILABLE"].includes(state) ? state : "UNKNOWN") as "LIVE" | "CACHED" | "STALE" | "PARTIAL" | "INSUFFICIENT" | "UNKNOWN";
}
