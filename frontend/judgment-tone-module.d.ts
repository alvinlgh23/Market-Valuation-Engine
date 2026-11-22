declare module "*judgment-tone.mjs" {
  export type Tone = "supportive" | "against" | "mixed" | "unknown";
  export const TONE_GLYPH: Record<Tone, string>;
  export const TONE_LABEL: Record<Tone, string>;
  export function axisTone(axis: string, state: string): Tone;
  export function confidenceDots(confidence: string): 1 | 2 | 3;
  export function percentileWidth(value: unknown): number | null;
}
