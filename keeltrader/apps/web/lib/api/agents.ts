import { apiJson, type ApiRequestInit } from '@/lib/api/client'
import type {
  AgentStatus,
  AgentDetailStatus,
  HealthResponse,
  GhostTradesResponse,
  PortfolioSummary,
  RecentEventsResponse,
  StreamInfo,
  EventSubmitRequest,
  EventSubmitResponse,
  AgentChatRequest,
  AgentChatResponse,
  CachedPrices,
} from '@/lib/types/agents'

class AgentsAPI {
  private request<T>(path: string, init?: ApiRequestInit): Promise<T> {
    return apiJson<T>(path, init)
  }

  async getAgents(): Promise<AgentStatus[]> {
    return this.request('/agent-matrix/agents')
  }

  async getAgentStatus(agentId: string): Promise<AgentDetailStatus> {
    return this.request(`/agent-matrix/agents/${agentId}/status`)
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request('/agent-matrix/agents/health')
  }

  async getGhostTrades(userId: string = 'default', status: string = 'all'): Promise<GhostTradesResponse> {
    const params = new URLSearchParams({ user_id: userId, status })
    return this.request(`/agent-matrix/agents/ghost-trades?${params}`)
  }

  async getPortfolio(userId: string = 'default'): Promise<PortfolioSummary> {
    const params = new URLSearchParams({ user_id: userId })
    return this.request(`/agent-matrix/agents/ghost-trades/portfolio?${params}`)
  }

  async getPrices(): Promise<CachedPrices> {
    return this.request('/agent-matrix/agents/prices')
  }

  async getRecentEvents(count: number = 50): Promise<RecentEventsResponse> {
    const params = new URLSearchParams({ count: String(count) })
    return this.request(`/agent-matrix/agents/events/recent?${params}`)
  }

  async getStreamInfo(): Promise<StreamInfo> {
    return this.request('/agent-matrix/agents/events/stream-info')
  }

  async submitEvent(req: EventSubmitRequest): Promise<EventSubmitResponse> {
    return this.request('/agent-matrix/events', {
      method: 'POST',
      body: req
    })
  }

  async chatWithAgent(req: AgentChatRequest): Promise<AgentChatResponse> {
    return this.request('/agent-matrix/agents/chat', {
      method: 'POST',
      body: req
    })
  }
}

export const agentsAPI = new AgentsAPI()
