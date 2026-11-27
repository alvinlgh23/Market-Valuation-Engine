// Factual sentences for the Market view (owner-approved 2026-11-27). Descriptions of stored numbers, never a reading.

function pct(v: number, digits = 1) {
  const r = Number((v * 100).toFixed(digits));
  return r === 0 ? "0%" : `${r < 0 ? "−" : "+"}${Math.abs(r).toFixed(digits)}%`;
}

/** Factual sentence comparing the last month with the three months (both to the same date). */
export function concentration(one: number | null, three: number | null): string | null {
  if (one == null || three == null) return null;
  if (Math.abs(three) < 0.01 && Math.abs(one) < 0.01) return null;
  const opposite = Math.abs(three) >= 0.01 && Math.abs(one) >= 0.01 && Math.sign(one) !== Math.sign(three);
  if (opposite || Math.abs(three) < 0.01) return `${pct(three)} over three months but ${pct(one)} in the last month: the last month went the other way from the two months before it.`;
  const ratio = one / three;
  if (ratio >= 0.9 && ratio <= 1.1) return `${pct(three)} over three months and ${pct(one)} in the last month: almost all of the move came in the last month.`;
  if (Math.abs(one) > Math.abs(three)) return `${pct(one)} in the last month, more than the ${pct(three)} over three months: the last month ${one < 0 ? "gave back gains" : "made up losses"} from the two months before it.`;
  const share = one / three;
  const head = `${pct(three)} over three months, ${pct(one)} of it in the last month`;
  return share >= 0.75 ? `${head}: most of the move came in the last month.` : share <= 0.25 ? `${head}: little of it came in the last month.` : `${head}: the move was spread across the three months.`;
}

