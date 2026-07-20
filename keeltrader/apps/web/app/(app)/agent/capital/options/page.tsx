'use client'

import { AlertTriangle, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { agentPlatformApi, type OptionSeries, type OptionsChain, type OptionsHistory, type OptionsSeriesResponse } from '@/lib/api/agent-platform'
import { DataLedger, MarketShell } from '../_components/market-shell'
import { NativeSeriesChart } from '../_components/native-series-chart'

type Field='volume'|'amount'|'oi'|'contracts'
const fieldNames:Record<Field,string>={volume:'成交量',amount:'成交额',oi:'持仓量',contracts:'合约数'}

export default function OptionsMarketPage(){
  const [catalog,setCatalog]=useState<OptionsSeriesResponse|null>(null),[code,setCode]=useState(''),[history,setHistory]=useState<OptionsHistory|null>(null),[chain,setChain]=useState<OptionsChain|null>(null)
  const [field,setField]=useState<Field>('volume'),[loading,setLoading]=useState(true),[refreshing,setRefreshing]=useState(false),[offset,setOffset]=useState(0),[query,setQuery]=useState('')
  const loadCatalog=useCallback(async(refresh=false)=>{refresh?setRefreshing(true):setLoading(true);try{const result=await agentPlatformApi.optionsSeries();setCatalog(result);setCode(current=>current||result.items[0]?.opt_code||'')}catch(error){toast.error(error instanceof Error?error.message:'期权序列加载失败')}finally{setLoading(false);setRefreshing(false)}},[])
  useEffect(()=>{queueMicrotask(()=>void loadCatalog())},[loadCatalog])
  useEffect(()=>{if(!code)return;let active=true;Promise.all([agentPlatformApi.optionsHistory(code),agentPlatformApi.optionsChain(code,{limit:200})]).then(([nextHistory,nextChain])=>{if(active){setHistory(nextHistory);setChain(nextChain)}}).catch(error=>toast.error(error instanceof Error?error.message:'期权数据加载失败'));return()=>{active=false}},[code])
  useEffect(()=>{if(!code||offset===0)return;agentPlatformApi.optionsChain(code,{limit:200,offset}).then(setChain).catch(error=>toast.error(error instanceof Error?error.message:'期权链翻页失败'))},[code,offset])
  const rows=history?.history||[],selected=catalog?.items.find(item=>item.opt_code===code)
  const visibleSeries=useMemo(()=>{const needle=query.trim().toLowerCase();return (catalog?.items||[]).filter(item=>!needle||item.opt_code.toLowerCase().includes(needle)||String(item.exchange||'').toLowerCase().includes(needle)).slice(0,250)},[catalog,query])
  return <MarketShell title="期权市场" subtitle="看涨与看跌原始汇总、行权价与到期日链条" refreshing={refreshing} onRefresh={()=>void loadCatalog(true)}>
    {loading?<Loading/>:<>
      <section className="rounded-2xl border bg-card/88 p-5 shadow-sm"><div className="grid gap-4 lg:grid-cols-[1fr_auto]"><div><h2 className="font-display text-2xl font-semibold">期权源数据面板</h2><p className="mt-2 text-xs leading-6 text-muted-foreground">日历史仅分别汇总看涨与看跌合约的源成交、金额、持仓和合约数量；期权链逐合约展示行权价、到期日与当日行情。</p></div><div className="flex flex-wrap items-center gap-2"><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="搜索序列代码或交易所" className="h-9 w-52 rounded-md border bg-background px-3 text-xs"/><select className="h-9 min-w-64 rounded-md border bg-background px-3 text-xs" value={code} onChange={event=>{setOffset(0);setCode(event.target.value)}}><option value={code}>{selected ? `${selected.exchange} · ${selected.opt_code} · ${selected.active_contracts} 活跃` : code}</option>{visibleSeries.filter(item=>item.opt_code!==code).map(item=><option key={item.opt_code} value={item.opt_code}>{item.exchange} · {item.opt_code} · {item.active_contracts} 活跃</option>)}</select>{(Object.keys(fieldNames) as Field[]).map(key=><Button key={key} size="sm" variant={field===key?'default':'outline'} onClick={()=>setField(key)}>{fieldNames[key]}</Button>)}</div></div></section>
      <div className="flex gap-3 rounded-xl border border-amber-500/35 bg-amber-500/8 p-4 text-xs leading-5 text-amber-800 dark:text-amber-200"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0"/><div><p className="font-medium">期权历史仍在持续补全</p><p className="mt-1 opacity-80">当前展示数据库已同步的全部可用记录（current_available），目标起点 {catalog?.history_meta.backfill_target || '2015-02-09'}。缺失日期不会用其他数据补齐。</p></div></div>
      <DataLedger source={history?.history_meta.source||catalog?.history_meta.source||'tushare.opt_daily+opt_basic'} start={history?.history_meta.start_date} end={history?.history_meta.end_date} points={history?.history_meta.points} scope="当前已同步的全部可用历史"/>
      <NativeSeriesChart key={`${code}-${field}`} dates={rows.map(row=>row.trade_date)} series={[{key:`call_${field}`,label:'看涨',color:'#d95d6f',values:rows.map(row=>numberOrNull(row[`call_${field}` as keyof typeof row]))},{key:`put_${field}`,label:'看跌',color:'#238d72',values:rows.map(row=>numberOrNull(row[`put_${field}` as keyof typeof row]))}]}/>
      <ChainPanel chain={chain} selected={selected} offset={offset} setOffset={setOffset}/>
    </>}
  </MarketShell>
}

function ChainPanel({chain,selected,offset,setOffset}:{chain:OptionsChain|null;selected?:OptionSeries;offset:number;setOffset:(value:number)=>void}){const items=chain?.items||[],limit=chain?.limit||200;return <section className="rounded-2xl border bg-card/82 p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-end"><div><h2 className="font-display text-lg font-semibold">原始期权链</h2><p className="mt-1 text-[10px] text-muted-foreground">{chain?.trade_date||'—'} · {selected?.exchange||'—'} · 共 {chain?.total||0} 条</p></div><div className="flex gap-2 sm:ml-auto"><Button size="sm" variant="outline" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-limit))}>上一页</Button><Button size="sm" variant="outline" disabled={offset+limit>=(chain?.total||0)} onClick={()=>setOffset(offset+limit)}>下一页</Button></div></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[940px] text-left text-[10px]"><thead className="border-b text-muted-foreground"><tr><th className="p-2">合约</th><th>方向</th><th>行权价</th><th>到期日</th><th>收盘</th><th>结算</th><th>成交量</th><th>成交额</th><th>持仓量</th></tr></thead><tbody>{items.map(item=><tr key={item.ts_code} className="border-b last:border-0"><td className="p-2 font-data">{item.ts_code}</td><td className={item.call_put==='C'?'text-rose-600 dark:text-rose-400':'text-emerald-600 dark:text-emerald-400'}>{item.call_put==='C'?'看涨':'看跌'}</td><td>{fmt(item.exercise_price)}</td><td>{item.maturity_date||'—'}</td><td>{fmt(item.close)}</td><td>{fmt(item.settle)}</td><td>{fmt(item.vol)}</td><td>{fmt(item.amount)}</td><td>{fmt(item.oi)}</td></tr>)}</tbody></table></div></section>}
const numberOrNull=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?value:null
const fmt=(value?:number)=>value===undefined||value===null?'—':value.toLocaleString('zh-CN',{maximumFractionDigits:4})
const Loading=()=> <div className="grid h-80 place-items-center"><Loader2 className="h-7 w-7 animate-spin"/></div>
