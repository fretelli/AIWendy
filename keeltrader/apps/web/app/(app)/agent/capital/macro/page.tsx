'use client'

import { Database, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { agentPlatformApi, type MacroMarketSnapshot } from '@/lib/api/agent-platform'
import { DataLedger, MarketShell } from '../_components/market-shell'
import { NativeSeriesChart } from '../_components/native-series-chart'

const seriesNames: Record<string, string> = { gdp:'国内生产总值', cpi:'居民消费价格', ppi:'工业生产者价格', money_supply:'货币供应', social_financing:'社会融资', pmi:'采购经理指数', shibor:'上海银行间拆放利率', lpr:'贷款市场报价利率', us_treasury:'美国国债收益率', us_real_treasury:'美国实际国债收益率' }
const fieldNames: Record<string, string> = { value:'数值', close:'收盘', gdp:'GDP', gdp_yoy:'GDP同比', pi:'第一产业', si:'第二产业', ti:'第三产业', nt_yoy:'全国同比', nt_mom:'全国环比', ppi_yoy:'PPI同比', ppi_mom:'PPI环比', m0:'M0', m1:'M1', m2:'M2', on:'隔夜', '1w':'1周', '1m':'1月', '3m':'3月', '1y':'1年', lpr_1y:'1年LPR', lpr_5y:'5年LPR' }

export default function MacroMarketPage() {
  const [data, setData] = useState<MacroMarketSnapshot | null>(null), [loading, setLoading] = useState(true), [refreshing, setRefreshing] = useState(false)
  const [seriesKey, setSeriesKey] = useState('gdp'), [field, setField] = useState('')
  const load = useCallback(async (refresh=false) => { refresh ? setRefreshing(true) : setLoading(true); try { setData(await agentPlatformApi.macroMarket()) } catch (error) { toast.error(error instanceof Error ? error.message : '宏观数据加载失败') } finally { setLoading(false); setRefreshing(false) } }, [])
  useEffect(() => { queueMicrotask(() => void load()) }, [load])
  const availableKeys = useMemo(() => Object.keys(data?.series || {}).filter(key => data?.series[key].available), [data])
  const activeSeriesKey = availableKeys.includes(seriesKey) ? seriesKey : availableKeys[0] || seriesKey
  const selected = data?.series[activeSeriesKey], fields = useMemo(() => numericFields(selected?.rows || [], selected?.period_field), [selected])
  const activeField = fields.includes(field) ? field : fields[0] || ''
  const rows = selected?.rows || [], periodField = selected?.period_field || 'date'
  return <MarketShell title="宏观原始数据" subtitle="国内增长、价格、信用与中美利率 · 只展示源字段" refreshing={refreshing} onRefresh={() => void load(true)}>
    {loading && !data ? <Loading /> : <>
      <section className="overflow-hidden rounded-2xl border bg-card/88 shadow-sm"><div className="grid gap-4 p-5 lg:grid-cols-[1fr_auto]"><div><p className="font-display text-2xl font-semibold">宏观数据航道</p><p className="mt-2 max-w-3xl text-xs leading-6 text-muted-foreground">选择数据表与源字段，图表按数据库中可用的完整时间范围绘制。上游提供的同比或环比字段会原样出现，本地不再生成派生序列。</p></div><div className="flex flex-wrap gap-2 lg:max-w-2xl lg:justify-end">{availableKeys.map(key => <Button key={key} size="sm" variant={activeSeriesKey === key ? 'default' : 'outline'} onClick={() => setSeriesKey(key)}>{seriesNames[key] || key}</Button>)}</div></div></section>
      {selected && <><DataLedger source={`tushare.${selected.table}`} start={selected.start} end={selected.end} points={selected.points} scope="数据库当前全部可用历史" />
        <section className="rounded-2xl border bg-card/88 p-4 shadow-sm md:p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><div><h2 className="font-display text-xl font-semibold">{seriesNames[activeSeriesKey] || activeSeriesKey}</h2><p className="mt-1 font-data text-[10px] text-muted-foreground">频率 {selected.frequency} · 时间字段 {periodField}</p></div><label className="sm:ml-auto"><span className="sr-only">源字段</span><select value={activeField} onChange={event => setField(event.target.value)} className="h-9 min-w-48 rounded-md border bg-background px-3 text-xs">{fields.map(key => <option key={key} value={key}>{fieldNames[key] || key}</option>)}</select></label></div></section>
        <NativeSeriesChart key={`${activeSeriesKey}-${activeField}`} dates={rows.map(row => String(row[periodField] ?? ''))} series={[{ key: activeField, label: fieldNames[activeField] || activeField, color: 'hsl(var(--accent))', values: rows.map(row => numberOrNull(row[activeField])) }]} />
        <section className="rounded-2xl border bg-card/82 p-5"><div className="flex items-center gap-2"><Database className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h2 className="font-display text-lg font-semibold">最近源记录</h2></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-[10px]"><thead className="border-b text-muted-foreground"><tr>{Object.keys(rows.at(-1) || {}).map(key => <th key={key} className="px-3 py-2 font-medium">{key}</th>)}</tr></thead><tbody>{rows.slice(-12).reverse().map((row,index) => <tr key={`${row[periodField]}-${index}`} className="border-b last:border-0">{Object.keys(rows.at(-1) || {}).map(key => <td key={key} className="whitespace-nowrap px-3 py-2 font-data">{String(row[key] ?? '—')}</td>)}</tr>)}</tbody></table></div></section>
      </>}
    </>}
  </MarketShell>
}

const numericFields = (rows: Array<Record<string, string | number | null>>, period?: string) => { const sample = rows.slice(-20); return Array.from(new Set(sample.flatMap(row => Object.keys(row)))).filter(key => key !== period && !['ts_code','exchange'].includes(key) && sample.some(row => typeof row[key] === 'number')) }
const numberOrNull = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
const Loading = () => <div className="grid h-80 place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div>
