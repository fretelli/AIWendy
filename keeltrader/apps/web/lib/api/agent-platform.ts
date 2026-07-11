import { apiJson } from '@/lib/api/client'

export type AgentModelProfile = { id: string; name: string; provider: string; model: string; key_prefix?: string }
export type AgentDefinition = { id: string; name: string; role: string; description?: string; model_profile_id: string; tool_names: string[] }
export type AgentRun = { id: string; prompt: string; status: string; current_step: number; tokens_used: number; cost_used_usd: number; created_at: string }
export type InteractionMode = 'ask' | 'research' | 'plan'
export type AgentSession = { id: string; agent_definition_id?: string; title: string; status: string; interaction_mode: InteractionMode; summary?: string; context_tokens: number; is_pinned: boolean; archived_at?: string; last_message_at: string; created_at: string }
export type AgentMessage = { id: string; session_id: string; run_id?: string; role: 'user' | 'assistant' | 'system'; kind: string; status: string; content: string; metadata_json?: Record<string, unknown>; created_at: string }
export type AgentApproval = { id: string; kind: string; preview: Record<string, unknown>; created_at: string }
export type AgentMemory = { id: string; key: string; value: unknown; confidence: number; version: number; is_deleted: boolean }
export type MCPServer = { id: string; name: string; url: string; status: string; tools_snapshot: Array<{ name: string; description?: string }> }
export type AgentSchedule = { id: string; name: string; cron: string; prompt: string; enabled: boolean; next_run_at?: string }
export type Usage = { today: { input_tokens: number; output_tokens: number; cost_usd: number }; limits: { tokens: number; cost_usd: number } }

const base = '/agent'
export const agentPlatformApi = {
  health: () => apiJson<{ status: string; mode: string }>(`${base}/health`),
  models: () => apiJson<{ items: AgentModelProfile[] }>(`${base}/model-credentials`),
  createModel: (body: object) => apiJson<AgentModelProfile>(`${base}/model-credentials`, { method: 'POST', body }),
  agents: () => apiJson<{ items: AgentDefinition[]; builtin_tools: string[]; mcp_tools: Array<{ name: string; server: string; description: string }> }>(`${base}/definitions`),
  createAgent: (body: object) => apiJson<AgentDefinition>(`${base}/definitions`, { method: 'POST', body }),
  runs: () => apiJson<{ items: AgentRun[] }>(`${base}/runs`),
  createRun: (body: object) => apiJson<AgentRun>(`${base}/runs`, { method: 'POST', body }),
  sessions: (includeArchived = false) => apiJson<{ items: AgentSession[] }>(`${base}/sessions?include_archived=${includeArchived}`),
  createSession: (body: { agent_definition_id: string; title?: string; interaction_mode?: InteractionMode }) => apiJson<AgentSession>(`${base}/sessions`, { method: 'POST', body }),
  updateSession: (id: string, body: { title?: string; is_pinned?: boolean; archived?: boolean; interaction_mode?: InteractionMode }) => apiJson<AgentSession>(`${base}/sessions/${id}`, { method: 'PATCH', body }),
  timeline: (id: string) => apiJson<{ session: AgentSession; messages: AgentMessage[]; runs: AgentRun[] }>(`${base}/sessions/${id}/timeline`),
  sendMessage: (id: string, body: { content: string; agent_definition_id?: string }) => apiJson<{ run: AgentRun; session: AgentSession }>(`${base}/sessions/${id}/messages`, { method: 'POST', body }),
  compactSession: (id: string) => apiJson<AgentSession>(`${base}/sessions/${id}/compact`, { method: 'POST' }),
  stopSession: (id: string) => apiJson<AgentRun>(`${base}/sessions/${id}/stop`, { method: 'POST' }),
  controlRun: (id: string, action: 'pause' | 'resume' | 'cancel') => apiJson<AgentRun>(`${base}/runs/${id}/${action}`, { method: 'POST' }),
  approvals: () => apiJson<{ items: AgentApproval[] }>(`${base}/approvals`),
  resolveApproval: (id: string, decision: 'approved' | 'rejected', scope: 'once' | 'always' = 'once') => apiJson(`${base}/approvals/${id}/resolve`, { method: 'POST', body: { decision, scope } }),
  memories: (includeDeleted = false) => apiJson<{ items: AgentMemory[] }>(`${base}/memories?include_deleted=${includeDeleted}`),
  deleteMemory: (id: string) => apiJson(`${base}/memories/${id}`, { method: 'DELETE' }),
  restoreMemory: (id: string) => apiJson(`${base}/memories/${id}/restore`, { method: 'POST' }),
  mcpServers: () => apiJson<{ items: MCPServer[] }>(`${base}/mcp-servers`),
  createMcp: (body: object) => apiJson<MCPServer>(`${base}/mcp-servers`, { method: 'POST', body }),
  schedules: () => apiJson<{ items: AgentSchedule[] }>(`${base}/schedules`),
  createSchedule: (body: object) => apiJson<AgentSchedule>(`${base}/schedules`, { method: 'POST', body }),
  usage: () => apiJson<Usage>(`${base}/usage`),
}
