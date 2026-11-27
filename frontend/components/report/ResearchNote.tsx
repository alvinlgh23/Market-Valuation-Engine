import { arr, big, money, num, obj, pct, pick, str, type PriceChart, type ReportData } from "../../lib/report-data";

// The downloadable research note, laid out like a sell-side equity research report: a first page with headline,
// key takeaways and a data sidebar; numbered exhibits with sources; a financial summary; important disclosures.
// CHAINSTOX branding only. No rating or price target: the product describes data and gives no recommendation, so the
// rating slot shows what the price assumes. Judgments come from the card's fixed rules; commentary from the checked
// AI write-up (labelled); the only arithmetic here is simple ratios of reported figures.

const AGREEMENT: Record<string, string> = {
  OPPOSED: "Price and business disagree", LEANS_OPPOSED: "Price leans against the business", ALIGNED: "Price and business agree",
  LEANS_ALIGNED: "Price leans with the business", OUTSIDE: "Price moved with outside forces", UNCLEAR: "No clear reading",
};
const AXES: Array<[string, string, string]> = [
  ["fundamentals", "Fundamentals", "6–12m"], ["expectations", "Estimates", "6–12m"], ["macro", "Macro", "6–12m"],
  ["flow", "Money flow", "1–3m"], ["crowding", "Crowding", "1–3m"], ["valuation", "Valuation", "3–5y"],
];

function dateText(value: unknown, style: "short" | "long" = "short"): string {
  const text = str(value);
  if (!text) return "—";
  const d = new Date(text.length <= 10 ? `${text}T12:00:00` : text);
  if (Number.isNaN(d.getTime())) return text;
  return d.toLocaleDateString("en-GB", style === "long" ? { day: "numeric", month: "long", year: "numeric" } : { day: "numeric", month: "short", year: "numeric" });
}

function Exhibit({ n, title, source, children }: { n: number; title: string; source: string; children: React.ReactNode }) {
  return <figure className="ib-exhibit"><figcaption><b>Exhibit {n}:</b> {title}</figcaption>{children}<p className="ib-src">Source: {source}</p></figure>;
}

function Box({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="ib-box"><h4>{title}</h4>{children}</section>;
}

function Chart({ chart, ticker }: { chart: PriceChart; ticker: string }) {
  const w = 300, h = 130, pad = 4;
  const all = [...chart.stock, ...chart.index];
  const lo = Math.min(...all), hi = Math.max(...all);
  const x = (i: number) => pad + (i / (chart.dates.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - lo) / (hi - lo || 1)) * (h - 2 * pad);
  const line = (series: number[]) => series.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const ticks = [0, Math.floor(chart.dates.length / 2), chart.dates.length - 1];
  return <svg viewBox={`0 0 ${w} ${h + 14}`} className="ib-chart" role="img" aria-label={`${ticker} against the S&P 500, rebased to 100`}>
    <line x1={pad} x2={w - pad} y1={y(100)} y2={y(100)} className="ib-chart-base" />
    <path d={line(chart.index)} className="ib-chart-index" />
    <path d={line(chart.stock)} className="ib-chart-stock" />
    {ticks.map((i) => <text key={i} x={x(i)} y={h + 11} textAnchor={i === 0 ? "start" : i === chart.dates.length - 1 ? "end" : "middle"}>{dateText(chart.dates[i]).replace(/^\d+ /, "")}</text>)}
  </svg>;
}

export function ResearchNote({ data }: { data: ReportData }) {
  const card = obj(data.card);
  const report = data.valuation;
  const axes = obj(card.axes);
  const vdetail = obj(pick(axes, "valuation", "detail"));
  const quarter = obj(pick(axes, "fundamentals", "detail", "quarterly"));
  const edetail = obj(pick(axes, "expectations", "detail"));
  const currency = str(report?.company.currency) ?? "USD";
  const price = num(vdetail.price) ?? num(report?.company.current_market_price);
  const name = str(card.name) ?? str(report?.company.name) ?? data.ticker;
  const metrics = obj(data.snapshot?.metrics);
  const conclusion = obj(card.conclusion);
  const short = obj(conclusion.short);
  const reading = obj(card.price_reading);
  const parts = obj(reading.parts);
  const since = obj(pick(card, "attribution", "recent_move", "since_window_end"));
  const fair = obj(vdetail.fair_value);
  const band = obj(vdetail.growth_band);
  const bank = obj(vdetail.bank_implied_roe);
  const isBank = num(bank.implied_roe) != null;
  const ai = obj(card.ai);
  const writeup = obj(ai.writeup);
  const review = obj(ai.review);
  const operating = obj(card.operating);
  const histories = obj(data.snapshot?.histories);
  const revenue = arr(histories.revenue).map(num);
  const opIncome = arr(histories.operating_income).map(num);
  const ocf = arr(histories.operating_cash_flow).map(num);
  const capex = arr(histories.capex).map(num);
  const fcf = arr(histories.fcf).map(num);
  const years = Math.min(4, revenue.length);
  const cols = Array.from({ length: years }, (_, i) => i);
  const growth = (i: number) => (revenue[i] != null && revenue[i + 1] != null && revenue[i + 1]! > 0 ? revenue[i]! / revenue[i + 1]! - 1 : null);
  const margin = (series: Array<number | null>, i: number) => (series[i] != null && revenue[i] ? series[i]! / revenue[i]! : null);
  const shares = arr(report?.historical_base.diluted_share_history).map(num).filter((v): v is number => v != null && v > 0);
  const dilution = shares.length >= 2 ? Math.pow(shares[0] / shares[shares.length - 1], 1 / (shares.length - 1)) - 1 : null;
  const sens = obj(report?.sensitivity);
  const sensWacc = arr(sens.wacc).map(num);
  const sensTg = arr(sens.terminal_growth).map(num);
  const sensValues = arr(sens.values).map((row) => arr(row).map(num));
  const reverse = obj(report?.fair_value?.method === "PHASED" && report?.fair_value.reverse_dcf ? report.fair_value.reverse_dcf : report?.reverse_dcf);
  const implied = num(vdetail.implied_5y_revenue_cagr) ?? num(reverse.required_5y_revenue_cagr);
  const refs = [num(band.consensus_2y_faded), num(band.history_3y_faded)].filter((v): v is number => v != null).sort((a, b) => a - b);
  const sentences = arr(conclusion.sentences).map(String);
  const agreement = AGREEMENT[String(conclusion.agreement)] ?? null;
  const valueLine = str(short.value);
  const headline = [agreement, valueLine].filter(Boolean).join("; the market ") || `${name}: research note`;
  const notCovered: string[] = [];
  for (const [key, label] of AXES) for (const item of arr(pick(axes, key, "missing"))) if (str(item)) notCovered.push(`${label}: ${item}`);
  const sector = [str(card.archetype)?.replaceAll("_", " ").toLowerCase(), str(card.sector_etf)].filter(Boolean).join(" · ");
  let exhibit = data.chart ? 1 : 0;
  const next = () => ++exhibit;

  return <article className="rn-doc ib">
    {/* ---------------- Page 1 ---------------- */}
    <header className="ib-band">
      <div><b>CHAINSTOX</b> Equity Research</div>
      <div>Company Note</div>
      <div>{dateText(data.generatedAt, "long")}</div>
    </header>
    <div className="ib-meta"><span>United States</span><span>{sector}</span></div>
    <div className="ib-titleblock">
      <div>
        <h1>{name}</h1>
        <p className="ib-ticker">{data.ticker} · {money(price, currency)} · data as of {dateText(card.generated_on)}</p>
      </div>
      <div className="ib-rating">
        <span>{isBank ? "Return on equity the price assumes" : "Sales growth the price assumes"}</span>
        <b>{isBank ? pct(bank.implied_roe) : implied != null ? `${pct(implied, 1, true)} / yr` : num(vdetail.price_to_max_case) != null ? `>${num(vdetail.price_to_max_case)!.toFixed(1)}× best case` : "—"}</b>
        <small>{isBank ? `Bank earns ${pct(bank.latest_roe)}` : refs.length ? `Business shows ${pct(refs[0], 1, true)}${refs.length > 1 && Math.abs(refs[1] - refs[0]) >= 0.005 ? ` to ${pct(refs[1], 1, true)}` : ""}` : "No rating or price target"}</small>
      </div>
    </div>
    <h2 className="ib-headline">{headline}</h2>

    <div className="ib-p1">
      <div className="ib-main">
        <h3 className="ib-kicker">Key takeaways</h3>
        <ul className="ib-takeaways">
          {sentences.slice(0, 1).map((s, i) => <li key={`b${i}`}><b>The business.</b> {s}</li>)}
          {sentences.length > 1 ? <li><b>The price.</b> {sentences.slice(1, sentences.length - 1).join(" ")}</li> : null}
          {sentences.length > 2 ? <li><b>Valuation.</b> {sentences[sentences.length - 1]}</li> : null}
        </ul>
        {str(writeup.business) ? <>
          <h3 className="ib-kicker">Discussion <span className="ib-ai">AI commentary · not counted in any reading</span></h3>
          <p>{String(writeup.business)}</p>
          <p>{String(writeup.price)}</p>
        </> : null}
        <p className="ib-src">Takeaways are built by fixed, versioned rules from the readings in this note; a description of the data, not a forecast or a recommendation.</p>
      </div>
      <aside className="ib-side">
        {data.chart ? <Box title={`Exhibit 1: ${data.ticker} vs S&P 500 (rebased to 100)`}>
          <Chart chart={data.chart} ticker={data.ticker} />
          <p className="ib-legend"><i className="ib-l-stock" />{data.ticker} <i className="ib-l-index" />S&amp;P 500 (SPY)</p>
          <p className="ib-src">Source: Yahoo Finance daily closes, 1 year.</p>
        </Box> : null}
        <Box title="Stock data">
          <dl className="ib-kv">
            <div><dt>Price</dt><dd>{money(price, currency)}</dd></div>
            <div><dt>3-month change</dt><dd>{pct(reading.price_change, 1, true)}</dd></div>
            {num(since.stock_change) != null ? <div><dt>Since {dateText(since.from).replace(/ \d{4}$/, "")}</dt><dd>{pct(since.stock_change, 1, true)}</dd></div> : null}
            <div><dt>Market cap</dt><dd>{big(metrics.market_cap, currency)}</dd></div>
            {isBank ? <><div><dt>Deposits, 1-yr change</dt><dd>{pct(metrics.deposit_growth, 1, true)}</dd></div><div><dt>Loans, 1-yr change</dt><dd>{pct(metrics.loan_growth, 1, true)}</dd></div></>
              : <div><dt>Net debt</dt><dd>{big(quarter.net_debt, currency)}</dd></div>}
            <div><dt>Shares, yearly change</dt><dd>{pct(dilution, 1, true)}</dd></div>
            <div><dt>Next earnings</dt><dd>{dateText(pick(card, "next_catalysts", "earnings"))}</dd></div>
          </dl>
        </Box>
        {years >= 2 ? <Box title={`Financial summary (${currency})`}>
          <table className="ib-mini">
            <thead><tr><th>FY</th>{cols.slice(0, 3).map((i) => <th key={i}>{i === 0 ? "Latest" : `−${i}`}</th>)}</tr></thead>
            <tbody>
              <tr><td>Revenue</td>{cols.slice(0, 3).map((i) => <td key={i}>{big(revenue[i], currency).replace(/^\$/, "")}</td>)}</tr>
              <tr><td>Growth</td>{cols.slice(0, 3).map((i) => <td key={i}>{pct(growth(i), 1, true)}</td>)}</tr>
              {!isBank ? <>
                <tr><td>Op. margin</td>{cols.slice(0, 3).map((i) => <td key={i}>{pct(margin(opIncome, i))}</td>)}</tr>
                <tr><td>FCF margin</td>{cols.slice(0, 3).map((i) => <td key={i}>{pct(margin(fcf, i))}</td>)}</tr>
              </> : null}
            </tbody>
          </table>
        </Box> : null}
        <Box title="The six readings">
          <table className="ib-mini ib-readings"><tbody>{AXES.map(([key, label, horizon]) => <tr key={key}><td>{label} <small>{horizon}</small></td><td>{str(pick(axes, key, "state")) ?? "—"}</td></tr>)}</tbody></table>
        </Box>
      </aside>
    </div>

    {/* ---------------- Valuation ---------------- */}
    <section className="ib-section ib-break">
      <h3 className="ib-h">Valuation: what the price assumes</h3>
      {isBank ? <>
        <p>At {num(bank.price_to_book) != null ? `${num(bank.price_to_book)!.toFixed(2)}x book value` : "today's price"}, the shares assume a {pct(bank.implied_roe)} return on equity, against {pct(bank.latest_roe)} earned in the latest year. Banks are read on what their equity earns rather than with a cash-flow model.</p>
        <Exhibit n={next()} title="Justified price-to-book reading" source="Company filings, Yahoo Finance; CHAINSTOX. Implied ROE = g + P/B × (cost of equity − g).">
          <table className="ib-table"><thead><tr><th>Measure</th><th>Value</th></tr></thead><tbody>
            <tr><td>Price-to-book</td><td>{num(bank.price_to_book) != null ? `${num(bank.price_to_book)!.toFixed(2)}x` : "—"}</td></tr>
            <tr><td>Return on equity the price assumes</td><td>{pct(bank.implied_roe)}</td></tr>
            <tr><td>Return on equity, latest year</td><td>{pct(bank.latest_roe)}</td></tr>
            <tr><td>Cost of equity</td><td>{pct(bank.cost_of_equity)}</td></tr>
            <tr><td>Long-run growth</td><td>{pct(bank.long_run_growth)}</td></tr>
          </tbody></table>
        </Exhibit>
      </> : <>
        <p>We do not set a price target. Instead we solve for the five-year sales growth today&apos;s price requires and compare it with what the business has shown, with analysts&apos; and past growth both faded to 2.5% by year five. Reading: <b>{str(pick(axes, "valuation", "state")) ?? "—"}</b>.</p>
        <Exhibit n={next()} title="Five-year sales growth: priced in versus shown" source="Company filings, Yahoo Finance consensus; CHAINSTOX reverse DCF.">
          <table className="ib-table"><thead><tr><th>Five-year sales growth</th><th>Per year</th></tr></thead><tbody>
            <tr><td>Priced in at {money(price, currency)} (reverse DCF)</td><td>{implied != null ? pct(implied, 1, true) : num(vdetail.price_to_max_case) != null ? `above model best case (${num(vdetail.price_to_max_case)!.toFixed(1)}x)` : "—"}</td></tr>
            <tr><td>Analysts&apos; two-year growth, faded</td><td>{pct(band.consensus_2y_faded, 1, true)}</td></tr>
            <tr><td>Past three-year growth, faded</td><td>{pct(band.history_3y_faded, 1, true)}</td></tr>
            {refs.length ? <tr className="ib-total"><td>Range read as &ldquo;roughly in line&rdquo;</td><td>{pct(refs[0] - 0.05, 1, true)} to {pct(refs[refs.length - 1] + 0.05, 1, true)}</td></tr> : null}
          </tbody></table>
        </Exhibit>
        {num(fair.base) != null ? <Exhibit n={next()} title="Model value per share under three sets of assumptions (not a price target)" source="CHAINSTOX five-year FCFF model; company filings.">
          <table className="ib-table"><thead><tr><th /><th>Low case</th><th>Middle case</th><th>High case</th><th>Share price</th></tr></thead><tbody>
            <tr><td>Value per share</td><td>{money(fair.bear, currency)}</td><td>{money(fair.base, currency)}</td><td>{money(fair.bull, currency)}</td><td>{money(price, currency)}</td></tr>
          </tbody></table>
        </Exhibit> : null}
        {sensWacc.length && sensTg.length && sensValues.length ? <Exhibit n={next()} title="Middle-case value per share: discount rate (rows) vs long-run growth (columns)" source={`CHAINSTOX FCFF model. Base discount rate ${pct(vdetail.wacc)}, fixed ${pct(vdetail.fixed_erp)} equity risk premium.`}>
          <table className="ib-table ib-sens"><thead><tr><th />{sensTg.map((g, j) => <th key={j}>{pct(g)}</th>)}</tr></thead>
            <tbody>{sensWacc.map((w, i) => <tr key={i}><th>{pct(w)}</th>{sensTg.map((_, j) => <td key={j}>{money(sensValues[i]?.[j], currency)}</td>)}</tr>)}</tbody></table>
        </Exhibit> : null}
      </>}
    </section>

    {/* ---------------- Financials ---------------- */}
    <section className="ib-section">
      <h3 className="ib-h">Financial summary</h3>
      {str(quarter.summary) ? <p><b>Latest quarter.</b> {String(quarter.summary)}</p> : null}
      {years >= 2 ? <Exhibit n={next()} title={`Annual financial summary (${currency}, fiscal years, newest first)`} source={isBank ? "Company filings via structured data provider. Bank cash flows swing with deposits and lending, so cash-flow lines are not shown." : "Company filings via structured data provider; CHAINSTOX. Free cash flow is after capital spending."}>
        <table className="ib-table ib-fin"><thead><tr><th>Fiscal year</th>{cols.map((i) => <th key={i}>{i === 0 ? "Latest" : `FY −${i}`}</th>)}</tr></thead><tbody>
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
        </tbody></table>
      </Exhibit> : null}
      {isBank ? <Exhibit n={next()} title="Balance sheet and estimates" source="SEC company facts (10-K/10-Q); Yahoo Finance; CHAINSTOX justified price-to-book.">
        <table className="ib-table"><tbody>
          <tr><td>Deposits</td><td>{big(metrics.deposits, currency)}</td><td>Change from a year earlier</td><td>{pct(metrics.deposit_growth, 1, true)}</td></tr>
          <tr><td>Loans</td><td>{big(metrics.loans, currency)}</td><td>Change from a year earlier</td><td>{pct(metrics.loan_growth, 1, true)}</td></tr>
          <tr><td>Return on equity, latest year</td><td>{pct(bank.latest_roe)}</td><td>Price-to-book</td><td>{num(bank.price_to_book) != null ? `${num(bank.price_to_book)!.toFixed(2)}x` : "—"}</td></tr>
          <tr><td>Analyst revisions, 30 days</td><td>{num(edetail.revisions_up_30d) != null ? `${edetail.revisions_up_30d} up / ${edetail.revisions_down_30d} down` : "—"}</td><td>Consensus revenue growth, next year</td><td>{pct(edetail.revenue_growth_next_year ?? vdetail.consensus_next_year_growth, 1, true)}</td></tr>
        </tbody></table>
      </Exhibit> : <Exhibit n={next()} title="Balance sheet and estimates" source="Latest 10-Q/10-K; Yahoo Finance analyst revisions.">
        <table className="ib-table"><tbody>
          <tr><td>Free cash flow, last four quarters</td><td>{big(quarter.fcf_ttm, currency)}</td><td>Net debt</td><td>{big(quarter.net_debt, currency)}</td></tr>
          <tr><td>Financial health</td><td>{str(pick(quarter, "health", "label")) ?? "—"}</td><td>Diluted shares, yearly change</td><td>{dilution != null ? `${pct(dilution, 1, true)} (${shares.length - 1}y)` : "—"}</td></tr>
          <tr><td>Analyst revisions, 30 days</td><td>{num(edetail.revisions_up_30d) != null ? `${edetail.revisions_up_30d} up / ${edetail.revisions_down_30d} down` : "—"}</td><td>Consensus sales growth, next year</td><td>{pct(edetail.revenue_growth_next_year ?? vdetail.consensus_next_year_growth, 1, true)}</td></tr>
        </tbody></table>
      </Exhibit>}
      {arr(operating.signals).length ? <Exhibit n={next()} title={`Operating signals: ${str(operating.summary) ?? ""}`} source="SEC company facts (10-K/10-Q); each measure against sales growth over the same period.">
        <table className="ib-table"><thead><tr><th>Measure</th><th>Change</th><th>Sales</th><th>Reading</th><th>Period</th></tr></thead>
          <tbody>{arr(operating.signals).map((raw, i) => { const s = obj(raw); return <tr key={i}><td>{str(s.label)}</td><td>{pct(s.change, 0, true)}</td><td>{pct(s.sales_change, 0, true)}</td><td>{str(s.reading)}</td><td>{str(s.basis)}, {dateText(s.as_of)}</td></tr>; })}</tbody></table>
      </Exhibit> : null}
    </section>

    {/* ---------------- Price drivers ---------------- */}
    <section className="ib-section">
      <h3 className="ib-h">What moved the shares</h3>
      <p>{str(reading.label) ? `${String(reading.label)}.` : ""} {num(since.stock_change) != null ? `Since ${dateText(since.from)} the shares have moved ${pct(since.stock_change, 1, true)} against the S&P 500's ${pct(since.spy_change, 1, true)}, not yet in the split.` : ""}</p>
      <Exhibit n={next()} title="Three-month price change by source" source={`Weekly regression on the market, an equal-weight sector basket and mapped macro factors; parts add up to the total. ${str(reading.low_fit_note) ?? ""}`}>
        <table className="ib-table"><thead><tr><th /><th>Total</th><th>Macro</th><th>Market</th><th>Sector</th><th>Company</th></tr></thead>
          <tbody><tr><td>Three months to {dateText(pick(card, "attribution", "as_of"))}</td><td>{pct(reading.price_change, 1, true)}</td><td>{pct(parts.macro, 1, true)}</td><td>{pct(parts.market, 1, true)}</td><td>{pct(parts.sector, 1, true)}</td><td>{pct(parts.company, 1, true)}</td></tr></tbody></table>
      </Exhibit>
      {arr(pick(axes, "macro", "evidence")).length ? <p className="ib-src">Macro exposure: {arr(pick(axes, "macro", "evidence")).map(String).join(" · ")}</p> : null}
    </section>

    {/* ---------------- Management & filing review (AI) ---------------- */}
    {arr(writeup.management).length || arr(review.notes).length || str(writeup.macro) ? <section className="ib-section">
      <h3 className="ib-h">Management commentary and filing review <span className="ib-ai">AI · not counted in any reading</span></h3>
      {str(writeup.macro) ? <p><b>Macro.</b> {String(writeup.macro)}</p> : null}
      {arr(writeup.management).map((raw, i) => { const m = obj(raw); return <figure className="ib-quote" key={`m${i}`}><p>{str(m.point)}</p><blockquote>&ldquo;{str(m.quote)}&rdquo;</blockquote></figure>; })}
      {arr(review.notes).map((raw, i) => { const n = obj(raw); return <figure className="ib-quote" key={`r${i}`}><p><b>Filing review.</b> {str(n.note)}</p><blockquote>&ldquo;{str(n.quote)}&rdquo;</blockquote></figure>; })}
      <p className="ib-src">Written by {[str(writeup.model), str(review.model)].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(" and ")}. Quotes are checked word for word against the company&apos;s {str(pick(review, "source", "form")) ?? str(pick(writeup, "source", "form")) ?? "filing"}; every number is checked against this note&apos;s data.</p>
    </section> : null}

    {/* ---------------- Risks ---------------- */}
    <section className="ib-section">
      <h3 className="ib-h">Risks and what would change the view</h3>
      <ul className="ib-list">{arr(card.falsification).map((item, i) => <li key={i}>{String(item)}</li>)}</ul>
      {str(pick(card, "valuation_record", "text")) ? <p className="ib-src"><b>Track record of this reading.</b> {String(pick(card, "valuation_record", "text"))}</p> : null}
    </section>

    {/* ---------------- Appendix & disclosures ---------------- */}
    <section className="ib-section ib-break ib-appendix">
      <h3 className="ib-h">Appendix: methodology and data</h3>
      <ul className="ib-list">
        <li><b>Readings.</b> Six axes (fundamentals, estimates, macro, money flow, crowding, valuation) from fixed, versioned rules; the same inputs always give the same reading, and each reading is stored with its rules version.</li>
        <li><b>Valuation.</b> Five-year free-cash-flow-to-firm model with three sets of assumptions; model values are not price targets. Reverse DCF solves for the growth the price requires. Banks: justified price-to-book.</li>
        <li><b>Price attribution.</b> Weekly regression of the share price on the market, an equal-weight sector basket and mapped macro factors over three months.</li>
        <li><b>Data.</b> SEC filings (10-K, 10-Q), Yahoo Finance (prices, consensus), FRED and central-bank sources (macro). Card {dateText(card.generated_on)}; macro data to {dateText(card.environment_as_of)}; valuation {str(report?.company.as_of) ?? "—"}.</li>
        {notCovered.length ? <li><b>Not covered.</b> {notCovered.slice(0, 8).join("; ")}.</li> : null}
      </ul>
      <h3 className="ib-h">Important disclosures</h3>
      <p className="ib-disclosure">This report is produced by CHAINSTOX from public data using fixed rules and, where labelled, AI-written commentary whose quotations and figures are checked against the cited filings and this report&apos;s data. It is a research map, not investment advice, and not a recommendation or an offer to buy or sell any security. CHAINSTOX issues no ratings or price targets. Figures may contain errors from data providers; past readings do not guarantee future results. Verify against the cited filings before relying on any figure.</p>
    </section>
  </article>;
}
