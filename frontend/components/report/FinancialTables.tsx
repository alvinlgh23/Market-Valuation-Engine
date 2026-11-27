import type { FinancialModel, Segment } from "../../lib/financial-model";
import { arr, big, num, obj, pct, pick, str } from "../../lib/report-format";

// Financial tables shared by the downloadable research note and the Financials tab, so both always show the same
// figures. Plain tables only; the caller adds the exhibit caption (note) or section heading (site).

const x2 = (value: unknown) => (num(value) != null ? `${num(value)!.toFixed(2)}x` : "—");

export function AnnualTable({ m }: { m: FinancialModel }) {
  const { cols, currency, isBank, revenue, opIncome, ocf, capex, fcf, growth, margin } = m;
  return <table className="ib-table ib-fin">
    <thead><tr><th>Fiscal year</th>{cols.map((i) => <th key={i}>{i === 0 ? "Latest" : `FY −${i}`}</th>)}</tr></thead>
    <tbody>
      <tr><td>Revenue</td>{cols.map((i) => <td key={i}>{big(revenue[i], currency)}</td>)}</tr>
      <tr className="ib-subrow"><td>% growth</td>{cols.map((i) => <td key={i}>{pct(growth(i), 1, true)}</td>)}</tr>
      {!isBank ? <>
        <tr><td>Operating income</td>{cols.map((i) => <td key={i}>{big(opIncome[i], currency)}</td>)}</tr>
        <tr className="ib-subrow"><td>% margin</td>{cols.map((i) => <td key={i}>{pct(margin(opIncome, i))}</td>)}</tr>
        <tr><td>Operating cash flow</td>{cols.map((i) => <td key={i}>{big(ocf[i], currency)}</td>)}</tr>
        <tr><td>Capital spending</td>{cols.map((i) => <td key={i}>{big(capex[i], currency)}</td>)}</tr>
        <tr className="ib-total"><td>Free cash flow</td>{cols.map((i) => <td key={i}>{big(fcf[i], currency)}</td>)}</tr>
        <tr className="ib-subrow"><td>% margin</td>{cols.map((i) => <td key={i}>{pct(margin(fcf, i))}</td>)}</tr>
      </> : null}
    </tbody>
  </table>;
}

export function annualSource(m: FinancialModel) {
  return m.isBank
    ? "Company filings via structured data provider. Bank cash flows swing with deposits and lending, so cash-flow lines are not shown."
    : "Company filings via structured data provider; CHAINSTOX. Free cash flow is after capital spending.";
}

export function BalanceTable({ m }: { m: FinancialModel }) {
  const { metrics, bank, quarter, edetail, vdetail, currency, dilution, shares } = m;
  const revisions = num(edetail.revisions_up_30d) != null ? `${edetail.revisions_up_30d} up / ${edetail.revisions_down_30d} down` : "—";
  const nextYear = pct(edetail.revenue_growth_next_year ?? vdetail.consensus_next_year_growth, 1, true);
  if (m.isBank) return <table className="ib-table"><tbody>
    <tr><td>Deposits</td><td>{big(metrics.deposits, currency)}</td><td>Change from a year earlier</td><td>{pct(metrics.deposit_growth, 1, true)}</td></tr>
    <tr><td>Loans</td><td>{big(metrics.loans, currency)}</td><td>Change from a year earlier</td><td>{pct(metrics.loan_growth, 1, true)}</td></tr>
    <tr><td>Return on equity, latest year</td><td>{pct(bank.latest_roe)}</td><td>Price-to-book</td><td>{x2(bank.price_to_book)}</td></tr>
    <tr><td>Analyst revisions, 30 days</td><td>{revisions}</td><td>Consensus revenue growth, next year</td><td>{nextYear}</td></tr>
  </tbody></table>;
  return <table className="ib-table"><tbody>
    <tr><td>Free cash flow, last four quarters</td><td>{big(quarter.fcf_ttm, currency)}</td><td>Net debt</td><td>{big(quarter.net_debt, currency)}</td></tr>
    <tr><td>Financial health</td><td>{str(pick(quarter, "health", "label")) ?? "—"}</td><td>Diluted shares, yearly change</td><td>{dilution != null ? `${pct(dilution, 1, true)} (${shares.length - 1}y)` : "—"}</td></tr>
    <tr><td>Analyst revisions, 30 days</td><td>{revisions}</td><td>Consensus sales growth, next year</td><td>{nextYear}</td></tr>
    {m.scaling.revenue_per_employee != null ? <tr><td>Revenue per employee, latest year</td><td>{big(m.scaling.revenue_per_employee, currency)}</td><td /><td /></tr> : null}
  </tbody></table>;
}

export function balanceSource(m: FinancialModel) {
  return m.isBank ? "SEC company facts (10-K/10-Q); Yahoo Finance; CHAINSTOX justified price-to-book." : "Latest 10-Q/10-K; Yahoo Finance analyst revisions.";
}

/** Latest quarter against the same quarter a year earlier, from the card's quarterly read. */
export function QuarterTable({ m }: { m: FinancialModel }) {
  const q = m.quarter;
  if (!str(q.quarter) && num(q.revenue_yoy) == null) return null;
  const points = (v: unknown) => (num(v) != null ? `${num(v)! >= 0 ? "+" : "−"}${Math.abs(num(v)! * 100).toFixed(1)} pts` : "—");
  return <table className="ib-table"><tbody>
    <tr><td>Sales vs a year earlier</td><td>{pct(q.revenue_yoy, 1, true)}</td>{num(q.revenue_yoy_prior_quarter) != null ? <><td>Previous quarter</td><td>{pct(q.revenue_yoy_prior_quarter, 1, true)}</td></> : <><td>Quarter ended</td><td>{str(q.quarter) ?? "—"}</td></>}</tr>
    <tr><td>Operating margin</td><td>{pct(q.operating_margin)}</td><td>Change vs a year earlier</td><td>{points(q.margin_change)}</td></tr>
    <tr><td>Earnings per share</td><td>{num(q.eps_actual) != null ? num(q.eps_actual)!.toFixed(2) : "—"}</td><td>Against estimate</td><td>{num(q.eps_estimate) != null ? `${num(q.eps_estimate)!.toFixed(2)} (${pct(q.eps_surprise, 1, true)})` : "—"}</td></tr>
    <tr><td>Free cash flow, quarter</td><td>{big(q.fcf_quarter, m.currency)}</td><td>Free cash flow, last four quarters</td><td>{big(q.fcf_ttm, m.currency)}</td></tr>
  </tbody></table>;
}

/** Company-reported operating series (segments and unit counts) — only what the company itself publishes. */
export function SegmentTable({ segments }: { segments: Segment[] }) {
  if (!segments.length) return null;
  const periods = Array.from(new Set(segments.flatMap((s) => s.periods.map((p) => p.period)))).slice(-4);
  return <table className="ib-table">
    <thead><tr><th>Company-reported measure</th>{periods.map((p) => <th key={p}>{p}</th>)}<th>Change</th></tr></thead>
    <tbody>{segments.map((s) => <tr key={s.name}>
      <td>{s.name} <small>({s.unit})</small></td>
      {periods.map((p) => { const v = s.periods.find((o) => o.period === p)?.value; return <td key={p}>{v != null ? v.toLocaleString("en-US", { maximumFractionDigits: 1 }) : "—"}</td>; })}
      <td>{pct(s.growth, 1, true)}</td>
    </tr>)}</tbody>
  </table>;
}

export function segmentSource(segments: Segment[]) {
  const sources = Array.from(new Set(segments.map((s) => s.source).filter(Boolean)));
  return `Company disclosures${sources.length ? ` (${sources.slice(0, 2).join("; ")})` : ""}. Reported by the company; not every measure is an audited segment.`;
}

export function signalRows(m: FinancialModel) {
  return arr(m.operating.signals).map(obj);
}
