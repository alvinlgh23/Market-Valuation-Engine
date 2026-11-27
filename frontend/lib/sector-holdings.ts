import type { TodayHolding } from "./today-model";

// Which of the 11 S&P 500 sectors each holding sits in (owner-approved 2026-11-27). A card names one fund for the
// company; industry and theme funds are shown under their parent sector (semiconductors and cybersecurity under
// Technology, banks under Financials...). Funds with no parent sector (e.g. Bitcoin) are left off the sector tiles.

export const GICS_PARENT: Record<string, string> = {
  XLK: "XLK", XLC: "XLC", XLY: "XLY", XLP: "XLP", XLV: "XLV", XLF: "XLF", XLE: "XLE", XLI: "XLI", XLB: "XLB", XLU: "XLU", XLRE: "XLRE",
  SMH: "XLK", SOXX: "XLK", IGV: "XLK", CIBR: "XLK", SKYY: "XLK", QTUM: "XLK",
  KBE: "XLF", KRE: "XLF",
  XBI: "XLV", IBB: "XLV",
  XRT: "XLY", ITB: "XLY",
  ITA: "XLI", IYT: "XLI", JETS: "XLI", UFO: "XLI",
  XOP: "XLE", URA: "XLE", ICLN: "XLE",
  COPX: "XLB", GDX: "XLB",
};

/** Holdings by S&P 500 sector fund, in the order they were added. */
export function holdingsBySector(holdings: TodayHolding[]): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const h of holdings) {
    const parent = h.sectorEtf ? GICS_PARENT[h.sectorEtf] : undefined;
    if (parent) (out[parent] ??= []).push(h.ticker);
  }
  return out;
}

/** Holdings to list on one fund's page: an exact match, or every holding whose fund rolls up to this sector. */
export function holdingsForFund(holdings: TodayHolding[], etf: string): TodayHolding[] {
  return holdings.filter((h) => h.sectorEtf === etf || (h.sectorEtf && GICS_PARENT[h.sectorEtf] === etf));
}
