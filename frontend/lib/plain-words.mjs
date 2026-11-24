// Owner request 2026-11-24: no "69th pct" anywhere. A reading's place in its own history is said in
// plain words; the exact number survives only as a plain sentence in the hover panel.
// Bands follow the thresholds the readings already use: the middle third is typical, the outer
// fifths unusual, the outer twentieths extreme.

function valid(p) { return typeof p === "number" && Number.isFinite(p) && p >= 0 && p <= 1; }

/** How unusual a reading is, regardless of direction: Typical, Slightly unusual, Unusual, Extreme. */
export function unusualness(p) {
  if (!valid(p)) return null;
  if (p <= 0.05 || p >= 0.95) return "Extreme";
  if (p <= 0.2 || p >= 0.8) return "Unusual";
  if (p < 0.33 || p > 0.67) return "Slightly unusual";
  return "Typical";
}

/** "Higher than 69 of every 100 readings in the past three years." */
export function versusHistory(p, period = "the past three years", noun = "readings") {
  if (!valid(p)) return null;
  const n = Math.round(p * 100);
  return n >= 50 ? `Higher than ${n} of every 100 ${noun} in ${period}.` : `Lower than ${100 - n} of every 100 ${noun} in ${period}.`;
}

const LABELS = {
  level: ["Much lower than usual", "Lower than usual", "About usual", "Higher than usual", "Much higher than usual"],
  strength: ["Much weaker than usual", "Weaker than usual", "About usual", "Stronger than usual", "Much stronger than usual"],
  price: ["Cheap for its history", "Cheaper than usual", "About usual for its history", "Pricier than usual", "Expensive for its history"]
};

/** A direction-aware label: kind "level", "strength" or "price" (for valuation, high is expensive). */
export function historyLabel(p, kind = "level") {
  if (!valid(p)) return null;
  const labels = LABELS[kind] ?? LABELS.level;
  if (p <= 0.2) return labels[0];
  if (p < 0.33) return labels[1];
  if (p <= 0.67) return labels[2];
  if (p < 0.8) return labels[3];
  return labels[4];
}
