"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { DashboardPage, EmptyPanel, MetricCard, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { agentPlatformApi, marketsApi, type HolderInboxEvent, type HolderWatchItem, type Opportunity } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

export default function OpportunitiesPage() {
  const params = useSearchParams();
  const { locale, formatNumber } = useI18n();
  const [items, setItems] = useState<Opportunity[]>([]);
  const [holders, setHolders] = useState<HolderWatchItem[]>([]);
  const [events, setEvents] = useState<HolderInboxEvent[]>([]);
  const load = async () => {
    const [feed, holderData, eventData] = await Promise.all([
      marketsApi.opportunities({ limit: 100, offset: 0 }),
      agentPlatformApi.holderWatchlist(),
      agentPlatformApi.holderEvents(false),
    ]);
    setItems(feed.items); setHolders(holderData.items); setEvents(eventData.items);
  };
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [feed, holderData, eventData] = await Promise.all([
        marketsApi.opportunities({ limit: 100, offset: 0 }),
        agentPlatformApi.holderWatchlist(),
        agentPlatformApi.holderEvents(false),
      ]);
      if (cancelled) return;
      setItems(feed.items);
      setHolders(holderData.items);
      setEvents(eventData.items);
    })().catch(() => undefined);
    return () => { cancelled = true; };
  }, []);
  const signals = items.filter((item) => ["company", "holder", "macro", "capital"].includes(item.domain));
  const relative = items.filter((item) => ["rates", "futures", "options"].includes(item.domain));
  const active = items.filter((item) => ["new", "active", "changed", "challenged"].includes(item.state));
  const defaultTab = ["signals", "relative", "people"].includes(params.get("tab") || "") ? params.get("tab")! : "signals";
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><MetricCard label="ACTIVE SIGNALS" value={formatNumber(active.length)} note={`${items.length} ${locale === "zh" ? "条可审计机会" : "auditable opportunities"}`} color="text-agent-mint" /><MetricCard label="RELATIVE VALUE" value={formatNumber(relative.length)} note={locale === "zh" ? "利率、期货与期权" : "Rates, futures, and options"} color="text-agent-blue" /><MetricCard label="TRACKED PEOPLE" value={formatNumber(holders.filter((item) => item.enabled).length)} note={`${events.filter((item) => !item.read_at).length} ${locale === "zh" ? "条未读变化" : "unread changes"}`} color="text-agent-amber" /><MetricCard label="CHALLENGED" value={formatNumber(items.filter((item) => item.state === "challenged" || item.state === "invalidated").length)} note={locale === "zh" ? "与现有假设冲突" : "Conflicts with current theses"} color="text-agent-up" /></div>
    <Tabs key={defaultTab} defaultValue={defaultTab} className="flex flex-col gap-3"><TabsList className="h-auto w-fit border border-agent-border bg-agent-chrome p-1"><TabsTrigger value="signals">{locale === "zh" ? "信号" : "Signals"}</TabsTrigger><TabsTrigger value="relative">{locale === "zh" ? "相对价值" : "Relative Value"}</TabsTrigger><TabsTrigger value="people">{locale === "zh" ? "跟踪人物/机构" : "People & Institutions"}</TabsTrigger></TabsList>
      <TabsContent value="signals" className="mt-0"><OpportunityTable items={signals} locale={locale} onFollow={async (item) => { try { await marketsApi.followOpportunity(item.id, { state: "following" }); await load(); } catch (error) { toast.error(error instanceof Error ? error.message : "Follow failed"); } }} /></TabsContent>
      <TabsContent value="relative" className="mt-0"><OpportunityTable items={relative} locale={locale} onFollow={async (item) => { try { await marketsApi.followOpportunity(item.id, { state: "following" }); await load(); } catch (error) { toast.error(error instanceof Error ? error.message : "Follow failed"); } }} /></TabsContent>
      <TabsContent value="people" className="mt-0 grid gap-3 xl:grid-cols-[.75fr_1.25fr]">
        <Panel><SectionTitle title={locale === "zh" ? "跟踪清单" : "Watchlist"} en="HOLDER IDENTITY" />{holders.length ? <div className="divide-y divide-agent-border">{holders.map((item) => <div key={item.id} className="py-3"><div className="flex items-center gap-2"><StatusDot status={item.enabled ? "active" : "unavailable"} /><span className="text-xs text-agent-text">{item.holder_name}</span><span className="ml-auto font-data text-[9px] text-agent-dim">{item.holder_type}</span></div>{item.identity_warning ? <p className="mt-2 text-[10px] text-agent-amber">{item.identity_warning}</p> : null}<p className="mt-1 font-data text-[9px] text-agent-dim">{item.last_scanned_at || (locale === "zh" ? "等待首次扫描" : "Awaiting first scan")}</p></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有跟踪人物" : "No tracked people"} detail={locale === "zh" ? "可在 Agent 工作台搜索并确认股东身份后加入。" : "Search and confirm holder identity in the Agent workspace."} />}</Panel>
        <Panel><SectionTitle title={locale === "zh" ? "持仓变化事件" : "Position Change Events"} en="DISCLOSURE EVIDENCE" />{events.length ? <div className="divide-y divide-agent-border">{events.slice(0, 30).map((item) => <div key={item.id} className="grid grid-cols-[90px_1fr_90px] items-center gap-3 py-3 text-[10px]"><span className="font-data text-agent-mint">{item.event_type}</span><span className="min-w-0"><span className="block truncate text-xs text-agent-text">{item.holder_name} · {item.company_name || item.ts_code}</span><span className="mt-1 block font-data text-[9px] text-agent-dim">{item.end_date} · {item.ann_date || "—"}</span></span><span className="text-right font-data text-agent-dim">{item.read_at ? "READ" : "NEW"}</span></div>)}</div> : <EmptyPanel title={locale === "zh" ? "暂无披露事件" : "No disclosure events"} detail={locale === "zh" ? "事件只来自正式披露，不用社交媒体传闻补位。" : "Events come from formal disclosures, never social-media rumors."} />}</Panel>
      </TabsContent>
    </Tabs>
  </DashboardPage>;
}

function OpportunityTable({ items, locale, onFollow }: { items: Opportunity[]; locale: string; onFollow: (item: Opportunity) => Promise<void> }) {
  const sorted = useMemo(() => [...items].sort((a, b) => b.last_seen_at.localeCompare(a.last_seen_at)), [items]);
  return <Panel className="overflow-hidden p-0"><div className="p-4"><SectionTitle title={locale === "zh" ? "可审计机会" : "Auditable Opportunities"} en="NO SYNTHETIC SCORE" /></div>{sorted.length ? <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-[10px]"><thead className="border-y border-agent-border bg-agent-chrome font-data text-agent-dim"><tr><th className="px-4 py-2 font-normal">DOMAIN</th><th className="px-3 py-2 font-normal">{locale === "zh" ? "机会" : "Opportunity"}</th><th className="px-3 py-2 font-normal">STATE</th><th className="px-3 py-2 font-normal">AS OF</th><th className="px-3 py-2 font-normal">{locale === "zh" ? "证伪条件" : "Falsifiers"}</th><th className="px-3 py-2 font-normal" /></tr></thead><tbody className="divide-y divide-agent-border">{sorted.map((item) => <tr key={item.id} className="hover:bg-agent-raised"><td className="px-4 py-3 font-data uppercase text-agent-mint">{item.domain}</td><td className="max-w-[420px] px-3 py-3"><p className="text-xs text-agent-text">{item.title}</p><p className="mt-1 truncate text-[10px] text-agent-dim">{item.hypothesis}</p></td><td className="px-3 py-3"><span className={`font-data ${item.state === "challenged" || item.state === "invalidated" ? "text-agent-up" : item.state === "new" || item.state === "active" ? "text-agent-mint" : "text-agent-muted"}`}>{item.state}</span></td><td className="px-3 py-3 font-data text-agent-dim">{item.as_of || "—"}</td><td className="max-w-[240px] px-3 py-3 text-agent-muted">{item.falsifiers?.[0] || "—"}</td><td className="px-3 py-3 text-right"><Button variant="outline" size="sm" disabled={item.followed} onClick={() => void onFollow(item)}>{item.followed ? (locale === "zh" ? "已跟踪" : "Following") : (locale === "zh" ? "跟踪" : "Follow")}</Button></td></tr>)}</tbody></table></div> : <div className="p-4"><EmptyPanel title={locale === "zh" ? "没有符合条件的机会" : "No matching opportunities"} detail={locale === "zh" ? "机会必须包含触发、证据、来源日期和证伪条件。" : "Opportunities require triggers, evidence, source dates, and falsifiers."} /></div>}</Panel>;
}
