import { apiFetch, apiJson } from '@/lib/api/client'

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
  async listDocuments(projectId?: string | null): Promise<KnowledgeDocument[]> {
    const params = new URLSearchParams()
    if (projectId) params.append('project_id', projectId)
    return apiJson<KnowledgeDocument[]>(`/knowledge/documents?${params}`)
  }

  async createDocument(request: CreateKnowledgeDocumentRequest): Promise<KnowledgeDocument> {
    return apiJson<KnowledgeDocument>('/knowledge/documents', {
      method: 'POST',
      body: request,
    })
  }

  async deleteDocument(documentId: string, hardDelete: boolean = false): Promise<void> {
    const params = hardDelete ? '?hard_delete=true' : ''
    const response = await apiFetch(`/knowledge/documents/${documentId}${params}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error('Failed to delete document')
    }
  }

  async search(q: string, projectId?: string | null, limit: number = 5): Promise<KnowledgeSearchResult[]> {
    const params = new URLSearchParams()
    params.append('q', q)
    if (projectId) params.append('project_id', projectId)
    params.append('limit', String(limit))
    return apiJson<KnowledgeSearchResult[]>(`/knowledge/search?${params}`)
  }
}

export const knowledgeAPI = new KnowledgeAPI()
