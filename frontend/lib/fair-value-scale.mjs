export function fairValueCoordinates(values) {
  const entries = Object.entries(values).filter(([, value]) => Number.isFinite(value));
  if (!entries.length) return { domainMin: null, domainMax: null, positions: {}, valid: false };
  const numeric = entries.map(([, value]) => value);
  let domainMin = Math.min(...numeric);
  let domainMax = Math.max(...numeric);
  if (domainMin === domainMax) {
    const padding = Math.max(Math.abs(domainMin) * 0.05, 1);
    domainMin -= padding;
    domainMax += padding;
  }
  const span = domainMax - domainMin;
  const positions = Object.fromEntries(entries.map(([key, value]) => [key, ((value - domainMin) / span) * 100]));
  const scenarios = [values.bear, values.base, values.bull];
  const valid = scenarios.every(Number.isFinite) && values.bear <= values.base && values.base <= values.bull;
  return { domainMin, domainMax, positions, valid };
}
