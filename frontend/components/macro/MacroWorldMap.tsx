import type { MacroRegion, MacroTransmission } from "../../lib/macro-types";

const ANCHORS: Record<string, { cx: number; cy: number; boxX: number; boxY: number; boxW: number; shortCode: string }> = {
  US: { cx: 212, cy: 174, boxX: 38, boxY: 146, boxW: 156, shortCode: "US" },
  EURO_AREA: { cx: 492, cy: 138, boxX: 446, boxY: 74, boxW: 168, shortCode: "EURO AREA" },
  KR: { cx: 760, cy: 184, boxX: 604, boxY: 198, boxW: 154, shortCode: "KR" },
  JP: { cx: 816, cy: 176, boxX: 790, boxY: 112, boxW: 156, shortCode: "JP" },
};

const TRANSMISSION_PATHS: Record<string, { d: string; labelX: number; labelY: number; shortLabel: string }> = {
  "jp-us-yen-carry": {
    d: "M 816 170 C 660 8, 350 8, 212 168",
    labelX: 514,
    labelY: 30,
    shortLabel: "Yen carry → US risk",
  },
  "us-jp-rate-fx": {
    d: "M 208 184 C 380 392, 660 392, 816 184",
    labelX: 540,
    labelY: 344,
    shortLabel: "US rates → USD/JPY",
  },
  "us-eu-rate-fx": {
    d: "M 218 168 Q 332 104 486 136",
    labelX: 326,
    labelY: 118,
    shortLabel: "Fed / ECB → EUR/USD",
  },
  "us-kr-dollar-kospi": {
    d: "M 214 182 C 370 306, 598 306, 756 188",
    labelX: 486,
    labelY: 278,
    shortLabel: "USD → KRW & Semis",
  },
};

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
      <svg className="macro-world-map" viewBox="0 0 960 450" role="img" aria-label="World macro coverage map">
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

        <rect x="0" y="0" width="960" height="450" fill="url(#macro-ocean-glow)" />

        {/* Subtle latitude / longitude graticule */}
        <g className="macro-grid-lines" aria-hidden="true">
          <path d="M0 95h960M0 175h960M0 255h960M0 335h960M190 0v450M380 0v450M570 0v450M760 0v450" />
          <path className="macro-equator" d="M0 255h960" />
        </g>

        {/* Detailed recognizable world landmasses */}
        <g className="macro-land" aria-hidden="true">
          {/* North America */}
          <path d="M44 96 L72 76 L118 68 L168 64 L218 74 L256 96 L284 124 L272 146 L254 162 L244 188 L226 204 L212 218 L196 226 L186 242 L168 232 L154 214 L138 192 L130 168 L112 150 L88 134 L58 122 Z" />
          {/* Greenland */}
          <path d="M294 42 L346 34 L378 52 L364 82 L326 92 L298 72 Z" />
          {/* Caribbean / Central America bridge */}
          <path d="M186 242 L208 250 L226 264 L214 270 L194 256 Z" />
          {/* South America */}
          <path d="M234 264 L274 262 L316 282 L348 308 L344 344 L322 382 L296 418 L276 430 L264 404 L256 364 L238 326 L226 292 Z" />
          {/* UK & Ireland */}
          <path d="M442 114 L456 110 L462 128 L446 132 Z M432 120 L440 118 L440 128 L432 128 Z" />
          {/* Continental Europe + Scandinavia */}
          <path d="M468 74 L498 60 L532 66 L552 86 L538 104 L558 114 L566 138 L544 156 L524 166 L504 164 L492 174 L478 164 L456 168 L446 154 L458 136 L476 124 L474 102 Z" />
          {/* Africa */}
          <path d="M450 184 L492 180 L534 190 L568 212 L592 246 L584 282 L566 322 L546 364 L518 380 L498 354 L490 314 L476 278 L448 254 L438 218 Z" />
          {/* Madagascar */}
          <path d="M594 332 L606 328 L608 356 L596 362 Z" />
          {/* Eurasia + Middle East + India + China + SE Asia */}
          <path d="M554 68 L618 54 L704 52 L792 62 L866 82 L896 106 L868 128 L832 138 L804 156 L790 182 L772 208 L748 228 L724 248 L704 268 L692 246 L668 232 L646 258 L628 232 L604 218 L576 206 L562 184 L574 162 L564 136 Z" />
          {/* Korean Peninsula */}
          <path d="M752 172 L764 172 L768 192 L756 194 Z" />
          {/* Japanese Archipelago */}
          <path d="M812 150 L824 152 L828 166 L820 184 L804 196 L798 188 L810 172 Z" />
          {/* Maritime SE Asia / Indonesia / Philippines */}
          <path d="M726 274 L758 278 L778 292 L752 298 L722 288 Z M782 244 L794 248 L796 268 L784 266 Z" />
          {/* Australia & New Zealand */}
          <path d="M768 326 L818 314 L864 328 L878 362 L856 392 L808 396 L770 374 Z M898 392 L914 384 L918 408 L902 414 Z" />
        </g>

        {/* Cross-border transmission arcs */}
        <g className="macro-map-arcs">
          {transmissions.map((edge) => {
            const geom = TRANSMISSION_PATHS[edge.id];
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

        {/* Supported Economy Nodes + Live Stance Callout Cards */}
        {Object.entries(ANCHORS).map(([id, pos]) => {
          const region = regions[id];
          if (!region) return null;
          const isSelected = selected === id;
          const headline = regionHeadline(id, region);
          const cardCenterX = pos.boxX + pos.boxW / 2;
          const cardCenterY = pos.boxY + 24;
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
              <line x1={pos.cx} y1={pos.cy} x2={cardCenterX} y2={cardCenterY} className="marker-leader" />
              <circle className="marker-pulse" cx={pos.cx} cy={pos.cy} r={13} />
              <circle className="marker-dot" cx={pos.cx} cy={pos.cy} r={5.5} />
              <g className="marker-callout" transform={`translate(${pos.boxX}, ${pos.boxY})`}>
                <rect width={pos.boxW} height="48" rx="8" className="marker-card-bg" />
                <text x="10" y="16" className="marker-card-code">{pos.shortCode}</text>
                <text x="10" y="30" className="marker-card-line1">{headline.line1}</text>
                <text x="10" y="42" className="marker-card-line2">{headline.line2}</text>
              </g>
            </g>
          );
        })}

        {/* Subtle unmodelled marker preserved for honest coverage boundary & regression checks */}
        <g
          className="macro-map-marker unavailable"
          role="button"
          tabIndex={0}
          aria-label="Brazil not available"
          onMouseEnter={() => onHoverUnavailable?.("Brazil")}
          onMouseLeave={() => onLeave?.()}
          onFocus={() => onHoverUnavailable?.("Brazil")}
          onBlur={() => onLeave?.()}
          onClick={() => onUnavailable("Brazil")}
          onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onUnavailable("Brazil")}
        >
          <circle cx="306" cy="322" r="4.5" />
          <text x="316" y="325" className="marker-unavail-label">BR · unmodelled</text>
        </g>
      </svg>

      <div className="macro-map-legend">
        <span><i className="arc-key active" />Active cross-border stress</span>
        <span><i className="arc-key watch" />Monitored channel</span>
        <span><i className="available" />Modelled economy (click to inspect)</span>
        <span><i />Unmodelled region</span>
      </div>
    </div>
  );
}
