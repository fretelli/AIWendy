'use client'

import Link from 'next/link'
import { FormEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from 'react-resizable-panels'
import {
  Archive, Bot, Building2, Check, CircleStop, Command, Loader2, Menu, MessageSquarePlus, Plus,
  Compass, Database, LogOut, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Paperclip, Pin,
  Pencil, Radar, Search, Send, Settings2, ShieldCheck, Trash2, Waves, X,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import { LanguageSwitcher } from '@/lib/i18n/provider'
import { useAuth } from '@/lib/auth-context'
import {
  agentPlatformApi, type AgentApproval, type AgentDefinition, type AgentMemory,
  type AgentMessage, type AgentModelProfile, type AgentRun, type AgentSchedule,
  type AgentSession, type CompanyDossier, type CompanySearchItem, type InteractionMode, type MCPServer, type Usage, type WatchlistItem,
} from '@/lib/api/agent-platform'
import { apiFetch } from '@/lib/api/client'

type LiveEvent = { id: string; type: string; payload: Record<string, unknown> }
const TERMINAL = new Set(['completed', 'failed', 'cancelled'])
const COMMANDS = [
  ['/ask', '直接回答，不调用工具'], ['/research', '执行只读投研'], ['/plan', '只生成研究计划'],
  ['/new', '新建会话'], ['/clear', '开始空白会话'], ['/compact', '压缩当前上下文'], ['/stop', '停止当前任务'],
  ['/settings', '打开安全设置'], ['/model', '配置 BYOK'], ['/mcp', '配置 MCP'],
  ['/schedule', '管理定时任务'], ['/memory', '查看长期记忆'], ['/usage', '查看 Token 和费用'], ['/help', '显示命令帮助'],
]

export default function AgentWorkspacePage() {
  const { logout } = useAuth()
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
  const [contextSnapshots, setContextSnapshots] = useState<Array<{ id: string; label: string }>>([])
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [sending, setSending] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [renameSession, setRenameSession] = useState<AgentSession | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [modelForm, setModelForm] = useState({ name: '', provider: 'openai', base_url: '', model: '', api_key: '', context_window: 128000, max_output_tokens: 4096, input_cost_per_million: 0, output_cost_per_million: 0 })
  const [mcpForm, setMcpForm] = useState({ name: '', url: '', auth_token: '' })
  const [scheduleForm, setScheduleForm] = useState({ name: '', prompt: '', cron: '0 9 * * *', timezone: 'Asia/Shanghai' })
  const bottomRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const rightPanelRef = useRef<ImperativePanelHandle>(null)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [desktopPanels, setDesktopPanels] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches)
  const defaultAgentId = agents[0]?.id || ''

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)')
    const sync = () => setDesktopPanels(media.matches)
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  useEffect(() => {
    const query = new URLSearchParams(window.location.search)
    const id = query.get('context_snapshot'), label = query.get('context_label')
    if (!id) return
    queueMicrotask(() => {
      setContextSnapshots(items => items.some(item => item.id === id) ? items : [...items, { id, label: label || '市场证据' }])
      setNotice(`已暂存市场上下文：${label || '市场证据'}。只会在你下次发送消息时带入。`)
    })
    window.history.replaceState({}, '', window.location.pathname)
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
    for (const type of ['run.queued', 'run.planned', 'run.retry', 'message.delta', 'step.started', 'step.completed', 'step.retry', 'approval.required', 'run.completed', 'run.failed', 'run.cancel', 'run.paused_budget']) source.addEventListener(type, onEvent)
    source.onerror = () => { source.close(); if (currentId) void loadTimeline(currentId) }
    return () => source.close()
  }, [activeRun, currentId, loadTimeline, refreshWorkspace])

  useEffect(() => {
    if (!activeRun || !currentId) return
    const timer = window.setInterval(() => { void loadTimeline(currentId) }, 15000)
    return () => window.clearInterval(timer)
  }, [activeRun, currentId, loadTimeline])

  const createSession = async (companyCode?: string) => {
    if (!defaultAgentId) { setSettingsOpen(true); toast.error('请先配置 KeelTrader 模型'); return null }
    const company = watchlist.find(item => item.company_code === companyCode)
    const item = await agentPlatformApi.createSession({ agent_definition_id: defaultAgentId,
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
    else if (['/settings', '/model', '/mcp', '/schedule', '/memory'].includes(command)) setSettingsOpen(true)
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
      const result = await agentPlatformApi.sendMessage(sessionId, { content, client_request_id: crypto.randomUUID(), agent_definition_id: defaultAgentId || undefined, attachment_ids: attachments.map(item => item.id), context_snapshot_ids: contextSnapshots.map(item => item.id) })
      setRuns(previous => [...previous, result.run]); setEvents([]); await loadTimeline(sessionId); await refreshWorkspace()
      setAttachments([])
      setContextSnapshots([])
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
  const deleteCurrent = async () => {
    if (!currentId) return
    try {
      await agentPlatformApi.deleteSession(currentId)
      setDeleteConfirmOpen(false); setCurrentId(null); setMessages([]); setRuns([]); setEvents([])
      toast.success('研究会话已永久删除')
      await refreshWorkspace()
    } catch (error) { toast.error(error instanceof Error ? error.message : '删除会话失败') }
  }

  const openRename = (session: AgentSession) => {
    setRenameSession(session)
    setRenameTitle(session.title)
  }

  const saveRename = async (event?: FormEvent) => {
    event?.preventDefault()
    if (!renameSession || renaming) return
    const title = renameTitle.trim()
    if (!title) { toast.error('会话名称不能为空'); return }
    if (title.length > 200) { toast.error('会话名称不能超过 200 个字符'); return }
    if (title === renameSession.title) { setRenameSession(null); return }
    setRenaming(true)
    try {
      const updated = await agentPlatformApi.updateSession(renameSession.id, { title })
      setSessions(previous => previous.map(item => item.id === updated.id ? updated : item))
      setRenameSession(null)
      toast.success('会话名称已更新')
    } catch (error) { toast.error(error instanceof Error ? error.message : '会话重命名失败') }
    finally { setRenaming(false) }
  }

  const sidebar = <div className="chart-surface flex h-full flex-col">
    <div className="flex items-center gap-2 border-b border-border/70 p-3"><Button className="flex-1 justify-start shadow-sm" onClick={() => void createSession()}><MessageSquarePlus className="mr-2 h-4 w-4" />新建研究</Button><Button size="icon" variant="outline" aria-label="打开设置" onClick={() => setSettingsOpen(true)}><Settings2 className="h-4 w-4" /></Button></div>
    <div className="border-b border-border/70 p-3"><div className="mb-2 flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground"><span className="flex items-center gap-2"><Building2 className="h-3.5 w-3.5" />我的自选</span><span className="font-data tracking-normal">{watchlist.length}</span></div><div className="relative"><Input value={companyQuery} onChange={e => { setCompanyQuery(e.target.value); if (!e.target.value) setCompanyResults([]) }} placeholder="搜索 A 股代码或名称" className="h-9 bg-card/90 text-xs" />{companyResults.length > 0 && <div className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border bg-popover p-1 shadow-xl">{companyResults.map(company => <button key={company.ts_code} className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs hover:bg-secondary" onClick={() => void addCompany(company)}><Plus className="h-3 w-3 text-[hsl(var(--copper-foreground))]" /><span className="truncate">{company.name}</span><span className="ml-auto font-data text-muted-foreground">{company.ts_code}</span></button>)}</div>}</div><div className="mt-2 space-y-1">{watchlist.map(company => <div key={company.company_code} className={`group flex items-center rounded-lg border border-transparent transition-colors ${currentSession?.company_code === company.company_code ? 'border-[hsl(var(--accent)/.35)] bg-[hsl(var(--accent)/.09)]' : 'hover:bg-secondary/70'}`}><button className="min-w-0 flex-1 px-2.5 py-2 text-left text-xs" onClick={() => void selectCompany(company.company_code)}><span className="block truncate font-semibold">{company.company_name}</span><span className="font-data text-[10px] text-muted-foreground">{company.company_code}{company.industry ? ` · ${company.industry}` : ''}</span></button><Button className="mr-1 h-7 w-7 opacity-0 focus-visible:opacity-100 group-hover:opacity-100" aria-label={`移除 ${company.company_name}`} size="icon" variant="ghost" onClick={() => void removeCompany(company.company_code)}><X className="h-3 w-3" /></Button></div>)}</div></div>
    <div className="p-3"><div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">研究记录</div><div className="relative"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><Input className="h-9 bg-card/80 pl-8 text-xs" placeholder="搜索研究记录" value={search} onChange={e => setSearch(e.target.value)} /></div></div>
    <ScrollArea className="flex-1 px-2"><div className="space-y-1 pb-4">{filteredSessions.map(item => <div key={item.id} className={`group flex items-start rounded-lg transition-colors ${currentId === item.id ? 'bg-secondary shadow-sm' : 'hover:bg-secondary/60'}`}><button onClick={() => { setCurrentId(item.id); setSidebarOpen(false); setEvents([]) }} className="flex min-w-0 flex-1 items-start gap-2 px-3 py-2.5 text-left text-sm"><Compass className={`mt-0.5 h-4 w-4 shrink-0 ${currentId === item.id ? 'text-[hsl(var(--copper-foreground))]' : 'text-muted-foreground'}`} /><span className="min-w-0 flex-1"><span className="block truncate font-semibold">{item.title}</span><span className="font-data block text-[10px] text-muted-foreground">{new Date(item.last_message_at || item.created_at).toLocaleString()}</span></span>{item.is_pinned && <Pin className="h-3 w-3 shrink-0 text-[hsl(var(--copper-foreground))]" />}</button><Button size="icon" variant="ghost" className="mr-1 mt-1 h-8 w-8 shrink-0 opacity-70 xl:opacity-0 xl:group-hover:opacity-100 focus-visible:opacity-100" aria-label={`重命名 ${item.title}`} onClick={() => openRename(item)}><Pencil className="h-3.5 w-3.5" /></Button></div>)}</div></ScrollArea>
    <div className="border-t border-border/70 bg-card/55 p-3 text-[11px] text-muted-foreground"><div className="flex justify-between"><span>上下文</span><span className="font-data">{sessions.find(s => s.id === currentId)?.context_tokens || 0} tokens</span></div><div className="mt-1.5 flex justify-between"><span>今日模型费用</span><span className="font-data">${(usage?.today.cost_usd || 0).toFixed(4)}</span></div></div>
  </div>

  const mainPanel = <main className="flex h-full min-w-0 flex-1 flex-col bg-background/80 backdrop-blur-[2px]">
      <header className="research-bearing flex min-h-16 shrink-0 items-center gap-2 border-b bg-card/92 px-3 shadow-[0_1px_0_hsl(var(--border)/.45)]"><Button className="xl:hidden" size="icon" variant="ghost" aria-label="打开自选与会话" onClick={() => setSidebarOpen(true)}><Menu className="h-5 w-5" /></Button><Button className="hidden xl:inline-flex" size="icon" variant="ghost" aria-label="折叠左栏" onClick={() => leftPanelRef.current?.isCollapsed() ? leftPanelRef.current.expand() : leftPanelRef.current?.collapse()}>{leftCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}</Button><div className="hidden border-r pr-4 md:block"><KeelMark /></div><ResearchBearing session={currentSession} dossier={dossier} run={activeRun} onRename={() => currentSession && openRename(currentSession)} /><Badge variant="outline" className="hidden border-[hsl(var(--copper)/.35)] bg-card font-data text-[10px] text-[hsl(var(--copper-foreground))] lg:inline-flex">KeelTrader</Badge><Button asChild size="sm" variant="outline"><Link href="/agent/holders"><Radar className="mr-1.5 h-4 w-4" />股东雷达</Link></Button><ThemeMenu /><LanguageSwitcher className="hidden 2xl:block" /><Button size="icon" variant="ghost" aria-label="公司档案" onClick={() => desktopPanels ? (rightPanelRef.current?.isCollapsed() ? rightPanelRef.current.expand() : rightPanelRef.current?.collapse()) : setContextOpen(true)}>{rightCollapsed ? <PanelRightOpen className="h-5 w-5" /> : <PanelRightClose className="h-5 w-5" />}</Button><Button size="icon" variant="ghost" aria-label="退出登录" onClick={() => void logout()}><LogOut className="h-4 w-4" /></Button></header>

      <ScrollArea className="flex-1"><div className="mx-auto max-w-[840px] space-y-6 px-4 py-7 md:px-7">
        {!messages.length && !activeRun && <ResearchEmptyState companyName={watchlist.find(item => item.company_code === currentSession?.company_code)?.company_name} onPrompt={setInput} />}
        {messages.map(message => <MessageBubble key={message.id} message={message} />)}
        {streamedText && <div className="relative pl-6"><span className="evidence-rail absolute inset-y-1 left-1 w-px" /><span className="absolute left-[-1px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-[hsl(var(--accent))]" /><div className="prose prose-sm max-w-none rounded-xl border bg-card/90 p-5 shadow-sm dark:prose-invert"><ReactMarkdown>{streamedText}</ReactMarkdown></div></div>}{events.filter(event => event.type !== 'message.delta').map(event => <EventCard key={`${event.id}-${event.type}`} event={event} />)}
        {activeRun && <div className="flex items-center gap-2 rounded-full border bg-card/75 px-3 py-2 text-xs text-muted-foreground shadow-sm"><Loader2 className="h-3.5 w-3.5 animate-spin text-[hsl(var(--accent))]" /><span>{statusLabel(activeRun.status)} · 航段 {activeRun.current_step} · <span className="font-data">{activeRun.tokens_used} tokens</span></span></div>}
        {approvals.filter(item => !currentId || runs.some(run => run.id === (item as AgentApproval & { run_id?: string }).run_id)).map(item => <ApprovalCard key={item.id} item={item} onResolve={resolveApproval} />)}
        {notice && <Card className="border-primary/30"><CardContent className="whitespace-pre-wrap p-4 font-mono text-sm">{notice}</CardContent></Card>}
        <div ref={bottomRef} />
      </div></ScrollArea>

      <div className="border-t bg-background/92 p-3 backdrop-blur-md"><div className="relative mx-auto max-w-[840px]">{input.startsWith('/') && <div className="absolute bottom-full z-20 mb-2 max-h-64 w-full overflow-y-auto rounded-xl border bg-popover p-1.5 shadow-2xl">{COMMANDS.filter(([name]) => name.startsWith(input.split(/\s/, 1)[0])).map(([name, label]) => <button type="button" key={name} onClick={() => setInput(`${name} `)} className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm hover:bg-secondary"><span className="font-data font-medium text-[hsl(var(--copper-foreground))]">{name}</span><span className="text-xs text-muted-foreground">{label}</span></button>)}</div>}{(attachments.length > 0 || contextSnapshots.length > 0) && <div className="mb-2 flex flex-wrap gap-1.5">{attachments.map(file => <Badge key={file.id} variant="outline" className="bg-card">{file.fileName}</Badge>)}{contextSnapshots.map(item => <Badge key={item.id} variant="outline" className="border-[hsl(var(--copper)/.45)] bg-card">{item.label}<button type="button" className="ml-1" onClick={() => setContextSnapshots(items => items.filter(value => value.id !== item.id))}><X className="h-3 w-3" /></button></Badge>)}</div>}<form onSubmit={send} className="overflow-hidden rounded-2xl border bg-card/95 shadow-[0_10px_35px_hsl(var(--deep-sounding)/.10)] transition-shadow focus-within:border-[hsl(var(--accent)/.6)] focus-within:shadow-[0_14px_42px_hsl(var(--deep-sounding)/.14)]"><Textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send() } if (e.key === 'Escape' && activeRun && currentId) void agentPlatformApi.stopSession(currentId) }} placeholder="写下问题，或输入 / 选择研究方式…" className="min-h-24 resize-none border-0 bg-transparent px-4 pt-4 focus-visible:ring-0" /><div className="flex items-center gap-2 border-t border-border/60 bg-secondary/35 px-2 py-2"><label className="inline-flex min-h-9 min-w-9 cursor-pointer items-center justify-center rounded-lg hover:bg-secondary focus-within:ring-2 focus-within:ring-ring"><Paperclip className="h-4 w-4" /><span className="sr-only">添加附件</span><input className="hidden" type="file" accept=".pdf,.docx,.xlsx,.csv,.txt,.md,image/*" onChange={e => { const file = e.target.files?.[0]; if (file) void agentPlatformApi.uploadAttachment(file).then(uploaded => setAttachments(items => [...items, uploaded])).catch(error => toast.error(error instanceof Error ? error.message : '附件上传失败')); e.currentTarget.value = '' }} /></label><Badge variant="outline" className="border-[hsl(var(--copper)/.35)] bg-card font-data text-[hsl(var(--copper-foreground))]">/{currentSession?.interaction_mode || 'ask'}</Badge>{input.startsWith('/') && <div className="hidden text-xs text-muted-foreground sm:block"><Command className="mr-1 inline h-3 w-3" />命令模式</div>}<div className="flex-1" />{activeRun && <Button type="button" size="sm" variant="outline" onClick={() => currentId && void agentPlatformApi.stopSession(currentId)}><CircleStop className="mr-1 h-4 w-4" />停止</Button>}<Button size="icon" className="rounded-xl" aria-label="发送" disabled={!input.trim() || sending || !defaultAgentId}>{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button></div></form></div><div className="mx-auto mt-1.5 flex max-w-[840px] justify-between px-1 text-[10px] text-muted-foreground"><span>Enter 发送 · Shift+Enter 换行 · 附件与市场证据由你显式带入</span><span className="font-data">/{currentSession?.interaction_mode || 'ask'}</span></div></div>
    </main>

  return <div className="flex h-full min-h-0 overflow-hidden bg-background/80">
    <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}><SheetContent side="left" className="w-80 p-0"><SheetHeader className="sr-only"><SheetTitle>会话</SheetTitle></SheetHeader>{sidebar}</SheetContent></Sheet>
    {desktopPanels ? <PanelGroup direction="horizontal" autoSaveId="keeltrader-agent-workspace" className="h-full w-full">
      <Panel ref={leftPanelRef} defaultSize={19} minSize={15} maxSize={30} collapsible collapsedSize={0} onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}><aside className="h-full border-r">{sidebar}</aside></Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/45 outline-none hover:bg-[hsl(var(--copper)/.55)] focus-visible:bg-[hsl(var(--accent))]"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel minSize={40}>{mainPanel}</Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/45 outline-none hover:bg-[hsl(var(--copper)/.55)] focus-visible:bg-[hsl(var(--accent))]"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel ref={rightPanelRef} defaultSize={25} minSize={19} maxSize={36} collapsible collapsedSize={0} onCollapse={() => setRightCollapsed(true)} onExpand={() => setRightCollapsed(false)}><aside className="chart-surface h-full overflow-y-auto border-l"><ContextContent session={currentSession} dossier={dossier} runs={runs} events={events} usage={usage} onPin={pinCurrent} onArchive={archiveCurrent} onDelete={() => setDeleteConfirmOpen(true)} /></aside></Panel>
    </PanelGroup> : mainPanel}
    <ContextSheet open={contextOpen} onOpenChange={setContextOpen} session={currentSession} dossier={dossier} runs={runs} events={events} usage={usage} onPin={pinCurrent} onArchive={archiveCurrent} onDelete={() => setDeleteConfirmOpen(true)} />
    <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} models={models} agents={agents} memories={memories} mcp={mcp} schedules={schedules} usage={usage} defaultAgentId={defaultAgentId} modelForm={modelForm} setModelForm={setModelForm} mcpForm={mcpForm} setMcpForm={setMcpForm} scheduleForm={scheduleForm} setScheduleForm={setScheduleForm} submit={submitSetting} />
    <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>永久删除这个研究会话？</AlertDialogTitle><AlertDialogDescription>消息、运行步骤和研究产物会一并删除，此操作无法撤销。公司档案和长期记忆不会被删除。</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>取消</AlertDialogCancel><AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => void deleteCurrent()}>永久删除</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    <Dialog open={Boolean(renameSession)} onOpenChange={open => { if (!open && !renaming) setRenameSession(null) }}><DialogContent className="sm:max-w-md"><form onSubmit={saveRename}><DialogHeader><DialogTitle className="font-display text-xl">重命名研究会话</DialogTitle><DialogDescription>名称会显示在会话列表中；未绑定公司时也会作为研究台标题。历史消息不会改变。</DialogDescription></DialogHeader><div className="py-5"><Input autoFocus maxLength={200} value={renameTitle} onChange={event => setRenameTitle(event.target.value)} placeholder="输入会话名称" aria-label="会话名称" /><div className="mt-2 text-right font-data text-[10px] text-muted-foreground">{renameTitle.length}/200</div></div><DialogFooter><Button type="button" variant="outline" disabled={renaming} onClick={() => setRenameSession(null)}>取消</Button><Button type="submit" disabled={renaming || !renameTitle.trim()}>{renaming ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}保存名称</Button></DialogFooter></form></DialogContent></Dialog>
  </div>
}

function MessageBubble({ message }: { message: AgentMessage }) {
  const user = message.role === 'user'
  if (user) return <div className="flex justify-end"><div className="max-w-[86%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-primary-foreground shadow-sm"><p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p><div className="font-data mt-2 text-[9px] text-primary-foreground/55">{new Date(message.created_at).toLocaleTimeString()}</div></div></div>
  return <div className="relative pl-6"><span className="evidence-rail absolute inset-y-1 left-1 w-px" /><span className="absolute left-[-3px] top-1 grid h-4 w-4 place-items-center rounded-full border bg-background"><Bot className="h-2.5 w-2.5 text-[hsl(var(--accent))]" /></span><article className="rounded-xl border bg-card/88 px-5 py-4 shadow-sm"><div className="prose prose-sm max-w-none leading-7 dark:prose-invert"><ReactMarkdown>{message.content}</ReactMarkdown></div><div className="font-data mt-3 text-[9px] text-muted-foreground">研究记录 · {new Date(message.created_at).toLocaleTimeString()}</div></article></div>
}

function ResearchBearing({ session, dossier, run, onRename }: { session?: AgentSession; dossier: CompanyDossier | null; run?: AgentRun; onRename: () => void }) {
  const company = String(dossier?.snapshot?.company?.name || session?.title || '未选择公司')
  const evidence = dossier?.snapshot?.evidence_status === 'sufficient' ? '证据充分' : dossier ? '证据待补' : '尚无档案'
  return <div className="min-w-0 flex-1 px-1 py-2">
    <div className="group flex min-w-0 items-center gap-2"><Compass className="h-4 w-4 shrink-0 text-[hsl(var(--copper-foreground))]" /><span className="truncate font-display text-base font-semibold">{company}</span>{session && <button type="button" className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-muted-foreground opacity-60 transition hover:bg-secondary hover:text-foreground sm:opacity-0 sm:group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`重命名 ${session.title}`} onClick={onRename}><Pencil className="h-3.5 w-3.5" /></button>}{session?.company_code && <span className="font-data hidden max-w-52 truncate text-[10px] text-muted-foreground md:inline">{session.title} · {session.company_code}</span>}</div>
    <div className="mt-1 flex items-center gap-2 overflow-hidden text-[10px] text-muted-foreground sm:gap-3"><span className="font-data shrink-0 text-[hsl(var(--copper-foreground))]">/{session?.interaction_mode || 'ask'}</span><Link href="/agent/capital" className="flex shrink-0 items-center gap-1 text-[hsl(var(--copper-foreground))] hover:underline"><Waves className="h-3 w-3" />资金面</Link><span className="flex shrink-0 items-center gap-1"><Database className="h-3 w-3" />{evidence}</span><span className="flex min-w-0 items-center gap-1"><Waves className="h-3 w-3 shrink-0" /><span className="truncate">{run ? statusLabel(run.status) : '研究台就绪'}</span></span><span className="hidden items-center gap-1 xl:flex"><ShieldCheck className="h-3 w-3" />只读，不执行交易</span></div>
  </div>
}

function ResearchEmptyState({ companyName, onPrompt }: { companyName?: string; onPrompt: (value: string) => void }) {
  const prompts = companyName
    ? [['商业模式', `解释${companyName}的商业模式与护城河`], ['投资假设', `梳理${companyName}当前投资假设`], ['风险证伪', `列出${companyName}的关键风险和证伪条件`], ['估值现金流', `分析${companyName}的估值与现金流质量`]]
    : [['商业模式', '解释一家公司的商业模式与护城河'], ['投资假设', '梳理一个可证伪的投资假设'], ['风险证伪', '列出关键风险和证伪条件'], ['标的比较', '比较两个标的的核心差异']]
  return <div className="flex min-h-[52vh] flex-col justify-center py-10"><div className="max-w-xl"><div className="mb-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[hsl(var(--copper-foreground))]"><span className="h-px w-10 bg-[hsl(var(--copper)/.6)]" />Fundamental research desk</div><h1 className="font-display text-4xl font-medium leading-[1.08] tracking-[-0.035em] md:text-5xl">{companyName ? `从 ${companyName} 的事实开始。` : '选择一家公司，建立可验证的判断。'}</h1><p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground">结论沿着财务数据、研报证据与证伪条件逐步形成。KeelTrader 只做研究，不替你交易。</p></div><div className="mt-8 grid max-w-2xl gap-2 sm:grid-cols-2">{prompts.map(([label, text]) => <button key={text} className="group flex min-h-14 items-center gap-3 rounded-xl border bg-card/75 px-4 py-3 text-left text-sm shadow-sm transition hover:-translate-y-0.5 hover:border-[hsl(var(--accent)/.5)] hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => onPrompt(text)}><span className="font-data min-w-16 text-[9px] uppercase tracking-wide text-[hsl(var(--copper-foreground))]">{label}</span><span>{text}</span></button>)}</div></div>
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

function ContextSheet({ open, onOpenChange, session, dossier, runs, events, usage, onPin, onArchive, onDelete }: { open: boolean; onOpenChange: (v: boolean) => void; session?: AgentSession; dossier: CompanyDossier | null; runs: AgentRun[]; events: LiveEvent[]; usage: Usage | null; onPin: () => Promise<void>; onArchive: () => Promise<void>; onDelete: () => void }) {
  return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent className="chart-surface w-[min(390px,100vw)] overflow-y-auto"><SheetHeader><SheetTitle className="font-display text-xl">公司档案</SheetTitle></SheetHeader><ContextContent session={session} dossier={dossier} runs={runs} events={events} usage={usage} onPin={onPin} onArchive={onArchive} onDelete={onDelete} /></SheetContent></Sheet>
}

function ContextContent({ session, dossier, runs, events, usage, onPin, onArchive, onDelete }: { session?: AgentSession; dossier: CompanyDossier | null; runs: AgentRun[]; events: LiveEvent[]; usage: Usage | null; onPin: () => Promise<void>; onArchive: () => Promise<void>; onDelete: () => void }) {
  const latest = runs.at(-1)
  const hasActiveRun = runs.some(run => !TERMINAL.has(run.status))
  const metrics = dossier?.snapshot?.metrics || {}
  const valuation = typeof metrics.derived_valuation === 'object' && metrics.derived_valuation ? metrics.derived_valuation as Record<string, unknown> : {}
  return <div className="space-y-6 p-5"><section><div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Company dossier</div><h2 className="mt-2 truncate font-display text-2xl font-semibold">{String(dossier?.snapshot?.company?.name || session?.title || '尚未绑定公司')}</h2><div className="mt-2 flex flex-wrap gap-2"><Badge variant="outline" className="font-data">{session?.company_code || '未绑定'}</Badge>{dossier?.dossier && <Badge variant={dossier.dossier.stale ? 'destructive' : 'secondary'}>v{dossier.dossier.current_version} · {dossier.dossier.stale ? '待刷新' : '已同步'}</Badge>}</div></section>{session?.company_code && <Button className="w-full" variant="outline" onClick={() => void agentPlatformApi.refreshDossier(session.company_code!).then(() => toast.success('基本面档案已进入刷新队列'))}><Waves className="mr-2 h-4 w-4" />刷新基本面档案</Button>}<section><SectionLabel>经营质量</SectionLabel><div className="grid grid-cols-2 gap-2"><Metric label="营收同比" value={formatMetric(metrics.revenue_growth_pct, '%')} /><Metric label="净利同比" value={formatMetric(metrics.net_profit_growth_pct, '%')} /><Metric label="ROE" value={formatMetric(metrics.roe_pct, '%')} /><Metric label="现金含量" value={formatMetric(metrics.cfo_to_profit)} /></div></section><section><SectionLabel>估值罗盘</SectionLabel><div className="grid grid-cols-3 gap-2"><Metric label="PE" value={formatMetric(valuation.pe, 'x')} compact /><Metric label="PB" value={formatMetric(valuation.pb, 'x')} compact /><Metric label="PS" value={formatMetric(valuation.ps, 'x')} compact /></div><div className="mt-2"><Metric label="近 12 月股息率" value={formatMetric(metrics.dividend_yield_pct, '%')} /></div></section>{dossier?.snapshot?.evidence_shortage && <p className="rounded-xl border border-[hsl(var(--copper)/.35)] bg-[hsl(var(--copper)/.07)] p-3 text-xs leading-5 text-[hsl(var(--copper-foreground))]">{dossier.snapshot.evidence_shortage}</p>}{Boolean(dossier?.snapshot?.anomaly_flags?.length) && <section><SectionLabel>异常信号</SectionLabel>{dossier!.snapshot!.anomaly_flags.map(flag => <div key={flag} className="mb-1.5 rounded-lg border border-destructive/20 bg-destructive/10 p-2.5 text-xs">{flag}</div>)}</section>}<section><SectionLabel>证据航迹</SectionLabel><div className="rounded-xl border bg-card/70 p-3 text-xs text-muted-foreground"><span className="font-data text-foreground">{dossier?.evidence.length || 0}</span> 条证据 · <span className="font-data text-foreground">{dossier?.versions.length || 0}</span> 个不可变版本</div></section><section><SectionLabel>本次研究</SectionLabel><div className="grid grid-cols-2 gap-2"><Metric label="今日费用" value={`$${(usage?.today.cost_usd || 0).toFixed(4)}`} /><Metric label="任务状态" value={latest ? statusLabel(latest.status) : '就绪'} /></div></section><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void onPin()}><Pin className="mr-1 h-4 w-4" />{session?.is_pinned ? '取消置顶' : '置顶'}</Button><Button size="sm" variant="outline" onClick={() => void onArchive()}><Archive className="mr-1 h-4 w-4" />归档</Button><Button size="sm" variant="destructive" disabled={!session || hasActiveRun} title={hasActiveRun ? '请先停止运行中的研究任务' : undefined} onClick={onDelete}><Trash2 className="mr-1 h-4 w-4" />删除</Button></div></div>
}

function formatMetric(value: unknown, suffix = '') { return typeof value === 'number' ? `${value.toFixed(2)}${suffix}` : '-' }

type SettingsProps = {
  open: boolean; onOpenChange: (v: boolean) => void; models: AgentModelProfile[]; agents: AgentDefinition[]; memories: AgentMemory[]; mcp: MCPServer[]; schedules: AgentSchedule[]; usage: Usage | null; defaultAgentId: string
  modelForm: Record<string, string | number>; setModelForm: (v: never) => void; mcpForm: Record<string, string>; setMcpForm: (v: never) => void; scheduleForm: Record<string, string>; setScheduleForm: (v: never) => void; submit: (fn: () => Promise<unknown>, message: string) => Promise<void>
}

type ResearchCloudConnection = {
  status: string
  connected: boolean
  key_prefix?: string | null
  plan_code?: string | null
  user_code?: string | null
  verification_uri?: string | null
  last_error?: string | null
  cloud_auto_context?: boolean
}

function SettingsSheet(props: SettingsProps) {
  const { open, onOpenChange, models, agents, memories, mcp, schedules, usage, defaultAgentId, modelForm, setModelForm, mcpForm, setMcpForm, scheduleForm, setScheduleForm, submit } = props
  const [section, setSection] = useState('setup')
  const [researchCloud, setResearchCloud] = useState<ResearchCloudConnection>({ status: 'disconnected', connected: false })
  const [researchCloudAvailable, setResearchCloudAvailable] = useState(true)
  const loadResearchCloud = useCallback(async (poll = false) => {
    const response = await apiFetch(poll ? '/research-cloud/connection/status' : '/research-cloud/connection')
    if (response.status === 503) { setResearchCloudAvailable(false); return }
    if (response.ok) { setResearchCloudAvailable(true); setResearchCloud(await response.json()) }
  }, [])
  useEffect(() => {
    if (open) queueMicrotask(() => void loadResearchCloud())
  }, [loadResearchCloud, open])
  useEffect(() => {
    if (!open || researchCloud.status !== 'pending') return
    const timer = window.setInterval(() => void loadResearchCloud(true), 5000)
    return () => window.clearInterval(timer)
  }, [loadResearchCloud, open, researchCloud.status])
  const connectResearchCloud = async () => {
    const response = await apiFetch('/research-cloud/connection/start', { method: 'POST' })
    if (!response.ok) { toast.error(response.status === 503 ? '管理员尚未启用云研报' : '无法启动云研报授权'); return }
    setResearchCloud(await response.json())
  }
  const disconnectResearchCloud = async () => {
    const response = await apiFetch('/research-cloud/connection', { method: 'DELETE' })
    if (response.ok) setResearchCloud(await response.json())
  }
  const setCloudAutoContext = async (enabled: boolean) => {
    const response = await apiFetch('/research-cloud/connection/preferences', { method: 'PUT', body: { cloud_auto_context: enabled } })
    if (response.ok) setResearchCloud(await response.json())
  }
  const activeModelId = agents[0]?.model_profile_id
  const labels: Record<string, string> = { setup: '模型与隐私', cloud: '云研报', mcp: '扩展工具', memory: '记忆', schedule: '定时研究', usage: '用量' }
  return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent className="chart-surface w-full overflow-y-auto sm:max-w-xl"><SheetHeader><SheetTitle className="font-display text-2xl">研究台设置</SheetTitle></SheetHeader><div className="mt-4 flex flex-wrap gap-2">{Object.keys(labels).map(item => <Button key={item} size="sm" variant={section === item ? 'default' : 'outline'} onClick={() => setSection(item)}>{labels[item]}</Button>)}</div><div className="mt-5 space-y-4">
    {section === 'setup' && <Card><CardHeader><CardTitle className="text-base">KeelTrader 模型与 BYOK</CardTitle></CardHeader><CardContent className="grid gap-3"><p className="text-sm text-muted-foreground">KeelTrader 始终只有一个研究助手。保存新的模型凭证后会直接切换使用，无需额外创建角色。</p><Input placeholder="配置名称" value={String(modelForm.name)} onChange={e => setModelForm({ ...modelForm, name: e.target.value } as never)} /><select className="rounded border bg-background p-2" value={String(modelForm.provider)} onChange={e => setModelForm({ ...modelForm, provider: e.target.value } as never)}><option value="openai">OpenAI-compatible</option><option value="anthropic">Anthropic</option></select><Input placeholder="Base URL（官方可留空）" value={String(modelForm.base_url)} onChange={e => setModelForm({ ...modelForm, base_url: e.target.value } as never)} /><Input placeholder="Model" value={String(modelForm.model)} onChange={e => setModelForm({ ...modelForm, model: e.target.value } as never)} /><Input type="password" autoComplete="off" placeholder="API Key（不会进入聊天记录）" value={String(modelForm.api_key)} onChange={e => setModelForm({ ...modelForm, api_key: e.target.value } as never)} /><Button onClick={() => void submit(() => agentPlatformApi.createModel({ ...modelForm, base_url: modelForm.base_url || null }), 'KeelTrader 模型已切换')}>保存并使用此模型</Button><div className="space-y-1">{models.map(item => <div className="flex items-center justify-between rounded border p-2 text-sm" key={item.id}><span>{item.name} · {item.model}</span>{activeModelId === item.id && <Badge>当前使用</Badge>}</div>)}</div></CardContent></Card>}
    {section === 'cloud' && <Card><CardHeader><CardTitle className="text-base">可选 Research Cloud</CardTitle></CardHeader><CardContent className="space-y-3">{!researchCloudAvailable ? <p className="text-sm text-muted-foreground">此部署未启用云研报，研究活动保持在本机与管理员配置的 report-kb 内。</p> : researchCloud.connected ? <><div className="flex items-center gap-2"><Badge>已连接</Badge><span className="text-xs text-muted-foreground">{researchCloud.plan_code || 'Research plan'} · {researchCloud.key_prefix || '加密凭证'}</span></div><p className="text-sm text-muted-foreground">只发送检索词、公司筛选和报告 ID；本地文档、持仓、交易、模型密钥与决策日志不会上传。</p><div className="flex items-center justify-between rounded-xl border p-3"><div><div className="text-sm font-medium">自动补充云研报上下文</div><div className="text-xs text-muted-foreground">默认关闭；仅在你接受自动云查询时启用。</div></div><Switch checked={Boolean(researchCloud.cloud_auto_context)} onCheckedChange={value => void setCloudAutoContext(value)} /></div><Button variant="outline" onClick={() => void disconnectResearchCloud()}>断开连接</Button></> : researchCloud.status === 'pending' ? <><p className="text-sm">打开授权页面并输入设备码：</p><div className="font-data text-2xl tracking-[0.18em]">{researchCloud.user_code}</div>{researchCloud.verification_uri && <a className="text-sm text-primary underline" href={researchCloud.verification_uri} target="_blank" rel="noreferrer">打开授权页面</a>}<p className="text-xs text-muted-foreground">本页每 5 秒检查一次授权状态。</p></> : <>{researchCloud.last_error && <p className="text-sm text-destructive">{researchCloud.last_error}</p>}<p className="text-sm text-muted-foreground">管理员启用后，每位用户仍需独立授权；默认不共享任何本地研究资产。</p><Button onClick={() => void connectResearchCloud()}>连接云研报</Button></>}</CardContent></Card>}
    {section === 'mcp' && <Card><CardHeader><CardTitle className="text-base">公网 HTTPS MCP</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="名称" value={mcpForm.name} onChange={e => setMcpForm({ ...mcpForm, name: e.target.value } as never)} /><Input placeholder="https://..." value={mcpForm.url} onChange={e => setMcpForm({ ...mcpForm, url: e.target.value } as never)} /><Input type="password" autoComplete="off" placeholder="Bearer Token（不会进入聊天记录）" value={mcpForm.auth_token} onChange={e => setMcpForm({ ...mcpForm, auth_token: e.target.value } as never)} /><Button onClick={() => void submit(() => agentPlatformApi.createMcp({ ...mcpForm, auth_token: mcpForm.auth_token || null }), 'MCP 已连接')}>发现工具</Button>{mcp.map(item => <div className="rounded border p-3 text-sm" key={item.id}>{item.name} <Badge>{item.status}</Badge><div className="text-xs text-muted-foreground">{item.url}</div></div>)}</CardContent></Card>}
    {section === 'memory' && <div className="space-y-2">{memories.map(item => <Card key={item.id}><CardContent className="p-3"><div className="font-medium">{item.key}</div><pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(item.value, null, 2)}</pre></CardContent></Card>)}</div>}
    {section === 'schedule' && <Card><CardHeader><CardTitle className="text-base">定时研究</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="计划名称" value={scheduleForm.name} onChange={e => setScheduleForm({ ...scheduleForm, name: e.target.value } as never)} /><Textarea placeholder="研究任务" value={scheduleForm.prompt} onChange={e => setScheduleForm({ ...scheduleForm, prompt: e.target.value } as never)} /><Input value={scheduleForm.cron} onChange={e => setScheduleForm({ ...scheduleForm, cron: e.target.value } as never)} /><Button disabled={!defaultAgentId} onClick={() => void submit(() => agentPlatformApi.createSchedule({ ...scheduleForm, agent_definition_id: defaultAgentId }), '定时研究已创建')}>创建计划</Button>{schedules.map(item => <div className="rounded border p-3 text-sm" key={item.id}>{item.name} · {item.cron}</div>)}</CardContent></Card>}
    {section === 'usage' && <div className="grid grid-cols-2 gap-3"><Metric label="今日输入" value={usage?.today.input_tokens || 0} /><Metric label="今日输出" value={usage?.today.output_tokens || 0} /><Metric label="今日成本" value={`$${(usage?.today.cost_usd || 0).toFixed(4)}`} /><Metric label="研究助手" value="KeelTrader" /></div>}
  </div></SheetContent></Sheet>
}

function SectionLabel({ children }: { children: ReactNode }) { return <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{children}</div> }
function Metric({ label, value, compact = false }: { label: string; value: string | number; compact?: boolean }) { return <div className={`rounded-xl border bg-card/75 ${compact ? 'p-2.5' : 'p-3'}`}><div className="text-[10px] text-muted-foreground">{label}</div><div className={`font-data mt-1 font-semibold tracking-[-0.03em] ${compact ? 'text-base' : 'text-lg'}`}>{value}</div></div> }
function statusLabel(status: string) { return ({ queued: '等待 Worker', planning: '规划研究步骤', running: '执行研究', waiting_approval: '等待审批', paused_budget: '预算暂停', paused: '已暂停' } as Record<string, string>)[status] || status }
