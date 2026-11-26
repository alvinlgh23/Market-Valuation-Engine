// AI model plan, phase B: the valuation page's what-if formula in one place, shared by the page and the parity test
// with the Python port (valuation_what_if.py). Not a new method: moved unchanged out of ValuationResearchPage.tsx.

/**
 * @param {{revenue:number,currentMargin:number,cash:number,debt:number,shares:number,growth0:number,targetMargin:number,
 *          wacc:number,terminalGrowth:number,dilution:number,extendedWeight:number,unitFactor:number}} params
 * @returns {number|null}
 */
export function computeInteractiveFairValue(params) {
  const { revenue, currentMargin, cash, debt, shares, growth0, targetMargin, wacc, terminalGrowth, dilution, extendedWeight, unitFactor } = params;
  if (!(revenue > 0) || !(shares > 0) || wacc <= terminalGrowth + 0.005) return null;
  const runHorizon = (years, firstGrowth) => {
    let rev = revenue, pv = 0, lastFcff = 0;
    for (let y = 1; y <= years; y += 1) {
      const g = years === 5
        ? firstGrowth + (terminalGrowth + 0.01 - firstGrowth) * ((y - 1) / 4)
        : firstGrowth + (terminalGrowth - firstGrowth) * ((y - 1) / (years - 1));
      const m = currentMargin + (targetMargin - currentMargin) * (y / years);
      rev *= 1 + g;
      lastFcff = rev * m;
      pv += lastFcff / Math.pow(1 + wacc, y);
    }
    const tv = (lastFcff * (1 + terminalGrowth)) / (wacc - terminalGrowth);
    const ev = pv + tv / Math.pow(1 + wacc, years);
    const eq = ev + (cash - debt);
    const dilShares = shares * Math.pow(1 + dilution, years);
    return (eq / dilShares) * unitFactor;
  };
  const five = runHorizon(5, growth0);
  if (!(extendedWeight > 0)) return five;
  const ten = runHorizon(10, growth0);
  return (1 - extendedWeight) * five + extendedWeight * ten;
}
