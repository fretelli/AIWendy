/**
 * Exchange API Client
 */

import { apiJson } from '@/lib/api/client'

const API_BASE_URL = '/exchanges'

export interface ExchangeInfo {
  name: string
}

export interface Balance {
  exchange: string
  timestamp: string
  total: Record<string, number>
  free: Record<string, number>
  used: Record<string, number>
}

export interface Position {
  symbol: string
  side: 'long' | 'short'
  contracts: number
  notional: number
  leverage: number
  entry_price?: number
  mark_price?: number
  liquidation_price?: number
  unrealized_pnl: number
  percentage: number
  timestamp?: number
}

export interface Order {
  id: string
  symbol: string
  type: string
  side: 'buy' | 'sell'
  price?: number
  amount: number
  filled: number
  remaining: number
  status: string
  timestamp?: number
  datetime?: string
}

export interface Trade {
  id: string
  order_id?: string
  symbol: string
  type?: string
  side: 'buy' | 'sell'
  price: number
  amount: number
  cost: number
  fee?: {
    cost: number
    currency: string
  }
  timestamp?: number
  datetime?: string
}

export interface Market {
  symbol: string
  base: string
  quote: string
  active: boolean
  type: string
  spot: boolean
  future: boolean
  swap: boolean
}

export const exchangeApi = {
  /**
   * Get list of configured exchanges
   */
  async getExchanges(): Promise<ExchangeInfo[]> {
    return apiJson<ExchangeInfo[]>(API_BASE_URL)
  },

  /**
   * Get account balance from exchange
   */
  async getBalance(exchange: string): Promise<Balance> {
    return apiJson<Balance>(`${API_BASE_URL}/${exchange}/balance`)
  },

  /**
   * Get open positions from exchange
   */
  async getPositions(exchange: string): Promise<Position[]> {
    return apiJson<Position[]>(`${API_BASE_URL}/${exchange}/positions`)
  },

  /**
   * Get open orders from exchange
   */
  async getOrders(exchange: string, symbol?: string): Promise<Order[]> {
    const params = new URLSearchParams()
    if (symbol) params.append('symbol', symbol)

    const url = `${API_BASE_URL}/${exchange}/orders${params.toString() ? `?${params}` : ''}`

    return apiJson<Order[]>(url)
  },

  /**
   * Get trade history from exchange
   */
  async getTrades(
    exchange: string,
    options: {
      symbol?: string
      since?: number
      limit?: number
    } = {}
  ): Promise<Trade[]> {
    const params = new URLSearchParams()
    if (options.symbol) params.append('symbol', options.symbol)
    if (options.since) params.append('since', options.since.toString())
    if (options.limit) params.append('limit', options.limit.toString())

    const url = `${API_BASE_URL}/${exchange}/trades${params.toString() ? `?${params}` : ''}`

    return apiJson<Trade[]>(url)
  },

  /**
   * Get available markets from exchange
   */
  async getMarkets(exchange: string): Promise<Market[]> {
    return apiJson<Market[]>(`${API_BASE_URL}/${exchange}/markets`)
  },
}
