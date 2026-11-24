declare module "*plain-words.mjs" {
  export function unusualness(p: unknown): "Typical" | "Slightly unusual" | "Unusual" | "Extreme" | null;
  export function versusHistory(p: unknown, period?: string, noun?: string): string | null;
  export function historyLabel(p: unknown, kind?: "level" | "strength" | "price"): string | null;
}
