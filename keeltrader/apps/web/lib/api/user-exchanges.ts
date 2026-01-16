/**
 * User Exchange Connection API Client
 */

import { API_PROXY_PREFIX } from '@/lib/config'

const API_BASE_URL = `${API_PROXY_PREFIX}/v1/user/exchanges`

export type ExchangeType = 'binance' | 'okx' | 'bybit' | 'coinbase' | 'kraken'

export interface ExchangeConnection {
  id: string
  exchange_type: ExchangeType
  name: string
  api_key_masked: string
  is_active: boolean
  is_testnet: boolean
  last_sync_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface CreateExchangeConnectionRequest {
  exchange_type: ExchangeType
  name?: string
  api_key: string
  api_secret: string
  passphrase?: string
  is_testnet?: boolean
}

export interface UpdateExchangeConnectionRequest {
  name?: string
  api_key?: string
  api_secret?: string
  passphrase?: string
  is_active?: boolean
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

    const response = await fetch(
      `${API_BASE_URL}${params.toString() ? `?${params}` : ''}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for auth
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to fetch connections: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get a specific exchange connection
   */
  async getConnection(connectionId: string): Promise<ExchangeConnection> {
    const response = await fetch(`${API_BASE_URL}/${connectionId}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch connection: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Create a new exchange connection
   */
  async createConnection(
    request: CreateExchangeConnectionRequest
  ): Promise<ExchangeConnection> {
    const response = await fetch(API_BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create connection')
    }

    return response.json()
  },

  /**
   * Update an exchange connection
   */
  async updateConnection(
    connectionId: string,
    request: UpdateExchangeConnectionRequest
  ): Promise<ExchangeConnection> {
    const response = await fetch(`${API_BASE_URL}/${connectionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update connection')
    }

    return response.json()
  },

  /**
   * Delete an exchange connection
   */
  async deleteConnection(connectionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/${connectionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete connection')
    }
  },

  /**
   * Test an exchange connection
   */
  async testConnection(connectionId: string): Promise<TestConnectionResponse> {
    const response = await fetch(`${API_BASE_URL}/${connectionId}/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to test connection')
    }

    return response.json()
  },
}
