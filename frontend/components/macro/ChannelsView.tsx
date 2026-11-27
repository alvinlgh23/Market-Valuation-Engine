"use client";

import Link from "next/link";
import type { MacroTransmission, MacroWorld } from "../../lib/macro-types";
import { CHANNEL_CHAIN, channelExposure, type DriverLike } from "../../lib/channel-exposure";

// "Channels → your holdings" (replaces the Mechanism Graph, 2026-11-27): each cross-border channel as a chain, its
// current reading, and the holdings whose measured 3-month price split it touched.

const ORDER: Record<string, number> = { ACTIVE: 0, WATCH: 1, INSUFFICIENT: 2 };
const STATE_WORD: Record<string, string> = { ACTIVE: "Active", WATCH: "Watching", INSUFFICIENT: "Not enough data" };
const code = (id: string) => (id === "EURO_AREA" ? "EA" : id);

function pct(v: number) { return `${v < 0 ? "−" : "+"}${Math.abs(v * 100).toFixed(1)}%`; }

function Channel({ channel, drivers, world }: { channel: MacroTransmission; drivers: DriverLike[] | null; world: MacroWorld }) {
  const chain = CHANNEL_CHAIN[channel.id] ?? [channel.source, channel.target];
  const exposure = drivers ? channelExposure(channel.id, drivers) : null;
  const touched = exposure?.filter((f) => f.holdings.length) ?? [];
  const max = Math.max(0.05, ...touched.flatMap((f) => f.holdings.map((h) => Math.abs(h.value))));
  const evidence = channel.evidence_ids.map((id) => world.evidence_index[id]).filter(Boolean);
  const state = channel.current_state;
  return <article className={`ch-row state-${state.toLowerCase()}`}>
    <header>
      <span className="ch-route">{code(channel.source)} → {code(channel.target)}</span>
      <h3>{channel.label}</h3>
      <span className="ch-state">{STATE_WORD[state] ?? state}</span>
    </header>
    <ol className="ch-chain" aria-label="How the channel works">{chain.map((step, i) => <li key={step}>{step}{i < chain.length - 1 ? <i aria-hidden>→</i> : null}</li>)}</ol>
    <div className="ch-holdings">
      <span className="ch-sub">Your holdings it moved · 3 months</span>
      {!exposure ? <p className="ch-quiet">Reading your holdings…</p> : !touched.length
        ? <p className="ch-quiet">None of your holdings moved by a point or more through {exposure.map((f) => f.label.toLowerCase()).join(" or ")}.</p>
        : touched.map((f) => <div key={f.factor} className="ch-factor">
          <b>{f.label}</b>
          <div className="ch-bars">{f.holdings.map((h) => <Link key={h.ticker} href={`/company/${h.ticker}`} className={h.value < 0 ? "down" : "up"}>
            <span>{h.ticker}</span><i style={{ width: `${(Math.abs(h.value) / max) * 100}%` }} /><em>{pct(h.value)}</em>
          </Link>)}</div>
        </div>)}
    </div>
    <details className="ch-more"><summary>Mechanism and evidence</summary>
      <p>{channel.mechanism}</p>
      <p>{channel.summary}</p>
      {evidence.map((item) => <p key={item.id} className="ch-ev"><span>{item.label}</span><b>{item.value}</b><small>{item.period}</small></p>)}
      <p className="ch-caveat">{channel.caveat}</p>
    </details>
  </article>;
}

export function ChannelsView({ world, drivers }: { world: MacroWorld; drivers: DriverLike[] | null }) {
  const channels = [...world.transmissions].sort((a, b) => (ORDER[a.current_state] ?? 9) - (ORDER[b.current_state] ?? 9));
  return <section className="ch-view" aria-label="Cross-border channels and your holdings">
    <header className="ch-head">
      <h2>Channels → your holdings</h2>
      <p>How policy and currency moves abroad reach US stocks, and which of your holdings each channel measurably moved. A channel is not proof it caused a move.</p>
    </header>
    {channels.map((channel) => <Channel key={channel.id} channel={channel} drivers={drivers} world={world} />)}
  </section>;
}
