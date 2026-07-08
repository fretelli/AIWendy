import { apiJson } from '@/lib/api/client'
import type { JsonObject } from '@/lib/types/json'

// Types matching the backend API
export interface LLMProviderConfig {
  id?: string
  name: string
  provider_type: string
  is_active?: boolean
  is_default?: boolean

  // Connection settings
  api_key?: string
  base_url?: string

  // Model settings
  default_model?: string
  available_models?: string[]

  // Custom API settings (only for custom providers)
  api_format?: 'openai' | 'anthropic' | 'google' | 'custom'
  auth_type?: 'bearer' | 'api_key' | 'basic' | 'none'
  auth_header_name?: string

  // Endpoints (for custom providers)
  chat_endpoint?: string
  completions_endpoint?: string
  embeddings_endpoint?: string
  models_endpoint?: string

  // Extra configuration
  extra_headers?: Record<string, string>
  extra_body_params?: JsonObject

  // Features
  supports_streaming?: boolean
  supports_functions?: boolean
  supports_vision?: boolean
  supports_embeddings?: boolean

  // Limits
  max_tokens_limit?: number
  requests_per_minute?: number
  tokens_per_minute?: number

  // Metadata
  created_at?: string
  updated_at?: string
}

export interface LLMProviderInfo {
  type: string
  requires_api_key: boolean
  supports_streaming: boolean
  supports_functions: boolean
  supports_vision: boolean
  supports_embeddings: boolean
  default_model?: string
  description?: string
  preset_available: boolean
}

export interface ProviderTemplate {
  name: string
  provider_type: string
  api_format?: string
  auth_type?: string
  auth_header_name?: string
  base_url?: string
  chat_endpoint?: string
  completions_endpoint?: string
  embeddings_endpoint?: string
  models_endpoint?: string
  supports_streaming?: boolean
  supports_functions?: boolean
  supports_vision?: boolean
  supports_embeddings?: boolean
}

export interface TestLLMRequest {
  config_id: string
  message?: string
  model?: string
  temperature?: number
  max_tokens?: number
}

export interface QuickTestRequest {
  provider_type: string
  api_key: string
  base_url?: string
  model?: string
}

export interface FetchModelsRequest {
  provider_type: string
  api_key?: string
  base_url?: string
  api_format?: 'openai' | 'anthropic' | 'google' | 'custom'
  auth_type?: 'bearer' | 'api_key' | 'basic' | 'none'
  auth_header_name?: string
  models_endpoint?: string
  extra_headers?: Record<string, string>
}

class LLMConfigApi {
  /**
   * Get available LLM provider types and presets
   */
  async getAvailableProviders(): Promise<{
    providers: LLMProviderInfo[]
    presets: {
      cloud: string[]
      local: string[]
      proxy: string[]
    }
  }> {
    return apiJson('/llm-config/providers')
  }

  /**
   * Get user's LLM configurations
   */
  async getUserConfigs(): Promise<LLMProviderConfig[]> {
    return apiJson('/llm-config/user-configs')
  }

  /**
   * Create a new LLM configuration
   */
  async createConfig(config: LLMProviderConfig): Promise<{
    status: string
    message: string
    config_id: string
  }> {
    return apiJson('/llm-config/user-configs', {
      method: 'POST',
      body: config,
    })
  }

  /**
   * Update an existing LLM configuration
   */
  async updateConfig(configId: string, config: LLMProviderConfig): Promise<{
    status: string
    message: string
  }> {
    return apiJson(`/llm-config/user-configs/${configId}`, {
      method: 'PUT',
      body: config,
    })
  }

  /**
   * Delete an LLM configuration
   */
  async deleteConfig(configId: string): Promise<{
    status: string
    message: string
  }> {
    return apiJson(`/llm-config/user-configs/${configId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Test an LLM configuration with a sample message
   */
  async testConfig(request: TestLLMRequest): Promise<{
    status: string
    response: string
    provider: string
    model: string
    latency_ms: number
  }> {
    return apiJson('/llm-config/test', {
      method: 'POST',
      body: request,
    })
  }

  /**
   * Quick test a provider without saving configuration
   */
  async quickTest(request: QuickTestRequest): Promise<{
    status: string
    connected: boolean
    response?: string
    error?: string
    provider: string
    model?: string
  }> {
    return apiJson('/llm-config/quick-test', {
      method: 'POST',
      body: request,
    })
  }

  /**
   * Get configuration templates for popular providers
   */
  async getTemplates(): Promise<{
    templates: Record<string, ProviderTemplate>
  }> {
    return apiJson('/llm-config/templates')
  }

  /**
   * Fetch models server-side (avoids browser CORS limits)
   */
  async fetchModels(request: FetchModelsRequest): Promise<string[]> {
    const data = await apiJson<{ models?: unknown }>('/llm-config/models', {
      method: 'POST',
      body: request,
    })
    return Array.isArray(data.models) ? data.models : []
  }

  /**
   * Fetch models for an existing saved configuration (uses encrypted key server-side)
   */
  async getModelsForConfig(configId: string): Promise<string[]> {
    const data = await apiJson<{ models?: unknown }>(`/llm-config/user-configs/${configId}/models`)
    return Array.isArray(data.models) ? data.models : []
  }
}

// Export singleton instance
export const llmConfigApi = new LLMConfigApi()
