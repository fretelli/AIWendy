'use client'

import Link from 'next/link'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from 'react-resizable-panels'
import {
  Bell, Building2, ChevronRight, History, Loader2, Menu, PanelLeftClose, PanelLeftOpen,
  PanelRightClose, PanelRightOpen, Plus, Radar, RefreshCw, Search, ShipWheel, Trash2, UserRoundSearch,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import {
  agentPlatformApi,
  type HolderHistoryEvent,
  type HolderInboxEvent,
  type HolderPosition,
  type HolderSearchItem,
  type HolderWatchItem,
} from '@/lib/api/agent-platform'

type View = 'latest' | 'history'

const EVENT_LABELS: Record<string, string> = {
  first_seen: '首次记录', new: '新进前十', increased: '增持', reduced: '减持',
  unchanged: '持仓不变', exited_top10: '退出前十',
}

const EVENT_STYLES: Record<string, string> = {
  first_seen: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  new: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  increased: 'border-[hsl(var(--accent)/.35)] bg-[hsl(var(--accent)/.1)] text-[hsl(var(--accent))]',
  reduced: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  unchanged: 'border-border bg-secondary/55 text-muted-foreground',
  exited_top10: 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300',
}

export default function HolderRadarPage() {
  const [watchlist, setWatchlist] = useState<HolderWatchItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<HolderSearchItem[]>([])
  const [sourceAvailable, setSourceAvailable] = useState(true)
  const [view, setView] = useState<View>('latest')
  const [allHistory, setAllHistory] = useState(false)
  const [positions, setPositions] = useState<Array<HolderPosition | HolderHistoryEvent>>([])
  const [total, setTotal] = useState(0)
  const [sourceAsOf, setSourceAsOf] = useState<string | undefined>()
  const [inbox, setInbox] = useState<HolderInboxEvent[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)
  const [positionsLoading, setPositionsLoading] = useState(false)
  const [watchlistOpen, setWatchlistOpen] = useState(false)
  const [inboxOpen, setInboxOpen] = useState(false)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [desktopPanels, setDesktopPanels] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches)
  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const rightPanelRef = useRef<ImperativePanelHandle>(null)
  const selected = watchlist.find(item => item.id === selectedId)

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)')
    const sync = () => setDesktopPanels(media.matches)
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  const loadWorkspace = useCallback(async () => {
    try {
      const [watchData, eventData] = await Promise.all([
        agentPlatformApi.holderWatchlist(), agentPlatformApi.holderEvents(),
      ])
      setWatchlist(watchData.items)
      setInbox(eventData.items)
      setUnread(eventData.unread)
      setSelectedId(previous => previous || watchData.items[0]?.id || null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '股东雷达加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { queueMicrotask(() => { void loadWorkspace() }) }, [loadWorkspace])

  useEffect(() => {
    if (!query.trim()) return
    const timer = window.setTimeout(() => {
      void agentPlatformApi.searchHolders(query.trim()).then(data => {
        setResults(data.items); setSourceAvailable(data.source_available)
      }).catch(error => {
        setResults([]); toast.error(error instanceof Error ? error.message : '股东搜索失败')
      })
    }, 260)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!selectedId) return
    queueMicrotask(() => setPositionsLoading(true))
    void agentPlatformApi.holderPositions(selectedId, view, 200, 0, allHistory).then(data => {
      setPositions(data.items); setTotal(data.total); setSourceAvailable(data.source_available)
      setSourceAsOf(data.source_as_of)
    }).catch(error => toast.error(error instanceof Error ? error.message : '持仓记录加载失败'))
      .finally(() => setPositionsLoading(false))
  }, [allHistory, selectedId, view])

  const addHolder = async (candidate: HolderSearchItem) => {
    try {
      const item = await agentPlatformApi.addHolderWatch({
        holder_name: candidate.holder_name, holder_type: candidate.holder_type,
      })
      setWatchlist(previous => previous.some(existing => existing.id === item.id) ? previous : [item, ...previous])
      setSelectedId(item.id); setQuery(''); setResults([]); setWatchlistOpen(false)
      toast.success(`已关注 ${item.holder_name}`)
    } catch (error) { toast.error(error instanceof Error ? error.message : '添加关注失败') }
  }

  const removeHolder = async (item: HolderWatchItem) => {
    try {
      await agentPlatformApi.removeHolderWatch(item.id)
      const remaining = watchlist.filter(existing => existing.id !== item.id)
      setWatchlist(remaining)
      if (selectedId === item.id) setSelectedId(remaining[0]?.id || null)
      toast.success(`已移除 ${item.holder_name}`)
    } catch (error) { toast.error(error instanceof Error ? error.message : '移除失败') }
  }

  const refreshSelected = async () => {
    if (!selected) return
    try {
      await agentPlatformApi.refreshHolderWatch(selected.id)
      toast.success('已加入刷新队列')
    } catch (error) { toast.error(error instanceof Error ? error.message : '刷新失败') }
  }

  const markAllRead = async () => {
    await agentPlatformApi.readHolderEvents()
    setInbox(previous => previous.map(item => ({ ...item, read_at: new Date().toISOString() })))
    setUnread(0)
  }

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div>

  const watchPanel = <aside className="chart-surface flex h-full min-h-0 flex-col">
        <div className="border-b p-4">
          <div className="mb-2 flex items-center justify-between"><span className="text-xs font-semibold">关注股东</span><Badge variant="outline" className="font-data">{watchlist.length}</Badge></div>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input value={query} onChange={event => { setQuery(event.target.value); if (!event.target.value) setResults([]) }} className="h-9 bg-card pl-9 text-sm" placeholder="输入完整姓名或机构名称" />
            {query.trim() && <div className="absolute z-30 mt-1 max-h-80 w-full overflow-y-auto rounded-xl border bg-popover p-1.5 shadow-2xl">
              {!sourceAvailable && <p className="p-3 text-xs text-destructive">股东数据源暂不可用，请稍后重试。</p>}
              {sourceAvailable && results.length === 0 && <p className="p-3 text-xs text-muted-foreground">没有找到精确或相似披露名称。</p>}
              {results.map(item => <button key={`${item.holder_name}-${item.holder_type}`} className="w-full rounded-lg px-3 py-2 text-left hover:bg-secondary" onClick={() => void addHolder(item)}>
                <div className="flex items-center gap-2"><Plus className="h-3.5 w-3.5 text-[hsl(var(--accent))]" /><span className="truncate text-sm font-semibold">{item.holder_name}</span>{item.exact_match && <Badge className="ml-auto text-[9px]">精确</Badge>}</div>
                <div className="mt-1 flex justify-between pl-5 font-data text-[10px] text-muted-foreground"><span>{item.holder_type}</span><span>历史涉及 {item.stock_count} 只 · 至 {formatDate(item.last_end_date)}</span></div>
                {item.identity_warning && <p className="mt-1 pl-5 text-[10px] text-amber-700 dark:text-amber-300">{item.identity_warning}</p>}
              </button>)}
            </div>}
          </div>
        </div>
        <ScrollArea className="h-[calc(100%-105px)]"><div className="space-y-1 p-2">
          {watchlist.length === 0 && <Empty title="还没有关注股东" body="搜索披露姓名后加入关注，即可反查股票和查看历史变化。" />}
          {watchlist.map(item => <div key={item.id} className={`group flex items-center rounded-xl border ${selectedId === item.id ? 'border-[hsl(var(--accent)/.4)] bg-[hsl(var(--accent)/.08)] shadow-sm' : 'border-transparent hover:bg-secondary/65'}`}>
            <button className="min-w-0 flex-1 px-3 py-3 text-left" onClick={() => { setSelectedId(item.id); setWatchlistOpen(false) }}>
              <span className="block truncate text-sm font-semibold">{item.holder_name}</span>
              <span className="font-data mt-1 block text-[10px] text-muted-foreground">{item.holder_type}{item.last_scanned_at ? ` · 扫描 ${formatDateTime(item.last_scanned_at)}` : ' · 等待首次扫描'}</span>
            </button>
            <Button size="icon" variant="ghost" className="mr-1 h-8 w-8 opacity-0 group-hover:opacity-100 focus-visible:opacity-100" aria-label={`移除 ${item.holder_name}`} onClick={() => void removeHolder(item)}><Trash2 className="h-3.5 w-3.5" /></Button>
          </div>)}
        </div></ScrollArea>
      </aside>

  const mainPanel = <main className="h-full min-h-0 min-w-0 bg-background/80">
        {selected ? <div className="flex h-full min-h-0 flex-col">
          <div className="border-b bg-card/70 px-5 py-4 md:px-7">
            <div className="flex flex-wrap items-start gap-3">
              <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><UserRoundSearch className="h-5 w-5 text-[hsl(var(--copper-foreground))]" /><h2 className="truncate font-display text-2xl font-semibold">{selected.holder_name}</h2><Badge variant="outline">{selected.holder_type}</Badge></div>
                <p className="mt-2 text-xs text-muted-foreground">所有结果均来自上市公司前十大流通股东披露。{selected.identity_warning || ''}</p></div>
              <Button size="sm" variant="outline" onClick={() => void refreshSelected()}><RefreshCw className="mr-1.5 h-3.5 w-3.5" />刷新事件</Button>
            </div>
            <div className="mt-4 flex items-center gap-1 rounded-lg bg-secondary/65 p-1">
              <ViewButton active={view === 'latest'} onClick={() => setView('latest')} icon={<Building2 className="h-3.5 w-3.5" />} label="当前持仓" />
              <ViewButton active={view === 'history'} onClick={() => { setView('history'); setAllHistory(false) }} icon={<History className="h-3.5 w-3.5" />} label="历史变化" />
              {view === 'history' && <button className="rounded-md px-2 py-1.5 text-[10px] text-[hsl(var(--copper-foreground))] hover:bg-card" onClick={() => setAllHistory(value => !value)}>{allHistory ? '只看最近约 8 季度' : '展开 2020 年以来'}</button>}
              <span className="ml-auto px-2 font-data text-[10px] text-muted-foreground">{total} 条 · 公告截至 {formatDate(sourceAsOf)}</span>
            </div>
          </div>
          <ScrollArea className="flex-1"><div className="p-4 md:p-6">
            {positionsLoading && <div className="grid min-h-48 place-items-center"><Loader2 className="h-6 w-6 animate-spin" /></div>}
            {!positionsLoading && !sourceAvailable && <Empty title="股东数据源暂不可用" body="这不是“没有持仓”。请在数据源恢复后重新查询。" />}
            {!positionsLoading && sourceAvailable && positions.length === 0 && <Empty title={view === 'latest' ? '最新披露中没有持仓' : '没有历史记录'} body="请确认选择的股东类型和披露姓名是否正确。" />}
            {!positionsLoading && positions.length > 0 && <div className="space-y-2">{positions.map((row, index) => <PositionRow key={`${row.ts_code}-${row.end_date}-${index}`} row={row} history={view === 'history'} />)}</div>}
          </div></ScrollArea>
        </div> : <div className="grid h-full place-items-center p-8"><Empty title="选择一个关注股东" body="左侧搜索姓名或机构全称，开始反查其披露持仓。" /></div>}
      </main>

  const inboxPanel = <aside className="chart-surface h-full min-h-0">
        <div className="flex h-16 items-center gap-2 border-b px-4"><Bell className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h2 className="flex-1 text-sm font-semibold">披露变化</h2>{unread > 0 && <Badge>{unread} 未读</Badge>}{inbox.length > 0 && <Button size="sm" variant="ghost" className="text-xs" onClick={() => void markAllRead()}>全部已读</Button>}</div>
        <ScrollArea className="h-[calc(100%-64px)]"><div className="space-y-2 p-3">
          {inbox.length === 0 && <Empty title="还没有新变化" body="首次历史扫描不会制造未读提醒；后续披露变化会出现在这里。" />}
          {inbox.map(item => <button key={item.id} className={`w-full rounded-xl border p-3 text-left transition hover:border-[hsl(var(--accent)/.45)] ${item.read_at ? 'bg-card/65' : 'border-[hsl(var(--copper)/.35)] bg-card shadow-sm'}`} onClick={() => { setSelectedId(item.watch_id); setInboxOpen(false) }}>
            <div className="flex items-center gap-2"><EventBadge event={item.event_type} /><span className="ml-auto font-data text-[9px] text-muted-foreground">{formatDate(item.ann_date)}</span></div>
            <p className="mt-2 text-sm font-semibold">{item.holder_name} · {item.company_name || item.ts_code}</p>
            <p className="font-data mt-1 text-[10px] text-muted-foreground">{item.ts_code} · 报告期 {formatDate(item.end_date)}</p>
          </button>)}
        </div></ScrollArea>
      </aside>

  return <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background/80">
    <header className="research-bearing flex min-h-16 shrink-0 items-center gap-2 border-b bg-card/92 px-3 shadow-sm sm:gap-3 sm:px-4">
      <Button className="xl:hidden" size="icon" variant="ghost" aria-label="打开关注股东" onClick={() => setWatchlistOpen(true)}><Menu className="h-5 w-5" /></Button>
      <Button className="hidden xl:inline-flex" size="icon" variant="ghost" aria-label="折叠关注股东栏" onClick={() => leftPanelRef.current?.isCollapsed() ? leftPanelRef.current.expand() : leftPanelRef.current?.collapse()}>{leftCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}</Button>
      <div className="hidden border-r pr-4 sm:block"><KeelMark /></div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2"><Radar className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h1 className="font-display text-lg font-semibold">股东雷达</h1></div>
        <p className="truncate text-[10px] text-muted-foreground">按公开披露姓名反查前十大流通股东 · 不评分，不推荐</p>
      </div>
      <Button asChild size="sm" variant="outline"><Link href="/agent"><ShipWheel className="mr-1.5 h-4 w-4" /><span className="hidden sm:inline">研究台</span></Link></Button>
      <ThemeMenu />
      <Button className="hidden xl:inline-flex" size="icon" variant="ghost" aria-label="折叠披露变化栏" onClick={() => rightPanelRef.current?.isCollapsed() ? rightPanelRef.current.expand() : rightPanelRef.current?.collapse()}>{rightCollapsed ? <PanelRightOpen className="h-5 w-5" /> : <PanelRightClose className="h-5 w-5" />}</Button>
      <Button className="relative xl:hidden" size="icon" variant="ghost" aria-label="打开披露变化" onClick={() => setInboxOpen(true)}><Bell className="h-4 w-4" />{unread > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[hsl(var(--accent))]" />}</Button>
    </header>

    <Sheet open={watchlistOpen} onOpenChange={setWatchlistOpen}><SheetContent side="left" className="w-[min(360px,92vw)] p-0"><SheetHeader className="sr-only"><SheetTitle>关注股东</SheetTitle></SheetHeader>{watchPanel}</SheetContent></Sheet>
    <Sheet open={inboxOpen} onOpenChange={setInboxOpen}><SheetContent side="right" className="w-[min(390px,94vw)] p-0"><SheetHeader className="sr-only"><SheetTitle>披露变化</SheetTitle></SheetHeader>{inboxPanel}</SheetContent></Sheet>

    {desktopPanels ? <PanelGroup direction="horizontal" autoSaveId="keeltrader-holder-radar-workspace" className="min-h-0 flex-1">
      <Panel ref={leftPanelRef} defaultSize={22} minSize={16} maxSize={32} collapsible collapsedSize={0} onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}><div className="h-full border-r">{watchPanel}</div></Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/45 outline-none hover:bg-[hsl(var(--copper)/.55)] focus-visible:bg-[hsl(var(--accent))]"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel minSize={40}>{mainPanel}</Panel>
      <PanelResizeHandle className="group relative w-1 bg-border/45 outline-none hover:bg-[hsl(var(--copper)/.55)] focus-visible:bg-[hsl(var(--accent))]"><span className="absolute inset-y-0 -left-1 -right-1" /></PanelResizeHandle>
      <Panel ref={rightPanelRef} defaultSize={25} minSize={20} maxSize={36} collapsible collapsedSize={0} onCollapse={() => setRightCollapsed(true)} onExpand={() => setRightCollapsed(false)}><div className="h-full border-l">{inboxPanel}</div></Panel>
    </PanelGroup> : <div className="min-h-0 flex-1">{mainPanel}</div>}
  </div>
}

function PositionRow({ row, history }: { row: HolderPosition | HolderHistoryEvent; history: boolean }) {
  const historyRow = history ? row as HolderHistoryEvent : null
  const event = historyRow?.event_type || null
  const exited = event === 'exited_top10'
  return <div className="group grid gap-3 rounded-xl border bg-card/82 p-4 shadow-sm transition hover:border-[hsl(var(--accent)/.42)] md:grid-cols-[minmax(170px,1.2fr)_110px_repeat(3,minmax(90px,.7fr))_auto] md:items-center">
    <div className="min-w-0"><div className="flex items-center gap-2"><span className="truncate font-semibold">{row.company_name || row.ts_code}</span>{event && <EventBadge event={event} />}</div><div className="font-data mt-1 text-[10px] text-muted-foreground">{row.ts_code}{row.industry ? ` · ${row.industry}` : ''}</div></div>
    <Datum label="报告期" value={formatDate(row.end_date)} />
    <Datum label="持股数" value={exited ? '—' : formatNumber(row.hold_amount)} />
    <Datum label="持股比例" value={exited ? '—' : formatPercent(row.hold_ratio)} />
    <Datum label="流通占比" value={exited ? '—' : formatPercent(row.hold_float_ratio)} />
    <div className="flex items-center justify-between gap-2 md:justify-end"><span className="font-data text-[9px] text-muted-foreground">公告 {formatDate(row.ann_date)}</span><Button size="sm" variant="ghost" aria-label={`将 ${row.company_name || row.ts_code} 加入公司自选`} onClick={() => void agentPlatformApi.addWatchlist(row.ts_code).then(() => toast.success('已加入公司自选')).catch(error => toast.error(error instanceof Error ? error.message : '加入自选失败'))}><Plus className="h-3.5 w-3.5" /><span className="sr-only">加入公司自选</span></Button></div>
    {historyRow && <PriceWindow event={historyRow} />}
  </div>
}

function PriceWindow({ event }: { event: HolderHistoryEvent }) {
  if (event.event_type === 'unchanged') return null
  const estimate = event.price_estimate
  if (!estimate) return <div className="col-span-full border-t border-dashed pt-3 text-[10px] text-muted-foreground">
    {event.event_type === 'first_seen' ? '首次进入数据可见范围，缺少上一报告期，无法可靠估算成交价格。' : '对应报告期之间缺少足够的复权行情，无法可靠估算成交价格。'}
  </div>

  const action = estimate.side === 'buy' ? '估算买入参考' : estimate.side === 'sell' ? '估算卖出参考' : '可能卖出价格窗口'
  return <div className="col-span-full grid gap-3 border-t border-dashed pt-3 md:grid-cols-[minmax(190px,1.1fr)_minmax(180px,1fr)_minmax(180px,1fr)] md:items-center">
    <div>
      <div className="text-[9px] uppercase tracking-[.14em] text-[hsl(var(--copper-foreground))]">披露区间估算</div>
      <div className="font-data mt-1 text-sm font-semibold">{action} {estimate.side === 'possible_sell' ? formatPriceRange(estimate.low, estimate.high) : formatPrice(estimate.volume_weighted_price)}</div>
      {estimate.side !== 'possible_sell' && <div className="font-data mt-1 text-[10px] text-muted-foreground">价格窗口 {formatPriceRange(estimate.low, estimate.high)}</div>}
    </div>
    <div className="font-data text-[10px] text-muted-foreground">
      <div>{formatDate(estimate.window_start)} → {formatDate(estimate.window_end)}</div>
      <div className="mt-1">{estimate.trading_days} 个交易日 · 前复权收盘价成交量加权</div>
    </div>
    <div className="text-[10px] text-muted-foreground md:text-right">
      {estimate.side !== 'possible_sell' && estimate.changed_shares != null && <div className="font-data text-foreground">变动约 {formatNumber(estimate.changed_shares)} 股{estimate.estimated_amount != null ? ` · 金额约 ${formatMoney(estimate.estimated_amount)}` : ''}</div>}
      <div className="mt-1 leading-4">{estimate.disclaimer}</div>
    </div>
  </div>
}

function ViewButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return <button className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${active ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`} onClick={onClick}>{icon}{label}</button>
}

function EventBadge({ event }: { event: string }) {
  return <Badge variant="outline" className={`text-[9px] ${EVENT_STYLES[event] || EVENT_STYLES.unchanged}`}>{EVENT_LABELS[event] || event}</Badge>
}

function Datum({ label, value }: { label: string; value: string }) {
  return <div><div className="text-[9px] uppercase tracking-wide text-muted-foreground">{label}</div><div className="font-data mt-1 text-xs font-semibold">{value}</div></div>
}

function Empty({ title, body }: { title: string; body: string }) {
  return <div className="mx-auto max-w-sm py-10 text-center"><div className="mx-auto grid h-10 w-10 place-items-center rounded-full border bg-card"><ChevronRight className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /></div><h3 className="mt-3 font-display text-lg font-semibold">{title}</h3><p className="mt-2 text-xs leading-5 text-muted-foreground">{body}</p></div>
}

function formatDate(value?: string) {
  if (!value) return '—'
  const compact = value.replaceAll('-', '')
  return compact.length === 8 ? `${compact.slice(0, 4)}-${compact.slice(4, 6)}-${compact.slice(6, 8)}` : value
}

function formatDateTime(value?: string) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatNumber(value?: number) {
  if (value == null) return '—'
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value)
}

function formatPercent(value?: number) {
  if (value == null) return '—'
  return `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 3 }).format(value)}%`
}

function formatPrice(value: number) {
  return `¥${new Intl.NumberFormat('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}`
}

function formatPriceRange(low: number, high: number) {
  return `${formatPrice(low)}–${formatPrice(high)}`
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', notation: 'compact', maximumFractionDigits: 2 }).format(value)
}
