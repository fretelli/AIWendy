'use client'

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from 'react-resizable-panels'
import {
  Archive, Bot, Building2, Check, CircleStop, Command, Loader2, Menu, MessageSquarePlus, Plus,
  PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Paperclip, Pin, Search, Send, Settings2, Sparkles, X,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import {
  agentPlatformApi, type AgentApproval, type AgentDefinition, type AgentMemory,
  type AgentMessage, type AgentModelProfile, type AgentRun, type AgentSchedule,
  type AgentSession, type CompanyDossier, type CompanySearchItem, type InteractionMode, type MCPServer, type Usage, type WatchlistItem,
} from '@/lib/api/agent-platform'

type LiveEvent = { id: string; type: string; payload: Record<string, unknown> }
const BUILTIN_TOOLS = ['query_research_reports', 'query_tushare_data', 'run_daily_brief', 'deep_research', 'run_weekly_review', 'record_fundamental_validation', 'record_investment_decision']
const TERMINAL = new Set(['completed', 'failed', 'cancelled'])
const COMMANDS = [
  ['/ask', '直接回答，不调用工具'], ['/research', '执行只读投研'], ['/plan', '只生成研究计划'],
  ['/new', '新建会话'], ['/clear', '开始空白会话'], ['/compact', '压缩当前上下文'], ['/stop', '停止当前任务'],
  ['/settings', '打开安全设置'], ['/agents', '管理 Agent'], ['/model', '配置 BYOK'], ['/mcp', '配置 MCP'],
  ['/schedule', '管理定时任务'], ['/memory', '查看长期记忆'], ['/usage', '查看 Token 和费用'], ['/help', '显示命令帮助'],
]

export default function AgentWorkspacePage() {
  const [loading, setLoading] = useState(true)
  const [sessions, setSessions] = useState<AgentSession[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [events, setEvents] = useState<LiveEvent[]>([])
  const [agents, setAgents] = useState<AgentDefinition[]>([])
  const [models, setModels] = useState<AgentModelProfile[]>([])
  const [approvals, setApprovals] = useState<AgentApproval[]>([])
  const [memories, setMemories] = useState<AgentMemory[]>([])
  const [mcp, setMcp] = useState<MCPServer[]>([])
  const [schedules, setSchedules] = useState<AgentSchedule[]>([])
  const [usage, setUsage] = useState<Usage | null>(null)
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [dossier, setDossier] = useState<CompanyDossier | null>(null)
  const [companyQuery, setCompanyQuery] = useState('')
  const [companyResults, setCompanyResults] = useState<CompanySearchItem[]>([])
  const [attachments, setAttachments] = useState<Array<{ id: string; fileName: string }>>([])
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [sending, setSending] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [selectedAgent, setSelectedAgent] = useState('')
  const [modelForm, setModelForm] = useState({ name: '', provider: 'openai', base_url: '', model: '', api_key: '', context_window: 128000, max_output_tokens: 4096, input_cost_per_million: 0, output_cost_per_million: 0 })
  const [agentForm, setAgentForm] = useState({ name: '', role: 'custom', description: '', system_prompt: 'You are a fundamental investment research agent. Never place trades. Cite evidence and state uncertainty.', model_profile_id: '', tool_names: BUILTIN_TOOLS, memory_enabled: true, max_steps: 12, max_parallel: 3, task_token_budget: 50000, task_cost_budget_usd: 5 })
  const [mcpForm, setMcpForm] = useState({ name: '', url: '', auth_token: '' })
  const [scheduleForm, setScheduleForm] = useState({ name: '', prompt: '', cron: '0 9 * * *', timezone: 'Asia/Shanghai' })
  const bottomRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const rightPanelRef = useRef<ImperativePanelHandle>(null)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [desktopPanels, setDesktopPanels] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches)

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)')
    const sync = () => setDesktopPanels(media.matches)
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  const refreshWorkspace = useCallback(async () => {
    try {
      const [sessionData, agentData, modelData, approvalData, memoryData, mcpData, scheduleData, usageData, watchlistData] = await Promise.all([
        agentPlatformApi.sessions(), agentPlatformApi.agents(), agentPlatformApi.models(), agentPlatformApi.approvals(),
        agentPlatformApi.memories(true), agentPlatformApi.mcpServers(), agentPlatformApi.schedules(), agentPlatformApi.usage(), agentPlatformApi.watchlist(),
      ])
      setSessions(sessionData.items); setAgents(agentData.items); setModels(modelData.items); setApprovals(approvalData.items)
      setMemories(memoryData.items); setMcp(mcpData.items); setSchedules(scheduleData.items); setUsage(usageData)
      setWatchlist(watchlistData.items)
      if (agentData.items[0]) setSelectedAgent(previous => previous || agentData.items[0].id)
      setCurrentId(previous => previous || sessionData.items[0]?.id || null)
      if (!agentData.items.length) setSettingsOpen(true)
    } catch (error) { toast.error(error instanceof Error ? error.message : '工作台加载失败') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (!companyQuery.trim()) return
    const timer = window.setTimeout(() => {
      void agentPlatformApi.companies(companyQuery.trim()).then(data => setCompanyResults(data.items)).catch(() => setCompanyResults([]))
    }, 250)
    return () => window.clearTimeout(timer)
  }, [companyQuery])

  const loadTimeline = useCallback(async (sessionId: string) => {
    try {
      const data = await agentPlatformApi.timeline(sessionId)
      setMessages(data.messages); setRuns(data.runs)
    } catch (error) { toast.error(error instanceof Error ? error.message : '会话加载失败') }
  }, [])

  useEffect(() => { queueMicrotask(() => { void refreshWorkspace() }) }, [refreshWorkspace])
  useEffect(() => { if (currentId) queueMicrotask(() => { void loadTimeline(currentId) }) }, [currentId, loadTimeline])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, events, runs])

  const currentSession = sessions.find(item => item.id === currentId)
  const activeRun = useMemo(() => [...runs].reverse().find(run => !TERMINAL.has(run.status)), [runs])
  const streamedText = useMemo(() => events.filter(event => event.type === 'message.delta').map(event => String(event.payload.delta || '')).join(''), [events])
  useEffect(() => {
    const code = currentSession?.company_code
    if (!code) { queueMicrotask(() => setDossier(null)); return }
    let cancelled = false
    void agentPlatformApi.dossier(code).then(data => { if (!cancelled) setDossier(data) }).catch(() => { if (!cancelled) setDossier(null) })
    return () => { cancelled = true }
  }, [currentSession?.company_code])
  useEffect(() => {
    eventSourceRef.current?.close()
    if (!activeRun) return
    const source = new EventSource(`/api/proxy/v1/agent/runs/${activeRun.id}/events`)
    eventSourceRef.current = source
    const onEvent = (event: MessageEvent) => {
      let payload: Record<string, unknown> = {}
      try { payload = JSON.parse(event.data) } catch { payload = { text: event.data } }
      setEvents(previous => [...previous, { id: event.lastEventId || crypto.randomUUID(), type: event.type, payload }].slice(-100))
      if (event.type === 'run.completed' || event.type === 'run.failed' || event.type === 'run.cancel') {
        source.close(); if (currentId) void loadTimeline(currentId); void refreshWorkspace()
      }
    }
    for (const type of ['run.queued', 'run.planned', 'step.started', 'step.completed', 'step.retry', 'approval.required', 'run.completed', 'run.failed', 'run.cancel', 'run.paused_budget']) source.addEventListener(type, onEvent)
    source.onerror = () => { source.close(); if (currentId) void loadTimeline(currentId) }
    return () => source.close()
  }, [activeRun, currentId, loadTimeline, refreshWorkspace])

  useEffect(() => {
    if (!activeRun || !currentId) return
    const timer = window.setInterval(() => { void loadTimeline(currentId); void refreshWorkspace() }, 2500)
    return () => window.clearInterval(timer)
  }, [activeRun, currentId, loadTimeline, refreshWorkspace])

  const createSession = async (companyCode?: string) => {
    if (!selectedAgent) { setSettingsOpen(true); toast.error('请先配置模型并创建 Agent'); return null }
    const company = watchlist.find(item => item.company_code === companyCode)
    const item = await agentPlatformApi.createSession({ agent_definition_id: selectedAgent,
      title: company ? `${company.company_name}研究` : '新会话', interaction_mode: 'ask', company_code: companyCode || null })
    setSessions(previous => [item, ...previous]); setCurrentId(item.id); setMessages([]); setRuns([]); setEvents([]); setNotice(null)
    return item
  }

  const switchMode = async (mode: InteractionMode) => {
    let sessionId = currentId
    if (!sessionId) sessionId = (await createSession())?.id || null
    if (!sessionId) return false
    const updated = await agentPlatformApi.updateSession(sessionId, { interaction_mode: mode })
    setSessions(previous => previous.map(item => item.id === sessionId ? updated : item))
    setNotice(`已切换到 /${mode} 模式。`)
    return true
  }

  const runCommand = async (raw: string): Promise<string | null> => {
    const trimmed = raw.trim()
    const [rawCommand, ...parts] = trimmed.split(/\s+/)
    const command = rawCommand.toLowerCase()
    if (!command.startsWith('/')) return trimmed
    const remainder = parts.join(' ').trim()
    if (command === '/ask' || command === '/research' || command === '/plan') {
      const changed = await switchMode(command.slice(1) as InteractionMode)
      return changed && remainder ? remainder : null
    }
    if (command === '/new' || command === '/clear') await createSession()
    else if (command === '/compact' && currentId) { await agentPlatformApi.compactSession(currentId); setNotice('上下文已压缩，最近消息和会话摘要会继续参与后续研究。') }
    else if (command === '/stop' && currentId) { await agentPlatformApi.stopSession(currentId); setNotice('已请求停止当前任务。') }
    else if (['/settings', '/agents', '/model', '/mcp', '/schedule', '/memory'].includes(command)) setSettingsOpen(true)
    else if (command === '/usage') setNotice(`今日 Tokens：${(usage?.today.input_tokens || 0) + (usage?.today.output_tokens || 0)} · 成本 $${(usage?.today.cost_usd || 0).toFixed(4)}`)
    else if (command === '/help') setNotice(COMMANDS.map(([name, label]) => `${name}  ${label}`).join('\n'))
    else { setNotice(`未知命令：${command}\n输入 /help 查看可用命令。`) }
    return null
  }

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const rawContent = input.trim()
    if (!rawContent || sending) return
    setInput(''); setNotice(null)
    const content = await runCommand(rawContent)
    if (!content) return
    setSending(true)
    try {
      let sessionId = currentId
      if (!sessionId) sessionId = (await createSession())?.id || null
      if (!sessionId) return
      const result = await agentPlatformApi.sendMessage(sessionId, { content, agent_definition_id: selectedAgent || undefined, attachment_ids: attachments.map(item => item.id) })
      setRuns(previous => [...previous, result.run]); setEvents([]); await loadTimeline(sessionId); await refreshWorkspace()
      setAttachments([])
    } catch (error) { toast.error(error instanceof Error ? error.message : '发送失败'); setInput(rawContent) }
    finally { setSending(false) }
  }

  const resolveApproval = async (item: AgentApproval, decision: 'approved' | 'rejected', scope: 'once' | 'always' = 'once') => {
    await agentPlatformApi.resolveApproval(item.id, decision, scope); toast.success(decision === 'approved' ? '已批准，任务将继续' : '已拒绝')
    await refreshWorkspace(); if (currentId) await loadTimeline(currentId)
  }

  const submitSetting = async (fn: () => Promise<unknown>, message: string) => {
    try { await fn(); toast.success(message); await refreshWorkspace() } catch (error) { toast.error(error instanceof Error ? error.message : '保存失败') }
  }

  const selectCompany = async (companyCode: string) => {
    let sessionId = currentId
    if (!sessionId) sessionId = (await createSession(companyCode))?.id || null
    if (!sessionId) return
    const updated = await agentPlatformApi.updateSession(sessionId, { company_code: companyCode })
    setSessions(previous => previous.map(item => item.id === sessionId ? updated : item))
    const company = watchlist.find(item => item.company_code === companyCode)
    setNotice(company ? `当前研究公司：${company.company_name}（${company.company_code}）` : `当前研究公司：${companyCode}`)
  }

  const addCompany = async (company: CompanySearchItem) => {
    try {
      const item = await agentPlatformApi.addWatchlist(company.ts_code)
      setWatchlist(previous => previous.some(existing => existing.company_code === item.company_code) ? previous : [item, ...previous])
      setCompanyQuery(''); setCompanyResults([]); await selectCompany(item.company_code)
    } catch (error) { toast.error(error instanceof Error ? error.message : '加入自选失败') }
  }

  const removeCompany = async (companyCode: string) => {
    await agentPlatformApi.removeWatchlist(companyCode)
    setWatchlist(previous => previous.filter(item => item.company_code !== companyCode))
  }

  const filteredSessions = sessions.filter(item => item.title.toLowerCase().includes(search.toLowerCase()))
  if (loading) return <div className="flex h-full items-center justify-center"><Loader2 className="h-7 w-7 animate-spin" /></div>
  const pinCurrent = async () => { if (currentSession) { await agentPlatformApi.updateSession(currentSession.id, { is_pinned: !currentSession.is_pinned }); await refreshWorkspace() } }
  const archiveCurrent = async () => { if (currentId) { await agentPlatformApi.updateSession(currentId, { archived: true }); setCurrentId(null); await refreshWorkspace() } }

  const sidebar = <div className="flex h-full flex-col bg-muted/20">
    <div className="flex items-center gap-2 border-b p-3"><Button className="flex-1 justify-start" onClick={() => void createSession()}><MessageSquarePlus className="mr-2 h-4 w-4" />新会话</Button><Button size="icon" variant="outline" onClick={() => setSettingsOpen(true)}><Settings2 className="h-4 w-4" /></Button></div>
    <div className="border-b p-3"><div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground"><Building2 className="h-3.5 w-3.5" />我的自选</div><div className="relative"><Input value={companyQuery} onChange={e => { setCompanyQuery(e.target.value); if (!e.target.value) setCompanyResults([]) }} placeholder="搜索A股代码或名称" className="h-8 text-xs" />{companyResults.length > 0 && <div className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-md border bg-popover p-1 shadow-lg">{companyResults.map(company => <button key={company.ts_code} className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-accent" onClick={() => void addCompany(company)}><Plus className="h-3 w-3" /><span className="truncate">{company.name}</span><span className="ml-auto text-muted-foreground">{company.ts_code}</span></button>)}</div>}</div><div className="mt-2 space-y-1">{watchlist.map(company => <div key={company.company_code} className={`group flex items-center rounded-md ${currentSession?.company_code === company.company_code ? 'bg-accent' : 'hover:bg-accent/60'}`}><button className="min-w-0 flex-1 px-2 py-1.5 text-left text-xs" onClick={() => void selectCompany(company.company_code)}><span className="block truncate font-medium">{company.company_name}</span><span className="text-[10px] text-muted-foreground">{company.company_code}{company.industry ? ` · ${company.industry}` : ''}</span></button><Button className="mr-1 h-6 w-6 opacity-0 group-hover:opacity-100" size="icon" variant="ghost" onClick={() => void removeCompany(company.company_code)}><X className="h-3 w-3" /></Button></div>)}</div></div>
    <div className="p-3"><div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" /><Input className="pl-8" placeholder="搜索会话" value={search} onChange={e => setSearch(e.target.value)} /></div></div>
    <ScrollArea className="flex-1 px-2"><div className="space-y-1 pb-4">{filteredSessions.map(item => <button key={item.id} onClick={() => { setCurrentId(item.id); setSidebarOpen(false); setEvents([]) }} className={`group flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm ${currentId === item.id ? 'bg-accent' : 'hover:bg-accent/60'}`}><MessageSquarePlus className="mt-0.5 h-4 w-4 shrink-0" /><span className="min-w-0 flex-1"><span className="block truncate font-medium">{item.title}</span><span className="block text-xs text-muted-foreground">{new Date(item.last_message_at || item.created_at).toLocaleString()}</span></span>{item.is_pinned && <Pin className="h-3 w-3" />}</button>)}</div></ScrollArea>
    <div className="border-t p-3 text-xs text-muted-foreground"><div className="flex justify-between"><span>上下文</span><span>{sessions.find(s => s.id === currentId)?.context_tokens || 0} tokens</span></div><div className="mt-1 flex justify-between"><span>今日成本</span><span>${(usage?.today.cost_usd || 0).toFixed(4)}</span></div></div>
  </div>

  const mainPanel = <main className="flex h-full min-w-0 flex-1 flex-col">
      <header className="flex h-14 items-center gap-2 border-b px-3"><Button className="xl:hidden" size="icon" variant="ghost" onClick={() => setSidebarOpen(true)}><Menu className="h-5 w-5" /></Button><Button className="hidden xl:inline-flex" size="icon" variant="ghost" onClick={() => leftPanelRef.current?.isCollapsed() ? leftPanelRef.current.expand() : leftPanelRef.current?.collapse()}>{leftCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}</Button><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><div className="truncate font-medium">{currentSession?.title || 'KeelTrader Agent'}</div>{currentSession?.company_code && <Badge variant="outline" className="font-mono text-[10px]">{currentSession.company_code}</Badge>}</div><div className="text-xs text-muted-foreground">只读投研 · 不执行交易</div></div><select className="max-w-48 rounded-md border bg-background px-2 py-1 text-xs" value={selectedAgent} onChange={e => setSelectedAgent(e.target.value)}><option value="">选择 Agent</option>{agents.map(agent => <option value={agent.id} key={agent.id}>{agent.name}</option>)}</select><Button size="icon" variant="ghost" onClick={() => desktopPanels ? (rightPanelRef.current?.isCollapsed() ? rightPanelRef.current.expand() : rightPanelRef.current?.collapse()) : setContextOpen(true)}>{rightCollapsed ? <PanelRightOpen className="h-5 w-5" /> : <PanelRightClose className="h-5 w-5" />}</Button></header>

      <ScrollArea className="flex-1"><div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
        {!messages.length && !activeRun && <div className="flex min-h-[45vh] flex-col items-center justify-center text-center"><div className="mb-4 rounded-2xl bg-primary/10 p-4"><Sparkles className="h-8 w-8 text-primary" /></div><h1 className="text-2xl font-semibold">今天想研究什么？</h1><div className="mt-5 grid gap-2 sm:grid-cols-2">{['解释这家公司的商业模式', '梳理一个投资假设', '列出关键风险和证伪条件', '比较两个标的的核心差异'].map(text => <Button key={text} variant="outline" onClick={() => setInput(text)}>{text}</Button>)}</div></div>}
        {messages.map(message => <MessageBubble key={message.id} message={message} />)}
        {streamedText && <div className="rounded-xl border bg-card p-4"><ReactMarkdown>{streamedText}</ReactMarkdown></div>}{events.filter(event => event.type !== 'message.delta').map(event => <EventCard key={`${event.id}-${event.type}`} event={event} />)}
        {activeRun && <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /><span>{statusLabel(activeRun.status)} · 步骤 {activeRun.current_step} · {activeRun.tokens_used} tokens</span></div>}
        {approvals.filter(item => !currentId || runs.some(run => run.id === (item as AgentApproval & { run_id?: string }).run_id)).map(item => <ApprovalCard key={item.id} item={item} onResolve={resolveApproval} />)}
        {notice && <Card className="border-primary/30"><CardContent className="whitespace-pre-wrap p-4 font-mono text-sm">{notice}</CardContent></Card>}
        <div ref={bottomRef} />
      </div></ScrollArea>

      <div className="border-t bg-background p-3"><div className="relative mx-auto max-w-3xl">{input.startsWith('/') && <div className="absolute bottom-full z-20 mb-2 max-h-64 w-full overflow-y-auto rounded-lg border bg-popover p-1 shadow-lg">{COMMANDS.filter(([name]) => name.startsWith(input.split(/\s/, 1)[0])).map(([name, label]) => <button type="button" key={name} onClick={() => setInput(`${name} `)} className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm hover:bg-accent"><span className="font-mono">{name}</span><span className="text-xs text-muted-foreground">{label}</span></button>)}</div>}{attachments.length > 0 && <div className="mb-2 flex flex-wrap gap-1">{attachments.map(file => <Badge key={file.id} variant="outline">{file.fileName}</Badge>)}</div>}<form onSubmit={send} className="rounded-xl border bg-muted/20 shadow-sm focus-within:ring-1 focus-within:ring-ring"><Textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send() } if (e.key === 'Escape' && activeRun && currentId) void agentPlatformApi.stopSession(currentId) }} placeholder="输入问题，或输入 / 查看命令…" className="min-h-20 resize-none border-0 bg-transparent focus-visible:ring-0" /><div className="flex items-center gap-2 border-t px-2 py-2"><label className="inline-flex cursor-pointer items-center rounded p-2 hover:bg-accent"><Paperclip className="h-4 w-4" /><input className="hidden" type="file" accept=".pdf,.docx,.xlsx,.csv,.txt,.md,image/*" onChange={e => { const file = e.target.files?.[0]; if (file) void agentPlatformApi.uploadAttachment(file).then(uploaded => setAttachments(items => [...items, uploaded])).catch(error => toast.error(error instanceof Error ? error.message : '附件上传失败')); e.currentTarget.value = '' }} /></label><Badge variant="secondary" className="font-mono">/{currentSession?.interaction_mode || 'ask'}</Badge>{input.startsWith('/') && <div className="text-xs text-muted-foreground"><Command className="mr-1 inline h-3 w-3" />命令模式</div>}<div className="flex-1" />{activeRun && <Button type="button" size="sm" variant="outline" onClick={() => currentId && void agentPlatformApi.stopSession(currentId)}><CircleStop className="mr-1 h-4 w-4" />停止</Button>}<Button size="icon" disabled={!input.trim() || sending || !selectedAgent}>{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button></div></form></div><div className="mx-auto mt-1 flex max-w-3xl justify-between px-1 text-[11px] text-muted-foreground"><span>Enter 发送 · Shift+Enter 换行 · 可附 PDF/DOCX/XLSX/图片</span><span>/{currentSession?.interaction_mode || 'ask'}</span></div></div>
    </main>

  return <div className="flex h-full min-h-0 overflow-hidden bg-background">
    <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}><SheetContent side="left" className="w-80 p-0"><SheetHeader className="sr-only"><SheetTitle>会话</SheetTitle></SheetHeader>{sidebar}</SheetContent></Sheet>
    {desktopPanels ? <PanelGroup direction="horizontal" autoSaveId="keeltrader-agent-workspace" className="h-full w-full">
      <Panel ref={leftPanelRef} defaultSize={18} minSize={14} maxSize={30} collapsible collapsedSize={0} onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}><aside className="h-full border-r">{sidebar}</aside></Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/40 outline-none hover:bg-primary/40 focus-visible:bg-primary"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel minSize={40}>{mainPanel}</Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/40 outline-none hover:bg-primary/40 focus-visible:bg-primary"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel ref={rightPanelRef} defaultSize={24} minSize={18} maxSize={35} collapsible collapsedSize={0} onCollapse={() => setRightCollapsed(true)} onExpand={() => setRightCollapsed(false)}><aside className="h-full overflow-y-auto border-l bg-muted/10"><ContextContent session={currentSession} dossier={dossier} runs={runs} events={events} usage={usage} onPin={pinCurrent} onArchive={archiveCurrent} /></aside></Panel>
    </PanelGroup> : mainPanel}
    <ContextSheet open={contextOpen} onOpenChange={setContextOpen} session={currentSession} dossier={dossier} runs={runs} events={events} usage={usage} onPin={pinCurrent} onArchive={archiveCurrent} />
    <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} models={models} agents={agents} memories={memories} mcp={mcp} schedules={schedules} usage={usage} selectedAgent={selectedAgent} setSelectedAgent={setSelectedAgent} modelForm={modelForm} setModelForm={setModelForm} agentForm={agentForm} setAgentForm={setAgentForm} mcpForm={mcpForm} setMcpForm={setMcpForm} scheduleForm={scheduleForm} setScheduleForm={setScheduleForm} submit={submitSetting} />
  </div>
}

function MessageBubble({ message }: { message: AgentMessage }) {
  const user = message.role === 'user'
  return <div className={`flex gap-3 ${user ? 'justify-end' : 'justify-start'}`}>{!user && <div className="mt-1 rounded-full bg-primary/10 p-2"><Bot className="h-4 w-4 text-primary" /></div>}<div className={`max-w-[88%] rounded-2xl px-4 py-3 ${user ? 'bg-primary text-primary-foreground' : 'bg-muted/60'}`}>{user ? <p className="whitespace-pre-wrap text-sm">{message.content}</p> : <div className="prose prose-sm max-w-none dark:prose-invert"><ReactMarkdown>{message.content}</ReactMarkdown></div>}<div className={`mt-2 text-[10px] ${user ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>{new Date(message.created_at).toLocaleTimeString()}</div></div></div>
}

function EventCard({ event }: { event: LiveEvent }) {
  if (event.type === 'step.started') return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" />{String(event.payload.role || 'Agent')} {event.payload.tool ? `正在调用 ${event.payload.tool}` : '正在分析'}</div>
  if (event.type === 'step.completed') return <details className="rounded-lg border bg-muted/20 px-3 py-2 text-sm"><summary className="cursor-pointer font-medium"><Check className="mr-2 inline h-4 w-4 text-emerald-500" />{String(event.payload.role || '步骤')}完成{event.payload.tool ? ` · ${event.payload.tool}` : ''}</summary><pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">{JSON.stringify(event.payload.output, null, 2)}</pre></details>
  if (event.type === 'step.retry') return <div className="text-sm text-amber-600">步骤失败，正在自动重试…</div>
  if (event.type === 'run.failed') return <Card className="border-destructive/50"><CardContent className="p-3 text-sm text-destructive">任务失败：{String(event.payload.reason || 'unknown error')}</CardContent></Card>
  return null
}

function ApprovalCard({ item, onResolve }: { item: AgentApproval; onResolve: (item: AgentApproval, decision: 'approved' | 'rejected', scope?: 'once' | 'always') => Promise<void> }) {
  return <Card className="border-amber-500/50"><CardHeader className="pb-2"><CardTitle className="text-base">需要你的批准</CardTitle></CardHeader><CardContent className="space-y-3"><pre className="max-h-60 overflow-auto rounded bg-muted p-3 text-xs">{JSON.stringify(item.preview, null, 2)}</pre><div className="flex gap-2"><Button size="sm" onClick={() => void onResolve(item, 'approved', 'once')}><Check className="mr-1 h-4 w-4" />仅本次</Button>{item.kind === 'mcp_tool' && <Button size="sm" variant="secondary" onClick={() => void onResolve(item, 'approved', 'always')}>永久允许</Button>}<Button size="sm" variant="destructive" onClick={() => void onResolve(item, 'rejected')}><X className="mr-1 h-4 w-4" />拒绝</Button></div></CardContent></Card>
}

function ContextSheet({ open, onOpenChange, session, dossier, runs, events, usage, onPin, onArchive }: { open: boolean; onOpenChange: (v: boolean) => void; session?: AgentSession; dossier: CompanyDossier | null; runs: AgentRun[]; events: LiveEvent[]; usage: Usage | null; onPin: () => Promise<void>; onArchive: () => Promise<void> }) {
  return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent className="w-[380px] overflow-y-auto"><SheetHeader><SheetTitle>公司档案</SheetTitle></SheetHeader><ContextContent session={session} dossier={dossier} runs={runs} events={events} usage={usage} onPin={onPin} onArchive={onArchive} /></SheetContent></Sheet>
}

function ContextContent({ session, dossier, runs, events, usage, onPin, onArchive }: { session?: AgentSession; dossier: CompanyDossier | null; runs: AgentRun[]; events: LiveEvent[]; usage: Usage | null; onPin: () => Promise<void>; onArchive: () => Promise<void> }) {
  const latest = runs.at(-1)
  const metrics = dossier?.snapshot?.metrics || {}
  return <div className="space-y-5 p-5"><div><div className="text-xs text-muted-foreground">当前公司</div><div className="truncate font-medium">{String(dossier?.snapshot?.company?.name || session?.title || '-')}</div><div className="mt-2 flex gap-2"><Badge variant="outline" className="font-mono">{session?.company_code || '未绑定'}</Badge>{dossier?.dossier && <Badge variant={dossier.dossier.stale ? 'destructive' : 'secondary'}>v{dossier.dossier.current_version} · {dossier.dossier.stale ? '待刷新' : '最新'}</Badge>}</div></div>{session?.company_code && <Button className="w-full" variant="outline" onClick={() => void agentPlatformApi.refreshDossier(session.company_code!).then(() => toast.success('档案刷新已入队'))}>刷新基本面档案</Button>}<div className="grid grid-cols-2 gap-2"><Metric label="营收增速" value={formatMetric(metrics.revenue_growth_pct, '%')} /><Metric label="净利增速" value={formatMetric(metrics.net_profit_growth_pct, '%')} /><Metric label="ROE" value={formatMetric(metrics.roe_pct, '%')} /><Metric label="现金含量" value={formatMetric(metrics.cfo_to_profit)} /></div>{dossier?.snapshot?.evidence_shortage && <p className="rounded border border-amber-500/40 p-2 text-xs text-amber-700">{dossier.snapshot.evidence_shortage}</p>}{Boolean(dossier?.snapshot?.anomaly_flags?.length) && <div><div className="mb-2 text-sm font-medium">异常信号</div>{dossier!.snapshot!.anomaly_flags.map(flag => <div key={flag} className="mb-1 rounded bg-destructive/10 p-2 text-xs">{flag}</div>)}</div>}<div><div className="mb-2 text-sm font-medium">证据与版本</div><div className="text-xs text-muted-foreground">{dossier?.evidence.length || 0} 条证据 · {dossier?.versions.length || 0} 个不可变版本</div></div><div className="grid grid-cols-2 gap-2"><Metric label="今日费用" value={`$${(usage?.today.cost_usd || 0).toFixed(4)}`} /><Metric label="任务状态" value={latest?.status || '-'} /></div><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => void onPin()}><Pin className="mr-1 h-4 w-4" />{session?.is_pinned ? '取消置顶' : '置顶'}</Button><Button variant="outline" onClick={() => void onArchive()}><Archive className="mr-1 h-4 w-4" />归档</Button></div></div>
}

function formatMetric(value: unknown, suffix = '') { return typeof value === 'number' ? `${value.toFixed(2)}${suffix}` : '-' }

type SettingsProps = {
  open: boolean; onOpenChange: (v: boolean) => void; models: AgentModelProfile[]; agents: AgentDefinition[]; memories: AgentMemory[]; mcp: MCPServer[]; schedules: AgentSchedule[]; usage: Usage | null; selectedAgent: string; setSelectedAgent: (v: string) => void
  modelForm: Record<string, string | number>; setModelForm: (v: never) => void; agentForm: Record<string, unknown>; setAgentForm: (v: never) => void; mcpForm: Record<string, string>; setMcpForm: (v: never) => void; scheduleForm: Record<string, string>; setScheduleForm: (v: never) => void; submit: (fn: () => Promise<unknown>, message: string) => Promise<void>
}

function SettingsSheet(props: SettingsProps) {
  const { open, onOpenChange, models, agents, memories, mcp, schedules, usage, selectedAgent, setSelectedAgent, modelForm, setModelForm, agentForm, setAgentForm, mcpForm, setMcpForm, scheduleForm, setScheduleForm, submit } = props
  const [section, setSection] = useState('setup')
  return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent className="w-full overflow-y-auto sm:max-w-xl"><SheetHeader><SheetTitle>Agent 设置</SheetTitle></SheetHeader><div className="mt-4 flex flex-wrap gap-2">{['setup', 'agents', 'mcp', 'memory', 'schedule', 'usage'].map(item => <Button key={item} size="sm" variant={section === item ? 'default' : 'outline'} onClick={() => setSection(item)}>{item}</Button>)}</div><div className="mt-5 space-y-4">
    {section === 'setup' && <Card><CardHeader><CardTitle className="text-base">安全配置 BYOK</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="配置名称" value={String(modelForm.name)} onChange={e => setModelForm({ ...modelForm, name: e.target.value } as never)} /><select className="rounded border bg-background p-2" value={String(modelForm.provider)} onChange={e => setModelForm({ ...modelForm, provider: e.target.value } as never)}><option value="openai">OpenAI-compatible</option><option value="anthropic">Anthropic</option></select><Input placeholder="Base URL（官方可留空）" value={String(modelForm.base_url)} onChange={e => setModelForm({ ...modelForm, base_url: e.target.value } as never)} /><Input placeholder="Model" value={String(modelForm.model)} onChange={e => setModelForm({ ...modelForm, model: e.target.value } as never)} /><Input type="password" autoComplete="off" placeholder="API Key（不会进入聊天记录）" value={String(modelForm.api_key)} onChange={e => setModelForm({ ...modelForm, api_key: e.target.value } as never)} /><Button onClick={() => void submit(() => agentPlatformApi.createModel({ ...modelForm, base_url: modelForm.base_url || null }), '模型凭证已加密保存')}>保存模型</Button><div className="space-y-1">{models.map(item => <div className="rounded border p-2 text-sm" key={item.id}>{item.name} · {item.model}</div>)}</div></CardContent></Card>}
    {section === 'agents' && <Card><CardHeader><CardTitle className="text-base">Agent</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="名称" value={String(agentForm.name || '')} onChange={e => setAgentForm({ ...agentForm, name: e.target.value } as never)} /><Input placeholder="描述" value={String(agentForm.description || '')} onChange={e => setAgentForm({ ...agentForm, description: e.target.value } as never)} /><select className="rounded border bg-background p-2" value={String(agentForm.model_profile_id || '')} onChange={e => setAgentForm({ ...agentForm, model_profile_id: e.target.value } as never)}><option value="">选择模型</option>{models.map(item => <option key={item.id} value={item.id}>{item.name} · {item.model}</option>)}</select><Textarea value={String(agentForm.system_prompt || '')} onChange={e => setAgentForm({ ...agentForm, system_prompt: e.target.value } as never)} /><Button onClick={() => void submit(() => agentPlatformApi.createAgent(agentForm), 'Agent 已创建')}>创建 Agent</Button>{agents.map(item => <button className={`rounded border p-3 text-left ${selectedAgent === item.id ? 'border-primary' : ''}`} key={item.id} onClick={() => setSelectedAgent(item.id)}><div className="font-medium">{item.name}</div><div className="text-xs text-muted-foreground">{item.role} · {item.tool_names.length} tools</div></button>)}</CardContent></Card>}
    {section === 'mcp' && <Card><CardHeader><CardTitle className="text-base">公网 HTTPS MCP</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="名称" value={mcpForm.name} onChange={e => setMcpForm({ ...mcpForm, name: e.target.value } as never)} /><Input placeholder="https://..." value={mcpForm.url} onChange={e => setMcpForm({ ...mcpForm, url: e.target.value } as never)} /><Input type="password" autoComplete="off" placeholder="Bearer Token（不会进入聊天记录）" value={mcpForm.auth_token} onChange={e => setMcpForm({ ...mcpForm, auth_token: e.target.value } as never)} /><Button onClick={() => void submit(() => agentPlatformApi.createMcp({ ...mcpForm, auth_token: mcpForm.auth_token || null }), 'MCP 已连接')}>发现工具</Button>{mcp.map(item => <div className="rounded border p-3 text-sm" key={item.id}>{item.name} <Badge>{item.status}</Badge><div className="text-xs text-muted-foreground">{item.url}</div></div>)}</CardContent></Card>}
    {section === 'memory' && <div className="space-y-2">{memories.map(item => <Card key={item.id}><CardContent className="p-3"><div className="font-medium">{item.key}</div><pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(item.value, null, 2)}</pre></CardContent></Card>)}</div>}
    {section === 'schedule' && <Card><CardHeader><CardTitle className="text-base">定时研究</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="计划名称" value={scheduleForm.name} onChange={e => setScheduleForm({ ...scheduleForm, name: e.target.value } as never)} /><Textarea placeholder="研究任务" value={scheduleForm.prompt} onChange={e => setScheduleForm({ ...scheduleForm, prompt: e.target.value } as never)} /><Input value={scheduleForm.cron} onChange={e => setScheduleForm({ ...scheduleForm, cron: e.target.value } as never)} /><Button disabled={!selectedAgent} onClick={() => void submit(() => agentPlatformApi.createSchedule({ ...scheduleForm, agent_definition_id: selectedAgent }), '定时研究已创建')}>创建计划</Button>{schedules.map(item => <div className="rounded border p-3 text-sm" key={item.id}>{item.name} · {item.cron}</div>)}</CardContent></Card>}
    {section === 'usage' && <div className="grid grid-cols-2 gap-3"><Metric label="今日输入" value={usage?.today.input_tokens || 0} /><Metric label="今日输出" value={usage?.today.output_tokens || 0} /><Metric label="今日成本" value={`$${(usage?.today.cost_usd || 0).toFixed(4)}`} /><Metric label="Agent 数" value={agents.length} /></div>}
  </div></SheetContent></Sheet>
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-lg border p-3"><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 font-semibold">{value}</div></div> }
function statusLabel(status: string) { return ({ queued: '等待 Worker', planning: '规划研究步骤', running: '执行研究', waiting_approval: '等待审批', paused_budget: '预算暂停', paused: '已暂停' } as Record<string, string>)[status] || status }
