export type FairValueScaleInput = { bear?: number | null; base?: number | null; bull?: number | null; market?: number | null };
export type FairValueScaleResult = { domainMin: number | null; domainMax: number | null; positions: Record<string, number>; valid: boolean };
export function fairValueCoordinates(values: FairValueScaleInput): FairValueScaleResult;
