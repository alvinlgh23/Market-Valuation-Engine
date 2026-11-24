"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { loadCompanyCard } from "../../lib/company-card";
import { CARD_AXES, cellLabel, resetWatchlistLoaders } from "../../lib/watchlist-summary";
import { axisTone, shortState, TONE_GLYPH, TONE_LABEL } from "../../lib/judgment-tone.mjs";
import { DriverBar, factorBreakdown, PriceDriversLegend, ReadingTag, type Attribution, type PriceReading } from "./PriceDrivers";

type Row = { ticker: string; last_card: string | null; axes: Record<string, string>; price_to_max_case?: number | null; changed: Array<{ axis: string; from: string; to: string; on: string; origin?: string }> };
type Drivers = { ticker: string; reading: PriceReading; attribution: Attribution; archetype_source: string | null };
type WeightTier = "core" | "standard" | "watch";

const CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CNY", "HKD", "SGD", "AUD", "CAD", "KRW", "INR", "TWD"];
const KIND_ORDER = ["fundamentals", "company", "watch", "noise", "unknown"];
const WEIGHT_ORDER: Record<WeightTier, number> = { core: 0, standard: 1, watch: 2 };
const WEIGHT_NEXT: Record<WeightTier, WeightTier> = { standard: "core", core: "watch", watch: "standard" };
const WEIGHT_LABEL: Record<WeightTier, string> = { core: "★ Core", standard: "Hold", watch: "Watch" };
const AXES = CARD_AXES;

function savedCurrency() { try { return window.localStorage.getItem("chainstox.homeCurrency") || "USD"; } catch { return "USD"; } }
function savedWeights(): Record<string, WeightTier> {
  try {
    const raw = window.localStorage.getItem("chainstox.weights");
    return raw ? (JSON.parse(raw) as Record<string, WeightTier>) : {};
  } catch { return {}; }
}

/** Checklists 8.2, 9.6, 19.1 + Auto-Hydration & Portfolio Weights */
export function WatchlistTable() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<Record<string, Drivers> | null>(null);
  const [driversError, setDriversError] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState<Record<string, boolean>>({});
  const [weights, setWeights] = useState<Record<string, WeightTier>>(() => (typeof window === "undefined" ? {} : savedWeights()));
  const [toast, setToast] = useState<{ text: string; undo?: () => void } | null>(null);

  const fetchSummaryAndDrivers = useCallback(() => {
    fetch("/api/research?action=watchlist-summary", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (Array.isArray(body.rows)) setRows(body.rows as Row[]); })
      .catch(() => {});
    fetch("/api/research?action=watchlist-drivers", { cache: "no-store" })
      .then(async (response) => { const body = await response.json(); if (Array.isArray(body.rows)) setDrivers(Object.fromEntries((body.rows as Drivers[]).map((row) => [row.ticker, row]))); })
      .catch(() => {});
  }, []);

  const hydrateTicker = useCallback((ticker: string) => {
    setHydrating((prev) => ({ ...prev, [ticker]: true }));
    loadCompanyCard(ticker)
      .then(() => { fetchSummaryAndDrivers(); })
      .finally(() => { setHydrating((prev) => { const copy = { ...prev }; delete copy[ticker]; return copy; }); });
  }, [fetchSummaryAndDrivers]);

  const saveList = async (tickers: string[], previous: Row[]) => {
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
    const previous = rows, next = [...rows, { ticker, last_card: null, axes: {}, changed: [] }];
    setRows(next);
    void saveList(next.map((row) => row.ticker), previous).then(() => hydrateTicker(ticker));
    setToast({ text: `Added ${ticker} — analyzing filings & price in background…` });
  };

  const cycleWeight = (ticker: string) => {
    setWeights((prev) => {
      const current = prev[ticker] ?? "standard";
      const nextTier = WEIGHT_NEXT[current];
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
    const usdText = `${usd >= 0 ? "+" : ""}${(usd * 100).toFixed(1)}%`;
    if (currency === "USD") return usdText;
    if (!fx) return `Converting to ${currency}…`;
    const change = fx[currency];
    if (change == null) return `${usdText} USD (no ${currency} rate)`;
    const home = (1 + usd) * (1 + change) - 1;
    return `${home >= 0 ? "+" : ""}${(home * 100).toFixed(1)}% ${currency}`;
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
      .then(async (response) => { const body = await response.json(); if (!active) return; if (Array.isArray(body.rows)) setRows(body.rows as Row[]); else setError(body.error || "Watchlist unavailable."); })
      .catch((failure) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, []);

  if (error) return <p className="watchlist-note">Watchlist unavailable: {error}</p>;
  if (!rows) return <p className="watchlist-note">Loading the watchlist…</p>;
  const companyChanges = (row: Row) => row.changed.filter((item) => item.origin === "COMPANY");
  const changedCount = rows.filter((row) => companyChanges(row).length).length;
  const kinds = drivers ? Object.values(drivers).map((item) => item.reading.kind) : [];
  const count = (kind: string) => kinds.filter((item) => item === kind).length;

  return <section className="watchlist-grid" aria-label="Watchlist">
    <header>
      <h1>Watchlist</h1>
      <TickerAdd existing={rows.map((row) => row.ticker)} onAdd={addTicker} />
      <div className="wl-legend">{(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}<span className="wl-changed-key">changed since last card</span></div>
    </header>
    {toast ? <div className="wl-toast" role="status">{toast.text}{toast.undo ? <button type="button" onClick={() => { toast.undo?.(); setToast(null); }}>Undo</button> : null}</div> : null}
    {drivers ? <div className="wl-drivers-summary" aria-label="What is moving the watchlist">
      <span><b>{count("noise")}</b> moved with macro, market or sector; company part normal</span>
      <span><b>{count("watch")}</b> some company-specific move</span>
      <span className="pd-kind-company"><b>{count("company") + count("fundamentals")}</b> company-specific{count("fundamentals") ? `, ${count("fundamentals")} with estimates moving` : ""}</span>
      <PriceDriversLegend />
      <label className="wl-currency">Show moves in <select value={currency} onChange={(event) => chooseCurrency(event.target.value)}>{CURRENCIES.map((code) => <option key={code} value={code}>{code}</option>)}</select></label>
      {currency !== "USD" && fx?.[currency] != null ? <small>USD {((fx[currency] as number) >= 0 ? "+" : "")}{((fx[currency] as number) * 100).toFixed(1)}% vs {currency} in 3M</small> : null}
    </div> : <p className="wl-summary">{driversError ? `Price drivers unavailable: ${driversError}` : "Working out what moved each price…"}</p>}
    {changedCount ? <p className="wl-summary">{changedCount} of {rows.length} companies changed since their previous card.</p> : null}
    {!rows.length ? (
      <div className="wl-empty-starter">
        <p>Your watchlist is empty. Add companies above, or start with a preset group:</p>
        <div>
          <button type="button" onClick={() => { const preset = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]; setRows(preset.map((t) => ({ ticker: t, last_card: null, axes: {}, changed: [] }))); void saveList(preset, []); }}>US Tech Leaders</button>
          <button type="button" onClick={() => { const preset = ["COST", "V", "LLY", "JPM", "CAT", "WMT"]; setRows(preset.map((t) => ({ ticker: t, last_card: null, axes: {}, changed: [] }))); void saveList(preset, []); }}>Quality Compounders</button>
        </div>
      </div>
    ) : (
      <div className="wl-table" role="table">
        <div className="wl-row wl-head" role="row"><span role="columnheader">Company</span><span role="columnheader">What moved the price (3M)</span>{AXES.map(([, label]) => <span role="columnheader" key={label}>{label}</span>)}<span role="columnheader">Card</span></div>
        {[...rows].sort((a, b) => {
          const wa = WEIGHT_ORDER[weights[a.ticker] ?? "standard"], wb = WEIGHT_ORDER[weights[b.ticker] ?? "standard"];
          if (wa !== wb) return wa - wb;
          return drivers ? KIND_ORDER.indexOf(drivers[a.ticker]?.reading.kind ?? "unknown") - KIND_ORDER.indexOf(drivers[b.ticker]?.reading.kind ?? "unknown") : 0;
        }).map((row) => {
          const tier = weights[row.ticker] ?? "standard";
          const isHydrating = Boolean(hydrating[row.ticker]);
          const hasAnyReading = Object.keys(row.axes).length > 0;
          return <Link href={`/company/${row.ticker}`} className={`wl-row${tier === "core" ? " wl-row-core" : ""}`} role="row" key={row.ticker}>
            <span role="cell" className="wl-ticker">
              <b>{row.ticker}</b>
              <button
                type="button"
                className={`wl-weight tier-${tier}`}
                title="Click to cycle position importance: Core holding → Standard → Watch only"
                onClick={(event) => { event.preventDefault(); event.stopPropagation(); cycleWeight(row.ticker); }}
              >
                {WEIGHT_LABEL[tier]}
              </button>
            </span>
            <span role="cell" className="wl-drivers">{drivers?.[row.ticker] ? <>
              <span className="wl-move" title={currency === "USD" ? "3-month price change in US dollars" : `3-month return in ${currency}: USD return combined with the dollar's move against ${currency}. The bar still splits the USD move.`}>{homeMove(drivers[row.ticker].attribution?.windows?.["3M"]?.price_change)}</span>
              <DriverBar parts={drivers[row.ticker].attribution?.windows?.["3M"]?.parts} title={factorBreakdown(drivers[row.ticker].attribution)} />
              <ReadingTag reading={drivers[row.ticker].reading} compact />
            </> : <span className="wl-move">{isHydrating ? "Analyzing…" : drivers || driversError ? "—" : "…"}</span>}</span>
            {isHydrating && !hasAnyReading ? (
              <span role="cell" className="wl-cell wl-hydrating" style={{ gridColumn: "span 6" }}>Building first judgment card in background…</span>
            ) : AXES.map(([key, label]) => {
              const state = row.axes[key];
              const tone = state ? axisTone(key, state) : "unknown";
              const change = companyChanges(row).find((item) => item.axis === key);
              return <span role="cell" key={key} className={`wl-cell tone-${tone}${change ? " changed" : ""}`} title={`${label}: ${state ?? "no card"}${change ? ` (was ${change.from})` : ""}`}>
                <em aria-hidden>{TONE_GLYPH[tone]}</em>{cellLabel(shortState(state), key, row)}
              </span>;
            })}
            <span role="cell" className="wl-date">
              {!hasAnyReading && !isHydrating ? (
                <button type="button" className="wl-hydrate-btn" onClick={(event) => { event.preventDefault(); event.stopPropagation(); hydrateTicker(row.ticker); }}>Analyze</button>
              ) : (row.last_card ?? "—")}
              <button type="button" className="wl-remove" aria-label={`Remove ${row.ticker} from the watchlist`} title={`Remove ${row.ticker}`} onClick={(event) => { event.preventDefault(); event.stopPropagation(); removeTicker(row.ticker); }}>×</button>
            </span>
          </Link>;
        })}
      </div>
    )}
  </section>;
}

function TickerAdd({ existing, onAdd }: { existing: string[]; onAdd: (ticker: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ ticker: string; name: string }>>([]);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    if (!query.trim()) return;
    let active = true;
    const timer = setTimeout(() => {
      fetch(`/api/research?action=ticker-search&q=${encodeURIComponent(query.trim())}`, { cache: "no-store" })
        .then((response) => response.json()).then((body) => { if (active) setResults(Array.isArray(body.results) ? body.results : []); }).catch(() => { if (active) setResults([]); });
    }, 120);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);
  const pick = (ticker: string) => {
    if (existing.includes(ticker)) { setMessage(`${ticker} is already on the list.`); return; }
    if (existing.length >= 40) { setMessage("The list holds at most 40 companies."); return; }
    onAdd(ticker); setQuery(""); setResults([]); setMessage(null);
  };
  return <form className="wl-add" onSubmit={(event) => { event.preventDefault(); if (results[0]) pick(results[0].ticker); else if (query.trim()) setMessage(`No listed company matches "${query.trim()}".`); }}>
    <input value={query} onChange={(event) => { setQuery(event.target.value); setMessage(null); if (!event.target.value.trim()) setResults([]); }} placeholder="Add a company: AAPL or Apple" aria-label="Add a company to the watchlist" autoComplete="off" />
    {results.length ? <ul role="listbox">{results.map((item) => <li key={item.ticker}><button type="button" onClick={() => pick(item.ticker)} disabled={existing.includes(item.ticker)}><b>{item.ticker}</b><span>{item.name}</span>{existing.includes(item.ticker) ? <small>on the list</small> : null}</button></li>)}</ul> : null}
    {message ? <p role="alert">{message}</p> : null}
  </form>;
}
