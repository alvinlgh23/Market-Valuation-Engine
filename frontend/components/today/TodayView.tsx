"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { attentionItems, buildAlerts, dataAge, marketRead, type Alert } from "../../lib/alerts.mjs";
import type { ResearchSystem } from "../../lib/research-system-types";
import { loadWatchlistDrivers, type DriverRow } from "../../lib/watchlist-drivers";
import { loadWatchlistSummary, resetWatchlistLoaders, type SummaryRow } from "../../lib/watchlist-summary";
import { refreshLine, useDailyRefresh } from "../../lib/daily-refresh";
import { loadWatchlistEvents, type WatchlistEvents } from "../../lib/watchlist-events";
import {
  AGREEMENT_LABEL, BUSINESS_COLUMNS, FOCUS_RULE, VALUE_ROWS, businessColumn, daysBetween, focusItems, shortDay, signed, valueRow,
  type Change, type FocusItem, type TodayHolding, type TodayPayload,
} from "../../lib/today-model";
import { Criteria } from "./Criteria";
import { loadTodayHoldings, resetTodayHoldings } from "../../lib/today-client";

// Today (owner-approved redesign, 2026-11-27): what changed and what deserves a look, in about 30 seconds.
// 1 status band · 2 exceptions only · 3 next 21 days · 4 holdings at a glance. The full list lives in Watchlist,
// sectors and themes in Markets, the full market story in Macro.

function coreHoldings(): Set<string> {
  try {
    const raw = window.localStorage.getItem("chainstox.weights");
    const weights = raw ? (JSON.parse(raw) as Record<string, string>) : {};
    return new Set(Object.entries(weights).filter(([, tier]) => tier === "core").map(([t]) => t));
  } catch { return new Set(); }
}

function Card({ title, aside, children, className = "", label }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string; label?: string }) {
  return <section className={`tdy-card ${className}`} aria-label={label ?? title}>{title ? <header><h2>{title}</h2>{aside}</header> : null}{children}</section>;
}

// ---- 1. Status band -------------------------------------------------------------------------------------------
function StatusBand({ read, counts, pattern, loading }: { read: ReturnType<typeof marketRead>; counts: Array<{ text: string; tone: string }>; pattern: Alert | null; loading: boolean }) {
  return <section className="tdy-band" aria-label="Today in one line">
    <div className="tdy-band-main">
      {read.chip ? <span className="tdy-pill">{read.chip}</span> : null}
      <p className="tdy-band-line">{loading ? "Reading your holdings…" : read.headline}</p>
      <Link href="/macro" className="tdy-band-link">Full market story →</Link>
    </div>
    <div className="tdy-band-counts">
      {counts.map((c) => <span key={c.text} className={`tdy-count tone-${c.tone}`}>{c.text}</span>)}
      {pattern ? <Criteria criteria={pattern.criteria}><span className="tdy-count tone-tested">Tested pattern: {pattern.title.replace(/:.*$/, "")}</span></Criteria> : null}
    </div>
  </section>;
}

// ---- 2. Exceptions only -----------------------------------------------------------------------------------------
const REASON_TEXT = { changed: "Reading changed", disagree: "Price vs business", earnings: "Earnings soon" } as const;

function Move({ label, stock, spy }: { label: string; stock: number | null; spy: number | null }) {
  if (stock == null) return null;
  return <span className="tdy-move"><small>{label}</small><b className={stock < 0 ? "down" : "up"}>{signed(stock)}</b>{spy != null ? <small>S&amp;P {signed(spy)}</small> : null}</span>;
}

function FocusCard({ item, core }: { item: FocusItem; core: boolean }) {
  const h = item.holding;
  const meta = AGREEMENT_LABEL[h.agreement ?? ""] ?? AGREEMENT_LABEL.UNCLEAR;
  return <article className={`tdy-focus tone-${meta.tone}`}>
    <header>
      <Link href={`/company/${h.ticker}`} className="tdy-focus-title"><b>{h.ticker}</b>{core ? <i title="Core holding">★</i> : null}<span>{h.name}</span></Link>
      <div className="tdy-reasons">{item.reasons.map((r) => <span key={r}>{REASON_TEXT[r]}{r === "earnings" && item.earningsIn != null ? ` · ${item.earningsIn === 0 ? "today" : `in ${item.earningsIn}d`}` : ""}</span>)}</div>
    </header>
    <div className="tdy-focus-verdict">
      <span className={`tdy-agree is-${meta.tone}`}>{meta.label}</span>
      <p>{[h.short?.business, h.short?.value].filter(Boolean).join(" · ")}</p>
    </div>
    <div className="tdy-focus-moves">
      <Move label="3 months" stock={h.priceChange3m} spy={null} />
      {h.since ? <Move label={`Since ${shortDay(h.since.from)}`} stock={h.since.stock} spy={h.since.spy} /> : null}
      {h.last5d ? <Move label="Last 5 days" stock={h.last5d.stock} spy={h.last5d.spy} /> : null}
    </div>
    {item.changes.map((c) => <p key={c.axis} className="tdy-focus-change">{c.axis}: {c.from} → <b>{c.to}</b> ({shortDay(c.on)})</p>)}
    {h.strain ? <p className="tdy-strain">⚠ {h.strain.label}: {h.strain.reading.toLowerCase()} ({signed(h.strain.change)} vs sales {signed(h.strain.sales)})</p> : null}
    {h.aiNote ? <Criteria block criteria={{ rule: `Checked AI filing review${h.aiNote.model ? ` (${h.aiNote.model})` : ""}: the quote is matched word for word against the company's ${h.aiNote.form ?? "filing"}. Not counted in any reading.`, now: h.aiNote.quote ? `“${h.aiNote.quote.slice(0, 320)}${h.aiNote.quote.length > 320 ? "…" : ""}”` : null }}>
      <p className="tdy-ai" title={h.aiNote.note}><em>AI · from the filing</em> <span>{h.aiNote.note}</span></p>
    </Criteria> : null}
    {item.reasons.includes("earnings") && h.watch.length ? <div className="tdy-watchfor"><em>What would change the reading</em>{h.watch.map((w) => <p key={w}>{w}</p>)}</div> : null}
  </article>;
}

function Focus({ data, changes, today, core }: { data: TodayPayload | null; changes: Record<string, Change[]> | null; today: string; core: Set<string> }) {
  const result = useMemo(() => (data && changes ? focusItems(data.holdings, changes, today, core) : null), [data, changes, today, core]);
  return <Card className="tdy-focus-wrap" label="What deserves a look today" title="What deserves a look today" aside={<Criteria align="right" criteria={{ rule: FOCUS_RULE }}><small className="tdy-rule">Why these?</small></Criteria>}>
    {!result ? <p className="tdy-empty">Reading your holdings…</p> : !result.items.length
      ? <p className="tdy-calm">No change that needs you today. No reading changed, no holding&apos;s price and business disagree, and no earnings in the next two weeks.</p>
      : <>
        <div className="tdy-focus-grid">{result.items.map((item) => <FocusCard key={item.holding.ticker} item={item} core={core.has(item.holding.ticker)} />)}</div>
        {result.overflow.length ? <p className="tdy-muted">Also qualifying: {result.overflow.map((t, i) => <span key={t}>{i ? ", " : ""}<Link href={`/company/${t}`}>{t}</Link></span>)}.</p> : null}
      </>}
  </Card>;
}

// ---- 3. Next 21 days ----------------------------------------------------------------------------------------------
type Event = { day: string; inDays: number; kind: "earnings" | "fed" | "reported" | "track"; title: string; href: string; holding?: TodayHolding };

function Timeline({ events, holdings, trackCheck, today }: { events: WatchlistEvents | null; holdings: TodayHolding[]; trackCheck: string | null; today: string }) {
  const items = useMemo(() => {
    const out: Event[] = [];
    const byTicker = new Map(holdings.map((h) => [h.ticker, h]));
    for (const e of events?.earnings ?? []) {
      const n = daysBetween(today, e.date);
      if (n == null || !e.date) continue;
      if (n >= 0 && n <= 21) out.push({ day: e.date, inDays: n, kind: "earnings", title: `${e.ticker} earnings`, href: `/company/${e.ticker}`, holding: byTicker.get(e.ticker) });
      else if (n < 0 && n >= -7) out.push({ day: e.date, inDays: n, kind: "reported", title: `${e.ticker} reported`, href: `/company/${e.ticker}` });
    }
    const fed = events?.fomc?.date, nf = daysBetween(today, fed);
    if (fed && nf != null && nf >= 0 && nf <= 21) out.push({ day: fed, inDays: nf, kind: "fed", title: "Fed rate decision", href: "/macro" });
    const nt = daysBetween(today, trackCheck);
    if (trackCheck && nt != null && nt >= 0 && nt <= 30) out.push({ day: trackCheck, inDays: nt, kind: "track", title: "First 1-month check of the valuation reading", href: "/companies" });
    return out.sort((a, b) => a.inDays - b.inDays);
  }, [events, holdings, trackCheck, today]);
  return <Card title="Next three weeks" className="tdy-timeline-card" aside={<small>Earnings, the Fed and our own track-record checks</small>}>
    {events == null ? <p className="tdy-empty">Checking the calendar…</p> : !items.length ? <p className="tdy-empty">No earnings or Fed decision in the next three weeks.</p> : <ol className="tdy-timeline">
      {items.map((e) => <li key={`${e.kind}-${e.title}`} className={`kind-${e.kind}`} style={{ ["--pos" as string]: `${Math.max(0, Math.min(1, (e.inDays + 7) / 30))}` }}>
        <span className="tdy-tl-date">{shortDay(e.day)}<small>{e.inDays === 0 ? "today" : e.inDays > 0 ? `in ${e.inDays}d` : `${-e.inDays}d ago`}</small></span>
        <div>
          <Link href={e.href}>{e.title}</Link>
          {e.holding?.watch[0] ? <p>Watch: {e.holding.watch[0]}</p> : null}
        </div>
      </li>)}
    </ol>}
  </Card>;
}

// ---- 4. Holdings at a glance ----------------------------------------------------------------------------------
function HoldingsGrid({ holdings, core }: { holdings: TodayHolding[]; core: Set<string> }) {
  const rows = VALUE_ROWS.filter((r) => holdings.some((h) => valueRow(h.valuation) === r.key));
  return <Card title="Your holdings at a glance" className="tdy-glance" aside={<Link href="/companies">Full watchlist →</Link>}>
    <div className="tdy-grid3" role="table" aria-label="Holdings by business direction and what the price assumes">
      <div role="row" className="tdy-grid3-head"><span role="columnheader" />{BUSINESS_COLUMNS.map((c) => <span role="columnheader" key={c.key}>{c.label}</span>)}</div>
      {rows.map((r) => <div role="row" key={r.key} className="tdy-grid3-row">
        <span role="rowheader">{r.label}</span>
        {BUSINESS_COLUMNS.map((c) => <div role="cell" key={c.key} className="tdy-grid3-cell">
          {holdings.filter((h) => valueRow(h.valuation) === r.key && businessColumn(h.business) === c.key).map((h) => {
            const meta = AGREEMENT_LABEL[h.agreement ?? ""] ?? AGREEMENT_LABEL.UNCLEAR;
            return <Link key={h.ticker} href={`/company/${h.ticker}`} className={`tdy-dot tone-${meta.tone}${core.has(h.ticker) ? " core" : ""}`} title={`${h.ticker}: ${meta.label}. ${[h.short?.business, h.short?.price, h.short?.value].filter(Boolean).join(" · ")}`}>{h.ticker}</Link>;
          })}
        </div>)}
      </div>)}
    </div>
    <p className="tdy-legend">
      {(["opposed", "leans", "outside", "aligned", "unclear"] as const).map((tone) => <span key={tone}><i className={`tone-${tone}`} />{{ opposed: "Disagree", leans: "Leans against", outside: "Moved with outside forces", aligned: "Agree / leans with", unclear: "No clear reading" }[tone]}</span>)}
      <span><b>★</b> bold = core holding</span>
    </p>
  </Card>;
}

function SharedExposure({ alerts, holdings, loading }: { alerts: Alert[]; holdings: TodayHolding[]; loading: boolean }) {
  const macro = alerts.filter((a) => a.holdings?.length).slice(0, 4);
  const strained = holdings.filter((h) => h.strain);
  return <Card title="What your holdings share" className="tdy-shared" aside={<small>Past 3 months; conditions, not forecasts</small>}>
    {loading ? <p className="tdy-empty">Reading your holdings…</p> : <ul>
      {macro.map((a) => <li key={a.id}>
        <Criteria block criteria={a.criteria}><div className="tdy-shared-head"><Link href={a.href}>{a.title}</Link><span>{(a.holdings?.length ?? 0) + (a.more ?? 0)} holdings</span></div></Criteria>
        <div className="tdy-shared-bars">{a.holdings!.map((x) => <Link key={x.ticker} href={`/company/${x.ticker}`} style={{ ["--w" as string]: `${Math.min(100, Math.abs(x.value) * 500)}%` }} className={x.value < 0 ? "down" : "up"}><span>{x.ticker}</span><i /><b>{signed(x.value, 1)}</b></Link>)}</div>
      </li>)}
      {!macro.length ? <li className="tdy-empty">No macro condition moved your holdings by a point or more.</li> : null}
      <li className="tdy-shared-strain">
        <div className="tdy-shared-head"><span>Operating strain in the filings</span><span>{strained.length} of {holdings.length}</span></div>
        <p>{strained.length ? strained.map((h) => `${h.ticker} (${h.strain!.label.toLowerCase()})`).join(" · ") : "None: inventory, receivables and spending move with sales."}</p>
      </li>
    </ul>}
  </Card>;
}

export function TodayView({ system, status }: { system: ResearchSystem; status?: ReactNode }) {
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  const [summary, setSummary] = useState<SummaryRow[] | null>(null);
  const [events, setEvents] = useState<WatchlistEvents | null>(null);
  const [today, setToday] = useState<TodayPayload | null>(null);
  const [core, setCore] = useState<Set<string>>(new Set());
  const [reloadKey, setReloadKey] = useState(0);
  // P20 item 6: when today's background refresh finishes, read its precomputed results again.
  const router = useRouter();
  // When it finishes, re-read the client data and the server's market snapshot (new market date and band).
  const refresh = useDailyRefresh(useCallback(() => { resetWatchlistLoaders(); resetTodayHoldings(); setReloadKey((key) => key + 1); router.refresh(); }, [router]));
  const refreshNote = refreshLine(refresh);

  useEffect(() => {
    let active = true;
    loadWatchlistEvents().then((value) => { if (active) setEvents(value); });
    loadWatchlistDrivers().then((rows) => { if (active) setDrivers(rows); });
    loadWatchlistSummary().then((rows) => { if (active) setSummary(rows); });
    loadTodayHoldings().then((value) => { if (active) { setCore(coreHoldings()); setToday(value); } });
    return () => { active = false; };
  }, [reloadKey]);

  const environment = system.environment;
  const now = useMemo(() => new Date(), []);
  const todayIso = now.toLocaleDateString("en-CA");
  const age = dataAge(environment?.as_of, todayIso);
  const alerts = useMemo(() => buildAlerts({ environment, drivers: drivers ?? [], summary: summary ?? [] }), [environment, drivers, summary]);
  const read = marketRead(alerts, environment);
  const pattern = useMemo(() => attentionItems({ events: events ?? undefined, summary: summary ?? [], environment, today: todayIso }).find((a) => a.kind === "pattern") ?? null, [events, summary, environment, todayIso]);
  const changes = useMemo(() => (summary ? Object.fromEntries(summary.map((row) => [row.ticker, row.changed as Change[]])) : null), [summary]);
  const holdings = useMemo(() => today?.holdings ?? [], [today]);
  const counts = useMemo(() => {
    const out: Array<{ text: string; tone: string }> = [];
    if (!today) return out;
    const disagree = holdings.filter((h) => h.agreement === "OPPOSED").length;
    const leans = holdings.filter((h) => h.agreement === "LEANS_OPPOSED").length;
    out.push({ text: disagree || leans ? `${disagree} disagree${leans ? ` · ${leans} lean against` : ""}` : "No price-vs-business disagreement", tone: disagree ? "opposed" : "calm" });
    const soon = (events?.earnings ?? []).filter((e) => { const n = daysBetween(todayIso, e.date); return n != null && n >= 0 && n <= 14; }).length;
    out.push({ text: soon ? `${soon} earnings in 14 days` : "No earnings in 14 days", tone: soon ? "info" : "calm" });
    const fed = events?.fomc?.date, nf = daysBetween(todayIso, fed);
    if (fed && nf != null && nf >= 0 && nf <= 21) out.push({ text: `Fed ${shortDay(fed)}`, tone: "info" });
    return out;
  }, [today, holdings, events, todayIso]);
  const loading = drivers == null || summary == null;

  return <div className="tdy">
    <header className="tdy-top">
      <div>
        <h1>Today</h1>
        <p suppressHydrationWarning>{now.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" })}</p>
      </div>
      <div className="tdy-top-right">{status}</div>
    </header>

    {refreshNote ? <div className={`data-refresh tone-${refreshNote.tone}`} role="status"><i aria-hidden="true" />{refreshNote.text}</div> : null}
    {age.stale ? <div className="tdy-stale" role="status" suppressHydrationWarning>
      <i aria-hidden="true" />Market data is from {environment?.as_of ?? "an unknown date"}{age.days != null ? `, ${age.days} business days ago` : ""}{holdings[0]?.last5d?.to ? `; company price moves run to ${shortDay(holdings[0].last5d.to)}` : ""}.
    </div> : null}

    <StatusBand read={read} counts={counts} pattern={pattern} loading={loading} />
    <Focus data={today} changes={changes} today={todayIso} core={core} />
    <Timeline events={events} holdings={holdings} trackCheck={today?.trackCheck ?? null} today={todayIso} />
    <div className="tdy-grid tdy-grid-glance">
      <HoldingsGrid holdings={holdings} core={core} />
      <SharedExposure alerts={alerts} holdings={holdings} loading={loading || !today} />
    </div>
    <p className="tdy-muted tdy-foot">Readings come from fixed, versioned rules on filings, analysts&apos; estimates and prices; AI notes are checked against the filing and not counted. A description of the data, not a forecast or a recommendation.</p>
  </div>;
}
