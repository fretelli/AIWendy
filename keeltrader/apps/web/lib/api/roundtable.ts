import { apiFetch, apiJson, apiStream } from '@/lib/api/client'
import type {
  CoachPreset,
  RoundtableSession,
  CreateRoundtableSessionRequest,
  SessionDetailResponse,
  RoundtableChatRequest,
  RoundtableEvent,
} from '@/lib/types/roundtable'

class RoundtableAPI {
  // ============= Presets =============

  async getPresets(): Promise<CoachPreset[]> {
    return apiJson<CoachPreset[]>('/roundtable/presets')
  }

  async getPreset(presetId: string): Promise<CoachPreset> {
    return apiJson<CoachPreset>(`/roundtable/presets/${presetId}`)
  }

  // ============= Sessions =============

  async createSession(request: CreateRoundtableSessionRequest): Promise<RoundtableSession> {
    return apiJson<RoundtableSession>('/roundtable/sessions', {
      method: 'POST',
      body: request,
    })
  }

  async getSessions(
    projectId?: string | null,
    isActive?: boolean,
    limit?: number
  ): Promise<RoundtableSession[]> {
    const params = new URLSearchParams()
    if (projectId) params.append('project_id', projectId)
    if (isActive !== undefined) params.append('is_active', String(isActive))
    if (limit) params.append('limit', String(limit))

    return apiJson<RoundtableSession[]>(`/roundtable/sessions?${params}`)
  }

  async getSession(sessionId: string): Promise<SessionDetailResponse> {
    return apiJson<SessionDetailResponse>(`/roundtable/sessions/${sessionId}`)
  }

  async endSession(sessionId: string): Promise<void> {
    const response = await apiFetch(`/roundtable/sessions/${sessionId}/end`, {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error('Failed to end session')
    }
  }

  async updateSessionSettings(
    sessionId: string,
    request: Partial<{
      config_id: string | null
      provider: string | null
      model: string | null
      temperature: number | null
      max_tokens: number | null
      kb_timing: string | null
      kb_top_k: number | null
      kb_max_candidates: number | null
    }>
  ): Promise<RoundtableSession> {
    return apiJson<RoundtableSession>(`/roundtable/sessions/${sessionId}`, {
      method: 'PATCH',
      body: request,
    })
  }

  // ============= Chat (Streaming) =============

  async *chat(
    request: RoundtableChatRequest
  ): AsyncGenerator<RoundtableEvent, void, unknown> {
    const params = new URLSearchParams({ session_id: request.session_id })
    const response = await apiStream(`/roundtable/chat?${params}`, {
      method: 'POST',
      body: request,
    })

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data) {
              try {
                const event = JSON.parse(data) as RoundtableEvent
                yield event
              } catch (e) {
                console.error('Failed to parse SSE event:', data)
              }
            }
          }
        }
      }

      // Process remaining buffer
      if (buffer.startsWith('data: ')) {
        const data = buffer.slice(6).trim()
        if (data) {
          try {
            const event = JSON.parse(data) as RoundtableEvent
            yield event
          } catch (e) {
            console.error('Failed to parse final SSE event:', data)
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }
}

export const roundtableAPI = new RoundtableAPI()
