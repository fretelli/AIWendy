'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Banknote, BookOpen,
  Database, Droplets, Gauge, Landmark, Loader2, Radar, RefreshCw, ShipWheel,
  SlidersHorizontal, Waves,
} from 'lucide-react'
import {
  Area, Bar, Brush, CartesianGrid, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis,
} from 'recharts'
import { toast } from 'sonner'

import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { agentPlatformApi, type MarketCapitalSnapshot } from '@/lib/api/agent-platform'
import { firstTooltipEntry, type ChartTooltipProps } from '@/lib/charts/recharts-tooltip'

type ChartMode = 'turnover' | 'breadth' | 'return'
type HistoryPoint = MarketCapitalSnapshot['history'][number] & {
  declines_negative: number
  turnover_average_20d: number
}

const WINDOWS = [20, 60, 120, 250] as const
const CHART_MODES: Array<{ value: ChartMode; label: string }> = [
  { value: 'turnover', label: '成交水位' },
  { value: 'breadth', label: '涨跌广度' },
  { value: 'return', label: '中位涨跌幅' },
]

export default function MarketCapitalPage() {
  const [data, setData] = useState<MarketCapitalSnapshot | null>(null)
  const [window, setWindow] = useState<(typeof WINDOWS)[number]>(60)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (days: number, refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true)
    try { setData(await agentPlatformApi.marketCapital(days)) }
    catch (error) { toast.error(error instanceof Error ? error.message : '资金面快照加载失败') }
    finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { queueMicrotask(() => { void load(window) }) }, [load, window])
  if (loading && !data) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div>

  return <div className="h-full min-h-0 overflow-y-auto bg-background/80">
    <header className="research-bearing sticky top-0 z-30 flex min-h-16 items-center gap-2 border-b bg-card/95 px-3 shadow-sm backdrop-blur sm:px-5">
      <div className="hidden border-r pr-4 sm:block"><KeelMark /></div>
      <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><Waves className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h1 className="font-display text-lg font-semibold">全市场资金面</h1></div><p className="truncate text-[10px] text-muted-foreground">A 股收盘后客观快照 · 不评分，不推荐</p></div>
      <Badge variant="outline" className="hidden font-data sm:inline-flex">截至 {fmtDate(data?.as_of)}</Badge>
      <Button size="sm" variant="outline" disabled={refreshing} onClick={() => void load(window, true)}><RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />刷新</Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent/holders"><Radar className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">股东雷达</span></Link></Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent"><ShipWheel className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">研究台</span></Link></Button><ThemeMenu />
    </header>

    <div className="mx-auto max-w-[1580px] space-y-5 p-4 md:p-7">
      <section className="overflow-hidden rounded-2xl border border-[hsl(var(--copper)/.32)] bg-card shadow-sm">
        <div className="grid gap-5 p-5 lg:grid-cols-[1.25fr_.75fr] lg:p-7">
          <div><p className="font-data text-[10px] uppercase tracking-[.22em] text-[hsl(var(--copper-foreground))]">Observable market conditions</p><h2 className="mt-2 font-display text-3xl font-semibold md:text-4xl">成交额不等于净流入</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">全市场每笔成交都有买方和卖方，无法直接观察一个字面意义上的“全市场净流入”。这里优先展示可验证的成交活跃度、涨跌广度、融资变化、ETF 份额变化与资金利率。</p></div>
          <div className="rounded-xl border bg-secondary/45 p-4"><p className="text-xs font-semibold">事实摘录</p><div className="mt-3 space-y-2">{data?.interpretations?.map(line => <p key={line} className="text-xs leading-5 text-muted-foreground">— {line}</p>)}{!data?.interpretations?.length && <p className="text-xs text-muted-foreground">当前没有足够数据生成事实摘录。</p>}</div></div>
        </div>
        {data?.sources && <SourceRail sources={data.sources} />}
      </section>

      {!data?.available && <Unavailable title="全市场基础行情不可用" />}
      {data?.available && <>
        <MarketTape data={data} window={window} onWindowChange={setWindow} refreshing={refreshing} />

        <section className="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
          <Panel title="流动性与成交结构" icon={<Droplets className="h-4 w-4" />} source={data.sources.stock_daily}><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="全市场成交额" value={money(data.liquidity.turnover_cny)} delta={data.liquidity.vs_20d_pct} suffix="较20日均值" /><Metric label="5日均额" value={money(data.liquidity.average_5d_cny)} /><Metric label="前20集中度" value={pct(data.liquidity.top20_turnover_share)} /><Metric label="前50集中度" value={pct(data.liquidity.top50_turnover_share)} /></div></Panel>
          <Panel title="市场广度" icon={<Activity className="h-4 w-4" />} source={data.sources.stock_daily}><div className="grid grid-cols-2 gap-3"><Metric label="上涨" value={String(data.breadth.advances)} positive /><Metric label="下跌" value={String(data.breadth.declines)} negative /><Metric label="平盘" value={String(data.breadth.flat)} /><Metric label="中位涨跌幅" value={signedPct(data.breadth.median_return_pct)} /></div><div className="mt-4 grid grid-cols-2 gap-3 border-t pt-4"><Metric label="涨停" value={data.breadth.limit_source_available ? String(data.breadth.limit_up) : '不可用'} /><Metric label="跌停" value={data.breadth.limit_source_available ? String(data.breadth.limit_down) : '不可用'} /></div></Panel>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <Panel title="杠杆资金" icon={<Landmark className="h-4 w-4" />} source={data.sources.leverage}>{data.leverage.available ? <><div className="grid grid-cols-2 gap-3"><Metric label="融资余额" value={money(data.leverage.balance_cny)} /><Metric label="当日融资净额" value={signedMoney(data.leverage.daily_net_financing_cny)} /><Metric label="融资买入" value={money(data.leverage.purchases_cny)} /><Metric label="5日融资净额" value={signedMoney(data.leverage.five_day_net_financing_cny)} /></div><p className="mt-4 text-[10px] text-muted-foreground">实际覆盖：{data.leverage.coverage_label || '未标明'}</p></> : <Unavailable title="融资数据不可用" />}</Panel>
          <Panel title="ETF 申赎估算" icon={<Gauge className="h-4 w-4" />} source={data.sources.etf_flows}>{data.etf_flows.available ? <><div className="grid grid-cols-2 gap-3"><Metric label="估算净申赎" value={signedMoney(data.etf_flows.estimated_net_flow_cny)} /><Metric label="NAV覆盖率" value={pct(data.etf_flows.coverage_ratio)} /></div><div className="mt-4 grid grid-cols-2 gap-2 text-xs">{Object.entries(data.etf_flows.groups || {}).map(([key,value]) => <div key={key} className="flex justify-between rounded-lg bg-secondary/45 px-3 py-2"><span>{groupName(key)}</span><span className="font-data">{signedMoney(value)}</span></div>)}</div><p className="mt-4 text-[10px] text-muted-foreground">{data.etf_flows.note}</p></> : <Unavailable title="ETF 份额或净值数据不可用" />}</Panel>
        </section>

        <section className="grid gap-4 lg:grid-cols-[.7fr_1.3fr]">
          <Panel title="短期资金价格" icon={<Banknote className="h-4 w-4" />} source={data.sources.shibor}>{data.funding_rates.available ? <div className="grid grid-cols-2 gap-3"><Metric label="SHIBOR O/N" value={rate(data.funding_rates.overnight_pct)} delta={data.funding_rates.overnight_change_bp} suffix="bp" /><Metric label="SHIBOR 7D" value={rate(data.funding_rates.seven_day_pct)} delta={data.funding_rates.seven_day_change_bp} suffix="bp" /></div> : <Unavailable title="SHIBOR 数据不可用" />}</Panel>
          <section className="rounded-2xl border border-dashed border-amber-500/45 bg-amber-500/[.045] p-5 shadow-sm"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-display text-xl font-semibold">供应商代理口径</h2><Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300">与可验证资金面隔离</Badge></div><p className="mt-2 text-xs leading-5 text-muted-foreground">“主力资金”来自供应商算法分类，只作为单独代理观察，不与成交额或融资数据混为一谈。</p></div><Source source={data.sources.moneyflow_mkt_dc} /></div>{data.flow_proxy.available ? <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="供应商净额" value={signedMoney(Number(data.flow_proxy.values?.net_amount || 0) * 10000)} /><Metric label="超大单" value={signedMoney(Number(data.flow_proxy.values?.buy_elg_amount || 0) * 10000)} /><Metric label="大单" value={signedMoney(Number(data.flow_proxy.values?.buy_lg_amount || 0) * 10000)} /><Metric label="中单" value={signedMoney(Number(data.flow_proxy.values?.buy_md_amount || 0) * 10000)} /></div> : <div className="mt-5"><Unavailable title="供应商代理数据不可用；不做替代估算" /></div>}</section>
        </section>

        <MethodologyCenter data={data} />
      </>}
    </div>
  </div>
}

function MarketTape({ data, window, onWindowChange, refreshing }: { data: MarketCapitalSnapshot; window: (typeof WINDOWS)[number]; onWindowChange: (value: (typeof WINDOWS)[number]) => void; refreshing: boolean }) {
  const [mode, setMode] = useState<ChartMode>('turnover')
  const chartData = useMemo<HistoryPoint[]>(() => data.history.map((row, index, rows) => {
    const sample = rows.slice(Math.max(0, index - 19), index + 1)
    return { ...row, declines_negative: -row.declines, turnover_average_20d: sample.reduce((sum, item) => sum + Number(item.turnover_cny || 0), 0) / sample.length }
  }), [data.history])

  return <section className="overflow-hidden rounded-2xl border bg-card/88 shadow-sm">
    <div className="flex flex-col gap-4 border-b p-5 lg:flex-row lg:items-center">
      <div className="flex min-w-0 items-start gap-3"><div className="rounded-lg border bg-secondary/55 p-2 text-[hsl(var(--copper-foreground))]"><SlidersHorizontal className="h-4 w-4" /></div><div><h2 className="font-display text-xl font-semibold">资金水位记录带</h2><p className="mt-1 text-xs text-muted-foreground">悬停查看单日明细，拖动底部时间轴缩放观察区间。</p></div></div>
      <div className="flex flex-wrap gap-2 lg:ml-auto">{CHART_MODES.map(item => <Button key={item.value} size="sm" variant={mode === item.value ? 'default' : 'outline'} onClick={() => setMode(item.value)}>{item.label}</Button>)}</div>
      <div className="flex items-center gap-1 rounded-lg border bg-background/55 p-1">{WINDOWS.map(days => <button key={days} type="button" disabled={refreshing} onClick={() => onWindowChange(days)} className={`rounded-md px-2.5 py-1.5 font-data text-[10px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${window === days ? 'bg-[hsl(var(--copper))] text-[hsl(var(--copper-foreground))]' : 'text-muted-foreground hover:bg-secondary'}`}>{days}日</button>)}</div>
    </div>
    <div className={`h-[360px] p-3 transition-opacity md:h-[420px] md:p-5 ${refreshing ? 'opacity-55' : ''}`}>
      <ResponsiveContainer width="100%" height="100%"><ComposedChart key={`${mode}-${window}-${data.as_of}`} data={chartData} margin={{ top: 12, right: 10, left: 4, bottom: 8 }}>
        <defs><linearGradient id="capital-turnover" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="hsl(var(--accent))" stopOpacity={.34}/><stop offset="95%" stopColor="hsl(var(--accent))" stopOpacity={0}/></linearGradient></defs>
        <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="trade_date" tickFormatter={shortDate} tick={{ fontSize: 10 }} minTickGap={24} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={mode === 'turnover' ? compactMoney : mode === 'return' ? v => `${v}%` : compactCount} tick={{ fontSize: 10 }} width={58} axisLine={false} tickLine={false} />
        <RechartsTooltip content={<CapitalTooltip mode={mode} />} cursor={{ stroke: 'hsl(var(--copper-foreground))', strokeDasharray: '3 3' }} />
        {mode === 'turnover' && <><Area type="monotone" dataKey="turnover_cny" name="成交额" stroke="hsl(var(--accent))" fill="url(#capital-turnover)" strokeWidth={2.2} /><Line type="monotone" dataKey="turnover_average_20d" name="20日均额" stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" dot={false} strokeWidth={1.3} /></>}
        {mode === 'breadth' && <><ReferenceLine y={0} stroke="hsl(var(--border))" /><Bar dataKey="advances" name="上涨" fill="#e05a67" radius={[3,3,0,0]} /><Bar dataKey="declines_negative" name="下跌" fill="#24906f" radius={[0,0,3,3]} /></>}
        {mode === 'return' && <><ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" /><Line type="monotone" dataKey="median_return_pct" name="中位涨跌幅" stroke="hsl(var(--copper-foreground))" dot={false} strokeWidth={2.2} /></>}
        <Brush dataKey="trade_date" height={24} travellerWidth={8} tickFormatter={shortDate} stroke="hsl(var(--border))" fill="hsl(var(--secondary))" />
      </ComposedChart></ResponsiveContainer>
    </div>
    <div className="flex flex-wrap gap-x-5 gap-y-2 border-t bg-secondary/25 px-5 py-3 text-[10px] text-muted-foreground"><span>成交额：全 A 股日成交金额合计</span><span>上涨/下跌：按个股日涨跌幅正负计数</span><span>虚线：所选数据内滚动 20 日均额</span></div>
  </section>
}

function CapitalTooltip(props: ChartTooltipProps<HistoryPoint> & { mode: ChartMode }) {
  const entry = firstTooltipEntry(props)
  const row = entry?.payload
  if (!row) return null
  return <div className="min-w-48 rounded-xl border bg-popover/96 p-3 text-xs shadow-xl backdrop-blur"><p className="font-data font-semibold">{fmtDate(row.trade_date)}</p><div className="mt-2 space-y-1.5 text-muted-foreground"><TooltipRow label="成交额" value={money(row.turnover_cny)} /><TooltipRow label="20日均额" value={money(row.turnover_average_20d)} /><TooltipRow label="上涨 / 下跌 / 平盘" value={`${row.advances} / ${row.declines} / ${row.flat}`} /><TooltipRow label="中位涨跌幅" value={signedPct(row.median_return_pct)} /></div></div>
}

function TooltipRow({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-5"><span>{label}</span><span className="font-data text-foreground">{value}</span></div> }

function SourceRail({ sources }: { sources: MarketCapitalSnapshot['sources'] }) {
  const items = [
    ['stock_daily', '行情'], ['stk_limit', '涨跌停'], ['leverage', '两融'],
    ['etf_flows', 'ETF'], ['shibor', '利率'], ['moneyflow_mkt_dc', '代理资金'],
  ]
  return <div className="grid border-t bg-secondary/20 sm:grid-cols-3 xl:grid-cols-6">{items.map(([key, label]) => { const source = sources[key]; return <div key={key} className="flex items-center gap-2 border-b px-4 py-3 last:border-b-0 sm:border-r xl:border-b-0"><span className={`h-1.5 w-1.5 rounded-full ${source?.available ? 'bg-emerald-500' : 'bg-destructive'}`} /><div className="min-w-0"><p className="text-[10px] font-medium">{label}</p><p className="truncate font-data text-[9px] text-muted-foreground">{source?.available ? `${fmtDate(source.as_of)}${source.lag_days ? ` · +${source.lag_days}天` : ''}` : '不可用'}</p></div></div> })}</div>
}

function MethodologyCenter({ data }: { data: MarketCapitalSnapshot }) {
  const methods = [
    { title: '完整交易日与时间范围', source: 'stock_daily', body: '以最近正常交易日股票数量的中位数为基准，股票记录数达到基准的 95% 才作为完整交易日。页面只展示收盘后日频数据，不代表盘中实时状态。' },
    { title: '成交额与集中度', source: 'stock_daily', body: '成交额 = stock_daily.amount × 1,000，统一换算为人民币元。前20/前50集中度 = 当日成交额最高的20/50只股票成交额 ÷ 全市场成交额。成交额不是净流入。' },
    { title: '市场广度与涨跌停', source: 'stock_daily + stk_limit', body: '上涨、下跌和平盘按个股 pct_chg 与 0 的关系计数；中位涨跌幅取全市场个股涨跌幅中位数。涨跌停要求收盘价精确等于当日涨停价或跌停价。' },
    { title: '融资余额与融资净额', source: 'margin + margin_detail', body: '优先采用交易所汇总，缺失交易所才由个股明细补齐，避免重复计数。融资净额 = 融资买入额 − 融资偿还额；5日融资净额为最近5个已披露日之和。' },
    { title: 'ETF 申赎估算', source: 'fund_share + fund_nav', body: '估算金额 =（最新份额 − 上一期份额）× 10,000 × 不晚于份额日期的最新单位净值。它是份额变化估算，不等同于交易所逐笔资金净流入；NAV覆盖率同时展示。' },
    { title: '资金价格', source: 'shibor', body: '展示 SHIBOR 隔夜和7天利率；变化基点 =（当日利率 − 前一披露日利率）× 100。来源滞后按自然日计算。' },
    { title: '供应商“主力资金”代理', source: 'moneyflow_mkt_dc', body: '供应商根据订单大小自行分类，页面仅原样换算单位并独立展示，不与成交额、融资或ETF估算合并，也不给出交易决策结论。' },
  ]
  return <section className="rounded-2xl border bg-card/82 p-5 shadow-sm md:p-6"><div className="flex flex-col gap-3 border-b pb-5 sm:flex-row sm:items-end"><div className="flex items-start gap-3"><div className="rounded-lg border bg-secondary/55 p-2 text-[hsl(var(--copper-foreground))]"><BookOpen className="h-4 w-4" /></div><div><h2 className="font-display text-xl font-semibold">数据口径中心</h2><p className="mt-1 text-xs text-muted-foreground">每一个数字如何计算、来自哪里、有哪些边界。</p></div></div><div className="sm:ml-auto"><Badge variant="outline" className="font-data">完整日阈值 {Math.round(Number(data.methodology?.complete_day_threshold || .95) * 100)}%</Badge></div></div><div className="mt-4 grid gap-3 lg:grid-cols-2">{methods.map(method => <details key={method.title} className="group rounded-xl border bg-background/45 open:bg-secondary/25"><summary className="flex cursor-pointer list-none items-center gap-3 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"><Database className="h-4 w-4 shrink-0 text-[hsl(var(--copper-foreground))]" /><span className="text-sm font-medium">{method.title}</span><span className="ml-auto font-data text-[9px] text-muted-foreground">{method.source}</span></summary><p className="border-t px-4 py-3 text-xs leading-6 text-muted-foreground">{method.body}</p></details>)}</div><div className="mt-4 rounded-xl border border-dashed p-4 text-xs leading-5 text-muted-foreground"><span className="font-semibold text-foreground">统一边界：</span>数值为空时显示“不可用”，不会以 0 或其他指标替代；各模块日期与滞后独立展示；页面不给出任何交易决策结论。</div></section>
}

function Panel({ title, icon, source, children }: { title: string; icon: ReactNode; source?: SourceMeta; children: ReactNode }) { return <section className="rounded-2xl border bg-card/82 p-5 shadow-sm"><div className="mb-5 flex items-center gap-2 text-[hsl(var(--copper-foreground))]">{icon}<h2 className="font-display text-xl font-semibold text-foreground">{title}</h2><div className="ml-auto"><Source source={source} /></div></div>{children}</section> }
type SourceMeta = { available: boolean; as_of?: string; lag_days?: number }
function Source({ source }: { source?: SourceMeta }) { return <span className={`font-data text-[9px] ${source?.available ? 'text-muted-foreground' : 'text-destructive'}`}>{source?.available ? `${fmtDate(source.as_of)}${source.lag_days ? ` · 滞后${source.lag_days}天` : ''}` : '来源不可用'}</span> }
function Metric({ label, value, delta, suffix, positive, negative }: { label: string; value: string; delta?: number; suffix?: string; positive?: boolean; negative?: boolean }) { const up = (delta ?? 0) >= 0; return <div className="rounded-xl border bg-background/45 p-3"><p className="text-[10px] text-muted-foreground">{label}</p><p className={`mt-2 font-data text-lg font-semibold ${positive ? 'text-rose-600 dark:text-rose-400' : negative ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>{value}</p>{delta !== undefined && delta !== null && <p className={`mt-1 flex items-center text-[10px] ${up ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>{up ? <ArrowUpRight className="mr-1 h-3 w-3" /> : <ArrowDownRight className="mr-1 h-3 w-3" />}{Math.abs(delta).toFixed(1)} {suffix}</p>}</div> }
function Unavailable({ title }: { title: string }) { return <div className="rounded-xl border border-dashed p-5 text-center text-xs text-muted-foreground">{title}</div> }
const fmtDate = (value?: string) => value ? new Date(`${value}T00:00:00`).toLocaleDateString('zh-CN') : '—'
const shortDate = (value: string) => value ? value.slice(5).replace('-', '/') : ''
const money = (value?: number) => value === undefined || value === null ? '—' : Math.abs(value) >= 1e12 ? `${(value/1e12).toFixed(2)} 万亿元` : `${(value/1e8).toFixed(1)} 亿元`
const compactMoney = (value: number) => Math.abs(value) >= 1e12 ? `${(value/1e12).toFixed(1)}万亿` : `${(value/1e8).toFixed(0)}亿`
const compactCount = (value: number) => `${Math.abs(value).toFixed(0)}`
const signedMoney = (value?: number) => value === undefined || value === null ? '—' : `${value >= 0 ? '+' : '-'}${money(Math.abs(value))}`
const pct = (value?: number) => value === undefined || value === null ? '—' : `${(value*100).toFixed(1)}%`
const signedPct = (value?: number) => value === undefined || value === null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
const rate = (value?: number) => value === undefined || value === null ? '—' : `${value.toFixed(3)}%`
const groupName = (value: string) => ({equity:'权益',bond:'债券',commodity:'商品',cross_border:'跨境',other:'其他'}[value] || value)
