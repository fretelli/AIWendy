import { getApiUrl } from '@/lib/config'

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
  private apiUrl: string

  constructor() {
    this.apiUrl = getApiUrl()
  }

  private getHeaders() {
    const token = localStorage.getItem('keeltrader_access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    }
  }

  async getCoaches(style?: string, isPremium?: boolean): Promise<Coach[]> {
    const params = new URLSearchParams()
    if (style) params.append('style', style)
    if (isPremium !== undefined) params.append('is_premium', String(isPremium))

    const response = await fetch(`${this.apiUrl}/coaches?${params}`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch coaches')
    }

    return response.json()
  }

  async getCoach(coachId: string): Promise<Coach> {
    const response = await fetch(`${this.apiUrl}/coaches/${coachId}`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch coach')
    }

    return response.json()
  }

  async getDefaultCoach(): Promise<Coach> {
    const response = await fetch(`${this.apiUrl}/coaches/default`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch default coach')
    }

    return response.json()
  }

  async createSession(request: CreateSessionRequest): Promise<ChatSession> {
    const response = await fetch(`${this.apiUrl}/coaches/sessions`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error('Failed to create session')
    }

    return response.json()
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

    const response = await fetch(`${this.apiUrl}/coaches/sessions/user?${params}`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch sessions')
    }

    return response.json()
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await fetch(`${this.apiUrl}/coaches/sessions/${sessionId}`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch session')
    }

    return response.json()
  }

  async endSession(sessionId: string, request: EndSessionRequest): Promise<ChatSession> {
    const response = await fetch(`${this.apiUrl}/coaches/sessions/${sessionId}/end`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error('Failed to end session')
    }

    return response.json()
  }

  async getSessionMessages(sessionId: string, limit?: number) {
    const params = limit ? `?limit=${limit}` : ''
    const response = await fetch(
      `${this.apiUrl}/coaches/sessions/${sessionId}/messages${params}`,
      {
        headers: this.getHeaders()
      }
    )

    if (!response.ok) {
      throw new Error('Failed to fetch messages')
    }

    return response.json()
  }

  async getCustomCoaches(): Promise<CustomCoach[]> {
    const response = await fetch(`${this.apiUrl}/coaches/custom`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to fetch custom coaches')
    }

    return response.json()
  }

  async createCustomCoach(request: CreateCustomCoachRequest): Promise<CustomCoach> {
    const response = await fetch(`${this.apiUrl}/coaches/custom`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error('Failed to create custom coach')
    }

    return response.json()
  }

  async updateCustomCoach(coachId: string, request: UpdateCustomCoachRequest): Promise<CustomCoach> {
    const response = await fetch(`${this.apiUrl}/coaches/custom/${coachId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error('Failed to update custom coach')
    }

    return response.json()
  }

  async deleteCustomCoach(coachId: string): Promise<{ ok: boolean }> {
    const response = await fetch(`${this.apiUrl}/coaches/custom/${coachId}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to delete custom coach')
    }

    return response.json()
  }
}

export const coachesAPI = new CoachesAPI()
