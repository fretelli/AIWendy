/**
 * Ollama API client for local model management
 */

import { apiJson, apiStream } from '@/lib/api/client'

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
    return apiJson<OllamaHealthResponse>('/ollama/health')
  }

  /**
   * List available models in Ollama
   */
  async listModels(): Promise<ListModelsResponse> {
    return apiJson<ListModelsResponse>('/ollama/models')
  }

  /**
   * Get recommended models for trading psychology coaching
   */
  async getRecommendedModels(): Promise<{ models: RecommendedModel[] }> {
    return apiJson<{ models: RecommendedModel[] }>('/ollama/recommended-models')
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
    const response = await apiStream('/ollama/models/pull', {
      method: 'POST',
      body: { model_name: modelName },
    })

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
    return apiJson<TestChatResponse>('/ollama/test-chat', {
      method: 'POST',
      body: { model, message },
    })
  }
}

export const ollamaApi = new OllamaApi()
