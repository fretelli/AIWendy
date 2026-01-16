/**
 * Authentication API client
 */

const API_BASE_URL = '/api/proxy/v1'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RegisterResponse {
  id: string
  email: string
  full_name: string | null
  subscription_tier: string
  created_at: string
}

export const authApi = {
  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    return response.json()
  },

  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    return response.json()
  },

  /**
   * Get current user
   */
  async getCurrentUser(token: string) {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to get user')
    }

    return response.json()
  },

  /**
   * Get auth headers
   */
  getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('keeltrader_access_token')
    if (!token) {
      return {}
    }

    return {
      'Authorization': `Bearer ${token}`,
    }
  },
}

/**
 * Get auth headers (exported for use in other modules)
 */
export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('keeltrader_access_token')
  if (!token) {
    return {}
  }

  return {
    'Authorization': `Bearer ${token}`,
  }
}
