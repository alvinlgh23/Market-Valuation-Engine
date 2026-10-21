import type { CompanyReport } from "../types";

export const companyPltr: CompanyReport = {
  ticker: "PLTR",
  name: "Palantir Technologies",
  venue: "NASDAQ",
  currency: "USD",
  updated: "24 JUN 2026",
  structuralRead: "Premium conviction-growth company in valuation-reset / base-building phase",
  summary:
    "Fundamentals remain strong, but price action no longer confirms the premium narrative. The central question is whether revenue growth, margin expansion, and free-cash-flow conversion can continue validating the valuation.",
  businessEvidence: [
    { Metric: "Revenue Growth", Current: "+29.0%", "Prior / Change": "Prior +21.0%" },
    { Metric: "Operating Margin", Current: "18.4%", "Prior / Change": "+3.2pp YoY" },
    { Metric: "Free Cash Flow", Current: "$1.75B", "Prior / Change": "Positive" },
    { Metric: "FCF Margin", Current: "22.1%", "Prior / Change": "Stable" }
  ],
  valuation: [
    { Metric: "Forward P/E", Current: "56.0x", Context: "Recent range 42x-80x" },
    { Metric: "FCF Yield", Current: "1.8%", Context: "Low" },
    { Metric: "Multiple Change", Current: "80x -> 56x", Context: "Compressed from peak" },
    { Metric: "Valuation Status", Current: "Demanding", Context: "Still premium" }
  ],
  positioning: [
    { Metric: "6M Price Return", Current: "-39.7%", Context: "Weak" },
    { Metric: "RS vs SPY", Current: "-31.4pp", Context: "Underperforming" },
    { Metric: "Distance from 200DMA", Current: "-26.9%", Context: "Below trend" },
    { Metric: "Momentum Regime", Current: "Valuation Reset", Context: "Base-building" }
  ],
  chart: [
    { period: "Jan", price: 100, revenue: 100, eps: 100, fcf: 100 },
    { period: "Feb", price: 92, revenue: 104, eps: 103, fcf: 106 },
    { period: "Mar", price: 81, revenue: 109, eps: 111, fcf: 114 },
    { period: "Apr", price: 70, revenue: 114, eps: 119, fcf: 122 },
    { period: "May", price: 63, revenue: 121, eps: 130, fcf: 131 },
    { period: "Jun", price: 60, revenue: 129, eps: 141, fcf: 138 }
  ],
  supportingThesis: [
    "Revenue growth remains elevated",
    "Operating margin is expanding",
    "Free cash flow remains positive",
    "Enterprise adoption narrative remains intact"
  ],
  challengingThesis: [
    "Forward valuation remains demanding",
    "Relative strength remains weak",
    "Premium multiple requires continued execution",
    "Estimate revisions must remain positive"
  ],
  changeView: [
    "Revenue growth falls below 25%",
    "Operating margin stalls for two quarters",
    "EPS revisions turn negative",
    "FCF conversion weakens",
    "Price reclaims 200DMA with improving relative strength"
  ],
  dataQuality: {
    source: "Mock SEC / market data",
    coverage: "High",
    refreshed: "24 Jun 2026"
  }
};
