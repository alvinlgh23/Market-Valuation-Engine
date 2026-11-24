declare module "*alerts.mjs" {
  export type AlertTrack = { predictive: boolean; verdict: string; text: string };
  export type AlertCriteria = { rule: string; now: string; exposure: string | null; asOf: string | null; track: AlertTrack | null; notes: string[] };
  export type AlertHolding = { ticker: string; value: number };
  export type Alert = {
    id: string;
    kind: "macro" | "carry" | "liquidity" | "company" | "earnings" | "reported" | "fomc" | "estimates" | "card" | "pattern";
    tone: "against" | "warning" | "info" | "tested";
    factor?: string;
    ticker?: string;
    title: string;
    metric: string;
    holdings?: AlertHolding[];
    more?: number;
    holdingsLabel?: string | null;
    holdingsNote?: string;
    score?: number;
    order?: number;
    criteria: AlertCriteria;
    href: string;
  };
  export type MarketRead = { chip: string | null; tone: string; headline: string; note: string };
  export const FACTOR_NAMES: Record<string, string>;
  export const FACTOR_RULES: Record<string, string>;
  export const EXPOSURE_RULE: string;
  export const CARRY_EXPOSURE_RULE: string;
  export const MIN_EFFECT: number;
  export function pct(value: number, digits?: number): string;
  export function historySentence(id: string, factor: unknown): string | null;
  export function plainTitle(id: string, factor: unknown): string;
  export function factorFigure(id: string, factor: unknown): string | null;
  export function factorEffects(drivers: unknown[] | undefined, factor: string): AlertHolding[];
  export function buildAlerts(input?: { environment?: unknown; drivers?: unknown[]; summary?: unknown[] }): Alert[];
  export function marketRead(alerts: Alert[], environment?: unknown): MarketRead;
  export function attentionItems(input: { events?: unknown; summary?: unknown[]; environment?: unknown; today: string }): Alert[];
  export function dataAge(asOf: string | null | undefined, today: string | null | undefined): { days: number | null; stale: boolean };
}
