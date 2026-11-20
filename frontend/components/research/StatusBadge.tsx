import { displayStatus, statusTone } from "../../lib/status-words";

/** Shared badge for every research surface; keeps the internal state in the tooltip. */
export function StatusBadge({ value, variant = "system" }: { value: unknown; variant?: "system" | "macro" }) {
  const raw = String(value ?? "UNAVAILABLE");
  const tone = statusTone(raw);
  const base = variant === "macro" ? "macro-status" : "system-badge";
  return <span className={`${base} status-word status-word-${tone}`} title={raw}>{displayStatus(raw)}</span>;
}
