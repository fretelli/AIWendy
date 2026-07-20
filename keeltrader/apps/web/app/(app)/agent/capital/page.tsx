'use client'

import Link from 'next/link'
import { useEffect, useState, type ReactNode } from 'react'
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Banknote, Droplets, Gauge, Landmark, Loader2, Radar, RefreshCw, ShipWheel, Waves } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { toast } from 'sonner'

import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { agentPlatformApi, type MarketCapitalSnapshot } from '@/lib/api/agent-platform'

export default function MarketCapitalPage() {
  const [data, setData] = useState<MarketCapitalSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const load = async () => {
    setLoading(true)
    try { setData(await agentPlatformApi.marketCapital(60)) }
    catch (error) { toast.error(error instanceof Error ? error.message : '资金面快照加载失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { queueMicrotask(() => { void load() }) }, [])
  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div>

  return <div className="h-full min-h-0 overflow-y-auto bg-background/80">
    <header className="research-bearing sticky top-0 z-30 flex min-h-16 items-center gap-2 border-b bg-card/95 px-3 shadow-sm backdrop-blur sm:px-5">
      <div className="hidden border-r pr-4 sm:block"><KeelMark /></div>
      <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><Waves className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h1 className="font-display text-lg font-semibold">全市场资金面</h1></div><p className="truncate text-[10px] text-muted-foreground">A 股收盘后客观快照 · 不评分，不推荐</p></div>
      <Badge variant="outline" className="hidden font-data sm:inline-flex">截至 {fmtDate(data?.as_of)}</Badge>
      <Button size="sm" variant="outline" onClick={() => void load()}><RefreshCw className="mr-1.5 h-3.5 w-3.5" />刷新</Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent/holders"><Radar className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">股东雷达</span></Link></Button>
      <Button asChild size="sm" variant="outline"><Link href="/agent"><ShipWheel className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">研究台</span></Link></Button><ThemeMenu />
    </header>
    <div className="mx-auto max-w-[1500px] space-y-5 p-4 md:p-7">
      <section className="overflow-hidden rounded-2xl border border-[hsl(var(--copper)/.32)] bg-card shadow-sm"><div className="grid gap-5 p-5 lg:grid-cols-[1.3fr_.7fr] lg:p-7"><div><p className="font-data text-[10px] uppercase tracking-[.22em] text-[hsl(var(--copper-foreground))]">Observable market conditions</p><h2 className="mt-2 font-display text-3xl font-semibold md:text-4xl">成交额不等于净流入</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">全市场每笔成交都有买方和卖方，无法直接观察一个字面意义上的“全市场净流入”。这里优先展示可验证的成交活跃度、涨跌广度、融资变化、ETF 份额变化与资金利率。</p></div><div className="rounded-xl border bg-secondary/45 p-4"><p className="text-xs font-semibold">事实摘录</p><div className="mt-3 space-y-2">{data?.interpretations?.map(line => <p key={line} className="text-xs leading-5 text-muted-foreground">— {line}</p>)}{!data?.interpretations?.length && <p className="text-xs text-muted-foreground">当前没有足够数据生成事实摘录。</p>}</div></div></div></section>
      {!data?.available && <Unavailable title="全市场基础行情不可用" />}
      {data?.available && <>
        <section className="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
          <Panel title="流动性与成交结构" icon={<Droplets className="h-4 w-4" />} source={data.sources.stock_daily}><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="两市成交额" value={money(data.liquidity.turnover_cny)} delta={data.liquidity.vs_20d_pct} suffix="较20日均值" /><Metric label="5日均额" value={money(data.liquidity.average_5d_cny)} /><Metric label="前20集中度" value={pct(data.liquidity.top20_turnover_share)} /><Metric label="前50集中度" value={pct(data.liquidity.top50_turnover_share)} /></div><div className="mt-5 h-60"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.history}><defs><linearGradient id="turnover" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="hsl(var(--accent))" stopOpacity={.35}/><stop offset="95%" stopColor="hsl(var(--accent))" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" opacity={.22}/><XAxis dataKey="trade_date" tick={{fontSize:10}} minTickGap={28}/><YAxis tickFormatter={v => `${(v/1e12).toFixed(1)}万亿`} tick={{fontSize:10}} width={58}/><Tooltip formatter={v => money(Number(v))} /><Area type="monotone" dataKey="turnover_cny" stroke="hsl(var(--accent))" fill="url(#turnover)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div></Panel>
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
      </>}
    </div>
  </div>
}

function Panel({ title, icon, source, children }: { title: string; icon: ReactNode; source?: SourceMeta; children: ReactNode }) { return <section className="rounded-2xl border bg-card/82 p-5 shadow-sm"><div className="mb-5 flex items-center gap-2 text-[hsl(var(--copper-foreground))]">{icon}<h2 className="font-display text-xl font-semibold text-foreground">{title}</h2><div className="ml-auto"><Source source={source} /></div></div>{children}</section> }
type SourceMeta = { available: boolean; as_of?: string; lag_days?: number }
function Source({ source }: { source?: SourceMeta }) { return <span className={`font-data text-[9px] ${source?.available ? 'text-muted-foreground' : 'text-destructive'}`}>{source?.available ? `${fmtDate(source.as_of)}${source.lag_days ? ` · 滞后${source.lag_days}天` : ''}` : '来源不可用'}</span> }
function Metric({ label, value, delta, suffix, positive, negative }: { label: string; value: string; delta?: number; suffix?: string; positive?: boolean; negative?: boolean }) { const up = (delta ?? 0) >= 0; return <div className="rounded-xl border bg-background/45 p-3"><p className="text-[10px] text-muted-foreground">{label}</p><p className={`font-data mt-2 text-lg font-semibold ${positive ? 'text-rose-600 dark:text-rose-400' : negative ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>{value}</p>{delta !== undefined && delta !== null && <p className={`mt-1 flex items-center text-[10px] ${up ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>{up ? <ArrowUpRight className="mr-1 h-3 w-3" /> : <ArrowDownRight className="mr-1 h-3 w-3" />}{Math.abs(delta).toFixed(1)} {suffix}</p>}</div> }
function Unavailable({ title }: { title: string }) { return <div className="rounded-xl border border-dashed p-5 text-center text-xs text-muted-foreground">{title}</div> }
const fmtDate = (v?: string) => v ? new Date(`${v}T00:00:00`).toLocaleDateString('zh-CN') : '—'
const money = (v?: number) => v === undefined || v === null ? '—' : Math.abs(v) >= 1e12 ? `${(v/1e12).toFixed(2)} 万亿元` : `${(v/1e8).toFixed(1)} 亿元`
const signedMoney = (v?: number) => v === undefined || v === null ? '—' : `${v >= 0 ? '+' : '-'}${money(Math.abs(v))}`
const pct = (v?: number) => v === undefined || v === null ? '—' : `${(v*100).toFixed(1)}%`
const signedPct = (v?: number) => v === undefined || v === null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
const rate = (v?: number) => v === undefined || v === null ? '—' : `${v.toFixed(3)}%`
const groupName = (v: string) => ({equity:'权益',bond:'债券',commodity:'商品',cross_border:'跨境',other:'其他'}[v] || v)
