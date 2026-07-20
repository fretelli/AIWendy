'use client'

import Link from 'next/link'
import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Banknote, BookOpen,
  Database, Droplets, Gauge, Landmark, Loader2, Radar, RefreshCw, ShipWheel,
  SlidersHorizontal, Waves,
} from 'lucide-react'
import { toast } from 'sonner'

import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { agentPlatformApi, type MarketCapitalSnapshot } from '@/lib/api/agent-platform'

type ChartMode = 'turnover' | 'breadth'
type HistoryPoint = MarketCapitalSnapshot['history'][number]

const CHART_MODES: Array<{ value: ChartMode; label: string }> = [
  { value: 'turnover', label: '成交水位' },
  { value: 'breadth', label: '涨跌广度' },
]

export default function MarketCapitalPage() {
  const [data, setData] = useState<MarketCapitalSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true)
    try { setData(await agentPlatformApi.marketCapital()) }
    catch (error) { toast.error(error instanceof Error ? error.message : '资金面快照加载失败') }
    finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { queueMicrotask(() => { void load() }) }, [load])
  if (loading && !data) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div>

  return <div className="h-full min-h-0 overflow-y-auto bg-background/80">
    <header className="research-bearing sticky top-0 z-30 flex min-h-16 items-center gap-2 border-b bg-card/95 px-3 shadow-sm backdrop-blur sm:px-5">
      <div className="hidden border-r pr-4 sm:block"><KeelMark /></div>
      <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><Waves className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h1 className="font-display text-lg font-semibold">全市场资金面</h1></div><p className="truncate text-[10px] text-muted-foreground">A 股收盘后客观快照 · 不评分，不推荐</p></div>
      <Badge variant="outline" className="hidden font-data sm:inline-flex">截至 {fmtDate(data?.as_of)}</Badge>
      <Button size="sm" variant="outline" disabled={refreshing} onClick={() => void load(true)}><RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />刷新</Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent/holders"><Radar className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">股东雷达</span></Link></Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent"><ShipWheel className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">研究台</span></Link></Button><ThemeMenu />
    </header>

    <div className="mx-auto max-w-[1580px] space-y-5 p-4 md:p-7">
      {!data?.available && <Unavailable title="全市场基础行情不可用" />}
      {data?.available && <>
        <MarketTape key={`${data.history_meta.start_date}-${data.as_of}`} data={data} refreshing={refreshing} />
        <MarketContext data={data} />

        <section className="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
          <Panel title="流动性与成交结构" icon={<Droplets className="h-4 w-4" />} source={data.sources.stock_daily}><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="全市场成交额" value={money(data.liquidity.turnover_cny)} /><Metric label="覆盖股票" value={`${data.history.at(-1)?.stock_count || '—'} 只`} /><Metric label="前20成交占比" value={pct(data.liquidity.top20_turnover_share)} /><Metric label="前50成交占比" value={pct(data.liquidity.top50_turnover_share)} /></div></Panel>
          <Panel title="市场广度" icon={<Activity className="h-4 w-4" />} source={data.sources.stock_daily}><div className="grid grid-cols-3 gap-3"><Metric label="上涨" value={String(data.breadth.advances)} positive /><Metric label="下跌" value={String(data.breadth.declines)} negative /><Metric label="平盘" value={String(data.breadth.flat)} /></div><div className="mt-4 grid grid-cols-2 gap-3 border-t pt-4"><Metric label="涨停" value={data.breadth.limit_source_available ? String(data.breadth.limit_up) : '不可用'} /><Metric label="跌停" value={data.breadth.limit_source_available ? String(data.breadth.limit_down) : '不可用'} /></div></Panel>
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

function MarketContext({ data }: { data: MarketCapitalSnapshot }) {
  return <section className="overflow-hidden rounded-2xl border border-[hsl(var(--copper)/.32)] bg-card shadow-sm">
    <div className="grid gap-4 p-4 md:grid-cols-[1.25fr_.75fr] md:items-center md:p-5">
      <div><p className="font-data text-[9px] uppercase tracking-[.2em] text-[hsl(var(--copper-foreground))]">Interpretation boundary</p><h2 className="mt-1 font-display text-xl font-semibold md:text-2xl">成交额不等于净流入</h2><p className="mt-2 max-w-3xl text-xs leading-5 text-muted-foreground">全市场每笔成交都有买方和卖方。这里展示可验证的成交活跃度、涨跌广度、融资变化、ETF份额变化与资金利率。</p></div>
      <div className="rounded-xl border bg-secondary/45 p-3"><p className="text-[10px] font-semibold">事实摘录</p><div className="mt-2 space-y-1">{data.interpretations?.map(line => <p key={line} className="text-[10px] leading-4 text-muted-foreground">— {line}</p>)}{!data.interpretations?.length && <p className="text-[10px] text-muted-foreground">当前没有足够数据生成事实摘录。</p>}</div></div>
    </div>
    <SourceRail sources={data.sources} />
  </section>
}

function MarketTape({ data, refreshing }: { data: MarketCapitalSnapshot; refreshing: boolean }) {
  const [mode, setMode] = useState<ChartMode>('turnover')
  const chartHost = useRef<HTMLDivElement>(null)
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 })
  const chartData = data.history
  const [rangeStart, setRangeStart] = useState(0)
  const [rangeEnd, setRangeEnd] = useState(Math.max(0, chartData.length - 1))
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  useEffect(() => {
    const node = chartHost.current
    if (!node) return
    const measure = () => setChartSize(current => {
      const next = { width: Math.floor(node.clientWidth), height: Math.floor(node.clientHeight) }
      return current.width === next.width && current.height === next.height ? current : next
    })
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return <section data-chart-priority="primary" className="overflow-hidden rounded-2xl border bg-card/88 shadow-sm">
    <div className="flex flex-col gap-3 border-b p-4 md:p-5 lg:flex-row lg:items-center">
      <div className="flex min-w-0 items-start gap-3"><div className="rounded-lg border bg-secondary/55 p-2 text-[hsl(var(--copper-foreground))]"><SlidersHorizontal className="h-4 w-4" /></div><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-display text-xl font-semibold">全量原始历史</h2><Badge variant="outline" className="font-data text-[9px]">{data.history_meta.points} 个交易日</Badge></div><p className="mt-1 text-xs text-muted-foreground">{fmtDate(data.history_meta.start_date)} — {fmtDate(data.history_meta.end_date)} · 悬停查看原始单日数据，底部滑块缩放区间。</p></div></div>
      <div className="flex flex-wrap gap-2 lg:ml-auto">{CHART_MODES.map(item => <Button key={item.value} size="sm" variant={mode === item.value ? 'default' : 'outline'} onClick={() => setMode(item.value)}>{item.label}</Button>)}</div>
    </div>
    <div className={`h-[350px] p-2 transition-opacity sm:h-[390px] md:h-[450px] md:p-5 ${refreshing ? 'opacity-55' : ''}`}>
      <div ref={chartHost} data-chart-canvas="market-capital" className="relative h-[calc(100%-48px)] min-h-0 w-full min-w-0">
        {chartSize.width > 0 && chartSize.height > 0 ? <NativeCapitalChart width={chartSize.width} height={chartSize.height} mode={mode} data={chartData.slice(rangeStart, rangeEnd + 1)} hoverIndex={hoverIndex} onHover={setHoverIndex} /> : <div className="grid h-full place-items-center text-xs text-muted-foreground"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />图表尺寸初始化中</div>}
      </div>
      <div className="grid h-12 grid-cols-[1fr_auto_1fr] items-center gap-3 border-t px-2 pt-2 text-[9px] text-muted-foreground">
        <label className="flex items-center gap-2"><span className="shrink-0">起点</span><input aria-label="图表起点" className="w-full accent-[hsl(var(--copper-foreground))]" type="range" min={0} max={Math.max(0, chartData.length - 1)} value={rangeStart} onChange={event => { setRangeStart(Math.min(Number(event.target.value), Math.max(0, rangeEnd - 1))); setHoverIndex(null) }} /></label>
        <span className="font-data">显示 {Math.max(0, rangeEnd - rangeStart + 1)} 日</span>
        <label className="flex items-center gap-2"><input aria-label="图表终点" className="w-full accent-[hsl(var(--copper-foreground))]" type="range" min={0} max={Math.max(0, chartData.length - 1)} value={rangeEnd} onChange={event => { setRangeEnd(Math.max(Number(event.target.value), Math.min(chartData.length - 1, rangeStart + 1))); setHoverIndex(null) }} /><span className="shrink-0">终点</span></label>
      </div>
    </div>
    <div className="flex flex-wrap gap-x-5 gap-y-2 border-t bg-secondary/25 px-5 py-3 text-[10px] text-muted-foreground"><span>成交额：全 A 股日成交金额原始合计</span><span>涨跌广度：按个股日涨跌幅正负原始计数</span><span>仅展示源数据历史与单日事实</span></div>
  </section>
}

function NativeCapitalChart({ width, height, mode, data, hoverIndex, onHover }: { width: number; height: number; mode: ChartMode; data: HistoryPoint[]; hoverIndex: number | null; onHover: (index: number | null) => void }) {
  const margin = { left: width < 520 ? 48 : 62, right: 16, top: 18, bottom: 32 }
  const plotWidth = Math.max(1, width - margin.left - margin.right)
  const plotHeight = Math.max(1, height - margin.top - margin.bottom)
  const values = mode === 'turnover'
    ? data.map(row => row.turnover_cny)
    : data.flatMap(row => [row.advances, -row.declines])
  const finite = values.filter(Number.isFinite)
  let minimum = mode === 'turnover' ? 0 : Math.min(0, ...finite)
  let maximum = Math.max(0, ...finite)
  if (mode === 'breadth') { const bound = Math.max(Math.abs(minimum), Math.abs(maximum), 1); minimum = -bound; maximum = bound }
  if (minimum === maximum) { minimum -= 1; maximum += 1 }
  const padding = mode === 'turnover' ? maximum * .06 : (maximum - minimum) * .08
  const yMin = mode === 'turnover' ? 0 : minimum - padding
  const yMax = maximum + padding
  const x = (index: number) => margin.left + (data.length <= 1 ? plotWidth / 2 : index / (data.length - 1) * plotWidth)
  const y = (value: number) => margin.top + (yMax - value) / (yMax - yMin) * plotHeight
  const linePath = (getter: (row: HistoryPoint) => number) => data.map((row, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(getter(row)).toFixed(1)}`).join(' ')
  const turnoverPath = linePath(row => row.turnover_cny)
  const areaPath = data.length ? `M${x(0)},${y(yMin)} ${data.map((row, index) => `L${x(index).toFixed(1)},${y(row.turnover_cny).toFixed(1)}`).join(' ')} L${x(data.length - 1)},${y(yMin)} Z` : ''
  const yTicks = Array.from({ length: 5 }, (_, index) => yMin + (yMax - yMin) * index / 4)
  const dateTickIndexes = Array.from(new Set(Array.from({ length: Math.min(5, data.length) }, (_, index) => Math.round(index * Math.max(0, data.length - 1) / Math.max(1, Math.min(5, data.length) - 1)))))
  const hovered = hoverIndex === null ? null : data[hoverIndex]
  const hoverX = hoverIndex === null ? 0 : x(hoverIndex)
  const formatTick = mode === 'turnover' ? compactMoney : compactCount
  const onPointerMove = (event: ReactPointerEvent<SVGRectElement>) => {
    if (!data.length) return
    const rect = event.currentTarget.getBoundingClientRect()
    const localX = event.clientX - rect.left - margin.left
    const index = Math.round(Math.max(0, Math.min(1, localX / plotWidth)) * Math.max(0, data.length - 1))
    onHover(index)
  }

  return <>
    <svg data-chart-series="market-capital" role="img" aria-label="全市场资金面历史图" width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block overflow-visible">
      <defs><linearGradient id="native-capital-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity=".32" /><stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity=".02" /></linearGradient></defs>
      {yTicks.map(tick => <g key={tick}><line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} stroke="hsl(var(--border))" strokeDasharray="3 5" /><text x={margin.left - 8} y={y(tick) + 3} textAnchor="end" fontSize="9" fill="hsl(var(--muted-foreground))">{formatTick(tick)}</text></g>)}
      {dateTickIndexes.map(index => <text key={index} x={x(index)} y={height - 7} textAnchor={index === 0 ? 'start' : index === data.length - 1 ? 'end' : 'middle'} fontSize="9" fill="hsl(var(--muted-foreground))">{shortDate(data[index]?.trade_date || '')}</text>)}
      {mode !== 'turnover' && <line x1={margin.left} x2={width - margin.right} y1={y(0)} y2={y(0)} stroke="hsl(var(--muted-foreground))" strokeWidth="1" />}
      {mode === 'turnover' && <><path d={areaPath} fill="url(#native-capital-area)" /><path d={turnoverPath} fill="none" stroke="hsl(var(--accent))" strokeWidth="2.5" strokeLinejoin="round" /></>}
      {mode === 'breadth' && <><path d={linePath(row => row.advances)} fill="none" stroke="#e05a67" strokeWidth="1.8" strokeLinejoin="round" /><path d={linePath(row => -row.declines)} fill="none" stroke="#24906f" strokeWidth="1.8" strokeLinejoin="round" /></>}
      {hovered && <><line x1={hoverX} x2={hoverX} y1={margin.top} y2={height-margin.bottom} stroke="hsl(var(--copper-foreground))" strokeDasharray="3 3" /><circle cx={hoverX} cy={y(mode === 'turnover' ? hovered.turnover_cny : hovered.advances)} r="4" fill="hsl(var(--background))" stroke="hsl(var(--copper-foreground))" strokeWidth="2" /></>}
      <rect x={margin.left} y={margin.top} width={plotWidth} height={plotHeight} fill="transparent" onPointerMove={onPointerMove} onPointerLeave={() => onHover(null)} />
    </svg>
    {hovered && <div className="pointer-events-none absolute top-2 z-10 min-w-48 rounded-xl border bg-popover/96 p-3 text-xs shadow-xl backdrop-blur" style={{ left: Math.max(4, Math.min(width - 205, hoverX + 10)) }}><p className="font-data font-semibold">{fmtDate(hovered.trade_date)}</p><div className="mt-2 space-y-1.5 text-muted-foreground"><TooltipRow label="覆盖股票" value={`${hovered.stock_count} 只`} /><TooltipRow label="成交额" value={money(hovered.turnover_cny)} /><TooltipRow label="上涨 / 下跌 / 平盘" value={`${hovered.advances} / ${hovered.declines} / ${hovered.flat}`} /></div></div>}
  </>
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
    { title: '完整交易日与时间范围', source: 'stock_daily', body: '以最近交易日中的最大股票记录数为完整度基准，记录数达到基准的 95% 才作为完整交易日。页面只展示收盘后日频数据，不代表盘中实时状态。' },
    { title: '成交额与集中度', source: 'stock_daily', body: '成交额 = stock_daily.amount × 1,000，统一换算为人民币元。前20/前50集中度 = 当日成交额最高的20/50只股票成交额 ÷ 全市场成交额。成交额不是净流入。' },
    { title: '市场广度与涨跌停', source: 'stock_daily + stk_limit', body: '上涨、下跌和平盘按个股 pct_chg 与 0 的关系直接计数。涨跌停要求收盘价精确等于当日涨停价或跌停价。' },
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
const rate = (value?: number) => value === undefined || value === null ? '—' : `${value.toFixed(3)}%`
const groupName = (value: string) => ({equity:'权益',bond:'债券',commodity:'商品',cross_border:'跨境',other:'其他'}[value] || value)
