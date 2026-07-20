'use client'

import { Database, Loader2 } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { agentPlatformApi, marketsApi, type MacroCatalog, type MacroSeriesDetail } from '@/lib/api/agent-platform'
import { DataLedger, MarketShell } from '../_components/market-shell'
import { NativeSeriesChart } from '../_components/native-series-chart'

export default function MacroMarketPage(){
  const router=useRouter(),params=useSearchParams(),[catalog,setCatalog]=useState<MacroCatalog|null>(null),[detail,setDetail]=useState<MacroSeriesDetail|null>(null),[loading,setLoading]=useState(true),[refreshing,setRefreshing]=useState(false)
  const key=params.get('series')||'',field=params.get('field')||''
  const setSelection=useCallback((nextKey:string,nextField:string)=>{const query=new URLSearchParams(params.toString());query.set('series',nextKey);query.set('field',nextField);router.replace(`/agent/capital/macro?${query}`)},[params,router])
  const loadCatalog=useCallback(async(refresh=false)=>{refresh?setRefreshing(true):setLoading(true);try{const next=await marketsApi.macroCatalog();setCatalog(next);const selected=next.items.find(item=>item.key===key&&item.fields.includes(field))||next.items.find(item=>item.available&&item.fields.length);if(selected&&(!key||!field))setSelection(selected.key,selected.fields[0])}catch(error){toast.error(error instanceof Error?error.message:'宏观目录加载失败')}finally{setLoading(false);setRefreshing(false)}},[field,key,setSelection])
  useEffect(()=>{queueMicrotask(()=>void loadCatalog())},[loadCatalog])
  useEffect(()=>{if(!key||!field)return;let active=true;marketsApi.macroSeries(key,field).then(value=>{if(active)setDetail(value)}).catch(error=>toast.error(error instanceof Error?error.message:'宏观序列加载失败'));return()=>{active=false}},[key,field])
  const selected=catalog?.items.find(item=>item.key===key),dates=useMemo(()=>detail?.rows.map(row=>String(row.period))||[],[detail]),values=useMemo(()=>detail?.rows.map(row=>typeof row.value==='number'?row.value:null)||[],[detail])
  const bring=async()=>{if(!detail)return;const snapshot=await agentPlatformApi.createContextSnapshot({resource_type:'macro',resource_id:detail.key,field:detail.field,visible_start:detail.start,visible_end:detail.end,source:detail.source,methodology:'展示数据库当前全部可用原始历史；不在本地生成派生序列。'});router.push(`/agent?context_snapshot=${snapshot.id}&context_label=${encodeURIComponent(`${detail.label}·${detail.field}`)}`)}
  return <MarketShell title="宏观原始数据" subtitle="先加载轻量目录，选中后仅请求一个源字段" refreshing={refreshing} onRefresh={()=>void loadCatalog(true)} onResearch={detail?()=>void bring():undefined} trail={{object:detail?`${detail.label} · ${detail.field}`:'宏观序列',asOf:detail?.end,source:detail?.source}}>
    {loading&&!catalog?<Loading/>:<PanelGroup direction="horizontal" autoSaveId="macro-market-workspace" className="min-h-[calc(100dvh-13rem)] overflow-hidden rounded-xl border bg-card/70">
      <Panel defaultSize={20} minSize={15} maxSize={32}><aside className="h-full overflow-y-auto border-r p-2"><p className="px-2 py-3 text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">宏观目录</p>{catalog?.items.filter(item=>item.available).map(item=><button key={item.key} onClick={()=>setSelection(item.key,item.fields[0])} className={`mb-1 w-full rounded-lg px-3 py-2.5 text-left ${item.key===key?'bg-[hsl(var(--accent)/.12)] shadow-[inset_2px_0_hsl(var(--copper))]':'hover:bg-secondary'}`}><span className="block text-xs font-medium">{item.label}</span><span className="font-data text-[9px] text-muted-foreground">{item.start} — {item.end} · {item.points}</span></button>)}</aside></Panel>
      <Handle/><Panel minSize={42}><main className="h-full overflow-y-auto p-4">{detail?<><DataLedger source={detail.source} start={detail.start} end={detail.end} points={detail.points} scope="全部可用原始历史"/><div className="mt-4"><NativeSeriesChart key={`${key}-${field}`} dates={dates} series={[{key:field,label:field,color:'hsl(var(--accent))',values}]}/></div></>:<Loading/>}</main></Panel>
      <Handle/><Panel defaultSize={24} minSize={18} maxSize={34}><aside className="h-full overflow-y-auto border-l p-4"><h2 className="font-display text-lg font-semibold">源字段与记录</h2><select value={field} onChange={event=>key&&setSelection(key,event.target.value)} className="mt-3 h-9 w-full rounded-md border bg-background px-3 text-xs">{selected?.fields.map(item=><option key={item}>{item}</option>)}</select><div className="mt-5 flex items-center gap-2 text-xs"><Database className="h-4 w-4 text-[hsl(var(--copper-foreground))]"/>最近 12 条源记录</div><div className="mt-3 space-y-2">{detail?.recent_source_rows.map((row,index)=><pre key={index} className="overflow-x-auto rounded-lg border bg-background/70 p-2 font-data text-[9px]">{JSON.stringify(row,null,1)}</pre>)}</div></aside></Panel>
    </PanelGroup>}
  </MarketShell>
}
const Handle=()=> <PanelResizeHandle className="w-1 bg-border/60 hover:bg-[hsl(var(--copper)/.6)]"/>
const Loading=()=> <div className="grid h-80 place-items-center"><Loader2 className="h-7 w-7 animate-spin"/></div>
