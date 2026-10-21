import type { QuantitativeDatum, TimeSeriesPoint } from "./visualization-types";

export function normalizeTimeSeriesPoints(points: TimeSeriesPoint[]): TimeSeriesPoint[] {
  return points.filter((point) => typeof point.date === "string" && point.date.length > 0 && point.value !== null && Number.isFinite(point.value));
}

export function groupDivergingData(data: QuantitativeDatum[]): QuantitativeDatum[][] {
  return Object.values(data.reduce<Record<string, QuantitativeDatum[]>>((groups, item) => {
    if (!Number.isFinite(item.value)) return groups;
    (groups[item.scaleGroup || item.unit] ||= []).push(item);
    return groups;
  }, {}));
}

export function coveragePercent(available?: number, total?: number): number | null {
  if (typeof available !== "number" || typeof total !== "number" || !Number.isFinite(available) || !Number.isFinite(total) || total <= 0) return null;
  return Math.max(0, Math.min(100, available / total * 100));
}
