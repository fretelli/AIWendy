'use client'

import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { agentsAPI } from '@/lib/api/agents'
import type { AgentStatus, AgentDetailStatus } from '@/lib/types/agents'

interface AgentDetailDialogProps {
  agent: AgentStatus | null
  open: boolean
  onClose: () => void
  onChat: (agentId: string) => void
}

export function AgentDetailDialog({ agent, open, onClose, onChat }: AgentDetailDialogProps) {
  const [detail, setDetail] = useState<AgentDetailStatus | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (agent && open) {
      setLoading(true)
      agentsAPI.getAgentStatus(agent.agent_id)
        .then(setDetail)
        .catch(() => setDetail(null))
        .finally(() => setLoading(false))
    }
  }, [agent, open])

  if (!agent) return null

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{agent.name}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant={agent.is_active ? 'default' : 'secondary'}>
              {agent.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Badge variant="outline">{agent.agent_type}</Badge>
            <span className="text-sm text-muted-foreground">Trust Level: {agent.trust_level}</span>
          </div>

          <div>
            <h4 className="mb-1 text-sm font-medium">Subscriptions</h4>
            <div className="flex flex-wrap gap-1">
              {agent.subscriptions.map((sub) => (
                <Badge key={sub} variant="outline" className="text-xs">{sub}</Badge>
              ))}
              {agent.subscriptions.length === 0 && (
                <span className="text-xs text-muted-foreground">No subscriptions</span>
              )}
            </div>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading status...</p>
          ) : detail ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm">Circuit Breaker:</span>
                <Badge variant={detail.circuit_breaker_active ? 'destructive' : 'default'}>
                  {detail.circuit_breaker_active ? 'ACTIVE' : 'Off'}
                </Badge>
              </div>
              {detail.cooldown_remaining_seconds > 0 && (
                <p className="text-sm text-muted-foreground">
                  Cooldown: {detail.cooldown_remaining_seconds}s remaining
                </p>
              )}
            </div>
          ) : null}

          <Button
            className="w-full"
            onClick={() => {
              onChat(agent.agent_id)
              onClose()
            }}
          >
            Chat with {agent.name}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
