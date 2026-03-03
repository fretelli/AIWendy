'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { useI18n } from '@/lib/i18n/provider'
import { agentsAPI } from '@/lib/api/agents'
import { HealthOverview } from '@/components/agents/HealthOverview'
import { AgentCards } from '@/components/agents/AgentCards'
import { AgentDetailDialog } from '@/components/agents/AgentDetailDialog'
import { GhostPortfolio } from '@/components/agents/GhostPortfolio'
import { EventStream } from '@/components/agents/EventStream'
import { EventSubmitDialog } from '@/components/agents/EventSubmitDialog'
import { AgentChat } from '@/components/agents/AgentChat'
import type {
  AgentStatus,
  HealthResponse,
  CachedPrices,
  GhostTrade,
  PortfolioSummary,
  StreamEvent,
  StreamInfo,
} from '@/lib/types/agents'
import { RefreshCw } from 'lucide-react'

export default function AgentMatrixPage() {
  const { t } = useI18n()

  // Data state
  const [agents, setAgents] = useState<AgentStatus[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [prices, setPrices] = useState<CachedPrices | null>(null)
  const [trades, setTrades] = useState<GhostTrade[]>([])
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null)
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [streamInfo, setStreamInfo] = useState<StreamInfo | null>(null)
  const [loading, setLoading] = useState(true)

  // UI state
  const [activeTab, setActiveTab] = useState('overview')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<AgentStatus | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [eventSubmitOpen, setEventSubmitOpen] = useState(false)
  const [chatAgentId, setChatAgentId] = useState<string | undefined>(undefined)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refreshAll = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        agentsAPI.getAgents(),
        agentsAPI.getHealth(),
        agentsAPI.getPrices(),
        agentsAPI.getGhostTrades(),
        agentsAPI.getPortfolio(),
        agentsAPI.getRecentEvents(),
        agentsAPI.getStreamInfo(),
      ])

      if (results[0].status === 'fulfilled') setAgents(results[0].value)
      if (results[1].status === 'fulfilled') setHealth(results[1].value)
      if (results[2].status === 'fulfilled') setPrices(results[2].value)
      if (results[3].status === 'fulfilled') setTrades(results[3].value.trades)
      if (results[4].status === 'fulfilled') setPortfolio(results[4].value)
      if (results[5].status === 'fulfilled') setEvents(results[5].value.events)
      if (results[6].status === 'fulfilled') setStreamInfo(results[6].value)
    } catch {
      // Individual errors handled by allSettled
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load + polling
  useEffect(() => {
    refreshAll()
  }, [refreshAll])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(refreshAll, 15000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [autoRefresh, refreshAll])

  const handleAgentSelect = (agent: AgentStatus) => {
    setSelectedAgent(agent)
    setDetailOpen(true)
  }

  const handleChatWithAgent = (agentId: string) => {
    setChatAgentId(agentId)
    setActiveTab('chat')
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('agents.title' as any)}</h1>
          <p className="text-sm text-muted-foreground">{t('agents.subtitle' as any)}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="auto-refresh"
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
            />
            <Label htmlFor="auto-refresh" className="text-sm">
              {t('agents.autoRefresh' as any)}
            </Label>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshAll}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            {t('agents.refresh' as any)}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">{t('agents.tabs.overview' as any)}</TabsTrigger>
          <TabsTrigger value="agents">{t('agents.tabs.agents' as any)}</TabsTrigger>
          <TabsTrigger value="portfolio">{t('agents.tabs.portfolio' as any)}</TabsTrigger>
          <TabsTrigger value="events">{t('agents.tabs.events' as any)}</TabsTrigger>
          <TabsTrigger value="chat">{t('agents.tabs.chat' as any)}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <HealthOverview health={health} prices={prices} loading={loading} />
        </TabsContent>

        <TabsContent value="agents" className="mt-4">
          <AgentCards
            agents={agents}
            loading={loading}
            onSelect={handleAgentSelect}
            onChat={handleChatWithAgent}
          />
        </TabsContent>

        <TabsContent value="portfolio" className="mt-4">
          <GhostPortfolio
            trades={trades}
            portfolio={portfolio}
            loading={loading}
          />
        </TabsContent>

        <TabsContent value="events" className="mt-4">
          <EventStream
            events={events}
            streamInfo={streamInfo}
            loading={loading}
            onSubmitEvent={() => setEventSubmitOpen(true)}
          />
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          <AgentChat agents={agents} initialAgentId={chatAgentId} />
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <AgentDetailDialog
        agent={selectedAgent}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        onChat={handleChatWithAgent}
      />
      <EventSubmitDialog
        open={eventSubmitOpen}
        onClose={() => setEventSubmitOpen(false)}
        onSuccess={refreshAll}
      />
    </div>
  )
}
