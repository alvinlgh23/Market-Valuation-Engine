import type { FragilityReport } from "../types";

export const fragility: FragilityReport = {
  title: "FRAGILITY LAB",
  headline: "Earnings-supported, valuation-sensitive AI expansion",
  intro:
    "This report does not predict a crash. It compares current market structure with prior speculative cycles using valuation, earnings, cash flow, leverage, concentration, and breadth.",
  decomposition: [
    { Metric: "AI Basket Price Return", Current: "+84.2%" },
    { Metric: "Revenue Growth", Current: "+31.6%" },
    { Metric: "EPS Growth", Current: "+46.8%" },
    { Metric: "FCF Growth", Current: "+28.4%" },
    { Metric: "Forward PE", Current: "24.1x -> 31.7x" }
  ],
  indexedSeries: [
    { period: "Q1", price: 100, revenue: 100, eps: 100, fcf: 100 },
    { period: "Q2", price: 118, revenue: 106, eps: 109, fcf: 104 },
    { period: "Q3", price: 137, revenue: 113, eps: 121, fcf: 112 },
    { period: "Q4", price: 160, revenue: 123, eps: 134, fcf: 119 },
    { period: "Q5", price: 184, revenue: 132, eps: 147, fcf: 128 }
  ],
  capex: [
    { Metric: "Hyperscaler Capex / OCF", Current: "58%" },
    { Metric: "One Year Ago", Current: "41%" },
    { Metric: "Operating Cash Flow Growth", Current: "+22%" },
    { Metric: "FCF After Capex", Current: "Positive but slowing" }
  ],
  capexBars: [
    { label: "1Y AGO", capex: 41, operatingCashFlow: 100 },
    { label: "NOW", capex: 58, operatingCashFlow: 122 }
  ],
  plumbing: [
    { Metric: "Margin Debt / Market Cap", Current: "2.4%", Context: "5Y avg 2.0%" },
    { Metric: "VIX", Current: "15.8", Context: "Compressed" },
    { Metric: "20D Realized Vol", Current: "10.6", Context: "Low" },
    { Metric: "Put / Call Ratio", Current: "0.72", Context: "Speculative leaning" }
  ],
  breadth: [
    { Metric: "Top 10 S&P 500 Weight", Current: "38.6%" },
    { Metric: "Top 10 Return Contribution", Current: "54%" },
    { Metric: "RSP vs SPY 3M", Current: "-7.8%" },
    { Metric: "S&P 500 Above 200DMA", Current: "54%" }
  ],
  historical: [
    { Metric: "Price vs EPS gap", Current: "+37%", "Dot-Com 1999": "+XX%", "1929": "+XX%", "2021": "+XX%" },
    { Metric: "FCF-positive leaders", Current: "5/5", "Dot-Com 1999": "Lower", "1929": "Mixed", "2021": "Mixed" },
    { Metric: "Margin debt / mkt cap", Current: "2.4%", "Dot-Com 1999": "X.X%", "1929": "X.X%", "2021": "X.X%" },
    { Metric: "Top-10 concentration", Current: "38.6%", "Dot-Com 1999": "XX%", "1929": "XX%", "2021": "XX%" },
    { Metric: "Speculative breadth", Current: "Contained", "Dot-Com 1999": "Broad", "1929": "Broad", "2021": "Broad" }
  ],
  notClassicBubble: [
    "Real earnings growth",
    "Positive free-cash-flow generation",
    "Internally financed capex",
    "Leadership concentrated in profitable firms"
  ],
  dangerTriggers: [
    "Price outpaces EPS by more than 40pp over 12M",
    "FCF declines while capex rises",
    "Low-quality AI names outperform Tier 1 leaders",
    "Margin debt growth exceeds market-cap growth",
    "Breadth deteriorates while index rises"
  ]
};
