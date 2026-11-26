declare module "*what-if.mjs" {
  export function computeInteractiveFairValue(params: {
    revenue: number; currentMargin: number; cash: number; debt: number; shares: number;
    growth0: number; targetMargin: number; wacc: number; terminalGrowth: number; dilution: number;
    extendedWeight: number; unitFactor: number;
  }): number | null;
}
