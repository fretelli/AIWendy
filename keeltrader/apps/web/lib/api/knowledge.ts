import { getApiUrl } from '@/lib/config'

export interface KnowledgeDocument {
  id: string
  project_id?: string | null
  title: string
  source_type: string
  source_name?: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface CreateKnowledgeDocumentRequest {
  project_id?: string | null
  title: string
  content: string
  source_type?: string
  source_name?: string | null
  metadata?: Record<string, any>
  embedding_provider?: string | null
  embedding_model?: string | null
}

export interface KnowledgeSearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  score: number
  content: string
}

class KnowledgeAPI {
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

  async listDocuments(projectId?: string | null): Promise<KnowledgeDocument[]> {
    const params = new URLSearchParams()
    if (projectId) params.append('project_id', projectId)
    const response = await fetch(`${this.apiUrl}/knowledge/documents?${params}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error('Failed to fetch documents')
    }
    return response.json()
  }

  async createDocument(request: CreateKnowledgeDocumentRequest): Promise<KnowledgeDocument> {
    const response = await fetch(`${this.apiUrl}/knowledge/documents`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to create document'
      throw new Error(detail)
    }
    return response.json()
  }

  async deleteDocument(documentId: string, hardDelete: boolean = false): Promise<void> {
    const params = hardDelete ? '?hard_delete=true' : ''
    const response = await fetch(`${this.apiUrl}/knowledge/documents/${documentId}${params}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to delete document'
      throw new Error(detail)
    }
  }

  async search(q: string, projectId?: string | null, limit: number = 5): Promise<KnowledgeSearchResult[]> {
    const params = new URLSearchParams()
    params.append('q', q)
    if (projectId) params.append('project_id', projectId)
    params.append('limit', String(limit))
    const response = await fetch(`${this.apiUrl}/knowledge/search?${params}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error('Failed to search knowledge base')
    }
    return response.json()
  }
}

export const knowledgeAPI = new KnowledgeAPI()

