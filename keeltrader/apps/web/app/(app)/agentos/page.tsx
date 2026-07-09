'use client'

import { useEffect } from 'react'
import { BrainCircuit, Loader2, RefreshCw } from 'lucide-react'

import { AgentOSTabs } from '@/components/agentos/AgentOSTabs'
import { Stat, StatusBadges } from '@/components/agentos/agentos-primitives'
import { Button } from '@/components/ui/button'
import { useAgentOSDashboard } from '@/lib/agentos/use-agentos-dashboard'
import { useI18n } from '@/lib/i18n/provider'

export default function AgentOSPage() {
  const { state, actions } = useAgentOSDashboard()
  const { refresh } = actions
  const { t } = useI18n()

  useEffect(() => {
    refresh()
  }, [refresh])

  if (state.loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <BrainCircuit className="h-6 w-6" />
              AgentOS
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('agentos.subtitle')}
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 md:items-end">
            <StatusBadges health={state.health} />
            <Button size="sm" variant="outline" onClick={actions.refresh}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('common.update')}
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <Stat label={t('agentos.stats.briefs')} value={state.briefs.length} />
          <Stat label={t('agentos.stats.researchMemos')} value={state.memos.length} />
          <Stat label={t('agentos.stats.decisions')} value={state.decisions.length} />
          <Stat label={t('agentos.stats.approvedLessons')} value={state.memory.length} />
        </div>

        <AgentOSTabs state={state} actions={actions} />
      </div>
    </div>
  )
}
