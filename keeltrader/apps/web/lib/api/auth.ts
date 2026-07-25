/**
 * Authentication API client
 */

import { apiJson } from '@/lib/api/client'

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
  created_at: string
}

export const authApi = {
  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    return apiJson<TokenResponse>('/auth/login', {
      method: 'POST',
      body: data,
    })
  },

  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    return apiJson<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: data,
    })
  },

  /**
   * Get current user
   */
  async getCurrentUser() {
    return apiJson('/users/me')
  },

  /**
   * Get auth headers
   */
  getAuthHeaders(): HeadersInit {
    return {}
  },
}

/**
 * Get auth headers (exported for use in other modules)
 */
export function getAuthHeaders(): HeadersInit {
  return {}
}
