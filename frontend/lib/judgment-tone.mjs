// Checklist 9.5: one visual tone per judgment-card state. Tones describe whether the reading
// supports or works against the company on that axis; they are never combined into a score.
//   supportive · against · mixed · unknown

const TONES = {
  macro: { Tailwind: "supportive", Headwind: "against", Mixed: "mixed" },
  flow: { "Money flowing in": "supportive", "Money flowing out": "against", "Mixed (not persistent)": "mixed" },
  crowding: { "Low Chase Risk": "supportive", "Chase Risk Not Excessive": "supportive", "Moderate Chase Risk": "mixed", "High Chase Risk": "against" },
  expectations: { "Estimates rising": "supportive", "Estimates falling": "against", "Estimates stable or mixed": "mixed" },
  fundamentals: { Improving: "supportive", Deteriorating: "against", Mixed: "mixed" },
  valuation: {
    "Price implies less growth than observed/consensus": "supportive",
    "Price implies contraction beyond the model's floor": "supportive",
    "Price roughly matches observed/consensus growth": "mixed",
    "Price implies more growth than observed/consensus": "against",
    "Price implies growth above what the model can reach": "against",
  },
};

export const TONE_GLYPH = { supportive: "▲", against: "▼", mixed: "◆", unknown: "○" };
export const TONE_LABEL = { supportive: "Supportive", against: "Against", mixed: "Mixed", unknown: "No reading" };

export function axisTone(axis, state) {
  return TONES[axis]?.[state] ?? "unknown";
}

export function confidenceDots(confidence) {
  return confidence === "HIGH" ? 3 : confidence === "MODERATE" ? 2 : 1;
}

/** Percent position (0-100) of a 0-1 percentile, or null. */
export function percentileWidth(value) {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(100, value * 100)) : null;
}
