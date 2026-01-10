/**
 * Ollama API client for local model management
 */

import { getAuthHeaders } from './auth'
import { API_V1_PREFIX } from '@/lib/config'

const API_BASE_URL = API_V1_PREFIX

export interface OllamaHealthResponse {
  healthy: boolean
  message: string
}

export interface OllamaModel {
  name: string
  modified_at?: string
  size?: number
  digest?: string
}

export interface ListModelsResponse {
  models: string[]
  available: boolean
}

export interface RecommendedModel {
  name: string
  description: string
  size: string
  recommended: boolean
  use_case: string
}

export interface PullProgress {
  status: string
  done?: boolean
}

export interface TestChatResponse {
  model: string
  message: string
  response: string
}

class OllamaApi {
  /**
   * Check if Ollama service is running
   */
  async checkHealth(): Promise<OllamaHealthResponse> {
    const response = await fetch(`${API_BASE_URL}/ollama/health`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error('Failed to check Ollama health')
    }

    return response.json()
  }

  /**
   * List available models in Ollama
   */
  async listModels(): Promise<ListModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/ollama/models`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error('Failed to list models')
    }

    return response.json()
  }

  /**
   * Get recommended models for trading psychology coaching
   */
  async getRecommendedModels(): Promise<{ models: RecommendedModel[] }> {
    const response = await fetch(`${API_BASE_URL}/ollama/recommended-models`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error('Failed to get recommended models')
    }

    return response.json()
  }

  /**
   * Pull a model from Ollama registry
   * @param modelName - Name of the model to pull
   * @param onProgress - Callback for progress updates
   */
  async pullModel(
    modelName: string,
    onProgress?: (progress: PullProgress) => void
  ): Promise<void> {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/ollama/models/pull`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model_name: modelName }),
    })

    if (!response.ok) {
      throw new Error('Failed to pull model')
    }

    // Handle Server-Sent Events stream
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No response body')
    }

    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })

      // Process complete messages
      const lines = buffer.split('\\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (onProgress) {
              onProgress(data)
            }
            if (data.done) {
              return
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  }

  /**
   * Test chat with a specific Ollama model
   */
  async testChat(model: string, message: string): Promise<TestChatResponse> {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/ollama/test-chat`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model, message }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || 'Failed to test chat')
    }

    return response.json()
  }
}

export const ollamaApi = new OllamaApi()
