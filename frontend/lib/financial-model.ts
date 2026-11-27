import { arr, num, obj, pick, str, type Json, type ReportData } from "./report-format";

// One reading of the stored data shared by the research note (PDF), the Financials tab and the Economic map, so the
// three always show the same figures. It only reads what the engines stored; the arithmetic is simple ratios of
// reported figures (growth, margins, yearly share change), exactly as the note has always shown them.

export type Segment = { name: string; unit: string; periods: Array<{ period: string; value: number }>; growth: number | null; source: string | null; limitation: string | null };

export type FinancialModel = {
  card: Json;
  axes: Json;
  vdetail: Json;
  quarter: Json;
  edetail: Json;
  metrics: Json;
  operating: Json;
  bank: Json;
  isBank: boolean;
  currency: string;
  price: number | null;
  revenue: Array<number | null>;
  opIncome: Array<number | null>;
  ocf: Array<number | null>;
  capex: Array<number | null>;
  fcf: Array<number | null>;
  years: number;
  cols: number[];
  growth: (i: number) => number | null;
  margin: (series: Array<number | null>, i: number) => number | null;
  shares: number[];
  dilution: number | null;
  implied: number | null;
  refs: number[];
  segments: Segment[];
  scaling: Record<string, number | null>;
};

export function financialModel(data: ReportData): FinancialModel {
  const card = obj(data.card);
  const report = data.valuation;
  const axes = obj(card.axes);
  const vdetail = obj(pick(axes, "valuation", "detail"));
  const histories = obj(data.snapshot?.histories);
  const series = (key: string) => arr(histories[key]).map(num);
  const revenue = series("revenue");
  const shares = arr(report?.historical_base?.diluted_share_history).map(num).filter((v): v is number => v != null && v > 0);
  const reverse = obj(report?.fair_value?.method === "PHASED" && report?.fair_value.reverse_dcf ? report.fair_value.reverse_dcf : report?.reverse_dcf);
  const band = obj(vdetail.growth_band);
  const bank = obj(vdetail.bank_implied_roe);
  const years = Math.min(4, revenue.length);
  const scaling: Record<string, number | null> = {};
  for (const raw of arr(pick(data.profile, "scaling_economics", "metrics"))) {
    const m = obj(raw);
    if (str(m.name)) scaling[String(m.name)] = num(m.value);
  }
  return {
    card,
    axes,
    vdetail,
    quarter: obj(pick(axes, "fundamentals", "detail", "quarterly")),
    edetail: obj(pick(axes, "expectations", "detail")),
    metrics: obj(data.snapshot?.metrics),
    operating: obj(card.operating),
    bank,
    isBank: num(bank.implied_roe) != null,
    currency: str(report?.company?.currency) ?? str(data.snapshot?.currency) ?? "USD",
    price: num(vdetail.price) ?? num(report?.company?.current_market_price),
    revenue,
    opIncome: series("operating_income"),
    ocf: series("operating_cash_flow"),
    capex: series("capex"),
    fcf: series("fcf"),
    years,
    cols: Array.from({ length: years }, (_, i) => i),
    growth: (i) => (revenue[i] != null && revenue[i + 1] != null && revenue[i + 1]! > 0 ? revenue[i]! / revenue[i + 1]! - 1 : null),
    margin: (values, i) => (values[i] != null && revenue[i] ? values[i]! / revenue[i]! : null),
    shares,
    dilution: shares.length >= 2 ? Math.pow(shares[0] / shares[shares.length - 1], 1 / (shares.length - 1)) - 1 : null,
    implied: num(vdetail.implied_5y_revenue_cagr) ?? num(reverse.required_5y_revenue_cagr),
    refs: [num(band.consensus_2y_faded), num(band.history_3y_faded)].filter((v): v is number => v != null).sort((a, b) => a - b),
    segments: segmentsFrom(data.profile),
    scaling,
  };
}

/** Company-reported operating series (Data Center revenue, wafer shipments, customers…) as dated rows, oldest first. */
function segmentsFrom(profile: Json | null): Segment[] {
  return arr(pick(profile, "operational_research", "series")).map((raw) => {
    const s = obj(raw);
    const def = obj(s.definition);
    const periods = arr(s.observations)
      .map((o) => ({ period: str(obj(o).period) ?? "", value: num(pick(o, "evidence", "value")) }))
      .filter((o): o is { period: string; value: number } => !!o.period && o.value != null);
    const change = arr(s.changes).map(obj).find((c) => c.status === "CALCULATED");
    const last = arr(s.observations).at(-1);
    return {
      name: str(def.name) ?? "",
      unit: str(def.unit) ?? "",
      periods,
      growth: num(change?.growth),
      source: str(pick(last, "evidence", "source_name")),
      limitation: str(def.limitation),
    };
  }).filter((s) => s.name && s.periods.length);
}
