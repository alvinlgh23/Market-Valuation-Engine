"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { loadCompanyCard } from "../../lib/company-card";
import { refreshLine, useDailyRefresh } from "../../lib/daily-refresh";
import { CARD_AXES, cellLabel, resetWatchlistLoaders, type SummaryRow } from "../../lib/watchlist-summary";
import { axisTone, shortState, TONE_GLYPH, TONE_LABEL } from "../../lib/judgment-tone.mjs";
import { DriverBar, factorBreakdown, PriceDriversLegend, ReadingTag, type Attribution, type PriceReading } from "./PriceDrivers";

type Drivers = { ticker: string; reading: PriceReading; attribution: Attribution & { recent_move?: { latest_price?: number | null; since_window_end?: { stock_change: number; from: string; to: string } | null } | null }; archetype_source: string | null };
type WeightTier = "core" | "standard" | "watch";
type WatchlistMode = "overview" | "matrix";

const CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CNY", "HKD", "SGD", "AUD", "CAD", "KRW", "INR", "TWD"];
const KIND_ORDER = ["fundamentals", "company", "watch", "noise", "unknown"];
const AXES = CARD_AXES;

function savedCurrency() { try { return window.localStorage.getItem("chainstox.homeCurrency") || "USD"; } catch { return "USD"; } }
function savedWeights(): Record<string, WeightTier> {
  try {
    const raw = window.localStorage.getItem("chainstox.weights");
    return raw ? (JSON.parse(raw) as Record<string, WeightTier>) : {};
  } catch { return {}; }
}

function fmtMoney(val: number | null | undefined, currency = "USD") {
  if (typeof val !== "number" || !Number.isFinite(val)) return "—";
  const sym = currency === "USD" ? "$" : `${currency} `;
  return `${sym}${val >= 100 ? Math.round(val).toLocaleString("en-US") : val.toFixed(2)}`;
}

function needsAttention(row: SummaryRow, drv: Drivers | undefined): boolean {
  const hasChange = row.changed.some((c) => c.origin === "COMPANY");
  if (hasChange) return true;
  const kind = drv?.reading?.kind;
  if (kind === "fundamentals" || kind === "company") return true;
  const fundTone = row.axes.fundamentals ? axisTone("fundamentals", row.axes.fundamentals) : "unknown";
  const estTone = row.axes.expectations ? axisTone("expectations", row.axes.expectations) : "unknown";
  return fundTone === "against" || estTone === "against";
}

function plainDriverTag(drv: Drivers | undefined): { text: string; tone: "calm" | "watch" | "company" | "fundamentals" } {
  if (!drv?.reading) return { text: "Checking price drivers…", tone: "calm" };
  const kind = drv.reading.kind;
  if (kind === "fundamentals") return { text: "Moved with estimate shifts", tone: "fundamentals" };
  if (kind === "company") return { text: "Stock-specific move · estimates steady", tone: "company" };
  if (kind === "watch") return { text: "Mostly market · minor stock move", tone: "watch" };
  if (kind === "noise") return { text: "Market / sector noise", tone: "calm" };
  return { text: "Driver history pending", tone: "calm" };
}

function buildTakeaway(row: SummaryRow): { headline: string; pills: Array<{ text: string; tone: "good" | "warn" | "bad" | "neutral" }> } {
  const fund = row.axes.fundamentals;
  const est = row.axes.expectations;
  const crowd = row.axes.crowding;
  const flow = row.axes.flow;
  const fundTone = fund ? axisTone("fundamentals", fund) : "unknown";
  const estTone = est ? axisTone("expectations", est) : "unknown";

  const fundPart = !fund
    ? "Filings not yet read"
    : fundTone === "supportive"
      ? "Quarterly filings improving"
      : fundTone === "against"
        ? "Quarterly filings weakening"
        : "Quarterly filings steady";

  const estPart = !est
    ? "consensus unavailable"
    : estTone === "supportive"
      ? "analyst estimates rising"
      : estTone === "against"
        ? "analyst estimates cut"
        : "estimates steady";

  const pills: Array<{ text: string; tone: "good" | "warn" | "bad" | "neutral" }> = [];
  const changes = row.changed.filter((c) => c.origin === "COMPANY");
  if (changes.length > 0) {
    pills.push({ text: `Changed: ${changes.map((c) => c.axis).join(", ")}`, tone: "warn" });
  }
  if (row.operating_constraint) {
    const shortOp = row.operating_constraint.split(":")[0];
    pills.push({ text: `${shortOp} > sales`, tone: "warn" });
  }
  if (crowd && axisTone("crowding", crowd) === "against" && pills.length < 2) {
    pills.push({ text: "Crowded positioning", tone: "warn" });
  } else if (flow && axisTone("flow", flow) === "supportive" && pills.length < 2) {
    pills.push({ text: "Sector inflow", tone: "good" });
  }

  return { headline: `${fundPart} · ${estPart}`, pills: pills.slice(0, 2) };
}

function growthPct(value: number) {
  const rounded = Math.round(value * 100);
  return rounded === 0 ? "0%" : `${rounded > 0 ? "+" : "−"}${Math.abs(rounded)}%`;
}

function PriceVsValueCell({ row, livePrice, hydrating }: { row: SummaryRow; livePrice: number | null; hydrating: boolean }) {
  const det = row.valuation_detail;
  const price = det?.price ?? row.latest_price ?? livePrice;
  const bull = det?.bull ?? null;
  const currency = det?.currency ?? "USD";
  const valAxis = row.axes.valuation ?? "";
  const stretch = row.price_to_max_case ?? det?.price_to_max_case ?? (price && bull && bull > 0 && price > bull ? price / bull : null);

  if (price == null && hydrating) {
    return <div className="wl-val-box"><strong className="wl-price-num">Syncing…</strong><small className="wl-val-sub">Reading filings &amp; DCF</small></div>;
  }

  // Owner 2026-11-26: no "±X% vs base" target-price gap. Show what the card reads: the growth the price
  // assumes against what the business has shown (analysts' and past growth, both faded to year 5).
  const implied = det?.implied_growth ?? null;
  const low = det?.reference_low ?? null;
  const high = det?.reference_high ?? null;
  if (implied != null && low != null && high != null && price != null) {
    const tone = valAxis.startsWith("Price implies more") ? "rich" : valAxis.startsWith("Price implies less") ? "cheap" : "fair";
    const reference = Math.round(low * 100) === Math.round(high * 100) ? growthPct(low) : `${growthPct(low)} to ${growthPct(high)}`;
    return (
      <div className="wl-val-box" title={`${valAxis}. Five-year sales growth the price assumes, against analysts' and past growth faded to year 5.`}>
        <div className="wl-val-top">
          <strong className="wl-price-num">{fmtMoney(price, currency)}</strong>
          <span className={`wl-val-delta ${tone}`}>Prices in {growthPct(implied)}/yr</span>
        </div>
        <small className="wl-val-sub">Business shows {reference}/yr</small>
      </div>
    );
  }

  const fallbackNote = det?.implied_roe != null && det?.latest_roe != null
    ? `Implied ROE ${(det.implied_roe * 100).toFixed(1)}% · earns ${(det.latest_roe * 100).toFixed(1)}%`
    : valAxis.toLowerCase().includes("withheld")
      ? "Specialized / DCF withheld"
      : stretch != null && stretch > 1
        ? `${stretch.toFixed(1)}× the model's best case`
        : hydrating
          ? "Calculating fair value…"
          : shortState(valAxis) !== "—"
            ? shortState(valAxis)
            : "DCF pending";

  return (
    <div className="wl-val-box">
      <div className="wl-val-top">
        <strong className="wl-price-num">{fmtMoney(price, currency)}</strong>
      </div>
      <small className="wl-val-sub">{fallbackNote}</small>
    </div>
  );
}

export function WatchlistTable() {
  const [rows, setRows] = useState<SummaryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<Record<string, Drivers> | null>(null);
  const [driversError, setDriversError] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState<Record<string, boolean>>({});
  const [weights, setWeights] = useState<Record<string, WeightTier>>(() => (typeof window === "undefined" ? {} : savedWeights()));
  const [mode, setMode] = useState<WatchlistMode>("overview");
  const [toast, setToast] = useState<{ text: string; undo?: () => void } | null>(null);

  const fetchSummaryAndDrivers = useCallback(() => {
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (Array.isArray(body.rows)) setRows(body.rows as SummaryRow[]); })
      .catch(() => {});
    fetch("/api/research?action=watchlist-drivers", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (Array.isArray(body.rows)) setDrivers(Object.fromEntries((body.rows as Drivers[]).map((row) => [row.ticker, row]))); })
      .catch(() => {});
  }, []);

  const hydrateTicker = useCallback((ticker: string) => {
    setHydrating((prev) => ({ ...prev, [ticker]: true }));
    return loadCompanyCard(ticker)
      .then(() => { fetchSummaryAndDrivers(); })
      .finally(() => { setHydrating((prev) => { const copy = { ...prev }; delete copy[ticker]; return copy; }); });
  }, [fetchSummaryAndDrivers]);

  // P20 item 6: missing cards are built by the daily background refresh, not one by one from this page.
  const refresh = useDailyRefresh(fetchSummaryAndDrivers);
  const refreshNote = refreshLine(refresh);
  const refreshing = refresh?.state === "RUNNING";

  const saveList = async (tickers: string[], previous: SummaryRow[]) => {
    try {
      const response = await fetch("/api/research", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "watchlist-set", tickers }) });
      const body = await response.json();
      if (!response.ok || body.status !== "OK") throw new Error((body.errors ?? ["Couldn't save the list."]).join(" "));
      resetWatchlistLoaders();
    } catch (failure) {
      setRows(previous); setToast({ text: failure instanceof Error ? failure.message : "Couldn't save the list." });
    }
  };

  const removeTicker = (ticker: string) => {
    if (!rows) return;
    const previous = rows, index = rows.findIndex((row) => row.ticker === ticker);
    const next = rows.filter((row) => row.ticker !== ticker);
    setRows(next); void saveList(next.map((row) => row.ticker), previous);
    setToast({ text: `Removed ${ticker}`, undo: () => { const restored = [...next]; restored.splice(index, 0, previous[index]); setRows(restored); void saveList(restored.map((row) => row.ticker), next); } });
  };

  const addTicker = (ticker: string) => {
    if (!rows || rows.some((row) => row.ticker === ticker)) return;
    const previous = rows, next: SummaryRow[] = [...rows, { ticker, last_card: null, axes: {}, changed: [] }];
    setRows(next);
    void saveList(next.map((row) => row.ticker), previous).then(() => hydrateTicker(ticker));
    setToast({ text: `Added ${ticker} — reading filings & valuation in background…` });
  };

  const toggleStar = (ticker: string) => {
    setWeights((prev) => {
      const nextTier: WeightTier = prev[ticker] === "core" ? "standard" : "core";
      const updated = { ...prev, [ticker]: nextTier };
      try { window.localStorage.setItem("chainstox.weights", JSON.stringify(updated)); } catch { /* ignore */ }
      return updated;
    });
  };

  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(null), 6000); return () => clearTimeout(timer); }, [toast]);

  const [currency, setCurrency] = useState(() => (typeof window === "undefined" ? "USD" : savedCurrency()));
  const [fx, setFx] = useState<Record<string, number | null> | null>(null);
  useEffect(() => {
    if (currency === "USD" || fx) return;
    let active = true;
    fetch("/api/research?action=fx-moves", { cache: "no-store" }).then(async (response) => { const body = await response.json(); if (active) setFx(body.fx?.home_per_usd_change ?? {}); }).catch(() => { if (active) setFx({}); });
    return () => { active = false; };
  }, [currency, fx]);

  const chooseCurrency = (value: string) => { setCurrency(value); try { window.localStorage.setItem("chainstox.homeCurrency", value); } catch { /* per-viewer convenience only */ } };
  const homeMove = (usd: number | undefined) => {
    if (usd == null) return "—";
    const usdText = `${usd >= 0 ? "+" : "−"}${Math.abs(usd * 100).toFixed(1)}%`;
    if (currency === "USD") return usdText;
    if (!fx) return "…";
    const change = fx[currency];
    if (change == null) return `${usdText} USD`;
    const home = (1 + usd) * (1 + change) - 1;
    return `${home >= 0 ? "+" : "−"}${Math.abs(home * 100).toFixed(1)}% ${currency}`;
  };

  useEffect(() => {
    let active = true;
    fetch("/api/research?action=watchlist-drivers", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (!active) return; if (Array.isArray(body.rows)) setDrivers(Object.fromEntries((body.rows as Drivers[]).map((row) => [row.ticker, row]))); else setDriversError(body.error || "unavailable"); })
      .catch((failure) => { if (active) setDriversError(String(failure)); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (!active) return; if (Array.isArray(body.rows)) setRows(body.rows as SummaryRow[]); else setError(body.error || "Watchlist unavailable."); })
      .catch((failure) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, []);

  const grouped = useMemo(() => {
    if (!rows) return { focus: [] as SummaryRow[], steady: [] as SummaryRow[] };
    const sortFn = (a: SummaryRow, b: SummaryRow) => {
      const sa = weights[a.ticker] === "core" ? 0 : 1;
      const sb = weights[b.ticker] === "core" ? 0 : 1;
      if (sa !== sb) return sa - sb;
      if (drivers) {
        return KIND_ORDER.indexOf(drivers[a.ticker]?.reading.kind ?? "unknown") - KIND_ORDER.indexOf(drivers[b.ticker]?.reading.kind ?? "unknown");
      }
      return a.ticker.localeCompare(b.ticker);
    };
    const focus = rows.filter((r) => needsAttention(r, drivers?.[r.ticker])).sort(sortFn);
    const steady = rows.filter((r) => !needsAttention(r, drivers?.[r.ticker])).sort(sortFn);
    return { focus, steady };
  }, [rows, drivers, weights]);

  if (error) return <p className="watchlist-note">Watchlist unavailable: {error}</p>;
  if (!rows) return <p className="watchlist-note">Loading the watchlist…</p>;

  const companyChanges = (row: SummaryRow) => row.changed.filter((item) => item.origin === "COMPANY");
  const hydratingCount = Object.keys(hydrating).length;

  const renderOverviewRow = (row: SummaryRow) => {
    const starred = weights[row.ticker] === "core";
    const isHydrating = Boolean(hydrating[row.ticker]) || (refreshing && !row.valuation_detail);
    const drv = drivers?.[row.ticker];
    const move3m = drv?.attribution?.windows?.["3M"]?.price_change;
    const recentBridge = drv?.attribution?.recent_move?.since_window_end;
    const livePrice = drv?.attribution?.recent_move?.latest_price ?? null;
    const driverBadge = plainDriverTag(drv);
    const takeaway = buildTakeaway(row);

    return (
      <Link href={`/company/${row.ticker}`} className={`wl-clean-row${starred ? " is-starred" : ""}`} key={row.ticker}>
        <div className="wl-col-company">
          <button
            type="button"
            className={`wl-star${starred ? " active" : ""}`}
            aria-label={starred ? `Unpin ${row.ticker}` : `Pin ${row.ticker} to top`}
            title={starred ? "Core holding (click to unpin)" : "Pin as core holding"}
            onClick={(event) => { event.preventDefault(); event.stopPropagation(); toggleStar(row.ticker); }}
          >
            {starred ? "★" : "☆"}
          </button>
          <div className="wl-company-id">
            <b>{row.ticker}</b>
            <span>{row.name || row.ticker}</span>
          </div>
        </div>

        <div className="wl-col-price">
          <PriceVsValueCell row={row} livePrice={livePrice} hydrating={isHydrating} />
        </div>

        <div className="wl-col-driver" title={drv ? factorBreakdown(drv.attribution) : undefined}>
          <div className="wl-driver-top">
            <strong className={move3m == null ? "" : move3m >= 0 ? "up" : "down"}>{homeMove(move3m)}</strong>
            {recentBridge && Math.abs(recentBridge.stock_change) >= 0.03 ? (
              <small className={recentBridge.stock_change >= 0 ? "up" : "down"}>
                {recentBridge.stock_change >= 0 ? "+" : "−"}{Math.abs(recentBridge.stock_change * 100).toFixed(1)}% since Fri
              </small>
            ) : <small>3M total</small>}
          </div>
          <span className={`wl-noise-pill tone-${driverBadge.tone}`}>{driverBadge.text}</span>
        </div>

        <div className="wl-col-takeaway">
          <p>{takeaway.headline}</p>
          {takeaway.pills.length ? (
            <div className="wl-takeaway-pills">
              {takeaway.pills.map((pill) => <span key={pill.text} className={`wl-tpill pill-${pill.tone}`}>{pill.text}</span>)}
            </div>
          ) : null}
        </div>

        <div className="wl-col-actions">
          <button
            type="button"
            className="wl-remove"
            aria-label={`Remove ${row.ticker} from the watchlist`}
            title={`Remove ${row.ticker}`}
            onClick={(event) => { event.preventDefault(); event.stopPropagation(); removeTicker(row.ticker); }}
          >
            ×
          </button>
        </div>
      </Link>
    );
  };

  return (
    <section className="watchlist-grid wl-redesigned" aria-label="Watchlist">
      <header className="wl-top-bar">
        <div className="wl-title-group">
          <h1>Watchlist</h1>
          <p className="wl-digest">
            {rows.length} {rows.length === 1 ? "company" : "companies"}
            {drivers ? ` · ${grouped.focus.length} need a closer look · ${grouped.steady.length} with no company-specific change` : driversError ? ` · drivers unavailable` : " · checking price drivers…"}
            {hydratingCount > 0 ? <span className="wl-sync-inline"> · building {hydratingCount} {hydratingCount === 1 ? "card" : "cards"}…</span> : null}
          </p>
          {refreshNote ? <p className={`data-refresh tone-${refreshNote.tone}`} role="status"><i aria-hidden="true" />{refreshNote.text}</p> : null}
        </div>

        <div className="wl-toolbar">
          <TickerAdd existing={rows.map((row) => row.ticker)} onAdd={addTicker} />
          <div className="wl-mode-switch" role="tablist" aria-label="Watchlist view mode">
            <button type="button" role="tab" aria-selected={mode === "overview"} className={mode === "overview" ? "active" : ""} onClick={() => setMode("overview")}>Overview</button>
            <button type="button" role="tab" aria-selected={mode === "matrix"} className={mode === "matrix" ? "active" : ""} onClick={() => setMode("matrix")}>6-Axis Matrix</button>
          </div>
          <label className="wl-currency-compact" title="Display 3-month returns in your home currency">
            <select aria-label="Display currency" value={currency} onChange={(event) => chooseCurrency(event.target.value)}>
              {CURRENCIES.map((code) => <option key={code} value={code}>{code}</option>)}
            </select>
          </label>
        </div>
      </header>

      {toast ? <div className="wl-toast" role="status">{toast.text}{toast.undo ? <button type="button" onClick={() => { toast.undo?.(); setToast(null); }}>Undo</button> : null}</div> : null}

      {!rows.length ? (
        <div className="wl-empty-starter">
          <p>Your watchlist is empty. Search above to add any stock, or start with a preset portfolio:</p>
          <div>
            <button type="button" onClick={() => { const preset = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]; setRows(preset.map((t) => ({ ticker: t, last_card: null, axes: {}, changed: [] }))); void saveList(preset, []); }}>US Tech Leaders</button>
            <button type="button" onClick={() => { const preset = ["COST", "V", "LLY", "JPM", "CAT", "WMT"]; setRows(preset.map((t) => ({ ticker: t, last_card: null, axes: {}, changed: [] }))); void saveList(preset, []); }}>Quality Compounders</button>
          </div>
        </div>
      ) : mode === "overview" ? (
        <div className="wl-sections">
          <div className="wl-clean-head" aria-hidden="true">
            <span>Company</span>
            <span>Price vs Fair Value</span>
            <span>3M Move &amp; Cause</span>
            <span>Fundamentals &amp; Expectations</span>
            <span />
          </div>

          {grouped.focus.length > 0 ? (
            <section className="wl-group wl-group-focus" aria-label="Needs a closer look">
              <header className="wl-group-head">
                <span className="wl-group-dot focus" />
                <h2>Needs a closer look</h2>
                <small>{grouped.focus.length} — stock-specific move, estimate cuts, or recent reading change</small>
              </header>
              <div className="wl-group-list">
                {grouped.focus.map(renderOverviewRow)}
              </div>
            </section>
          ) : null}

          {grouped.steady.length > 0 ? (
            <section className="wl-group wl-group-steady" aria-label="Steady fundamentals">
              <header className="wl-group-head">
                <span className="wl-group-dot steady" />
                <h2>No company-specific change</h2>
                <small>{grouped.steady.length} — filings and analyst estimates unchanged; each row shows what drove its price</small>
              </header>
              <div className="wl-group-list">
                {grouped.steady.map(renderOverviewRow)}
              </div>
            </section>
          ) : null}
        </div>
      ) : (
        <div className="wl-matrix-wrap">
          <div className="wl-legend">
            {(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}
            <span className="wl-changed-key">changed since last card</span>
            <PriceDriversLegend />
          </div>
          <div className="wl-table" role="table">
            <div className="wl-row wl-head" role="row"><span role="columnheader">Company</span><span role="columnheader">What moved the price (3M)</span>{AXES.map(([, label]) => <span role="columnheader" key={label}>{label}</span>)}<span role="columnheader">Card</span></div>
            {[...rows].map((row) => {
              const isHydrating = Boolean(hydrating[row.ticker]) || (refreshing && !row.valuation_detail);
              const hasAnyReading = Object.keys(row.axes).length > 0;
              return <Link href={`/company/${row.ticker}`} className="wl-row" role="row" key={row.ticker}>
                <span role="cell" className="wl-ticker"><b>{row.ticker}</b></span>
                <span role="cell" className="wl-drivers">{drivers?.[row.ticker] ? <>
                  <span className="wl-move">{homeMove(drivers[row.ticker].attribution?.windows?.["3M"]?.price_change)}</span>
                  <DriverBar parts={drivers[row.ticker].attribution?.windows?.["3M"]?.parts} title={factorBreakdown(drivers[row.ticker].attribution)} />
                  <ReadingTag reading={drivers[row.ticker].reading} compact />
                </> : <span className="wl-move">{isHydrating ? "Analyzing…" : drivers || driversError ? "—" : "…"}</span>}</span>
                {isHydrating && !hasAnyReading ? (
                  <span role="cell" className="wl-cell wl-hydrating" style={{ gridColumn: "span 6" }}>Building judgment card…</span>
                ) : AXES.map(([key, label]) => {
                  const state = row.axes[key];
                  const tone = state ? axisTone(key, state) : "unknown";
                  const change = companyChanges(row).find((item) => item.axis === key);
                  return <span role="cell" key={key} className={`wl-cell tone-${tone}${change ? " changed" : ""}`} title={`${label}: ${state ?? "no card"}${change ? ` (was ${change.from})` : ""}`}>
                    <em aria-hidden>{TONE_GLYPH[tone]}</em>{cellLabel(shortState(state), key, row)}
                  </span>;
                })}
                <span role="cell" className="wl-date">
                  {row.last_card ?? "—"}
                  <button type="button" className="wl-remove" aria-label={`Remove ${row.ticker} from the watchlist`} title={`Remove ${row.ticker}`} onClick={(event) => { event.preventDefault(); event.stopPropagation(); removeTicker(row.ticker); }}>×</button>
                </span>
              </Link>;
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function TickerAdd({ existing, onAdd }: { existing: string[]; onAdd: (ticker: string) => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ ticker: string; name: string }>>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!query.trim()) return;
    let active = true;
    const timer = setTimeout(() => {
      fetch(`/api/research?action=ticker-search&q=${encodeURIComponent(query.trim())}`, { cache: "no-store" })
        .then((response) => response.json()).then((body) => { if (active) setResults(Array.isArray(body.results) ? body.results : []); }).catch(() => { if (active) setResults([]); });
    }, 100);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);

  const activeResults = query.trim() ? results : [];

  const pick = (ticker: string) => {
    if (existing.includes(ticker)) {
      setQuery(""); setResults([]); setMessage(null);
      router.push(`/company/${ticker}`);
      return;
    }
    if (existing.length >= 40) { setMessage("The list holds at most 40 companies."); return; }
    onAdd(ticker); setQuery(""); setResults([]); setMessage(null);
  };

  return (
    <form
      className="wl-add"
      onSubmit={(event) => {
        event.preventDefault();
        const raw = query.trim().toUpperCase();
        if (activeResults[0]) pick(activeResults[0].ticker);
        else if (/^[A-Z][A-Z0-9.\-]{0,6}$/.test(raw)) router.push(`/company/${raw}`);
        else if (raw) setMessage(`No listed company matches "${query.trim()}".`);
      }}
    >
      <input
        id="company-index-ticker"
        value={query}
        onChange={(event) => { setQuery(event.target.value); setMessage(null); }}
        placeholder="Add or open ticker (AAPL, Apple)…"
        aria-label="Add or open a company"
        autoComplete="off"
      />
      {activeResults.length ? (
        <ul role="listbox">
          {activeResults.map((item) => {
            const onList = existing.includes(item.ticker);
            return (
              <li key={item.ticker}>
                <button type="button" onClick={() => pick(item.ticker)}>
                  <b>{item.ticker}</b>
                  <span>{item.name}</span>
                  <small>{onList ? "Open →" : "+ Add"}</small>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {message ? <p role="alert">{message}</p> : null}
    </form>
  );
}
