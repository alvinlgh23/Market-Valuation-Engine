import type { WatchlistRow } from "../types";

export const watchlist: WatchlistRow[] = [
  { category: "Policy", metric: "Core CPI", current: "3.1%", threshold: "3.3%", change: "+0.1pp", status: "NORMAL", why: "Fed sensitivity", tone: "normal" },
  { category: "Liquidity", metric: "US 30Y Yield", current: "5.06%", threshold: "5.00%", change: "+8bp", status: "TRIGGERED", why: "Duration pressure", tone: "triggered" },
  { category: "Breadth", metric: "RSP vs SPY 3M", current: "-7.8%", threshold: "-10.0%", change: "-2.1pp", status: "WATCH", why: "Leadership concentration", tone: "watch" },
  { category: "AI Fundamentals", metric: "AI FCF Growth", current: "+28.4%", threshold: "+15%", change: "-3.0pp", status: "NORMAL", why: "Earnings support", tone: "normal" },
  { category: "Leverage", metric: "Margin Debt Growth", current: "+11%", threshold: "+20%", change: "+2.5pp", status: "NORMAL", why: "Forced selling risk", tone: "normal" }
];
