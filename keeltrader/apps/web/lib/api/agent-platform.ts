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
export type MarketSourceFreshness = { available: boolean; as_of?: string; lag_days?: number; lag_calendar_days?: number; lag_trading_days?: number; freshness_state?: 'current'|'lagged'|'unavailable'|'invalid'; row_count?: number }
export type MarketCapitalSnapshot = {
  available: boolean; as_of?: string; window: 'all'; interpretations: string[]
  history_meta: { scope: 'all_available'; raw: true; start_date: string; end_date: string; points: number; source: string }
  methodology?: { scope?: string; complete_day_threshold?: number; flow_warning?: string }
  sources: Record<string, MarketSourceFreshness>
  liquidity: { turnover_cny: number; top20_turnover_share?: number; top50_turnover_share?: number; note: string }
  breadth: { advances: number; declines: number; flat: number; advance_ratio?: number; limit_up?: number; limit_down?: number; limit_source_available: boolean }
  leverage: MarketSourceFreshness & { balance_cny?: number; purchases_cny?: number; repayments_cny?: number; daily_net_financing_cny?: number; five_day_net_financing_cny?: number; coverage_label?: string }
  etf_flows: MarketSourceFreshness & { estimated_net_flow_cny?: number; groups?: Record<string, number>; fund_count?: number; flow_covered_funds?: number; coverage_ratio?: number; method?: string; note?: string }
  funding_rates: MarketSourceFreshness & { overnight_pct?: number; seven_day_pct?: number; overnight_change_bp?: number; seven_day_change_bp?: number }
  flow_proxy: MarketSourceFreshness & { provider?: string; method?: string; warning?: string; values?: Record<string, number | string | null> }
  history: Array<{ trade_date: string; stock_count: number; turnover_cny: number; advances: number; declines: number; flat: number }>
}
export type RawMarketSeries = {
  available: boolean; table: string; frequency: string; period_field?: string
  start?: string; end?: string; points?: number; raw?: true; rows: Array<Record<string, string | number | null>>
}
export type MacroMarketSnapshot = {
  available: boolean; series: Record<string, RawMarketSeries>
  methodology: { raw: true; local_transforms: false; note: string }
}
export type FuturesProduct = {
  product_code: string; trade_date: string; mapping_ts_code: string; name?: string; fut_code?: string
  exchange?: string; close?: number; settle?: number; vol?: number; amount?: number; oi?: number
}
export type FuturesHistory = {
  available: boolean; product_code: string
  history: Array<{ trade_date: string; product_code: string; contract_code: string; open?: number; high?: number; low?: number; close?: number; settle?: number; vol?: number; amount?: number; oi?: number; oi_chg?: number }>
  history_meta: { scope: 'all_available'; raw: true; start_date?: string; end_date?: string; points: number; adjusted: false; source: string }
}
export type FuturesCurve = {
  available: boolean; product_code: string; fut_code?: string; trade_date?: string; raw: true
  items: Array<{ trade_date: string; contract_code: string; name?: string; list_date?: string; delist_date?: string; close?: number; settle?: number; vol?: number; amount?: number; oi?: number }>
}
export type OptionSeries = {
  opt_code: string; exchange?: string; opt_type?: string; list_date?: string; latest_maturity?: string; contracts: number; active_contracts: number
  underlying_code?: string; underlying_type?: 'index'|'etf'|'futures_contract'|'unresolved'
}
export type OptionsSeriesResponse = {
  available: boolean; items: OptionSeries[]
  history_meta: { scope: 'current_available'; raw: true; start_date?: string; end_date?: string; backfill_target: string; source: string }
}
export type OptionsHistory = {
  available: boolean; opt_code: string
  history: Array<{ trade_date: string; call_volume?: number; put_volume?: number; call_amount?: number; put_amount?: number; call_oi?: number; put_oi?: number; call_contracts?: number; put_contracts?: number }>
  history_meta: { scope: 'current_available'; raw_aggregation: true; start_date?: string; end_date?: string; points: number; source: string }
}
export type OptionsChain = {
  available: boolean; opt_code: string; trade_date?: string; maturity?: string; total: number; limit: number; offset: number; raw: true
  items: Array<{ trade_date: string; ts_code: string; name?: string; exchange?: string; call_put?: 'C' | 'P'; exercise_price?: number; maturity_date?: string; open?: number; high?: number; low?: number; close?: number; settle?: number; vol?: number; amount?: number; oi?: number }>
}
export type MarketUnderlying = { available: boolean; relationship: 'index'|'etf'|'futures_contract'|'deliverable_bond_basket'|'commodity_physical_market'|'unresolved'; code?: string; name?: string; source?: string; series_available: boolean; methodology: string; specification?: Record<string, unknown> }
export type UnderlyingSeries = { available: boolean; relationship: string; code: string; source?: string; start?: string; end?: string; points?: number; raw?: true; rows: Array<{ trade_date: string; open?: number; high?: number; low?: number; close?: number; pre_close?: number; vol?: number; amount?: number }> }
export type MacroCatalog = { available: boolean; items: Array<{ key:string; label:string; table:string; frequency?:string; period_field?:string; available:boolean; fields:string[]; start?:string; end?:string; points?:number; source?:string }>; methodology:{raw:true;local_transforms:false} }
export type MacroSeriesDetail = { available:boolean; key:string; label:string; field:string; frequency:string; period_field:string; source:string; start?:string; end?:string; points:number; raw:true; rows:Array<{period:string;value:number|null}>; recent_source_rows:Array<Record<string,string|number|null>> }
export type ContextSnapshot = { id:string; resource_type:string; resource_id:string; field?:string; visible_start?:string; visible_end?:string; source:string; methodology:string; created_at:string }

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
  sendMessage: (id: string, body: { content: string; client_request_id: string; agent_definition_id?: string; attachment_ids?: string[]; context_snapshot_ids?: string[] }) => apiJson<{ run: AgentRun; session: AgentSession }>(`${base}/sessions/${id}/messages`, { method: 'POST', body }),
  createContextSnapshot: (body: { resource_type:'macro'|'futures'|'options'|'underlying'|'capital'; resource_id:string; field?:string; visible_start?:string; visible_end?:string; selected_point?:Record<string,unknown>; source:string; methodology:string }) => apiJson<ContextSnapshot>(`${base}/context-snapshots`, { method:'POST', body }),
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
  macroMarket: () => apiJson<MacroMarketSnapshot>(`${base}/macro-market`),
  futuresProducts: () => apiJson<{ available: boolean; as_of?: string; items: FuturesProduct[]; source: string; raw: true }>(`${base}/futures/products`),
  futuresHistory: (productCode: string) => apiJson<FuturesHistory>(`${base}/futures/${encodeURIComponent(productCode)}/history`),
  futuresCurve: (productCode: string, tradeDate?: string) => apiJson<FuturesCurve>(`${base}/futures/${encodeURIComponent(productCode)}/curve${tradeDate ? `?trade_date=${encodeURIComponent(tradeDate)}` : ''}`),
  optionsSeries: () => apiJson<OptionsSeriesResponse>(`${base}/options/series`),
  optionsHistory: (optCode: string) => apiJson<OptionsHistory>(`${base}/options/${encodeURIComponent(optCode)}/history`),
  optionsChain: (optCode: string, params: { tradeDate?: string; maturity?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams()
    if (params.tradeDate) query.set('trade_date', params.tradeDate)
    if (params.maturity) query.set('maturity', params.maturity)
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    if (params.offset !== undefined) query.set('offset', String(params.offset))
    const suffix = query.size ? `?${query.toString()}` : ''
    return apiJson<OptionsChain>(`${base}/options/${encodeURIComponent(optCode)}/chain${suffix}`)
  },
}

const marketsBase = '/markets'
export const marketsApi = {
  macroCatalog: () => apiJson<MacroCatalog>(`${marketsBase}/macro/series`),
  macroSeries: (key:string, field:string) => apiJson<MacroSeriesDetail>(`${marketsBase}/macro/series/${encodeURIComponent(key)}?field=${encodeURIComponent(field)}`),
  futuresProducts: () => apiJson<{ available:boolean; as_of?:string; items:FuturesProduct[]; source:string; raw:true }>(`${marketsBase}/futures/products`),
  futuresHistory: (code:string) => apiJson<FuturesHistory>(`${marketsBase}/futures/${encodeURIComponent(code)}/history`),
  futuresCurve: (code:string) => apiJson<FuturesCurve>(`${marketsBase}/futures/${encodeURIComponent(code)}/curve`),
  futuresUnderlying: (code:string) => apiJson<MarketUnderlying>(`${marketsBase}/futures/${encodeURIComponent(code)}/underlying`),
  optionsCatalog: () => apiJson<OptionsSeriesResponse>(`${marketsBase}/options/underlyings`),
  optionsHistory: (code:string) => apiJson<OptionsHistory>(`${marketsBase}/options/${encodeURIComponent(code)}/history`),
  optionsChain: (code:string, params:{tradeDate?:string;maturity?:string;limit?:number;offset?:number}={}) => { const query=new URLSearchParams(); if(params.tradeDate)query.set('trade_date',params.tradeDate);if(params.maturity)query.set('maturity',params.maturity);if(params.limit!==undefined)query.set('limit',String(params.limit));if(params.offset!==undefined)query.set('offset',String(params.offset));return apiJson<OptionsChain>(`${marketsBase}/options/${encodeURIComponent(code)}/chain${query.size?`?${query}`:''}`) },
  optionUnderlying: (code:string) => apiJson<MarketUnderlying>(`${marketsBase}/options/${encodeURIComponent(code)}/underlying`),
  underlyingSeries: (relationship:string, code:string) => apiJson<UnderlyingSeries>(`${marketsBase}/underlyings/${encodeURIComponent(relationship)}/${encodeURIComponent(code)}/series`),
}
