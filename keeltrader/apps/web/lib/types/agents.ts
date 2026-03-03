export interface AgentStatus {
  agent_id: string
  name: string
  agent_type: string
  is_active: boolean
  subscriptions: string[]
  trust_level: number
}

export interface AgentDetailStatus {
  agent_id: string
  circuit_breaker_active: boolean
  cooldown_remaining_seconds: number
}

export interface HealthResponse {
  status: 'healthy' | 'degraded'
  services: {
    event_engine: { status: string; [key: string]: any }
    market_streamer: { status: string; [key: string]: any }
    circuit_breaker: { active: boolean }
    event_bus: { status: string; length?: number; groups?: number }
    market_data: { cached_symbols: number }
  }
}

export interface GhostTrade {
  id: string
  agent_id: string
  user_id: string
  symbol: string
  side: 'buy' | 'sell'
  amount: string
  entry_price: string
  entry_time: string
  exit_price?: string
  exit_time?: string
  stop_loss: string
  take_profit: string
  unrealized_pnl: string
  realized_pnl: string
  reasoning: string
  status: 'open' | 'closed'
  created_at: string
}

export interface GhostTradesResponse {
  trades: GhostTrade[]
  count: number
}

export interface PortfolioSummary {
  open_positions: number
  closed_trades: number
  total_unrealized_pnl: number
  total_realized_pnl: number
  total_pnl: number
  win_count: number
  loss_count: number
  win_rate: number
  open_trades: {
    id: string
    symbol: string
    side: string
    entry_price: number
    amount: number
    unrealized_pnl: number
  }[]
}

export interface StreamEvent {
  stream_id: string
  type?: string
  source?: string
  agent_id?: string
  user_id?: string
  timestamp?: string
  payload?: Record<string, any> | string
  correlation_id?: string
  [key: string]: any
}

export interface RecentEventsResponse {
  events: StreamEvent[]
  count: number
  message?: string
}

export interface StreamInfo {
  stream: string
  length: number
  first_entry?: any
  last_entry?: any
  groups?: number
  message?: string
}

export interface EventSubmitRequest {
  event_type: string
  user_id?: string
  payload?: Record<string, any>
  correlation_id?: string
}

export interface EventSubmitResponse {
  success: boolean
  event_id: string
  message: string
}

export interface AgentChatRequest {
  message: string
  user_id: string
  agent_id?: string
}

export interface AgentChatResponse {
  agent_id: string
  success: boolean
  message: string
  data: Record<string, any>
}

export interface CachedPrices {
  [symbol: string]: number
}
