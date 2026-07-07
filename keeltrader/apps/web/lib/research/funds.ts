"use client";

import { researchRequest } from "./client";
import { downloadResearchFile } from "./files";
import type { HedgeFundArchiveResponse, HedgeFundHoldingsResponse } from "./types";

export function getHedgeFundArchive() {
  return researchRequest<HedgeFundArchiveResponse>("/hedge-funds/archive", {}, { auth: "optional" });
}

export function getHedgeFundHoldings(fundId: string, market = "US", period?: string | null) {
  const params = new URLSearchParams();
  if (market) params.set("market", market);
  if (period) params.set("period", period);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return researchRequest<HedgeFundHoldingsResponse>(`/hedge-funds/${encodeURIComponent(fundId)}/holdings${suffix}`, {}, { auth: "optional" });
}

export function downloadHedgeFundMiniappCode(fundId: string) {
  return downloadResearchFile(`/hedge-funds/${encodeURIComponent(fundId)}/miniapp-code`, `${fundId}-miniapp-code.png`);
}
