'use client'

import { Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { agentPlatformApi, type FuturesCurve, type FuturesHistory, type FuturesProduct } from '@/lib/api/agent-platform'
import { DataLedger, MarketShell } from '../_components/market-shell'
import { NativeSeriesChart } from '../_components/native-series-chart'

type Field = 'close' | 'settle' | 'vol' | 'oi'
const fieldNames: Record<Field,string> = { close:'收盘价', settle:'结算价', vol:'成交量', oi:'持仓量' }

export default function FuturesMarketPage() {
  const [products,setProducts] = useState<FuturesProduct[]>([]), [product,setProduct] = useState(''), [history,setHistory] = useState<FuturesHistory|null>(null), [curve,setCurve] = useState<FuturesCurve|null>(null)
  const [field,setField] = useState<Field>('close'), [loading,setLoading] = useState(true), [refreshing,setRefreshing] = useState(false)
  const loadProducts = useCallback(async (refresh=false) => { refresh ? setRefreshing(true) : setLoading(true); try { const result=await agentPlatformApi.futuresProducts(); setProducts(result.items); setProduct(current => current || result.items[0]?.product_code || '') } catch(error) { toast.error(error instanceof Error ? error.message : '期货品种加载失败') } finally { setLoading(false); setRefreshing(false) } },[])
  useEffect(() => { queueMicrotask(() => void loadProducts()) },[loadProducts])
  useEffect(() => { if (!product) return; let active=true; Promise.all([agentPlatformApi.futuresHistory(product),agentPlatformApi.futuresCurve(product)]).then(([nextHistory,nextCurve]) => { if(active){setHistory(nextHistory);setCurve(nextCurve)} }).catch(error => toast.error(error instanceof Error ? error.message : '期货历史加载失败')); return () => {active=false} },[product])
  const current=products.find(item => item.product_code===product), historyRows=useMemo(() => history?.history || [], [history])
  const contractChanges=useMemo(() => historyRows.reduce<Array<{date:string;contract:string}>>((items,row,index) => { if(index===0 || row.contract_code!==historyRows[index-1].contract_code) items.push({date:row.trade_date,contract:row.contract_code}); return items },[]),[historyRows])
  return <MarketShell title="期货市场" subtitle="主力映射历史与当日期限结构 · 合约切换不做价格调整" refreshing={refreshing} onRefresh={() => void loadProducts(true)}>
    {loading ? <Loading/> : <>
      <section className="rounded-2xl border bg-card/88 p-5 shadow-sm"><div className="grid gap-4 lg:grid-cols-[1fr_auto]"><div><h2 className="font-display text-2xl font-semibold">主力合约原始轨迹</h2><p className="mt-2 text-xs leading-6 text-muted-foreground">每个交易点保留当日实际主力合约代码。切换发生时只记录新合约，不改写历史价格，也不拼接虚构数据。</p></div><div className="flex flex-wrap items-center gap-2"><select className="h-9 min-w-64 rounded-md border bg-background px-3 text-xs" value={product} onChange={event=>setProduct(event.target.value)}>{products.map(item=><option key={item.product_code} value={item.product_code}>{item.exchange} · {item.product_code} · {item.name || item.mapping_ts_code}</option>)}</select>{(Object.keys(fieldNames) as Field[]).map(key=><Button key={key} size="sm" variant={field===key?'default':'outline'} onClick={()=>setField(key)}>{fieldNames[key]}</Button>)}</div></div></section>
      <DataLedger source={history?.history_meta.source || 'tushare.fut_mapping+fut_daily'} start={history?.history_meta.start_date} end={history?.history_meta.end_date} points={history?.history_meta.points} scope="数据库当前全部可用历史；未调整" />
      <NativeSeriesChart key={`${product}-${field}`} dates={historyRows.map(row=>row.trade_date)} series={[{key:field,label:fieldNames[field],color:'hsl(var(--accent))',values:historyRows.map(row=>numberOrNull(row[field]))}]} />
      <section className="grid gap-4 xl:grid-cols-[.72fr_1.28fr]"><div className="rounded-2xl border bg-card/82 p-5"><h2 className="font-display text-lg font-semibold">合约切换记录</h2><p className="mt-1 text-[10px] text-muted-foreground">共 {contractChanges.length} 段 · 当前 {current?.mapping_ts_code || '—'}</p><div className="mt-4 max-h-72 overflow-auto border-t">{contractChanges.slice().reverse().map(item=><div key={`${item.date}-${item.contract}`} className="flex justify-between gap-4 border-b py-2 text-[10px]"><span>{item.date}</span><span className="font-data">{item.contract}</span></div>)}</div></div><CurvePanel curve={curve}/></section>
    </>}
  </MarketShell>
}

function CurvePanel({curve}:{curve:FuturesCurve|null}) { const items=curve?.items||[]; return <div className="rounded-2xl border bg-card/82 p-5"><div className="flex items-end justify-between"><div><h2 className="font-display text-lg font-semibold">当日期限结构</h2><p className="mt-1 text-[10px] text-muted-foreground">{curve?.trade_date || '—'} · 全部可用合约</p></div><span className="font-data text-[10px] text-muted-foreground">{items.length} 个合约</span></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[640px] text-left text-[10px]"><thead className="border-b text-muted-foreground"><tr><th className="p-2">合约</th><th>到期日</th><th>收盘</th><th>结算</th><th>成交量</th><th>持仓量</th></tr></thead><tbody>{items.map(item=><tr key={item.contract_code} className="border-b last:border-0"><td className="p-2 font-data">{item.contract_code}</td><td>{item.delist_date||'—'}</td><td>{fmt(item.close)}</td><td>{fmt(item.settle)}</td><td>{fmt(item.vol)}</td><td>{fmt(item.oi)}</td></tr>)}</tbody></table></div></div> }
const numberOrNull=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?value:null
const fmt=(value?:number)=>value===undefined||value===null?'—':value.toLocaleString('zh-CN',{maximumFractionDigits:4})
const Loading=()=> <div className="grid h-80 place-items-center"><Loader2 className="h-7 w-7 animate-spin"/></div>
