import { apiJson } from "@/lib/api/client";

export type DataStatus = "complete" | "partial" | "stale" | "unavailable";

export type PortfolioAccount = {
  id: string;
  name: string;
  account_type: "manual" | "csv";
  base_currency: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
};

export type PortfolioPosition = {
  instrument_id: string;
  symbol: string;
  name: string;
  market: string;
  asset_class: string;
  currency: string;
  quantity: number;
  average_cost?: number;
  price?: number;
  price_date?: string;
  price_source?: "tushare" | "manual" | "transaction";
  market_value?: number;
  unrealized_pnl?: number;
};

export type PortfolioValuation = {
  account: PortfolioAccount;
  as_of: string;
  data_status: DataStatus;
  total_value: number;
  base_currency: string;
  cash: Record<string, number>;
  positions: PortfolioPosition[];
  missing: Array<{ symbol: string; reason: string }>;
};

export type AgentOSOverview = {
  as_of: string;
  data_status: DataStatus;
  portfolio: PortfolioValuation | { data_status: "unavailable"; reason: string };
  research: { hypotheses: number; decisions: number; experiments: number; documents: number };
  sections: Record<string, { data_status: DataStatus; source: string }>;
};

export type Hypothesis = {
  id: string;
  title: string;
  status: string;
  current_version: number;
  review_date?: string;
  thesis: string;
  falsification: string;
  evidence: Array<Record<string, unknown>>;
  outcome: Record<string, unknown>;
};

export type Decision = {
  id: string;
  title: string;
  status: string;
  current_version: number;
  review_date?: string;
  decided_at?: string;
  rationale: string;
  action: Record<string, unknown>;
  conditions: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  attribution: Record<string, unknown>;
};

export type StrategyTemplate = {
  key: "dividend_low_vol" | "momentum_trend" | "quality_growth";
  name: string;
  name_en: string;
  rebalance: string;
  default_cost_bps: number;
  description: string;
};

export type ResearchDocument = {
  id: string;
  title: string;
  document_type: string;
  current_version: number;
  status: string;
  updated_at: string;
};

export function agentOSDownloadUrl(url: string): string {
  return url.replace(/^\/api\/v1\//, "/api/proxy/v1/");
}

export const agentOSApi = {
  overview: () => apiJson<AgentOSOverview>("/v1/agent/os/overview"),
  accounts: () => apiJson<{ items: PortfolioAccount[] }>("/v1/agent/portfolio/accounts"),
  createAccount: (body: Pick<PortfolioAccount, "name" | "base_currency"> & { account_type?: "manual" | "csv" }) =>
    apiJson<PortfolioAccount>("/v1/agent/portfolio/accounts", { method: "POST", body }),
  valuation: (accountId: string) => apiJson<PortfolioValuation>(`/v1/agent/portfolio/accounts/${accountId}/valuation`),
  transactions: (accountId: string) => apiJson<{ items: Array<Record<string, unknown>> }>(`/v1/agent/portfolio/accounts/${accountId}/transactions`),
  addTransaction: (accountId: string, body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>(`/v1/agent/portfolio/accounts/${accountId}/transactions`, { method: "POST", body }),
  previewImport: (body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>("/v1/agent/portfolio/imports/preview", { method: "POST", body }),
  commitImport: (batchId: string) =>
    apiJson<Record<string, unknown>>(`/v1/agent/portfolio/imports/${batchId}/commit`, { method: "POST" }),
  nav: (accountId: string) => apiJson<{ items: Array<{ date: string; nav: number; return?: number }>; history_available: boolean }>(`/v1/agent/portfolio/accounts/${accountId}/nav`),
  hypotheses: () => apiJson<{ items: Hypothesis[] }>("/v1/agent/hypotheses"),
  createHypothesis: (body: Record<string, unknown>) => apiJson<Hypothesis>("/v1/agent/hypotheses", { method: "POST", body }),
  decisions: () => apiJson<{ items: Decision[] }>("/v1/agent/decisions"),
  createDecision: (body: Record<string, unknown>) => apiJson<Decision>("/v1/agent/decisions", { method: "POST", body }),
  strategyTemplates: () => apiJson<{ items: StrategyTemplate[] }>("/v1/agent/strategy-experiments/templates"),
  experiments: () => apiJson<{ items: Array<Record<string, unknown>> }>("/v1/agent/strategy-experiments"),
  createExperiment: (body: { name: string; template_key: StrategyTemplate["key"]; parameters?: Record<string, unknown> }) =>
    apiJson<Record<string, unknown>>("/v1/agent/strategy-experiments", { method: "POST", body }),
  runExperiment: (experimentId: string, body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>(`/v1/agent/strategy-experiments/${experimentId}/runs`, { method: "POST", body }),
  consensus: () => apiJson<{ items: Array<Record<string, unknown>> }>("/v1/agent/consensus"),
  documents: () => apiJson<{ items: ResearchDocument[] }>("/v1/agent/research-documents"),
  createDocument: (body: { title: string; document_type: string }) =>
    apiJson<ResearchDocument>("/v1/agent/research-documents", { method: "POST", body }),
  generateDocument: (documentId: string, body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>(`/v1/agent/research-documents/${documentId}/generate`, { method: "POST", body }),
  documentVersions: (documentId: string) =>
    apiJson<{ items: Array<{ id: string; version: number; locale: string; status: string; content_sha256?: string; size_bytes?: number; download_url: string }> }>(`/v1/agent/research-documents/${documentId}/versions`),
};
