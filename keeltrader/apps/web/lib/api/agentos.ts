import { apiJson, type ApiRequestInit } from "@/lib/api/client";
import type { JsonObject, JsonValue } from "@/lib/types/json";

const API_BASE = "/agentos";

async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
  return apiJson<T>(`${API_BASE}${path}`, init);
}

export type JsonMap = JsonObject;

export type AgentOSHealth = {
  status: string;
  service?: string;
  engine?: JsonMap;
  tushare?: JsonMap;
  report_kb?: JsonMap;
  tushare_token_required: boolean;
};

export type ResearchReportHit = {
  report_id: string;
  section_id?: string;
  title?: string | null;
  broker?: string | null;
  report_date?: string | null;
  created_at?: string | null;
  doc_type?: string | null;
  section_type?: string | null;
  granularity?: string | null;
  page_number?: number | null;
  score?: number | null;
  excerpt?: string | null;
  metadata?: JsonMap;
};

export type InvestmentBrief = {
  id: string;
  title: string;
  brief_date: string;
  watchlist: string[];
  summary: string;
  signals: JsonMap[];
  risks: string[];
  falsifiers: JsonMap[];
  data_sources: string[];
  status: string;
  created_at: string;
};

export type InvestmentMemo = {
  id: string;
  symbol: string;
  market?: string | null;
  title: string;
  thesis: string;
  analyst_views: JsonMap;
  bull_case?: string | null;
  bear_case?: string | null;
  red_team?: string | null;
  risk_view?: string | null;
  recommendation?: string | null;
  confidence?: number | null;
  falsifiers: JsonValue[];
  data_sources: string[];
  status: string;
  created_at: string;
};

export type InvestmentDecision = {
  id: string;
  symbol: string;
  market?: string | null;
  action: string;
  thesis: string;
  confidence?: number | null;
  expected_horizon?: string | null;
  position_plan: JsonMap;
  risk_plan: JsonMap;
  falsifiers: JsonValue[];
  human_decision: string;
  human_reason?: string | null;
  outcome?: JsonMap | null;
  status: string;
  created_at: string;
};

export type ReviewLesson = {
  id: string;
  title: string;
  lesson: string;
  evidence: JsonMap[];
  category?: string | null;
  approved: boolean;
  approved_at?: string | null;
  created_at: string;
};

export type StrategyHypothesis = {
  id: string;
  name: string;
  hypothesis: string;
  rationale?: string | null;
  asset_universe: string[];
  frequency: string;
  status: string;
  attempt_count: number;
  created_at: string;
};

export type FundamentalValidation = {
  id: string;
  hypothesis_id?: string | null;
  symbol: string;
  strategy: string;
  params: JsonMap;
  metrics: JsonMap;
  trades: JsonMap[];
  attempt_number: number;
  passed_gate: boolean;
  notes?: string | null;
  created_at: string;
};

export const agentosApi = {
  health: () => request<AgentOSHealth>("/health"),
  listBriefs: () => request<{ briefs: InvestmentBrief[] }>("/briefs"),
  latestBrief: () => request<{ brief: InvestmentBrief | null }>("/briefs/latest"),
  runBrief: (watchlist: string[]) =>
    request<{ brief: InvestmentBrief }>("/briefs/run", {
      method: "POST",
      body: { watchlist },
    }),
  listResearch: () => request<{ memos: InvestmentMemo[] }>("/research"),
  runResearch: (symbol: string, market?: string) =>
    request<{ memo: InvestmentMemo }>("/research/run", {
      method: "POST",
      body: { symbol, market: market || null },
    }),
  listDecisions: () => request<{ decisions: InvestmentDecision[] }>("/decisions"),
  createDecision: (payload: Partial<InvestmentDecision> & { symbol: string; action: string; thesis: string }) =>
    request<{ decision: InvestmentDecision }>("/decisions", {
      method: "POST",
      body: payload,
    }),
  updateDecisionOutcome: (id: string, outcome: JsonMap) =>
    request<{ decision: InvestmentDecision }>(`/decisions/${id}/outcome`, {
      method: "POST",
      body: { outcome },
    }),
  listLessons: (approved?: boolean) =>
    request<{ lessons: ReviewLesson[] }>(`/lessons${approved === undefined ? "" : `?approved=${approved}`}`),
  runWeeklyReview: () =>
    request<{ lessons: ReviewLesson[] }>("/reviews/weekly/run", { method: "POST" }),
  approveLesson: (id: string) =>
    request<{ lesson: ReviewLesson }>(`/lessons/${id}/approve`, { method: "POST" }),
  listHypotheses: () => request<{ hypotheses: StrategyHypothesis[] }>("/strategy/hypotheses"),
  createHypothesis: (payload: {
    name: string;
    hypothesis: string;
    rationale?: string;
    asset_universe?: string[];
    frequency?: string;
  }) =>
    request<{ hypothesis: StrategyHypothesis }>("/strategy/hypotheses", {
      method: "POST",
      body: payload,
    }),
  listValidations: () => request<{ validations: FundamentalValidation[] }>("/strategy/validations"),
  runValidation: (payload: { symbol: string; strategy?: string; params?: JsonMap; hypothesis_id?: string | null }) =>
    request<{ validation: FundamentalValidation }>("/strategy/validations/run", {
      method: "POST",
      body: payload,
    }),
  queryTushare: (payload: { table: string; filters?: JsonMap; limit?: number }) =>
    request<{ rows: JsonMap[]; tushare_token_required: boolean }>("/tushare/query", {
      method: "POST",
      body: payload,
    }),
  searchReports: (payload: { query: string; top_k?: number; companies?: string[] }) =>
    request<{ reports: ResearchReportHit[] }>("/reports/search", {
      method: "POST",
      body: payload,
    }),
};
