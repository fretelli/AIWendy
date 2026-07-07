import { apiFetch, apiJson } from '@/lib/api/client'

export interface Coach {
  id: string
  name: string
  avatar_url?: string
  description?: string
  bio?: string
  style: string
  personality_traits: string[]
  specialty: string[]
  language: string
  is_premium: boolean
  is_public: boolean
  total_sessions: number
  avg_rating?: number
  rating_count: number
}

export interface CustomCoach {
  id: string
  name: string
  avatar_url?: string
  description?: string
  bio?: string
  style: string
  personality_traits: string[]
  specialty: string[]
  language: string
  is_public: boolean
  is_active: boolean
  llm_provider: string
  llm_model: string
  system_prompt: string
  temperature: number
  max_tokens: number
  created_at: string
  updated_at: string
}

export interface CreateCustomCoachRequest {
  name: string
  description?: string
  bio?: string
  avatar_url?: string
  style: string
  personality_traits?: string[]
  specialty?: string[]
  language?: string
  llm_provider?: string
  llm_model?: string
  system_prompt: string
  temperature?: number
  max_tokens?: number
  is_public?: boolean
}

export interface UpdateCustomCoachRequest extends Partial<CreateCustomCoachRequest> {
  is_active?: boolean
}

export interface ChatSession {
  id: string
  user_id: string
  coach_id: string
  project_id?: string | null
  title?: string
  context?: any
  mood_before?: number
  mood_after?: number
  message_count: number
  total_tokens: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateSessionRequest {
  coach_id: string
  project_id?: string | null
  title?: string
  context?: any
  mood_before?: number
}

export interface EndSessionRequest {
  mood_after?: number
  user_rating?: number
  user_feedback?: string
}

class CoachesAPI {
  async getCoaches(style?: string, isPremium?: boolean): Promise<Coach[]> {
    const params = new URLSearchParams()
    if (style) params.append('style', style)
    if (isPremium !== undefined) params.append('is_premium', String(isPremium))

    return apiJson<Coach[]>(`/coaches?${params}`)
  }

  async getCoach(coachId: string): Promise<Coach> {
    return apiJson<Coach>(`/coaches/${coachId}`)
  }

  async getDefaultCoach(): Promise<Coach> {
    return apiJson<Coach>('/coaches/default')
  }

  async createSession(request: CreateSessionRequest): Promise<ChatSession> {
    return apiJson<ChatSession>('/coaches/sessions', {
      method: 'POST',
      body: request
    })
  }

  async getUserSessions(
    coachId?: string,
    projectId?: string | null,
    isActive?: boolean,
    limit?: number
  ): Promise<ChatSession[]> {
    const params = new URLSearchParams()
    if (coachId) params.append('coach_id', coachId)
    if (projectId) params.append('project_id', projectId)
    if (isActive !== undefined) params.append('is_active', String(isActive))
    if (limit) params.append('limit', String(limit))

    return apiJson<ChatSession[]>(`/coaches/sessions/user?${params}`)
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    return apiJson<ChatSession>(`/coaches/sessions/${sessionId}`)
  }

  async endSession(sessionId: string, request: EndSessionRequest): Promise<ChatSession> {
    return apiJson<ChatSession>(`/coaches/sessions/${sessionId}/end`, {
      method: 'POST',
      body: request
    })
  }

  async getSessionMessages(sessionId: string, limit?: number) {
    const params = limit ? `?limit=${limit}` : ''
    return apiJson(`/coaches/sessions/${sessionId}/messages${params}`)
  }

  async getCustomCoaches(): Promise<CustomCoach[]> {
    return apiJson<CustomCoach[]>('/coaches/custom')
  }

  async createCustomCoach(request: CreateCustomCoachRequest): Promise<CustomCoach> {
    return apiJson<CustomCoach>('/coaches/custom', {
      method: 'POST',
      body: request
    })
  }

  async updateCustomCoach(coachId: string, request: UpdateCustomCoachRequest): Promise<CustomCoach> {
    return apiJson<CustomCoach>(`/coaches/custom/${coachId}`, {
      method: 'PATCH',
      body: request
    })
  }

  async deleteCustomCoach(coachId: string): Promise<{ ok: boolean }> {
    const response = await apiFetch(`/coaches/custom/${coachId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error('Failed to delete custom coach')
    }

    return response.json()
  }
}

export const coachesAPI = new CoachesAPI()
