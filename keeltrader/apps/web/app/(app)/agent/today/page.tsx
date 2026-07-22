"use client";

import { CalendarClock, CheckCheck, Clock3, Database, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { agentPlatformApi, marketsApi, type DataStatus, type ResearchCalendarItem, type ResearchEvent } from "@/lib/api/agent-platform";

export default function TodayPage() {
  const [events, setEvents] = useState<ResearchEvent[]>([]), [unread, setUnread] = useState(0);
  const [calendar, setCalendar] = useState<ResearchCalendarItem[]>([]), [status, setStatus] = useState<DataStatus | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false), [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      const [feed, dates, sources] = await Promise.all([agentPlatformApi.researchEvents(unreadOnly), agentPlatformApi.researchCalendar(), marketsApi.dataStatus()]);
      setEvents(feed.items); setUnread(feed.unread); setCalendar(dates.items); setStatus(sources);
    } catch (error) { toast.error(error instanceof Error ? error.message : "今日研究加载失败"); }
    finally { setLoading(false); }
  }, [unreadOnly]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  const markAll = async () => { await agentPlatformApi.readResearchEvents(); await load(); };
  return <main className="h-full overflow-y-auto bg-background p-4 md:p-7">
    <header className="mx-auto max-w-7xl border-b pb-5"><p className="font-data text-[9px] uppercase tracking-[.24em] text-[hsl(var(--copper-foreground))]">Research watch</p><div className="mt-2 flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-display text-3xl font-semibold">今日研究值更</h1><p className="mt-2 text-xs text-muted-foreground">同一事件同时保留上游源日期与 KeelTrader 发现时间，不做评分或推荐排序。</p></div><div className="flex gap-2"><Button variant={unreadOnly ? "default" : "outline"} onClick={() => setUnreadOnly(!unreadOnly)}>未读 {unread}</Button><Button variant="outline" onClick={() => void markAll()}><CheckCheck className="mr-2 h-4 w-4" />全部已读</Button></div></div></header>
    {loading ? <div className="grid h-72 place-items-center"><Loader2 className="h-6 w-6 animate-spin" /></div> : <div className="mx-auto mt-6 grid max-w-7xl gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="space-y-3">{events.length ? events.map((event) => <article key={event.id} className={`rounded-2xl border bg-card/70 p-4 ${event.read_at ? "opacity-70" : "border-l-2 border-l-[hsl(var(--copper))]"}`}><div className="flex flex-wrap items-center gap-2 text-[9px] uppercase tracking-[.12em] text-muted-foreground"><span>{event.category}</span><span>·</span><span>{event.event_type}</span></div><h2 className="mt-2 font-display text-lg font-semibold">{event.title}</h2><p className="mt-2 text-xs leading-6 text-muted-foreground">{event.summary}</p><div className="mt-4 grid gap-2 rounded-xl bg-secondary/35 p-3 font-data text-[10px] sm:grid-cols-2"><span className="flex items-center gap-2"><CalendarClock className="h-3.5 w-3.5" />源日期：{event.source_date || "源未提供"}</span><span className="flex items-center gap-2"><Clock3 className="h-3.5 w-3.5" />发现：{new Date(event.detected_at).toLocaleString("zh-CN")}</span></div></article>) : <div className="rounded-2xl border border-dashed p-12 text-center text-sm text-muted-foreground">当前没有研究事件。新变化会在后台物化后进入这里。</div>}</section>
      <aside className="space-y-5"><section className="rounded-2xl border bg-card/70 p-4"><h2 className="flex items-center gap-2 font-display text-lg font-semibold"><CalendarClock className="h-4 w-4" />复核与催化</h2><div className="mt-4 space-y-3">{calendar.slice(0, 12).map((item) => <div key={`${item.kind}-${item.resource_id}-${item.date}`} className="border-l pl-3 text-xs"><p className="font-medium">{item.title}</p><p className="mt-1 font-data text-[9px] text-muted-foreground">{new Date(item.date).toLocaleString("zh-CN")} · {item.source_type}</p></div>)}{!calendar.length && <p className="text-xs text-muted-foreground">尚未设置复核日期或研究计划。</p>}</div></section>
      <section className="rounded-2xl border bg-card/70 p-4"><h2 className="flex items-center gap-2 font-display text-lg font-semibold"><Database className="h-4 w-4" />数据源值守</h2><p className="mt-2 text-[10px] leading-5 text-muted-foreground">{status?.methodology}</p><div className="mt-3 space-y-2">{status?.opportunity_refresh.map((row) => <div key={row.domain} className="flex justify-between border-b pb-2 font-data text-[9px] last:border-0"><span>{row.domain}</span><span>{row.status} · {row.last_succeeded_at ? new Date(row.last_succeeded_at).toLocaleString("zh-CN") : "未成功"}</span></div>)}</div></section></aside>
    </div>}
  </main>;
}
