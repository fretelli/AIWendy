/**
 * User Exchange Connection API Client
 */

import { apiFetch, apiJson } from '@/lib/api/client'

const API_BASE_URL = '/user/exchanges'

export type ExchangeType = 'okx' | 'bybit' | 'coinbase' | 'kraken' | 'ibkr'
export type TradingMode = 'spot' | 'swap' | 'stock' | 'option' | 'future'

export interface ExchangeConnection {
  id: string
  exchange_type: ExchangeType
  name: string
  api_key_masked: string
  is_active: boolean
  is_testnet: boolean
  trading_mode: TradingMode
  last_sync_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface IbkrCredentialsExtra {
  gateway_host?: string
  gateway_port?: number
  client_id?: number
}

export interface CreateExchangeConnectionRequest {
  exchange_type: ExchangeType
  name?: string
  api_key: string
  api_secret: string
  passphrase?: string
  is_testnet?: boolean
  trading_mode?: TradingMode
  credentials_extra?: IbkrCredentialsExtra
}

export interface UpdateExchangeConnectionRequest {
  name?: string
  api_key?: string
  api_secret?: string
  passphrase?: string
  is_active?: boolean
  trading_mode?: TradingMode
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  data?: {
    exchange: string
    currencies_count: number
  }
}

export const userExchangeApi = {
  /**
   * Get all exchange connections for the current user
   */
  async getConnections(activeOnly: boolean = true): Promise<ExchangeConnection[]> {
    const params = new URLSearchParams()
    if (activeOnly) params.append('active_only', 'true')

    return apiJson<ExchangeConnection[]>(`${API_BASE_URL}${params.toString() ? `?${params}` : ''}`)
  },

  /**
   * Get a specific exchange connection
   */
  async getConnection(connectionId: string): Promise<ExchangeConnection> {
    return apiJson<ExchangeConnection>(`${API_BASE_URL}/${connectionId}`)
  },

  /**
   * Create a new exchange connection
   */
  async createConnection(
    request: CreateExchangeConnectionRequest
  ): Promise<ExchangeConnection> {
    return apiJson<ExchangeConnection>(API_BASE_URL, {
      method: 'POST',
      body: request,
    })
  },

  /**
   * Update an exchange connection
   */
  async updateConnection(
    connectionId: string,
    request: UpdateExchangeConnectionRequest
  ): Promise<ExchangeConnection> {
    return apiJson<ExchangeConnection>(`${API_BASE_URL}/${connectionId}`, {
      method: 'PUT',
      body: request,
    })
  },

  /**
   * Delete an exchange connection
   */
  async deleteConnection(connectionId: string): Promise<void> {
    const response = await apiFetch(`${API_BASE_URL}/${connectionId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error('Failed to delete connection')
    }
  },

  /**
   * Test an exchange connection
   */
  async testConnection(connectionId: string): Promise<TestConnectionResponse> {
    return apiJson<TestConnectionResponse>(`${API_BASE_URL}/${connectionId}/test`, {
      method: 'POST',
    })
  },
}
