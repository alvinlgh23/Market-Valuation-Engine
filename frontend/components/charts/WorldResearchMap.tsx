"use client";

import Link from "next/link";
import { useState } from "react";
import type { MacroWorld } from "../../lib/macro-types";
import { MacroWorldMap } from "../macro/MacroWorldMap";

export function WorldResearchMap({ world }: { world: MacroWorld }) {
  const [hovered, setHovered] = useState("");
  const [selected, setSelected] = useState("");
  const [unavailable, setUnavailable] = useState("");
  const active = world.regions[selected || hovered];
  return <div className="overview-world-map"><MacroWorldMap regions={world.regions} selected={selected} onSelect={(id) => { setSelected(id); setUnavailable(""); }} onUnavailable={(label) => { setUnavailable(label); setSelected(""); }} onHover={setHovered} onLeave={() => setHovered("")} />{unavailable ? <aside className="world-brief unavailable"><header><span>NOT AVAILABLE</span><b>{unavailable}</b></header><p>No verified CHAINSTOX macro profile is integrated for this region.</p></aside> : active ? <aside className="world-brief"><header><span>{selected ? "SELECTED REGION" : "REGION PREVIEW"}</span><b>{active.availability}</b></header><h4>{active.name}</h4><p>{active.brief}</p><div>{active.components.slice(0, 4).map((component) => <span key={component.id}><b>{component.label}</b>{component.state}</span>)}</div>{selected ? <Link href={`/macro?mode=regions&region=${active.id}`}>Open country research panel →</Link> : <small>Click the region to hold this brief.</small>}</aside> : <aside className="world-brief empty"><span>HOVER A SUPPORTED REGION</span><p>Preview the macro brief. Click only when you want to hold the country context and continue deeper.</p></aside>}</div>;
}
