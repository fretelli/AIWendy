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
  instrument_type: string;
  provider_symbol?: string;
  direction: "long" | "short";
  multiplier: number;
  currency: string;
  quantity: number;
  average_cost?: number;
  price?: number;
  price_date?: string;
  price_status?: "current" | "stale" | "unavailable";
  price_as_of?: string;
  price_source?: string;
  fx_source?: string;
  fx_as_of?: string;
  valuation_method?: string;
  market_value?: number;
  unrealized_pnl?: number;
  realized_pnl?: number;
  gap_reason?: string;
};

export type PortfolioValuation = {
  account: PortfolioAccount;
  as_of: string;
  data_status: DataStatus;
  total_value: number;
  base_currency: string;
  cash: Record<string, { amount: number; base_value?: number; fx_source?: string; fx_as_of?: string }>;
  positions: PortfolioPosition[];
  missing: Array<{ kind: string; symbol?: string; currency?: string; reason: string; price_as_of?: string }>;
};

export type AgentOSOverview = {
  as_of: string;
  data_status: DataStatus;
  portfolio: PortfolioValuation | { data_status: "unavailable"; reason: string };
  analytics: PortfolioAnalytics | { data_status: "unavailable"; reason: string };
  tasks: { active: number; total: number };
  research: { hypotheses: number; decisions: number; experiments: number; documents: number };
  sections: Record<string, { data_status: DataStatus; source: string }>;
};

export type PortfolioAnalytics = {
  account_id: string;
  as_of: string;
  period: "1M" | "3M" | "1Y" | "3Y";
  base_currency: string;
  data_status: DataStatus;
  total_value: number;
  cash: { status: DataStatus; value?: number | null; method: string };
  today_pnl: { status: DataStatus; value?: number | null; as_of?: string | null; method: string; reason?: string };
  volatility: { status: DataStatus; value?: number | null; observations: number; method: string; reason?: string };
  drawdown: { status: DataStatus; current?: number | null; maximum?: number | null; peak_date?: string | null; trough_date?: string | null; reason?: string };
  risk_contribution: { status: DataStatus; items: Array<Record<string, unknown>>; reason?: string };
  allocation_drift: { status: DataStatus; items: Array<Record<string, unknown>>; reason?: string };
  drift_decomposition: { status: DataStatus; active_tilt?: number | null; passive_drift?: number | null; reason?: string };
  risk_budget: { status: DataStatus; used?: number | null; limit?: number | null; reason?: string };
  nav: { items: Array<{ date: string; nav: number; net_flow?: number; return?: number }>; history_available: boolean };
  missing: PortfolioValuation["missing"];
};

export type HoldingDetail = {
  account_id: string;
  position: PortfolioPosition;
  history: { available: boolean; source?: string; reason?: string; items: Array<{ date: string; price: number }> };
  fundamentals: { available: boolean; reason?: string; data: Record<string, Array<Record<string, unknown>>> };
  derivatives: Record<string, unknown> & { available: boolean; reason?: string };
  portfolio_context: { market_value_weight?: number; risk_contribution?: number; risk_status: DataStatus; risk_reason?: string };
};

export type ResearchLibraryItem = {
  id?: string;
  report_id?: string;
  title?: string;
  display_title?: string;
  broker?: string;
  report_date?: string;
  summary?: string;
  excerpt?: string;
  ingest_status?: string;
  sections_count?: number;
  company_names?: string[];
  metadata?: Record<string, unknown>;
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
  analytics: (accountId: string, period: "1M" | "3M" | "1Y" | "3Y" = "1Y") =>
    apiJson<PortfolioAnalytics>(`/v1/agent/portfolio/accounts/${accountId}/analytics?period=${period}`),
  holdingDetail: (accountId: string, instrumentId: string) =>
    apiJson<HoldingDetail>(`/v1/agent/portfolio/accounts/${accountId}/holdings/${instrumentId}/detail`),
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
  submitContentBrief: (
    hypothesisId: string,
    body: {
      project_type: "article" | "social" | "drama" | "podcast" | "course" | "other";
      audience: string;
      objective: string;
      requested_channels: string[];
    },
  ) =>
    apiJson<Record<string, unknown>>(
      `/v1/agent/hypotheses/${hypothesisId}/content-brief`,
      { method: "POST", body },
    ),
  decisions: () => apiJson<{ items: Decision[] }>("/v1/agent/decisions"),
  createDecision: (body: Record<string, unknown>) => apiJson<Decision>("/v1/agent/decisions", { method: "POST", body }),
  strategyTemplates: () => apiJson<{ items: StrategyTemplate[] }>("/v1/agent/strategy-experiments/templates"),
  experiments: () => apiJson<{ items: Array<Record<string, unknown>> }>("/v1/agent/strategy-experiments"),
  createExperiment: (body: { name: string; template_key: StrategyTemplate["key"]; parameters?: Record<string, unknown> }) =>
    apiJson<Record<string, unknown>>("/v1/agent/strategy-experiments", { method: "POST", body }),
  runExperiment: (experimentId: string, body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>(`/v1/agent/strategy-experiments/${experimentId}/runs`, { method: "POST", body }),
  consensus: () => apiJson<{ items: Array<Record<string, unknown>> }>("/v1/agent/consensus"),
  researchLibrary: (options: { query?: string; limit?: number; offset?: number; sourceFamily?: string } = {}) => {
    const params = new URLSearchParams();
    if (options.query) params.set("query", options.query);
    if (options.limit) params.set("limit", String(options.limit));
    if (options.offset) params.set("offset", String(options.offset));
    if (options.sourceFamily) params.set("source_family", options.sourceFamily);
    return apiJson<{ available: boolean; items: ResearchLibraryItem[]; reason?: string }>(`/v1/agent/research/library?${params}`);
  },
  researchLibraryStatus: () => apiJson<{ available: boolean; data?: Record<string, unknown>; reason?: string }>("/v1/agent/research/library/status"),
  researchLibraryDetail: (reportId: string) => apiJson<{ available: boolean; report?: Record<string, unknown>; reason?: string }>(`/v1/agent/research/library/${reportId}`),
  researchLibraryPdf: (reportId: string) => apiJson<{ available: boolean; pdf_url?: string; expires_in?: number; reason?: string }>(`/v1/agent/research/library/${reportId}/pdf`),
  documents: () => apiJson<{ items: ResearchDocument[] }>("/v1/agent/research-documents"),
  createDocument: (body: { title: string; document_type: string }) =>
    apiJson<ResearchDocument>("/v1/agent/research-documents", { method: "POST", body }),
  generateDocument: (documentId: string, body: Record<string, unknown>) =>
    apiJson<Record<string, unknown>>(`/v1/agent/research-documents/${documentId}/generate`, { method: "POST", body }),
  generateBilingualDocument: (documentId: string, body: { summary?: string; structured?: Record<string, unknown>; source_snapshot: Record<string, unknown> }) =>
    apiJson<Record<string, unknown>>(`/v1/agent/research-documents/${documentId}/generate-bilingual`, { method: "POST", body }),
  documentVersions: (documentId: string) =>
    apiJson<{ items: Array<{ id: string; version: number; locale: string; status: string; content_sha256?: string; size_bytes?: number; download_url: string }> }>(`/v1/agent/research-documents/${documentId}/versions`),
};
