import {
  JournalCreate,
  JournalUpdate,
  JournalResponse,
  JournalListResponse,
  JournalStatistics,
  JournalFilter,
  QuickJournalEntry,
  JournalImportPreviewResponse,
  JournalImportResponse,
  JournalEntryAnalysisResponse,
  JournalPatternAnalysisResponse,
  JournalImprovementPlanResponse,
} from '@/lib/types/journal';
import { apiFetch, type ApiRequestInit } from '@/lib/api/client';

async function fetchWithAuth(url: string, options: ApiRequestInit = {}) {
  return apiFetch(url, options);
}

export const journalApi = {
  // Create a new journal entry
  async create(entry: JournalCreate): Promise<JournalResponse> {
    const response = await fetchWithAuth('/journals', {
      method: 'POST',
      body: entry,
    });

    if (!response.ok) {
      throw new Error('Failed to create journal entry');
    }

    return response.json();
  },

  // Get list of journal entries with filtering
  async list(params?: {
    page?: number;
    per_page?: number;
    filter?: JournalFilter;
  }): Promise<JournalListResponse> {
    const queryParams = new URLSearchParams();

    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString());

    if (params?.filter) {
      Object.entries(params.filter).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, value.toString());
        }
      });
    }

    const response = await fetchWithAuth(`/journals?${queryParams}`);

    if (!response.ok) {
      throw new Error('Failed to fetch journal entries');
    }

    return response.json();
  },

  // Get a single journal entry
  async get(id: string): Promise<JournalResponse> {
    const response = await fetchWithAuth(`/journals/${id}`);

    if (!response.ok) {
      throw new Error('Failed to fetch journal entry');
    }

    return response.json();
  },

  // Update a journal entry
  async update(id: string, entry: JournalUpdate): Promise<JournalResponse> {
    const response = await fetchWithAuth(`/journals/${id}`, {
      method: 'PUT',
      body: entry,
    });

    if (!response.ok) {
      throw new Error('Failed to update journal entry');
    }

    return response.json();
  },

  // Delete a journal entry
  async delete(id: string): Promise<void> {
    const response = await fetchWithAuth(`/journals/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to delete journal entry');
    }
  },

  // Get trading statistics
  async getStatistics(): Promise<JournalStatistics> {
    const response = await fetchWithAuth('/journals/statistics');

    if (!response.ok) {
      throw new Error('Failed to fetch statistics');
    }

    return response.json();
  },

  // Create a quick journal entry
  async createQuick(entry: QuickJournalEntry): Promise<JournalResponse> {
    const response = await fetchWithAuth('/journals/quick', {
      method: 'POST',
      body: entry,
    });

    if (!response.ok) {
      throw new Error('Failed to create quick journal entry');
    }

    return response.json();
  },

  // Analyze a single journal entry with AI
  async analyzeEntry(id: string): Promise<JournalEntryAnalysisResponse> {
    const response = await fetchWithAuth(`/journals/${id}/analyze`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to analyze journal entry');
    }

    return response.json();
  },

  // Analyze trading patterns
  async analyzePatterns(limit?: number): Promise<JournalPatternAnalysisResponse> {
    const queryParams = new URLSearchParams();
    if (limit) queryParams.append('limit', limit.toString());

    const response = await fetchWithAuth(`/journals/analyze/patterns?${queryParams}`);

    if (!response.ok) {
      throw new Error('Failed to analyze trading patterns');
    }

    return response.json();
  },

  // Generate improvement plan
  async generateImprovementPlan(): Promise<JournalImprovementPlanResponse> {
    const response = await fetchWithAuth('/journals/analyze/improvement-plan');

    if (!response.ok) {
      throw new Error('Failed to generate improvement plan');
    }

    return response.json();
  },

  async importPreview(file: File, previewRows = 20): Promise<JournalImportPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetchWithAuth(`/journals/import/preview?preview_rows=${previewRows}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to preview import file');
    }

    return response.json();
  },

  async importTrades(params: {
    file: File;
    mapping: Record<string, string>;
    project_id?: string | null;
    strict?: boolean;
    dry_run?: boolean;
    max_rows?: number;
  }): Promise<JournalImportResponse> {
    const formData = new FormData();
    formData.append('file', params.file);
    formData.append('mapping_json', JSON.stringify(params.mapping ?? {}));
    if (params.project_id) formData.append('project_id', params.project_id);
    if (typeof params.strict === 'boolean') formData.append('strict', String(params.strict));
    if (typeof params.dry_run === 'boolean') formData.append('dry_run', String(params.dry_run));
    if (typeof params.max_rows === 'number') formData.append('max_rows', String(params.max_rows));

    const response = await fetchWithAuth('/journals/import', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      throw new Error(detail || 'Failed to import trades');
    }

    return response.json();
  },
};
