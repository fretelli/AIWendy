import { getApiUrl } from '@/lib/config'

export interface Project {
  id: string
  user_id: string
  name: string
  description?: string | null
  is_default: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  name: string
  description?: string | null
}

export interface UpdateProjectRequest {
  name?: string
  description?: string | null
  is_archived?: boolean
  is_default?: boolean
}

class ProjectsAPI {
  private apiUrl: string

  constructor() {
    this.apiUrl = getApiUrl()
  }

  private getHeaders() {
    const token = localStorage.getItem('keeltrader_access_token')
    return {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
    }
  }

  async listProjects(includeArchived: boolean = false): Promise<Project[]> {
    const params = new URLSearchParams()
    if (includeArchived) params.append('include_archived', 'true')
    const response = await fetch(`${this.apiUrl}/projects?${params}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error('Failed to fetch projects')
    }
    return response.json()
  }

  async createProject(request: CreateProjectRequest): Promise<Project> {
    const response = await fetch(`${this.apiUrl}/projects`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to create project'
      throw new Error(detail)
    }
    return response.json()
  }

  async updateProject(projectId: string, request: UpdateProjectRequest): Promise<Project> {
    const response = await fetch(`${this.apiUrl}/projects/${projectId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to update project'
      throw new Error(detail)
    }
    return response.json()
  }

  async deleteProject(projectId: string, hardDelete: boolean = false): Promise<void> {
    const params = hardDelete ? '?hard_delete=true' : ''
    const response = await fetch(`${this.apiUrl}/projects/${projectId}${params}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to delete project'
      throw new Error(detail)
    }
  }
}

export const projectsAPI = new ProjectsAPI()

