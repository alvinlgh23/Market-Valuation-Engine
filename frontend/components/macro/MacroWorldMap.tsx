import type { MacroRegion } from "../../lib/macro-types";

const markerPositions: Record<string, [number, number]> = {
  US: [205, 185],
  EURO_AREA: [505, 157],
  JP: [785, 195],
  KR: [749, 200],
};

export function MacroWorldMap({ regions, selected, onSelect, onUnavailable, onHover, onLeave, onHoverUnavailable }: {
  regions: Record<string, MacroRegion>;
  selected?: string;
  onSelect: (region: string) => void;
  onUnavailable: (label: string) => void;
  onHover?: (region: string) => void;
  onLeave?: () => void;
  onHoverUnavailable?: (label: string) => void;
}) {
  return <div className="macro-map-frame">
    <svg className="macro-world-map" viewBox="0 0 960 470" role="img" aria-label="World macro coverage map">
      <g className="macro-land" aria-hidden="true">
        <path d="M73 91l82-47 95 8 65 41-26 39-48 7-25 43-35 6-22 71-32-14-22-82-52-23z" />
        <path d="M271 260l54 23 23 61-24 91-36-10-16-73-31-45z" />
        <path d="M432 80l54-32 93 18 37 36 94-17 111 44 67 59-36 49-90-10-39 35-39 78-59 2-13-76-52-41-40 13-17-73-63-16z" />
        <path d="M515 226l83 20 54 73-27 109-60-12-42-88z" />
        <path d="M766 351l65-29 59 37-13 59-75 11-45-42z" />
      </g>
      <g className="macro-grid-lines" aria-hidden="true"><path d="M0 117h960M0 235h960M0 353h960M240 0v470M480 0v470M720 0v470" /></g>
      {Object.entries(markerPositions).map(([id, [x, y]]) => {
        const region = regions[id];
        const isSelected = selected === id;
        return <g key={id} className={`macro-map-marker ${isSelected ? "selected" : ""} ${region.availability.toLowerCase()}`} role="button" tabIndex={0} aria-label={`Open ${region.name} macro profile`} onMouseEnter={() => onHover?.(id)} onMouseLeave={() => onLeave?.()} onFocus={() => onHover?.(id)} onBlur={() => onLeave?.()} onClick={() => onSelect(id)} onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onSelect(id)}>
          <circle cx={x} cy={y} r={8} />
          <circle className="marker-pulse" cx={x} cy={y} r={15} />
          <text x={x + 14} y={y - 12}>{id === "EURO_AREA" ? "EURO AREA" : id}</text>
        </g>;
      })}
      <g className="macro-map-marker unavailable" role="button" tabIndex={0} aria-label="Brazil not available" onMouseEnter={() => onHoverUnavailable?.("Brazil")} onMouseLeave={() => onLeave?.()} onFocus={() => onHoverUnavailable?.("Brazil")} onBlur={() => onLeave?.()} onClick={() => onUnavailable("Brazil")} onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onUnavailable("Brazil")}>
        <circle cx="299" cy="333" r="6" /><text x="311" y="327">BR · NOT AVAILABLE</text>
      </g>
    </svg>
    <div className="macro-map-legend"><span><i className="available" />Available</span><span><i className="partial" />Partial</span><span><i />Not available</span><small>EURO AREA = MONETARY UNION · SINGAPORE MARKER ENLARGED</small></div>
  </div>;
}
