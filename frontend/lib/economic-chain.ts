import { axisTone } from "./judgment-tone.mjs";
import type { FinancialModel } from "./financial-model";
import { arr, big, money, num, obj, pct, str } from "./report-format";

// The Economic map as one chain from what drives sales to what the price needs, ending in the card's own conclusion.
// Every number is a stored reading (filings, the card); tones only describe the direction of that number or reuse the
// card's axis tone. No new judgment rule lives here: the last step is the card's fixed-rule valuation sentence.

export type Tone = "supportive" | "against" | "mixed" | "unknown";
export type ChainStep = {
  key: string;
  title: string;
  value: string;
  sub: string | null;
  sentence: string;
  tone: Tone;
  how: string;
  missing?: boolean;
};
export type EngineChain = { steps: ChainStep[]; conclusion: { title: string; sentence: string; tone: Tone } | null; notInFilings: string[] };

const points = (v: number | null) => (v == null ? "—" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1)} pts`);
const signTone = (v: number | null, flat = 0.0025): Tone => (v == null ? "unknown" : v > flat ? "supportive" : v < -flat ? "against" : "mixed");

function missing(key: string, title: string, what: string, how: string): ChainStep {
  return { key, title, value: "Not in the filings", sub: null, sentence: `Not in the stored filings: ${what.charAt(0).toLowerCase()}${what.slice(1)}. This step is left open.`, tone: "unknown", how, missing: true };
}

export function buildEngineChain(m: FinancialModel): EngineChain {
  return m.isBank ? bankChain(m) : companyChain(m);
}

function companyChain(m: FinancialModel): EngineChain {
  const { revenue, opIncome, fcf, capex, quarter: q, currency } = m;
  const steps: ChainStep[] = [];
  const notInFilings: string[] = [];

  // 1. What drives sales
  const growing = m.segments.filter((s) => s.growth != null && !/percent/i.test(s.unit));
  const lead = growing.find((s) => /revenue|sales/i.test(s.name)) ?? growing[0];
  const salesGrowth = m.growth(0);
  const qYoy = num(q.revenue_yoy), qPrior = num(q.revenue_yoy_prior_quarter);
  const pace = qYoy != null && qPrior != null ? (qYoy > qPrior + 0.005 ? "speeding up" : qYoy < qPrior - 0.005 ? "slowing" : "steady") : null;
  if (revenue[0] != null) {
    const latest = lead?.periods.at(-1);
    const parts = [
      lead && latest ? `${lead.name}: ${latest.value.toLocaleString("en-US", { maximumFractionDigits: 1 })}${lead.unit.toLowerCase() === lead.name.toLowerCase() ? "" : ` ${lead.unit}`} in ${latest.period} (${pct(lead.growth, 0, true)}).` : null,
      `Total sales were ${big(revenue[0], currency)} in the latest year (${pct(salesGrowth, 0, true)}).`,
      qYoy != null ? `The latest quarter grew ${pct(qYoy, 0, true)} from a year earlier${qPrior != null ? `, against ${pct(qPrior, 0, true)} the quarter before (${pace})` : ""}.` : null,
    ];
    steps.push({
      key: "driver", title: "What drives sales",
      value: lead && latest ? `${lead.name} ${pct(lead.growth, 0, true)}` : `Sales ${pct(salesGrowth, 0, true)}`,
      sub: qYoy != null ? `Latest quarter ${pct(qYoy, 0, true)} y/y` : null,
      sentence: parts.filter(Boolean).join(" "),
      tone: signTone(qYoy ?? salesGrowth, 0.02),
      how: lead ? "Company-reported operating measure (earnings release or filing), plus annual sales from 10-K filings and the latest 10-Q." : "Annual sales from 10-K filings and the latest 10-Q. The company does not report a separate driver series that CHAINSTOX stores.",
    });
  } else {
    steps.push(missing("driver", "What drives sales", "Annual sales", "10-K filings."));
    notInFilings.push("annual sales history");
  }

  // 2. What could hold it back
  const signals = arr(m.operating.signals).map(obj);
  if (signals.length) {
    const against = signals.filter((s) => s.tone === "against");
    steps.push({
      key: "limits", title: "What could hold it back",
      value: against.length ? `${against.length} of ${signals.length} signals strained` : `No strain in ${signals.length} signals`,
      sub: str(m.operating.summary),
      sentence: against.length
        ? `${against.map((s) => `${str(s.label)}: ${String(str(s.reading) ?? "").toLowerCase()} (${pct(s.change, 0, true)} against sales ${pct(s.sales_change, 0, true)})`).join("; ")}.`
        : "Inventory, receivables and spending are moving in line with sales or better.",
      tone: against.length >= 2 ? "against" : against.length ? "mixed" : "supportive",
      how: "Each balance or cost line from SEC company facts (10-K/10-Q) against sales growth over the same period; the same signals as the Financials tab.",
    });
  } else {
    steps.push(missing("limits", "What could hold it back", "Inventory, receivables and spending lines", "SEC company facts."));
    notInFilings.push("operating signals");
  }

  // 3. Profit
  const marginNow = m.margin(opIncome, 0), marginPrev = m.margin(opIncome, 1);
  const marginYear = marginNow != null && marginPrev != null ? marginNow - marginPrev : null;
  const incremental = m.scaling.incremental_operating_margin ?? null;
  const qMargin = num(q.margin_change);
  if (marginNow != null) {
    steps.push({
      key: "profit", title: "Profit",
      value: `Operating margin ${pct(marginNow, 0)}`,
      sub: qMargin != null ? `Latest quarter ${points(qMargin)} y/y` : marginYear != null ? `${points(marginYear)} on the year` : null,
      sentence: [
        `Operating margin was ${pct(marginNow, 1)} in the latest year${marginPrev != null ? `, against ${pct(marginPrev, 1)} the year before` : ""}.`,
        incremental != null && salesGrowth != null && salesGrowth > 0 ? `Of each extra dollar of sales, about ${Math.round(incremental * 100)} cents became operating profit.` : null,
        qMargin != null ? `In the latest quarter the margin moved ${points(qMargin)} from a year earlier.` : null,
      ].filter(Boolean).join(" "),
      tone: signTone(qMargin ?? marginYear, 0.005),
      how: "Operating income divided by sales, from 10-K filings; extra-profit share = change in operating income over change in sales.",
    });
  } else {
    steps.push(missing("profit", "Profit", "Operating income", "10-K filings."));
    notInFilings.push("operating income");
  }

  // 4. Cash
  const fcfMargin = m.margin(fcf, 0);
  const capexGrowth = capex[0] != null && capex[1] != null && capex[1] !== 0 ? Math.abs(capex[0]) / Math.abs(capex[1]) - 1 : null;
  if (fcf[0] != null) {
    steps.push({
      key: "cash", title: "Cash",
      value: `Free cash flow ${big(fcf[0], currency)}`,
      sub: fcfMargin != null ? `${pct(fcfMargin, 0)} of sales` : null,
      sentence: [
        `After ${big(capex[0] != null ? Math.abs(capex[0]) : null, currency)} of capital spending, the company kept ${big(fcf[0], currency)} of free cash flow in the latest year${fcfMargin != null ? `, ${pct(fcfMargin, 1)} of sales` : ""}.`,
        capexGrowth != null && salesGrowth != null && capex[0] != null && revenue[0] && Math.abs(capex[0]) / revenue[0] >= 0.03 ? `Capital spending ${capexGrowth >= 0 ? "grew" : "fell"} ${pct(Math.abs(capexGrowth), 0)} while sales ${salesGrowth >= 0 ? "grew" : "fell"} ${pct(Math.abs(salesGrowth), 0)}.` : null,
      ].filter(Boolean).join(" "),
      tone: fcfMargin == null ? "unknown" : fcfMargin > 0.05 ? "supportive" : fcfMargin < 0 ? "against" : "mixed",
      how: "Operating cash flow minus capital spending, from 10-K cash-flow statements.",
    });
  } else {
    steps.push(missing("cash", "Cash", "Free cash flow", "10-K cash-flow statements."));
    notInFilings.push("free cash flow");
  }

  // 5. What the price needs
  const state = str(obj(m.axes.valuation).state);
  const maxCase = num(m.vdetail.price_to_max_case);
  steps.push({
    key: "price", title: "What the price needs",
    value: m.implied != null ? `${pct(m.implied, 0, true)} a year priced in` : maxCase != null ? `${maxCase.toFixed(1)}× the best case` : "No single reading",
    sub: m.refs.length ? `Business shows ${pct(m.refs[0], 0, true)}${m.refs.length > 1 && Math.abs(m.refs[1] - m.refs[0]) >= 0.005 ? ` to ${pct(m.refs[1], 0, true)}` : ""}` : null,
    sentence: m.implied != null
      ? `At ${m.price != null ? money(m.price, currency) : "today's price"} the shares need sales to grow about ${pct(m.implied, 0, true)} a year for five years.${m.refs.length ? ` Analysts' estimates and past growth, both faded over five years, point to ${pct(m.refs[0], 0, true)}${m.refs.length > 1 && Math.abs(m.refs[1] - m.refs[0]) >= 0.005 ? ` to ${pct(m.refs[1], 0, true)}` : ""}.` : ""}`
      : maxCase != null ? `The price is ${maxCase.toFixed(1)} times what even the model's highest growth case would justify.` : "The valuation model gives no single growth figure for this price.",
    tone: axisTone("valuation", state ?? "") as Tone,
    how: "Reverse DCF: the five-year sales growth that makes the CHAINSTOX cash-flow model equal today's price (Valuation tab).",
  });

  return { steps, conclusion: conclusionOf(m, state), notInFilings };
}

function bankChain(m: FinancialModel): EngineChain {
  const { metrics, bank, currency } = m;
  const steps: ChainStep[] = [];
  const notInFilings: string[] = [];
  const dep = num(metrics.deposits), depG = num(metrics.deposit_growth), loans = num(metrics.loans), loanG = num(metrics.loan_growth);
  if (dep != null) steps.push({ key: "deposits", title: "Deposits (the raw material)", value: big(dep, currency), sub: depG != null ? `${pct(depG, 1, true)} on the year` : null,
    sentence: `Customers hold ${big(dep, currency)} of deposits with the bank${depG != null ? `, ${pct(depG, 1, true)} from a year earlier` : ""}. Deposits are the cheap funding a bank lends out.`, tone: signTone(depG, 0.01), how: "SEC company facts (10-K/10-Q balance sheet)." });
  else { steps.push(missing("deposits", "Deposits (the raw material)", "Deposits", "SEC company facts.")); notInFilings.push("deposits"); }
  if (loans != null) steps.push({ key: "loans", title: "Loans (what it sells)", value: big(loans, currency), sub: loanG != null ? `${pct(loanG, 1, true)} on the year` : null,
    sentence: `The bank has ${big(loans, currency)} lent out${loanG != null ? `, ${pct(loanG, 1, true)} from a year earlier` : ""}${dep != null ? `, about ${Math.round((loans / dep) * 100)} cents of loans for each dollar of deposits` : ""}.`, tone: signTone(loanG, 0.01), how: "SEC company facts (10-K/10-Q balance sheet)." });
  else { steps.push(missing("loans", "Loans (what it sells)", "Loans", "SEC company facts.")); notInFilings.push("loans"); }
  const roe = num(bank.latest_roe);
  steps.push(roe != null ? { key: "roe", title: "Profit on its equity", value: `Return on equity ${pct(roe, 1)}`, sub: num(bank.cost_of_equity) != null ? `Cost of equity ${pct(bank.cost_of_equity, 1)}` : null,
    sentence: `The bank earned ${pct(roe, 1)} on its shareholders' equity in the latest year${num(bank.cost_of_equity) != null ? `, against the ${pct(bank.cost_of_equity, 1)} its shareholders require` : ""}.`, tone: num(bank.cost_of_equity) != null ? (roe > num(bank.cost_of_equity)! ? "supportive" : "against") : "unknown", how: "Latest annual net income to common shareholders over average common equity (10-K)." }
    : missing("roe", "Profit on its equity", "Return on equity", "10-K filings."));
  const state = str(obj(m.axes.valuation).state);
  steps.push({ key: "price", title: "What the price needs", value: num(bank.implied_roe) != null ? `Return on equity ${pct(bank.implied_roe, 1)} priced in` : "No reading",
    sub: num(bank.price_to_book) != null ? `${num(bank.price_to_book)!.toFixed(2)}× book value` : null,
    sentence: num(bank.implied_roe) != null ? `At ${num(bank.price_to_book) != null ? `${num(bank.price_to_book)!.toFixed(2)} times book value` : "today's price"} the shares need the bank to keep earning about ${pct(bank.implied_roe, 1)} on its equity${roe != null ? `, against ${pct(roe, 1)} earned in the latest year` : ""}.` : "The bank valuation gives no reading for this price.",
    tone: axisTone("valuation", state ?? "") as Tone, how: "Justified price-to-book: implied return on equity = long-run growth + price-to-book × (cost of equity − long-run growth)." });
  return { steps, conclusion: conclusionOf(m, state), notInFilings };
}

function conclusionOf(m: FinancialModel, state: string | null): EngineChain["conclusion"] {
  const sentences = arr(obj(m.card.conclusion).sentences).map(String);
  const valuationSentence = sentences.at(-1);
  if (!state && !valuationSentence) return null;
  const tone = axisTone("valuation", state ?? "") as Tone;
  const title = tone === "supportive" ? "The business supports more than the price assumes"
    : tone === "against" ? "The price assumes more than the business has shown"
    : state && /roughly/i.test(state) ? "The price and the business roughly match" : state ?? "No single reading";
  return { title, sentence: valuationSentence ?? state ?? "", tone };
}
