import { apiJson } from '@/lib/api/client'

export type AgentModelProfile = { id: string; name: string; provider: string; model: string; key_prefix?: string }
export type AgentDefinition = { id: string; name: string; role: string; description?: string; model_profile_id: string; tool_names: string[] }
export type AgentRun = { id: string; prompt: string; status: string; current_step: number; tokens_used: number; cost_used_usd: number; created_at: string }
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
