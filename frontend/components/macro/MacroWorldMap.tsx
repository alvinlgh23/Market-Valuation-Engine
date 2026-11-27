import type { MacroRegion, MacroTransmission } from "../../lib/macro-types";

import { LAND_DOTS } from "../../lib/world-dots";

// Real positions (2026-11-27): plate carree matching the dotted land in lib/world-dots.ts.
const K = 960 / 360;
function proj(lon: number, lat: number) { return { x: (lon + 180) * K, y: (84 - lat) * K }; }

type Anchor = { lon: number; lat: number; name: string; side: "left" | "right" };
const ANCHORS: Record<string, Anchor> = {
  US: { lon: -98, lat: 39, name: "United States", side: "left" },
  EURO_AREA: { lon: 10, lat: 50, name: "Euro area", side: "right" },
  KR: { lon: 127.8, lat: 36.5, name: "Korea", side: "left" },
  JP: { lon: 139.7, lat: 35.7, name: "Japan", side: "right" },
};
const BRAZIL = proj(-51, -10);

// Each channel: from, to, the two bezier control points, and its short label (drawn at the curve's midpoint).
const TRANSMISSION_PATHS: Record<string, { from: string; to: string; c1: [number, number]; c2: [number, number]; shortLabel: string }> = {
  "jp-us-yen-carry": { from: "JP", to: "US", c1: [700, 20], c2: [380, 20], shortLabel: "Yen carry → US risk" },
  "us-jp-rate-fx": { from: "US", to: "JP", c1: [380, 330], c2: [700, 330], shortLabel: "US rates → USD/JPY" },
  "us-eu-rate-fx": { from: "US", to: "EURO_AREA", c1: [300, 50], c2: [430, 40], shortLabel: "Fed / ECB → EUR/USD" },
  "us-kr-dollar-kospi": { from: "US", to: "KR", c1: [380, 260], c2: [680, 260], shortLabel: "USD → KRW & chips" },
};

function arcGeometry(id: string) {
  const g = TRANSMISSION_PATHS[id];
  if (!g) return null;
  const a = proj(ANCHORS[g.from].lon, ANCHORS[g.from].lat), b = proj(ANCHORS[g.to].lon, ANCHORS[g.to].lat);
  const [c1x, c1y] = g.c1, [c2x, c2y] = g.c2;
  return {
    d: `M ${a.x.toFixed(1)} ${a.y.toFixed(1)} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${b.x.toFixed(1)} ${b.y.toFixed(1)}`,
    labelX: 0.125 * a.x + 0.375 * c1x + 0.375 * c2x + 0.125 * b.x,
    labelY: 0.125 * a.y + 0.375 * c1y + 0.375 * c2y + 0.125 * b.y,
    shortLabel: g.shortLabel,
  };
}

function regionHeadline(id: string, region: MacroRegion | undefined): { line1: string; line2: string } {
  if (!region) return { line1: id, line2: "Unavailable" };
  const byId = Object.fromEntries(region.components.map((c) => [c.id, c.state]));
  if (id === "US") {
    return {
      line1: `Fed: ${byId.policy ?? "Active"}`,
      line2: `CPI ${byId.inflation ?? "—"} · ${String(byId.liquidity ?? "").replace("Liquidity ", "Liq ")}`,
    };
  }
  if (id === "EURO_AREA") {
    return {
      line1: `ECB: ${byId.policy ?? "Active"}`,
      line2: `CPI ${byId.inflation ?? "—"} · Growth ${byId.growth ?? "—"}`,
    };
  }
  if (id === "JP") {
    return {
      line1: `BOJ: ${byId.policy ?? "Active"}`,
      line2: `CPI ${byId.inflation ?? "—"} · Carry watch`,
    };
  }
  if (id === "KR") {
    return {
      line1: `KOSPI: ${byId.markets ?? "Active"}`,
      line2: `Semiconductor & FX cycle`,
    };
  }
  return { line1: region.name, line2: region.availability };
}

export function MacroWorldMap({
  regions,
  transmissions = [],
  selected,
  selectedEdge,
  onSelect,
  onSelectEdge,
  onUnavailable,
  onHover,
  onLeave,
  onHoverUnavailable,
}: {
  regions: Record<string, MacroRegion>;
  transmissions?: MacroTransmission[];
  selected?: string;
  selectedEdge?: string;
  onSelect: (region: string) => void;
  onSelectEdge?: (edgeId: string) => void;
  onUnavailable: (label: string) => void;
  onHover?: (region: string) => void;
  onLeave?: () => void;
  onHoverUnavailable?: (label: string) => void;
}) {
  return (
    <div className="macro-map-frame macro-map-cockpit">
      <svg className="macro-world-map" viewBox="0 0 960 395" role="img" aria-label="World macro coverage map">
        <defs>
          <radialGradient id="macro-ocean-glow" cx="50%" cy="44%" r="60%">
            <stop offset="0%" stopColor="#151924" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0b0c10" stopOpacity="1" />
          </radialGradient>
          <marker id="macro-arc-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0.5 L5.5,3 L0,5.5 Z" fill="#e5a54b" fillOpacity="0.85" />
          </marker>
          <marker id="macro-arc-arrow-watch" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0.5 L5.5,3 L0,5.5 Z" fill="#7d8597" fillOpacity="0.7" />
          </marker>
        </defs>

        <rect x="0" y="0" width="960" height="395" fill="url(#macro-ocean-glow)" />

        {/* Subtle latitude / longitude graticule */}
        <g className="macro-grid-lines" aria-hidden="true">
          <path d="M0 95h960M0 175h960M0 255h960M0 335h960M190 0v450M380 0v450M570 0v450M760 0v450" />
          <path className="macro-equator" d="M0 255h960" />
        </g>

        {/* Land as dots: Natural Earth 1:110m, public domain */}
        <path className="macro-dots" d={LAND_DOTS} aria-hidden="true" />

        {/* Cross-border transmission arcs */}
        <g className="macro-map-arcs">
          {transmissions.map((edge) => {
            const geom = arcGeometry(edge.id);
            if (!geom) return null;
            const isActive = edge.current_state === "ACTIVE";
            const isSelected = selectedEdge === edge.id;
            return (
              <g
                key={edge.id}
                className={`macro-map-arc ${isActive ? "is-active" : "is-watch"}${isSelected ? " is-selected" : ""}`}
                role={onSelectEdge ? "button" : undefined}
                tabIndex={onSelectEdge ? 0 : undefined}
                aria-label={`${edge.label}: ${edge.current_state}`}
                onClick={() => onSelectEdge?.(edge.id)}
                onKeyDown={(ev) => (ev.key === "Enter" || ev.key === " ") && onSelectEdge?.(edge.id)}
              >
                <path className="arc-hit" d={geom.d} />
                <path
                  className="arc-line"
                  d={geom.d}
                  markerEnd={isActive ? "url(#macro-arc-arrow)" : "url(#macro-arc-arrow-watch)"}
                />
                <g transform={`translate(${geom.labelX}, ${geom.labelY})`}>
                  <rect x="-66" y="-10" width="132" height="19" rx="9.5" className="arc-pill-bg" />
                  <text x="0" y="3" textAnchor="middle" className="arc-pill-text">
                    {geom.shortLabel}
                  </text>
                </g>
              </g>
            );
          })}
        </g>

        {/* Modelled economies: a dot and a name; the reading is in the tooltip and the side panel */}
        {Object.entries(ANCHORS).map(([id, pos]) => {
          const region = regions[id];
          if (!region) return null;
          const { x, y } = proj(pos.lon, pos.lat);
          const isSelected = selected === id;
          const headline = regionHeadline(id, region);
          const width = pos.name.length * 6.4 + 18;
          const left = pos.side === "left";
          const rx = left ? x - 12 - width : x + 12;
          return (
            <g
              key={id}
              className={`macro-map-marker ${isSelected ? "selected" : ""} ${region.availability.toLowerCase()}`}
              role="button"
              tabIndex={0}
              aria-label={`Open ${region.name} macro profile`}
              onMouseEnter={() => onHover?.(id)}
              onMouseLeave={() => onLeave?.()}
              onFocus={() => onHover?.(id)}
              onBlur={() => onLeave?.()}
              onClick={() => onSelect(id)}
              onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onSelect(id)}
            >
              <title>{`${region.name}: ${headline.line1} · ${headline.line2}`}</title>
              <circle className="marker-pulse" cx={x} cy={y} r={12} />
              <circle className="marker-dot" cx={x} cy={y} r={5} />
              <rect className="marker-name-bg" x={rx} y={y - 10} width={width} height={20} rx={10} />
              <text className="marker-name" x={rx + width / 2} y={y + 4} textAnchor="middle">{pos.name}</text>
            </g>
          );
        })}

        {/* Not modelled: a quiet dot, detail on hover (no label on the map) */}
        <g
          className="macro-map-marker unavailable"
          role="button"
          tabIndex={0}
          aria-label="Brazil: not modelled"
          onMouseEnter={() => onHoverUnavailable?.("Brazil")}
          onMouseLeave={() => onLeave?.()}
          onFocus={() => onHoverUnavailable?.("Brazil")}
          onBlur={() => onLeave?.()}
          onClick={() => onUnavailable("Brazil")}
          onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onUnavailable("Brazil")}
        >
          <title>Brazil: not modelled</title>
          <circle cx={BRAZIL.x} cy={BRAZIL.y} r="4" />
        </g>
      </svg>

      <div className="macro-map-legend">
        <span><i className="arc-key active" />Active cross-border stress</span>
        <span><i className="arc-key watch" />Monitored channel</span>
        <span><i className="available" />Modelled economy (click to inspect)</span>
        <span><i />Not modelled (hover for detail)</span>
      </div>
    </div>
  );
}
