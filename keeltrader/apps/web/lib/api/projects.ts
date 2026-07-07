import { apiFetch, apiJson } from '@/lib/api/client'

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
  async listProjects(includeArchived: boolean = false): Promise<Project[]> {
    const params = new URLSearchParams()
    if (includeArchived) params.append('include_archived', 'true')
    return apiJson<Project[]>(`/projects?${params}`)
  }

  async createProject(request: CreateProjectRequest): Promise<Project> {
    return apiJson<Project>('/projects', {
      method: 'POST',
      body: request,
    })
  }

  async updateProject(projectId: string, request: UpdateProjectRequest): Promise<Project> {
    return apiJson<Project>(`/projects/${projectId}`, {
      method: 'PATCH',
      body: request,
    })
  }

  async deleteProject(projectId: string, hardDelete: boolean = false): Promise<void> {
    const params = hardDelete ? '?hard_delete=true' : ''
    const response = await apiFetch(`/projects/${projectId}${params}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error('Failed to delete project')
    }
  }
}

export const projectsAPI = new ProjectsAPI()
