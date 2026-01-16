import { getApiUrl } from '@/lib/config'
import type {
  CoachPreset,
  RoundtableSession,
  CreateRoundtableSessionRequest,
  SessionDetailResponse,
  RoundtableChatRequest,
  RoundtableEvent,
} from '@/lib/types/roundtable'

type ApiErrorPayload =
  | {
      error?: {
        message?: unknown
      }
      detail?: unknown
    }
  | null
  | undefined

function formatFastApiDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const parts: string[] = []
    for (const item of detail) {
      if (!item || typeof item !== 'object') continue
      const msg = (item as { msg?: unknown }).msg
      const loc = (item as { loc?: unknown }).loc

      if (typeof msg !== 'string') continue
      if (Array.isArray(loc)) {
        const locText = loc.map(String).join('.')
        parts.push(locText ? `${locText}: ${msg}` : msg)
      } else {
        parts.push(msg)
      }
    }
    if (parts.length) return parts.join('; ')
  }

  return null
}

function getErrorMessage(payload: ApiErrorPayload): string | null {
  if (!payload || typeof payload !== 'object') return null

  const errorMessage = payload.error?.message
  if (typeof errorMessage === 'string' && errorMessage) return errorMessage

  return formatFastApiDetail(payload.detail)
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload
    return getErrorMessage(payload) ?? response.statusText ?? 'Request failed'
  }

  const text = await response.text().catch(() => '')
  return text || response.statusText || 'Request failed'
}

class RoundtableAPI {
  private apiUrl: string

  constructor() {
    this.apiUrl = getApiUrl()
  }

  private getHeaders() {
    const token = localStorage.getItem('keeltrader_access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    }
  }

  // ============= Presets =============

  async getPresets(): Promise<CoachPreset[]> {
    const response = await fetch(`${this.apiUrl}/roundtable/presets`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch presets')
    }

    return response.json()
  }

  async getPreset(presetId: string): Promise<CoachPreset> {
    const response = await fetch(`${this.apiUrl}/roundtable/presets/${presetId}`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch preset')
    }

    return response.json()
  }

  // ============= Sessions =============

  async createSession(request: CreateRoundtableSessionRequest): Promise<RoundtableSession> {
    const response = await fetch(`${this.apiUrl}/roundtable/sessions`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(await readErrorMessage(response))
    }

    return response.json()
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

    const response = await fetch(`${this.apiUrl}/roundtable/sessions?${params}`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch sessions')
    }

    return response.json()
  }

  async getSession(sessionId: string): Promise<SessionDetailResponse> {
    const response = await fetch(`${this.apiUrl}/roundtable/sessions/${sessionId}`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch session')
    }

    return response.json()
  }

  async endSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.apiUrl}/roundtable/sessions/${sessionId}/end`, {
      method: 'POST',
      headers: this.getHeaders(),
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
    const response = await fetch(`${this.apiUrl}/roundtable/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(await readErrorMessage(response))
    }

    return response.json()
  }

  // ============= Chat (Streaming) =============

  async *chat(
    request: RoundtableChatRequest
  ): AsyncGenerator<RoundtableEvent, void, unknown> {
    const params = new URLSearchParams({ session_id: request.session_id })
    const response = await fetch(`${this.apiUrl}/roundtable/chat?${params}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(await readErrorMessage(response))
    }

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
