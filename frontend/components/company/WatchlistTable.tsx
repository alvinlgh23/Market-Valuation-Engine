"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CARD_AXES, cellLabel } from "../../lib/watchlist-summary";
import { axisTone, shortState, TONE_GLYPH, TONE_LABEL } from "../../lib/judgment-tone.mjs";
import { DriverBar, factorBreakdown, PriceDriversLegend, ReadingTag, type Attribution, type PriceReading } from "./PriceDrivers";

type Row = { ticker: string; last_card: string | null; axes: Record<string, string>; price_to_max_case?: number | null; changed: Array<{ axis: string; from: string; to: string; on: string; origin?: string }> };
type Drivers = { ticker: string; reading: PriceReading; attribution: Attribution; archetype_source: string | null };
const CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CNY", "HKD", "SGD", "AUD", "CAD", "KRW", "INR", "TWD"];
function savedCurrency() { try { return window.localStorage.getItem("chainstox.homeCurrency") || "USD"; } catch { return "USD"; } }
const KIND_ORDER = ["fundamentals", "company", "watch", "noise", "unknown"];
const AXES = CARD_AXES;

/** Checklists 8.2, 9.6: company x axis grid of the last recorded card (history only, no live request). */
export function WatchlistTable() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<Record<string, Drivers> | null>(null);
  const [driversError, setDriversError] = useState<string | null>(null);
  // Checklist 10.9: users are global, so moves can be read in a home currency.
  // The currency control renders only after client-side data loads, so reading storage here cannot mismatch the server HTML.
  const [editing, setEditing] = useState(false);
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
    // Checklist 18.9: never show a dollar move as if it were in the chosen currency.
    if (!fx) return `Converting to ${currency}…`;
    const change = fx[currency];
    if (change == null) return `${usdText} USD (no ${currency} rate)`;
    const home = (1 + usd) * (1 + change) - 1;
    return `${home >= 0 ? "+" : ""}${(home * 100).toFixed(1)}% ${currency}`;
  };
  useEffect(() => {
    let active = true;
    // Checklist 10.3: what moved each price; loads after the grid (prices may need fetching).
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
      <button type="button" className="wl-edit-toggle" onClick={() => setEditing(!editing)} aria-expanded={editing}>{editing ? "Close" : "Edit list"}</button>
      <div className="wl-legend">{(["supportive", "against", "mixed", "unknown"] as const).map((tone) => <span key={tone} className={`tone-${tone}`}><em aria-hidden>{TONE_GLYPH[tone]}</em>{TONE_LABEL[tone]}</span>)}<span className="wl-changed-key">changed since last card</span></div>
    </header>
    {editing ? <WatchlistEditor tickers={rows.map((row) => row.ticker)} /> : null}
    {drivers ? <div className="wl-drivers-summary" aria-label="What is moving the watchlist">
      <span><b>{count("noise")}</b> moved with macro, market or sector; company part normal</span>
      <span><b>{count("watch")}</b> some company-specific move</span>
      <span className="pd-kind-company"><b>{count("company") + count("fundamentals")}</b> company-specific{count("fundamentals") ? `, ${count("fundamentals")} with estimates moving` : ""}</span>
      <PriceDriversLegend />
      <label className="wl-currency">Show moves in <select value={currency} onChange={(event) => chooseCurrency(event.target.value)}>{CURRENCIES.map((code) => <option key={code} value={code}>{code}</option>)}</select></label>
      {currency !== "USD" && fx?.[currency] != null ? <small>USD {((fx[currency] as number) >= 0 ? "+" : "")}{((fx[currency] as number) * 100).toFixed(1)}% vs {currency} in 3M</small> : null}
    </div> : <p className="wl-summary">{driversError ? `Price drivers unavailable: ${driversError}` : "Working out what moved each price…"}</p>}
    {changedCount ? <p className="wl-summary">{changedCount} of {rows.length} companies changed since their previous card.</p> : null}
    <div className="wl-table" role="table">
      <div className="wl-row wl-head" role="row"><span role="columnheader">Company</span><span role="columnheader">What moved the price (3M)</span>{AXES.map(([, label]) => <span role="columnheader" key={label}>{label}</span>)}<span role="columnheader">Card</span></div>
      {[...rows].sort((a, b) => drivers ? KIND_ORDER.indexOf(drivers[a.ticker]?.reading.kind ?? "unknown") - KIND_ORDER.indexOf(drivers[b.ticker]?.reading.kind ?? "unknown") : 0).map((row) => <Link href={`/company/${row.ticker}`} className="wl-row" role="row" key={row.ticker}>
        <span role="cell" className="wl-ticker">{row.ticker}</span>
        <span role="cell" className="wl-drivers">{drivers?.[row.ticker] ? <>
          <span className="wl-move" title={currency === "USD" ? "3-month price change in US dollars" : `3-month return in ${currency}: USD return combined with the dollar's move against ${currency}. The bar still splits the USD move.`}>{homeMove(drivers[row.ticker].attribution?.windows?.["3M"]?.price_change)}</span>
          <DriverBar parts={drivers[row.ticker].attribution?.windows?.["3M"]?.parts} title={factorBreakdown(drivers[row.ticker].attribution)} />
          <ReadingTag reading={drivers[row.ticker].reading} compact />
        </> : <span className="wl-move">{drivers || driversError ? "—" : "…"}</span>}</span>
        {AXES.map(([key, label]) => {
          const state = row.axes[key];
          const tone = state ? axisTone(key, state) : "unknown";
          const change = companyChanges(row).find((item) => item.axis === key);
          return <span role="cell" key={key} className={`wl-cell tone-${tone}${change ? " changed" : ""}`} title={`${label}: ${state ?? "no card"}${change ? ` (was ${change.from})` : ""}`}>
            <em aria-hidden>{TONE_GLYPH[tone]}</em>{cellLabel(shortState(state), key, row)}
          </span>;
        })}
        <span role="cell" className="wl-date">{row.last_card ?? "—"}</span>
      </Link>)}
    </div>
  </section>;
}


// Checklist 18.15: the reader's own list. Saved to data/watchlist.json; the page reloads to read it.
const TICKER = /^[A-Z][A-Z0-9.^=-]{0,11}$/;
function WatchlistEditor({ tickers }: { tickers: string[] }) {
  const [list, setList] = useState(tickers);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const add = () => {
    const ticker = draft.trim().toUpperCase();
    if (!ticker) { setMessage("Type a ticker first, such as AAPL."); return; }
    if (!TICKER.test(ticker)) { setMessage(`${ticker} doesn't look like a ticker.`); return; }
    if (list.includes(ticker)) { setMessage(`${ticker} is already on the list.`); return; }
    if (list.length >= 40) { setMessage("The list holds at most 40 companies."); return; }
    setList([...list, ticker]); setDraft(""); setMessage(null);
  };
  const save = async () => {
    setSaving(true); setMessage(null);
    try {
      const response = await fetch("/api/research", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "watchlist-set", tickers: list }) });
      const body = await response.json();
      if (!response.ok || body.status !== "OK") { setMessage((body.errors ?? ["Couldn't save the list."]).join(" ")); setSaving(false); return; }
      window.location.reload();
    } catch (failure) {
      setMessage(`Couldn't save the list: ${failure instanceof Error ? failure.message : String(failure)}`); setSaving(false);
    }
  };
  const changed = list.join(",") !== tickers.join(",");
  return <div className="wl-editor" aria-label="Edit watchlist">
    <div className="wl-editor-chips">{list.map((ticker) => <span key={ticker}>{ticker}<button type="button" aria-label={`Remove ${ticker}`} onClick={() => setList(list.filter((item) => item !== ticker))}>×</button></span>)}</div>
    <form onSubmit={(event) => { event.preventDefault(); add(); }}>
      <input value={draft} onChange={(event) => { setDraft(event.target.value); setMessage(null); }} placeholder="AAPL" aria-label="Ticker to add" />
      <button type="submit">Add</button>
      <button type="button" className="wl-editor-save" disabled={!changed || saving} onClick={save}>{saving ? "Saving…" : "Save list"}</button>
    </form>
    {message ? <p className="wl-editor-error" role="alert">{message}</p> : <p className="wl-editor-note">New companies get their first reading when their card is opened.</p>}
  </div>;
}
