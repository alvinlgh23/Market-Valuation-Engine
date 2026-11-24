/**
 * The only place that turns internal research states into words a reader sees.
 *
 * The engines use two dozen availability states (CACHED, PARTIAL, INSUFFICIENT_EVIDENCE,
 * WITHHELD, ...). Readers only need four: there is a result, part of one, none, or an
 * old one. Internal values stay in the data and in tooltips. Labels that are not about
 * data availability (WATCH, TRIGGERED, FACT, PROXY, HIGH, ...) are left as domain labels.
 */
export type StatusWord = "Available" | "Partial" | "Not available" | "Out of date";
export type StatusTone = "available" | "partial" | "unavailable" | "stale";

const WORDS: Record<StatusWord, readonly string[]> = {
  Available: ["AVAILABLE", "FULL", "LIVE", "CACHED", "OK", "PASSED", "VALID", "CURRENT", "COMPLETED", "GOOD", "OBSERVED_LIVE", "OBSERVED_CACHED", "HISTORICAL_REPORTED"],
  Partial: ["PARTIAL", "PROVISIONAL", "LIMITED", "OBSERVED_STALE_PARTIAL"],
  "Not available": [
    "UNAVAILABLE", "MISSING", "NOT_ANALYZED", "INSUFFICIENT", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_DATA",
    "EVIDENCE_INSUFFICIENT", "WITHHELD", "UNKNOWN", "FAILED", "INVALID", "NOT_ESTIMATED", "NOT_APPLICABLE",
    "INSUFFICIENT EVIDENCE", "INSUFFICIENT_FOR_FAIR_VALUE",
  ],
  "Out of date": ["STALE", "OBSERVED_STALE", "EXPIRED"],
};

const LOOKUP = new Map<string, StatusWord>(
  (Object.entries(WORDS) as [StatusWord, readonly string[]][]).flatMap(([word, states]) => states.map((state) => [state, word] as [string, StatusWord])),
);
const TONE: Record<StatusWord, StatusTone> = { Available: "available", Partial: "partial", "Not available": "unavailable", "Out of date": "stale" };

function normalize(raw: unknown) {
  return String(raw ?? "").trim().toUpperCase().replaceAll("-", "_");
}

/** The four-word reading of an availability state, or null when the value is a domain label. */
export function statusWord(raw: unknown): StatusWord | null {
  const key = normalize(raw);
  if (!key) return "Not available";
  return LOOKUP.get(key) ?? LOOKUP.get(key.replaceAll("_", " ")) ?? null;
}

export function statusTone(raw: unknown): StatusTone | "label" {
  const word = statusWord(raw);
  return word ? TONE[word] : "label";
}

const ACRONYMS = new Set(["US", "FX", "BOJ", "ECB", "FED", "KOSPI", "DCF", "FCFF", "RS", "ETF"]);

/** What a badge should say: the status word, or the domain label in sentence case. */
export function displayStatus(raw: unknown): string {
  const word = statusWord(raw);
  if (word) return word;
  const text = String(raw).trim().replaceAll("_", " ");
  if (!text) return "Not available";
  return text.split(" ").map((part, index) => {
    const upper = part.toUpperCase();
    if (ACRONYMS.has(upper)) return upper;
    const lower = part.toLowerCase();
    return index === 0 ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
  }).join(" ");
}
