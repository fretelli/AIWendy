'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { AgentStatus } from '@/lib/types/agents'

interface AgentCardsProps {
  agents: AgentStatus[]
  loading: boolean
  onSelect: (agent: AgentStatus) => void
  onChat: (agentId: string) => void
}

const agentTypeColors: Record<string, string> = {
  orchestrator: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  analyst: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  executor: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  psychology: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  guardian: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

function getTrustLevelLabel(level: number): string {
  if (level >= 9) return 'Critical'
  if (level >= 7) return 'High'
  if (level >= 5) return 'Medium'
  if (level >= 3) return 'Low'
  return 'Minimal'
}

export function AgentCards({ agents, loading, onSelect, onChat }: AgentCardsProps) {
  if (loading && agents.length === 0) {
    return <div className="text-sm text-muted-foreground">Loading agents...</div>
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => (
        <Card
          key={agent.agent_id}
          className="cursor-pointer transition-shadow hover:shadow-md"
          onClick={() => onSelect(agent)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{agent.name}</CardTitle>
              <Badge variant={agent.is_active ? 'default' : 'secondary'}>
                {agent.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${agentTypeColors[agent.agent_type] || ''}`}>
                {agent.agent_type}
              </span>
              <span className="text-xs text-muted-foreground">
                Trust: {getTrustLevelLabel(agent.trust_level)} ({agent.trust_level})
              </span>
            </div>

            {agent.subscriptions.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {agent.subscriptions.slice(0, 4).map((sub) => (
                  <Badge key={sub} variant="outline" className="text-xs">
                    {sub}
                  </Badge>
                ))}
                {agent.subscriptions.length > 4 && (
                  <Badge variant="outline" className="text-xs">
                    +{agent.subscriptions.length - 4}
                  </Badge>
                )}
              </div>
            )}

            <button
              className="text-xs text-primary hover:underline"
              onClick={(e) => {
                e.stopPropagation()
                onChat(agent.agent_id)
              }}
            >
              Chat with this agent &rarr;
            </button>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
