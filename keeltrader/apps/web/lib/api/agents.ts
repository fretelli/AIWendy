import { getApiUrl } from '@/lib/config'
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
  private apiUrl: string

  constructor() {
    this.apiUrl = getApiUrl()
  }

  private getHeaders() {
    const token = localStorage.getItem('keeltrader_access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    }
  }

  async getAgents(): Promise<AgentStatus[]> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch agents')
    return response.json()
  }

  async getAgentStatus(agentId: string): Promise<AgentDetailStatus> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/${agentId}/status`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch agent status')
    return response.json()
  }

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/health`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch health')
    return response.json()
  }

  async getGhostTrades(userId: string = 'default', status: string = 'all'): Promise<GhostTradesResponse> {
    const params = new URLSearchParams({ user_id: userId, status })
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/ghost-trades?${params}`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch ghost trades')
    return response.json()
  }

  async getPortfolio(userId: string = 'default'): Promise<PortfolioSummary> {
    const params = new URLSearchParams({ user_id: userId })
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/ghost-trades/portfolio?${params}`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch portfolio')
    return response.json()
  }

  async getPrices(): Promise<CachedPrices> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/prices`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch prices')
    return response.json()
  }

  async getRecentEvents(count: number = 50): Promise<RecentEventsResponse> {
    const params = new URLSearchParams({ count: String(count) })
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/events/recent?${params}`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch recent events')
    return response.json()
  }

  async getStreamInfo(): Promise<StreamInfo> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/events/stream-info`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to fetch stream info')
    return response.json()
  }

  async submitEvent(req: EventSubmitRequest): Promise<EventSubmitResponse> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/events`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(req)
    })
    if (!response.ok) throw new Error('Failed to submit event')
    return response.json()
  }

  async chatWithAgent(req: AgentChatRequest): Promise<AgentChatResponse> {
    const response = await fetch(`${this.apiUrl}/agent-matrix/agents/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(req)
    })
    if (!response.ok) throw new Error('Failed to chat with agent')
    return response.json()
  }
}

export const agentsAPI = new AgentsAPI()
