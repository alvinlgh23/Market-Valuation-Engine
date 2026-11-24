import type { MacroCoverage } from "../../lib/macro-types";

// Coverage is calculated from the engines' configured indicators (macro_world.region_coverage),
// so the bar shows exactly what is measured, what is missing, and how old the data is.
const STATE_LABEL: Record<string, string> = { FULL: "all indicators", PARTIAL: "some missing", STALE: "uses out-of-date data", MISSING: "no data", NOT_COVERED: "not modelled" };
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function shortDate(value: string | null | undefined): string {
  if (!value) return "no date";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return value;
  return `${MONTHS[month - 1]} ${day}${year === new Date().getFullYear() ? "" : `, ${year}`}`;
}

function ageDays(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value.slice(0, 10));
  return Number.isNaN(parsed) ? null : Math.floor((Date.now() - parsed) / 86_400_000);
}

function tooltip(coverage: MacroCoverage): string {
  const rows = coverage.areas.map((area) => `${area.label}: ${area.state === "NOT_COVERED" ? "not modelled" : `${area.available}/${area.expected}`}${area.stale?.length ? " · out-of-date input" : ""}`);
  const age = ageDays(coverage.as_of);
  const stale = coverage.stale_inputs?.length ? [`${coverage.stale_inputs.length} input(s) out of date`] : [];
  return [`${coverage.available} of ${coverage.expected} configured indicators`, ...rows, ...stale, `Latest data: ${coverage.as_of ?? "unknown"}${age === null ? "" : ` (${age} days old)`}`].join("\n");
}

export function CoverageBar({ coverage }: { coverage?: MacroCoverage | null }) {
  if (!coverage) return <span className="cov-bar cov-none">No coverage record</span>;
  return <span className="cov-bar" title={tooltip(coverage)} aria-label={`${coverage.available} of ${coverage.expected} indicators; data from ${coverage.as_of ?? "unknown date"}`}>
    <span className="cov-segments">{coverage.areas.map((area) => <i key={area.id} className={`cov-seg cov-${area.state.toLowerCase()}`} />)}</span>
    <b>{coverage.available}/{coverage.expected}</b>
    <small className={`cov-date cov-age-${coverage.freshness.toLowerCase()}`}>{shortDate(coverage.as_of)}</small>
    {coverage.stale_inputs?.length ? <small className="cov-stale-count" title="Inputs whose latest observation is older than their publication frequency allows">{coverage.stale_inputs.length} old</small> : null}
  </span>;
}

export function CoverageDetail({ coverage }: { coverage?: MacroCoverage | null }) {
  if (!coverage) return null;
  const age = ageDays(coverage.as_of);
  const range = coverage.newest && coverage.newest !== coverage.as_of ? `${shortDate(coverage.as_of)} – ${shortDate(coverage.newest)}` : shortDate(coverage.as_of);
  return <section className="cov-detail" aria-label="Data coverage">
    <header>
      <strong>{coverage.available}<span>/{coverage.expected}</span></strong>
      <span>indicators</span>
      <em className={`cov-date cov-age-${coverage.freshness.toLowerCase()}`} title="Latest data date (the earliest source when several are combined); newest after the dash">{range}{age !== null && coverage.freshness === "STALE" ? ` · ${age} days old` : ""}</em>
    </header>
    <div className="cov-areas">
      {coverage.areas.map((area) => <div key={area.id} className={`cov-area cov-${area.state.toLowerCase()}`} title={[area.missing.length ? `Missing: ${area.missing.join(", ")}` : STATE_LABEL[area.state], area.stale?.length ? `Out of date: ${area.stale.join(", ")}` : ""].filter(Boolean).join("\n")}>
        <span>{area.label}</span>
        <span className="cov-dots">{area.expected ? Array.from({ length: area.expected }, (_, index) => <i key={index} className={index < area.available ? "on" : ""} />) : <i className="off" />}</span>
        <small>{area.state === "NOT_COVERED" ? "—" : `${area.available}/${area.expected}`}</small>
      </div>)}
    </div>
    {coverage.stale_inputs?.length ? <div className="cov-stale-list"><span>Out-of-date inputs</span>{coverage.stale_inputs.map((item) => <p key={item.key}><b>{item.series_id ?? item.key}</b> {item.area ?? ""} · last {shortDate(item.last)} · {item.frequency}</p>)}</div> : null}
    {coverage.missing.length ? <details className="cov-missing"><summary>Missing data · {coverage.missing.length}</summary><ul>{coverage.missing.map((name) => <li key={name}>{name}</li>)}</ul></details> : null}
    {coverage.not_modelled.length ? <p className="cov-not-modelled">Not modelled: {coverage.not_modelled.join(", ")}</p> : null}
  </section>;
}
