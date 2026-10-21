import type { OverviewBriefing } from "../types";

export const overview: OverviewBriefing = {
  asOf: "24 JUN 2026",
  market: "US EQUITIES",
  dataStatus: "14/16 CURRENT",
  reportId: "MSOS-2026-0624",
  generated: "14:26 EDT",
  sessionId: "RCH-US-0624-DIB",
  cacheAge: "12 MIN",
  build: "v0.8.3",
  fedState: "HOLD",
  terminalStatus: "CONNECTED",
  structure: "Valuation-sensitive expansion",
  summary:
    "Current earnings support remains constructive, however breadth continues to narrow while long-duration assets become increasingly sensitive to long-end Treasury yields.",
  mainTension:
    "Strong corporate earnings are offset by rising duration pressure and concentrated leadership.",
  whatChanged: [
    "US 30Y yield: +8bp",
    "RSP lagged SPY by 2.1pp",
    "Semiconductors retained relative strength",
    "VIX remains below recent stress levels"
  ],
  watch: [
    {
      label: "US30Y",
      value: "5.06%",
      change: "+8bp today",
      threshold: "5.00%",
      status: "ABOVE STRUCTURAL WATCH LEVEL",
      why: "Long-duration equities become increasingly sensitive to discount-rate expansion.",
      tone: "triggered"
    },
    {
      label: "CPI RELEASE",
      value: "In 3 days",
      status: "EVENT WATCH",
      why: "Inflation surprise risk can reprice Fed-path assumptions and pressure valuation multiples.",
      tone: "watch"
    },
    {
      label: "AI EARNINGS",
      value: "NVDA next",
      status: "NORMAL",
      why: "Leadership durability depends on earnings confirmation, not only price momentum.",
      tone: "normal"
    },
    {
      label: "BREADTH",
      value: "RSP vs SPY -7.8% 3M",
      status: "NARROW LEADERSHIP",
      why: "Weak equal-weight participation keeps the expansion dependent on fewer mega-cap leaders.",
      tone: "watch"
    }
  ],
  commands: ["inflation", "company PLTR", "fragility", "historical", "watchlist"],
  recentReports: [
    { id: "MSOS-INFLATION", title: "US inflation pressure", time: "14:02 EDT", status: "Evidence-first" },
    { id: "MSOS-COMP-PLTR", title: "PLTR company intelligence", time: "13:48 EDT", status: "Reviewed" },
    { id: "MSOS-MACRO-30Y", title: "30Y yield threshold monitor", time: "12:10 EDT", status: "Triggered" },
    { id: "MSOS-LAB-BUBBLE", title: "AI fragility comparator", time: "09:35 EDT", status: "Updated" }
  ],
  researchLog: [
    { time: "14:26", event: "Daily integrated briefing generated", impact: "Sources 14/16 current" },
    { time: "14:11", event: "RSP underperformed SPY by 2.1pp", impact: "Breadth risk moved to watch" },
    { time: "13:52", event: "Semiconductor relative strength held", impact: "Leadership remains concentrated" },
    { time: "13:20", event: "30Y yield crossed watch threshold", impact: "Duration sensitivity elevated" }
  ]
};
