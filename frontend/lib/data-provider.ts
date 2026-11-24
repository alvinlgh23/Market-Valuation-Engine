import type { CompanyEconomicsPayload } from "./company-economics-types";
import cost from "./fixtures/company-economics/COST.json";
import jpm from "./fixtures/company-economics/JPM.json";
import msft from "./fixtures/company-economics/MSFT.json";
import nvda from "./fixtures/company-economics/NVDA.json";
import pltr from "./fixtures/company-economics/PLTR.json";
import tsm from "./fixtures/company-economics/TSM.json";
import amd from "./fixtures/company-economics/AMD.json";
import bac from "./fixtures/company-economics/BAC.json";
import cat from "./fixtures/company-economics/CAT.json";
import crm from "./fixtures/company-economics/CRM.json";
import lly from "./fixtures/company-economics/LLY.json";
import meta from "./fixtures/company-economics/META.json";
import uber from "./fixtures/company-economics/UBER.json";
import v from "./fixtures/company-economics/V.json";
import wmt from "./fixtures/company-economics/WMT.json";
import xom from "./fixtures/company-economics/XOM.json";

const companyEconomicsFixtures: Record<string, CompanyEconomicsPayload> = {
  PLTR: pltr as CompanyEconomicsPayload,
  NVDA: nvda as CompanyEconomicsPayload,
  MSFT: msft as CompanyEconomicsPayload,
  JPM: jpm as CompanyEconomicsPayload,
  COST: cost as CompanyEconomicsPayload,
  TSM: tsm as CompanyEconomicsPayload,
  AMD: amd as CompanyEconomicsPayload,
  BAC: bac as CompanyEconomicsPayload,
  CAT: cat as CompanyEconomicsPayload,
  CRM: crm as CompanyEconomicsPayload,
  LLY: lly as CompanyEconomicsPayload,
  META: meta as CompanyEconomicsPayload,
  UBER: uber as CompanyEconomicsPayload,
  V: v as CompanyEconomicsPayload,
  WMT: wmt as CompanyEconomicsPayload,
  XOM: xom as CompanyEconomicsPayload
};

export interface CompanyResearchProvider {
  getCompanyResearch(ticker: string): Promise<CompanyEconomicsPayload | null>;
  getCompanyEconomics(ticker: string): Promise<CompanyEconomicsPayload | null>;
  getValuation(ticker: string): Promise<CompanyEconomicsPayload["company_economics"]["valuation_assumption_review"] | null>;
}

export const fixtureCompanyResearchProvider: CompanyResearchProvider = {
  async getCompanyResearch(ticker) {
    return companyEconomicsFixtures[ticker.toUpperCase()] ?? null;
  },
  async getCompanyEconomics(ticker) {
    return companyEconomicsFixtures[ticker.toUpperCase()] ?? null;
  },
  async getValuation(ticker) {
    return companyEconomicsFixtures[ticker.toUpperCase()]?.company_economics.valuation_assumption_review ?? null;
  }
};

export function getCompanyResearchFixture(ticker: string): CompanyEconomicsPayload | null {
  return companyEconomicsFixtures[ticker.toUpperCase()] ?? null;
}
