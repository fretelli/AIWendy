import { apiForm, apiJson } from '@/lib/api/client'

export type AgentModelProfile = { id: string; name: string; provider: string; model: string; key_prefix?: string }
export type AgentDefinition = { id: string; name: string; role: string; description?: string; model_profile_id: string; tool_names: string[] }
export type AgentRun = { id: string; prompt: string; status: string; current_step: number; tokens_used: number; cost_used_usd: number; created_at: string }
export type InteractionMode = 'ask' | 'research' | 'plan'
export type AgentSession = { id: string; agent_definition_id?: string; title: string; status: string; interaction_mode: InteractionMode; company_code?: string; summary?: string; context_tokens: number; is_pinned: boolean; archived_at?: string; last_message_at: string; created_at: string }
export type CompanySearchItem = { ts_code: string; symbol: string; name: string; industry?: string; area?: string; market?: string; list_date?: string }
export type WatchlistItem = { id: string; company_code: string; company_name: string; industry?: string; refresh_enabled: boolean; added_at: string }
export type CompanyDossier = { dossier?: { status: string; current_version: number; stale: boolean; last_refreshed_at?: string }; snapshot?: { company: Record<string, unknown>; metrics: Record<string, unknown>; industry_peer_medians: Record<string, unknown>; anomaly_flags: string[]; evidence_status: string; evidence_shortage?: string }; diff?: Record<string, unknown>; evidence: Array<{ id: string; source_type: string; citation: Record<string, unknown> }>; versions: Array<{ id: string; version: number; created_at: string }> }
export type AgentMessage = { id: string; session_id: string; run_id?: string; role: 'user' | 'assistant' | 'system'; kind: string; status: string; content: string; metadata_json?: Record<string, unknown>; created_at: string }
export type AgentApproval = { id: string; kind: string; preview: Record<string, unknown>; created_at: string }
export type AgentMemory = { id: string; key: string; value: unknown; confidence: number; version: number; is_deleted: boolean }
export type MCPServer = { id: string; name: string; url: string; status: string; tools_snapshot: Array<{ name: string; description?: string }> }
export type AgentSchedule = { id: string; name: string; cron: string; prompt: string; enabled: boolean; next_run_at?: string }
export type Usage = { today: { input_tokens: number; output_tokens: number; cost_usd: number }; limits: { tokens: number; cost_usd: number } }
export type HolderSearchItem = { holder_name: string; holder_type: string; stock_count: number; first_end_date?: string; last_end_date?: string; last_ann_date?: string; exact_match: boolean; identity_warning?: string }
export type HolderWatchItem = { id: string; holder_name: string; normalized_name: string; holder_type: string; aliases: string[]; enabled: boolean; last_scanned_at?: string; identity_warning?: string; created_at: string }
export type HolderCostEstimate = { unit_cost: number; unit_cost_low: number; unit_cost_high: number; covered_shares: number; coverage_ratio: number; estimated_covered_cost: number; estimated_position_cost?: number; first_estimated_period?: string; last_estimated_period?: string; method: 'qfq_disclosure_average_cost_ledger'; disclaimer: string }
export type HolderPosition = { ts_code: string; company_name?: string; industry?: string; market?: string; end_date: string; ann_date?: string; matched_names?: string[]; hold_amount?: number; hold_ratio?: number; hold_float_ratio?: number; hold_change?: number; cost_estimate?: HolderCostEstimate | null }
export type HolderPriceEstimate = { side: 'buy' | 'sell' | 'possible_sell'; window_start: string; window_end: string; first_trade_date?: string; last_trade_date?: string; low: number; high: number; volume_weighted_price: number; trading_days: number; changed_shares?: number; estimated_amount?: number; method: 'qfq_close_volume_weighted_reporting_window'; disclaimer: string }
export type HolderHistoryEvent = HolderPosition & { event_type: 'first_seen' | 'new' | 'increased' | 'reduced' | 'unchanged' | 'exited_top10'; previous_end_date?: string; previous_hold_amount?: number; previous_hold_ratio?: number; previous_hold_float_ratio?: number; present: boolean; price_estimate?: HolderPriceEstimate | null }
export type HolderInboxEvent = { id: string; watch_id: string; ts_code: string; company_name?: string; holder_name: string; holder_type: string; event_type: HolderHistoryEvent['event_type']; end_date: string; ann_date?: string; previous_end_date?: string; values: Record<string, unknown>; read_at?: string; detected_at: string }
export type MarketCapitalSnapshot = {
  available: boolean; as_of?: string; window: 'all'; interpretations: string[]
  history_meta: { scope: 'all_available'; raw: true; start_date: string; end_date: string; points: number; source: string }
  methodology?: { scope?: string; complete_day_threshold?: number; flow_warning?: string }
  sources: Record<string, { available: boolean; as_of?: string; lag_days?: number; row_count?: number }>
  liquidity: { turnover_cny: number; top20_turnover_share?: number; top50_turnover_share?: number; note: string }
  breadth: { advances: number; declines: number; flat: number; advance_ratio?: number; limit_up?: number; limit_down?: number; limit_source_available: boolean }
  leverage: { available: boolean; as_of?: string; lag_days?: number; balance_cny?: number; purchases_cny?: number; repayments_cny?: number; daily_net_financing_cny?: number; five_day_net_financing_cny?: number; coverage_label?: string }
  etf_flows: { available: boolean; as_of?: string; lag_days?: number; estimated_net_flow_cny?: number; groups?: Record<string, number>; fund_count?: number; flow_covered_funds?: number; coverage_ratio?: number; method?: string; note?: string }
  funding_rates: { available: boolean; as_of?: string; lag_days?: number; overnight_pct?: number; seven_day_pct?: number; overnight_change_bp?: number; seven_day_change_bp?: number }
  flow_proxy: { available: boolean; as_of?: string; lag_days?: number; provider?: string; method?: string; warning?: string; values?: Record<string, number | string | null> }
  history: Array<{ trade_date: string; stock_count: number; turnover_cny: number; advances: number; declines: number; flat: number }>
}

const base = '/agent'
export const agentPlatformApi = {
  health: () => apiJson<{ status: string; mode: string }>(`${base}/health`),
  models: () => apiJson<{ items: AgentModelProfile[] }>(`${base}/model-credentials`),
  createModel: (body: object) => apiJson<AgentModelProfile>(`${base}/model-credentials`, { method: 'POST', body }),
  agents: () => apiJson<{ items: AgentDefinition[]; builtin_tools: string[]; mcp_tools: Array<{ name: string; server: string; description: string }> }>(`${base}/definitions`),
  runs: () => apiJson<{ items: AgentRun[] }>(`${base}/runs`),
  createRun: (body: object) => apiJson<AgentRun>(`${base}/runs`, { method: 'POST', body }),
  sessions: (includeArchived = false) => apiJson<{ items: AgentSession[] }>(`${base}/sessions?include_archived=${includeArchived}`),
  createSession: (body: { agent_definition_id: string; title?: string; interaction_mode?: InteractionMode; company_code?: string | null }) => apiJson<AgentSession>(`${base}/sessions`, { method: 'POST', body }),
  updateSession: (id: string, body: { title?: string; is_pinned?: boolean; archived?: boolean; interaction_mode?: InteractionMode; company_code?: string | null }) => apiJson<AgentSession>(`${base}/sessions/${id}`, { method: 'PATCH', body }),
  deleteSession: (id: string) => apiJson<{ ok: boolean }>(`${base}/sessions/${id}`, { method: 'DELETE' }),
  timeline: (id: string) => apiJson<{ session: AgentSession; messages: AgentMessage[]; runs: AgentRun[] }>(`${base}/sessions/${id}/timeline`),
  sendMessage: (id: string, body: { content: string; client_request_id: string; agent_definition_id?: string; attachment_ids?: string[] }) => apiJson<{ run: AgentRun; session: AgentSession }>(`${base}/sessions/${id}/messages`, { method: 'POST', body }),
  uploadAttachment: (file: File) => { const form = new FormData(); form.append('file', file); return apiForm<{ id: string; fileName: string }>('/files/upload', form, { method: 'POST' }) },
  compactSession: (id: string) => apiJson<AgentSession>(`${base}/sessions/${id}/compact`, { method: 'POST' }),
  stopSession: (id: string) => apiJson<AgentRun>(`${base}/sessions/${id}/stop`, { method: 'POST' }),
  controlRun: (id: string, action: 'pause' | 'resume' | 'cancel') => apiJson<AgentRun>(`${base}/runs/${id}/${action}`, { method: 'POST' }),
  approvals: () => apiJson<{ items: AgentApproval[] }>(`${base}/approvals`),
  resolveApproval: (id: string, decision: 'approved' | 'rejected', scope: 'once' | 'always' = 'once') => apiJson(`${base}/approvals/${id}/resolve`, { method: 'POST', body: { decision, scope } }),
  memories: (includeDeleted = false) => apiJson<{ items: AgentMemory[] }>(`${base}/memories?include_deleted=${includeDeleted}`),
  deleteMemory: (id: string) => apiJson(`${base}/memories/${id}`, { method: 'DELETE' }),
  restoreMemory: (id: string) => apiJson(`${base}/memories/${id}/restore`, { method: 'POST' }),
  mcpServers: () => apiJson<{ items: MCPServer[] }>(`${base}/mcp-servers`),
  createMcp: (body: object) => apiJson<MCPServer>(`${base}/mcp-servers`, { method: 'POST', body }),
  schedules: () => apiJson<{ items: AgentSchedule[] }>(`${base}/schedules`),
  createSchedule: (body: object) => apiJson<AgentSchedule>(`${base}/schedules`, { method: 'POST', body }),
  usage: () => apiJson<Usage>(`${base}/usage`),
  companies: (query: string) => apiJson<{ items: CompanySearchItem[] }>(`${base}/companies?query=${encodeURIComponent(query)}`),
  watchlist: () => apiJson<{ items: WatchlistItem[] }>(`${base}/watchlist`),
  addWatchlist: (company: string) => apiJson<WatchlistItem>(`${base}/watchlist`, { method: 'POST', body: { company } }),
  removeWatchlist: (companyCode: string) => apiJson(`${base}/watchlist/${encodeURIComponent(companyCode)}`, { method: 'DELETE' }),
  dossier: (companyCode: string) => apiJson<CompanyDossier>(`${base}/dossiers/${encodeURIComponent(companyCode)}`),
  refreshDossier: (companyCode: string) => apiJson(`${base}/dossiers/${encodeURIComponent(companyCode)}/refresh`, { method: 'POST' }),
  searchHolders: (query: string) => apiJson<{ items: HolderSearchItem[]; source_available: boolean }>(`${base}/holders/search?query=${encodeURIComponent(query)}`),
  holderWatchlist: () => apiJson<{ items: HolderWatchItem[] }>(`${base}/holder-watchlist`),
  addHolderWatch: (body: { holder_name: string; holder_type: string }) => apiJson<HolderWatchItem>(`${base}/holder-watchlist`, { method: 'POST', body }),
  updateHolderWatch: (id: string, body: { aliases?: string[]; enabled?: boolean }) => apiJson<HolderWatchItem>(`${base}/holder-watchlist/${id}`, { method: 'PATCH', body }),
  removeHolderWatch: (id: string) => apiJson<{ ok: boolean }>(`${base}/holder-watchlist/${id}`, { method: 'DELETE' }),
  refreshHolderWatch: (id: string) => apiJson<{ ok: boolean; status: string }>(`${base}/holder-watchlist/${id}/refresh`, { method: 'POST' }),
  holderPositions: (id: string, view: 'latest' | 'history', limit = 200, offset = 0, allHistory = false) => apiJson<{ items: Array<HolderPosition | HolderHistoryEvent>; total: number; source_available: boolean; source_as_of?: string; watch: HolderWatchItem }>(`${base}/holders/${id}/positions?view=${view}&limit=${limit}&offset=${offset}&all_history=${allHistory}`),
  holderEvents: (unreadOnly = false) => apiJson<{ items: HolderInboxEvent[]; unread: number }>(`${base}/holder-events?unread_only=${unreadOnly}`),
  readHolderEvents: (eventIds: string[] = []) => apiJson<{ ok: boolean; updated: number }>(`${base}/holder-events/read`, { method: 'POST', body: { event_ids: eventIds } }),
  marketCapital: () => apiJson<MarketCapitalSnapshot>(`${base}/market-capital`),
}
