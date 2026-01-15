/**
 * Exchange API Client
 */

import { API_PROXY_PREFIX } from '@/lib/config'

const API_BASE_URL = `${API_PROXY_PREFIX}/exchanges`

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
    const response = await fetch(API_BASE_URL, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch exchanges: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get account balance from exchange
   */
  async getBalance(exchange: string): Promise<Balance> {
    const response = await fetch(`${API_BASE_URL}/${exchange}/balance`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch balance: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get open positions from exchange
   */
  async getPositions(exchange: string): Promise<Position[]> {
    const response = await fetch(`${API_BASE_URL}/${exchange}/positions`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch positions: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get open orders from exchange
   */
  async getOrders(exchange: string, symbol?: string): Promise<Order[]> {
    const params = new URLSearchParams()
    if (symbol) params.append('symbol', symbol)

    const url = `${API_BASE_URL}/${exchange}/orders${params.toString() ? `?${params}` : ''}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch orders: ${response.statusText}`)
    }

    return response.json()
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

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch trades: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get available markets from exchange
   */
  async getMarkets(exchange: string): Promise<Market[]> {
    const response = await fetch(`${API_BASE_URL}/${exchange}/markets`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch markets: ${response.statusText}`)
    }

    return response.json()
  },
}
