"use client";

import { Anchor, ChevronDown, Clock3, Loader2, Radio, Star } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  agentPlatformApi,
  marketsApi,
  type Opportunity,
  type OpportunityFeed,
  type RiskProfile,
  type TradePlan,
} from "@/lib/api/agent-platform";
import { MarketShell } from "../../capital/_components/market-shell";

const LAST_SELECTION = "keeltrader:opportunity:last-selection";
const domains = ["macro", "rates", "capital", "futures", "options", "company", "holder"] as const;
const states = ["new", "active", "changed", "challenged", "invalidated", "stale", "closed"] as const;
const domainNames: Record<string, string> = {
  macro: "宏观", rates: "利率", capital: "资金", futures: "期货", options: "期权", company: "我的公司", holder: "我的股东",
};
const stateNames: Record<string, string> = {
  new: "新出现", active: "持续", changed: "变化", challenged: "有冲突", invalidated: "已证伪", stale: "源滞后", closed: "已关闭",
};
const views = [
  ["all", "全部"], ["global", "市场"], ["company", "我的公司"], ["holder", "我的股东"], ["followed", "已关注"],
] as const;

export default function OpportunitiesPage() {
  const router = useRouter();
  const [feed, setFeed] = useState<OpportunityFeed | null>(null);
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const [view, setView] = useState<(typeof views)[number][0]>("all");
  const [domain, setDomain] = useState<string>();
  const [state, setState] = useState<string>();
  const [loading, setLoading] = useState(true);

  const filters = useMemo(() => ({
    scope: view === "global" ? "global" as const : view === "company" || view === "holder" ? "private" as const : "all" as const,
    domain: view === "company" ? "company" : view === "holder" ? "holder" : domain,
    state,
    followed: view === "followed" || undefined,
  }), [view, domain, state]);

  const load = useCallback(async (restore = false) => {
    try {
      const result = await marketsApi.opportunities(filters);
      setFeed(result);
      if (selected && !result.items.some((item) => item.id === selected.id)) setSelected(null);
      if (restore && !selected) {
        const remembered = window.localStorage.getItem(LAST_SELECTION);
        if (remembered && result.items.some((item) => item.id === remembered)) {
          setSelected(await marketsApi.opportunity(remembered));
        }
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "机会中心加载失败");
    } finally {
      setLoading(false);
    }
  }, [filters, selected]);

  useEffect(() => {
    let current = true;
    marketsApi.opportunities(filters).then(async (result) => {
      if (!current) return;
      setFeed(result);
      setLoading(false);
      if (selected && !result.items.some((item) => item.id === selected.id)) setSelected(null);
      if (!selected) {
        const remembered = window.localStorage.getItem(LAST_SELECTION);
        if (remembered && result.items.some((item) => item.id === remembered)) {
          const detail = await marketsApi.opportunity(remembered);
          if (current) setSelected(detail);
        }
      }
    }).catch((error) => {
      if (current) {
        setLoading(false);
        toast.error(error instanceof Error ? error.message : "机会中心加载失败");
      }
    });
    return () => { current = false; };
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = async (item: Opportunity) => {
    try {
      const detail = await marketsApi.opportunity(item.id);
      setSelected(detail);
      window.localStorage.setItem(LAST_SELECTION, item.id);
    } catch (error) { toast.error(error instanceof Error ? error.message : "机会详情加载失败"); }
  };

  const chooseCell = (nextDomain: string, nextState: string) => {
    setView("all"); setDomain(nextDomain); setState(nextState); setSelected(null);
  };

  const bringToResearch = async () => {
    if (!selected) return;
    const latest = selected.snapshots?.[0];
    const snapshot = await agentPlatformApi.createContextSnapshot({
      resource_type: "opportunity",
      resource_id: latest?.id || selected.id,
      visible_start: selected.first_seen_at,
      visible_end: selected.as_of,
      selected_point: {
        opportunity_id: selected.id,
        snapshot_id: latest?.id,
        state: latest?.state || selected.state,
        trigger: latest?.trigger || selected.trigger,
        hypothesis: latest?.hypothesis || selected.hypothesis,
        source_dates: latest?.source_dates || selected.source_dates,
        evidence: latest?.evidence || selected.evidence || [],
        chart_refs: latest?.chart_refs || selected.chart_refs || [],
      },
      source: "KeelTrader immutable opportunity snapshot",
      methodology: "用户主动选择的确定性证据快照；AI 只解释该快照，不补造缺失数据，不把机会转为评分或自动交易指令。",
    });
    router.push(`/agent?context_snapshot=${snapshot.id}&context_label=${encodeURIComponent(selected.title)}`);
  };

  return (
    <MarketShell title="统一机会中心" subtitle="全市场事实变化 + 我的公司与股东证据；按领域、生命周期和源日期组织，不评分"
      onResearch={selected ? () => void bringToResearch() : undefined}
      trail={{ object: selected?.title || "机会航图", asOf: selected?.as_of, source: "确定性规则 · 不使用模型检测" }}>
      <OpportunityMap groups={feed?.groups || {}} activeDomain={domain} activeState={state} onChoose={chooseCell} />
      <div className="flex gap-2 overflow-x-auto pb-1" aria-label="机会范围">
        {views.map(([key, label]) => <Button key={key} size="sm" variant={view === key ? "default" : "outline"}
          onClick={() => { setView(key); setDomain(undefined); setState(undefined); setSelected(null); }}>{label}</Button>)}
        {(domain || state) && <Button size="sm" variant="ghost" onClick={() => { setDomain(undefined); setState(undefined); }}>清除航图筛选</Button>}
      </div>
      {loading && !feed ? <div className="grid h-72 place-items-center"><Loader2 className="h-7 w-7 animate-spin" /></div> : <>
        <PanelGroup direction="horizontal" autoSaveId="opportunity-workspace" className="hidden min-h-[620px] overflow-hidden rounded-2xl border bg-card/70 md:flex">
          <Panel defaultSize={31} minSize={22} maxSize={44}><OpportunityStream items={feed?.items || []} selectedId={selected?.id} onChoose={choose} /></Panel>
          <PanelResizeHandle className="group relative w-1 bg-border/70 hover:bg-[hsl(var(--copper)/.65)]"><span className="absolute left-1/2 top-1/2 h-10 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-muted-foreground/30 group-hover:bg-[hsl(var(--copper))]" /></PanelResizeHandle>
          <Panel minSize={42}><OpportunityDetail key={selected?.id || "overview"} item={selected} onChanged={(item) => { setSelected(item); void load(); }} onResearch={bringToResearch} /></Panel>
        </PanelGroup>
        <div className="space-y-4 md:hidden"><OpportunityStream items={feed?.items || []} selectedId={selected?.id} onChoose={choose} /><OpportunityDetail key={`mobile-${selected?.id || "overview"}`} item={selected} onChanged={(item) => { setSelected(item); void load(); }} onResearch={bringToResearch} /></div>
      </>}
      <SourceStatus status={feed?.source_status || {}} />
    </MarketShell>
  );
}

function OpportunityMap({ groups, activeDomain, activeState, onChoose }: { groups: Record<string, Record<string, number>>; activeDomain?: string; activeState?: string; onChoose: (domain: string, state: string) => void }) {
  return <section className="overflow-hidden rounded-2xl border bg-[linear-gradient(135deg,hsl(var(--card)),hsl(var(--secondary)/.45))] shadow-sm">
    <div className="flex items-end justify-between border-b px-5 py-4"><div><p className="font-data text-[9px] uppercase tracking-[.24em] text-[hsl(var(--copper-foreground))]">Opportunity chart</p><h2 className="font-display text-xl font-semibold">机会航图</h2></div><p className="max-w-md text-right text-[10px] leading-4 text-muted-foreground">格子只表示当前记录数量，不代表机会强弱、排名或建议仓位。</p></div>
    <div className="overflow-x-auto"><table className="w-full min-w-[760px] border-collapse text-center text-[10px]"><thead><tr><th className="border-b border-r p-3 text-left font-medium text-muted-foreground">领域 \ 生命周期</th>{states.map((s) => <th key={s} className="border-b p-3 font-medium text-muted-foreground">{stateNames[s]}</th>)}</tr></thead>
      <tbody>{domains.map((d) => <tr key={d}><th className="border-r p-3 text-left font-semibold">{domainNames[d]}</th>{states.map((s) => { const count = groups[d]?.[s] || 0; const active = activeDomain === d && activeState === s; return <td key={s} className="p-1.5"><button disabled={!count} aria-label={`${domainNames[d]} ${stateNames[s]} ${count}条`} onClick={() => onChoose(d, s)} className={`h-10 w-full rounded-lg border font-data transition ${active ? "border-[hsl(var(--copper))] bg-[hsl(var(--copper)/.18)]" : count ? "border-border bg-background/70 hover:border-[hsl(var(--copper)/.65)] hover:bg-[hsl(var(--accent)/.1)]" : "border-transparent text-muted-foreground/35"}`}>{count || "—"}</button></td>; })}</tr>)}</tbody>
    </table></div>
  </section>;
}

function OpportunityStream({ items, selectedId, onChoose }: { items: Opportunity[]; selectedId?: string; onChoose: (item: Opportunity) => void }) {
  const grouped = useMemo(() => domains.map((domain) => [domain, items.filter((item) => item.domain === domain)] as const).filter(([, rows]) => rows.length), [items]);
  return <aside className="h-full min-h-[320px] overflow-y-auto p-3"><div className="flex items-center justify-between px-2 py-2"><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">全部观察 · 不评分</p><span className="font-data text-[10px] text-muted-foreground">{items.length}</span></div>
    {!items.length && <div className="m-2 rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground">当前视图没有已物化机会。缺失来源不会按零处理。</div>}
    {grouped.map(([domain, rows]) => <section key={domain} className="mb-4"><h3 className="sticky top-0 z-10 bg-card/95 px-2 py-2 font-display text-sm font-semibold backdrop-blur">{domainNames[domain]}</h3>{rows.map((item) => <button key={item.id} onClick={() => void onChoose(item)} className={`mb-2 w-full rounded-xl border p-3 text-left transition ${selectedId === item.id ? "border-[hsl(var(--copper)/.7)] bg-[hsl(var(--accent)/.12)] shadow-sm" : "bg-background/55 hover:bg-secondary"}`}>
      <span className="flex items-start gap-2"><span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${item.state === "challenged" || item.state === "invalidated" ? "bg-amber-600" : "bg-emerald-700"}`} /><span className="min-w-0"><span className="block text-xs font-medium leading-5">{item.title}</span><span className="mt-1 block line-clamp-2 text-[10px] leading-4 text-muted-foreground">{item.trigger}</span></span>{item.followed && <Star className="ml-auto h-3 w-3 shrink-0 fill-current text-[hsl(var(--copper-foreground))]" />}</span>
      <span className="mt-2 flex items-center justify-between font-data text-[9px] text-muted-foreground"><span>{stateNames[item.state] || item.state}</span><span>{item.as_of || "日期不可用"}</span></span>
    </button>)}</section>)}</aside>;
}

function OpportunityDetail({ item, onChanged, onResearch }: { item: Opportunity | null; onChanged: (item: Opportunity) => void; onResearch: () => Promise<void> }) {
  const [notes, setNotes] = useState(item?.follow?.notes || "");
  const [risk, setRisk] = useState<RiskProfile | null>(null);
  const [plan, setPlan] = useState<TradePlan | null>(null);
  const [form, setForm] = useState({ direction: "", instrument: "", entry_trigger: "", entry_price: "", stop_price: "", target_price: "", horizon: "" });
  useEffect(() => { agentPlatformApi.riskProfile().then(setRisk).catch(() => undefined); }, []);
  if (!item) return <main className="grid h-full min-h-[420px] place-items-center p-8"><div className="max-w-lg text-center"><Anchor className="mx-auto h-9 w-9 text-[hsl(var(--copper-foreground))]" /><h2 className="mt-4 font-display text-2xl font-semibold">从航图或左侧机会流选择证据</h2><p className="mt-3 text-xs leading-6 text-muted-foreground">没有上次选择时保持总览，不自动选中第一条，也不会因为某个数据域最后写入而默认打开它。</p></div></main>;
  const evidenceGroups = { supporting: item.evidence?.filter((e) => e.stance === "supporting") || [], challenging: item.evidence?.filter((e) => e.stance === "challenging") || [], invalidating: item.evidence?.filter((e) => e.stance === "invalidating") || [] };
  const toggleFollow = async () => { if (item.followed) await marketsApi.unfollowOpportunity(item.id); else await marketsApi.followOpportunity(item.id, { notes }); onChanged(await marketsApi.opportunity(item.id)); };
  const saveNotes = async () => { await marketsApi.updateOpportunityFollow(item.id, { notes }); onChanged(await marketsApi.opportunity(item.id)); toast.success("关注笔记已保存"); };
  const draft = async () => setPlan(await marketsApi.createTradePlan(item.id, { ...form, entry_price: Number(form.entry_price) || undefined, stop_price: Number(form.stop_price) || undefined, target_price: Number(form.target_price) || undefined }));
  return <main className="h-full min-h-[520px] overflow-y-auto p-5 md:p-7"><div className="flex flex-wrap items-center gap-2 font-data text-[9px] uppercase tracking-[.12em] text-muted-foreground"><span>{domainNames[item.domain]}</span><span>·</span><span>{stateNames[item.state] || item.state}</span><span>·</span><span>{item.as_of || "日期不可用"}</span>{item.scope === "private" && <span className="rounded-full border px-2 py-1 text-foreground">仅我可见</span>}</div>
    <h2 className="mt-3 max-w-4xl font-display text-2xl font-semibold leading-tight">{item.title}</h2>
    <section className="mt-5 rounded-xl border-l-2 border-l-[hsl(var(--copper))] bg-background/60 p-4"><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">透明触发</p><p className="mt-2 text-sm leading-6">{item.trigger}</p></section>
    <section className="mt-5"><h3 className="font-display text-lg font-semibold">可证伪假设</h3><p className="mt-2 text-sm leading-7 text-foreground/90">{item.hypothesis}</p></section>
    <div className="mt-6 grid gap-5 xl:grid-cols-3"><EvidenceColumn title="支持证据" items={evidenceGroups.supporting} tone="support" /><EvidenceColumn title="冲突证据" items={evidenceGroups.challenging} tone="challenge" /><EvidenceColumn title="证伪证据" items={evidenceGroups.invalidating} tone="invalidate" /></div>
    <div className="mt-6 grid gap-4 lg:grid-cols-2"><TextList title="后续催化" items={item.catalysts} /><TextList title="明确证伪条件" items={item.falsifiers} /></div>
    <div className="mt-6 grid gap-4 lg:grid-cols-2"><Freshness freshness={item.freshness} /><Timeline snapshots={item.snapshots || []} /></div>
    <RawLinks item={item} />
    <details className="mt-7 rounded-2xl border bg-secondary/25"><summary className="flex cursor-pointer list-none items-center gap-2 p-4 text-sm font-semibold"><ChevronDown className="h-4 w-4" />操作舱 <span className="text-[10px] font-normal text-muted-foreground">默认收起 · 仅人工操作</span></summary><div className="grid gap-6 border-t p-4 xl:grid-cols-2">
      <section><div className="flex gap-2"><Button variant={item.followed ? "outline" : "default"} onClick={() => void toggleFollow()}>{item.followed ? "取消关注" : "关注机会"}</Button><Button variant="outline" onClick={() => void onResearch()}>带入研究</Button></div><Textarea className="mt-3" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="我的私有关注笔记" /><Button className="mt-2" size="sm" variant="outline" onClick={() => void saveNotes()}>保存笔记</Button></section>
      <section><p className="text-xs font-semibold">人工交易计划草案</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{(Object.keys(labels) as Array<keyof typeof labels>).map((key) => <Input key={key} placeholder={labels[key]} type={key.includes("price") ? "number" : "text"} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />)}</div><Button className="mt-3" onClick={() => void draft()}>生成待人工确认草案</Button>{risk && <p className="mt-2 text-[9px] text-muted-foreground">固定风险法 · 单笔风险 {risk.risk_per_trade * 100}% · 不连接券商执行</p>}{plan && <div className="mt-3 rounded-xl border bg-background/70 p-3 text-xs"><p className="font-semibold">{plan.status === "unavailable" ? "交易计划不可用" : "待人工确认，未连接券商执行"}</p><p className="mt-2 text-muted-foreground">{plan.unavailable_reason || `数量 ${plan.quantity} · 最大损失 ${plan.max_loss} · 名义金额 ${plan.notional}`}</p></div>}</section>
    </div></details>
  </main>;
}

function EvidenceColumn({ title, items, tone }: { title: string; items: NonNullable<Opportunity["evidence"]>; tone: "support" | "challenge" | "invalidate" }) { const color = tone === "support" ? "border-t-emerald-700" : tone === "challenge" ? "border-t-amber-600" : "border-t-rose-700"; return <section><h3 className="mb-2 text-xs font-semibold">{title} <span className="font-data text-muted-foreground">{items.length}</span></h3><div className="space-y-2">{items.length ? items.map((e, index) => <article key={`${e.source}-${index}`} className={`rounded-xl border border-t-2 ${color} bg-background/60 p-3`}><p className="text-xs leading-5">{e.fact}</p><p className="mt-2 break-all font-data text-[9px] text-muted-foreground">{e.source} · {e.source_date || "日期不可用"}</p></article>) : <div className="rounded-xl border border-dashed p-4 text-[10px] text-muted-foreground">当前快照无此类证据；不按零解释。</div>}</div></section>; }
function TextList({ title, items }: { title: string; items: string[] }) { return <section className="rounded-xl border bg-background/60 p-4"><h3 className="text-xs font-semibold">{title}</h3><ul className="mt-3 space-y-2 text-[11px] leading-5 text-muted-foreground">{items.map((item) => <li key={item}>· {item}</li>)}</ul></section>; }
function Freshness({ freshness }: { freshness: Opportunity["freshness"] }) { return <section className="rounded-xl border bg-background/60 p-4"><h3 className="flex items-center gap-2 text-xs font-semibold"><Radio className="h-3.5 w-3.5" />数据新鲜度与口径</h3><div className="mt-3 space-y-2">{Object.entries(freshness || {}).map(([key, value]) => <div key={key} className="flex items-start justify-between gap-3 border-b pb-2 text-[10px] last:border-0"><span>{key}</span><span className="text-right font-data text-muted-foreground">{value.available === false ? "不可用" : value.as_of || "日期不可用"}</span></div>)}</div></section>; }
function Timeline({ snapshots }: { snapshots: NonNullable<Opportunity["snapshots"]> }) { return <section className="rounded-xl border bg-background/60 p-4"><h3 className="flex items-center gap-2 text-xs font-semibold"><Clock3 className="h-3.5 w-3.5" />不可变快照航迹</h3><div className="mt-3 max-h-48 space-y-3 overflow-y-auto">{snapshots.map((s) => <div key={s.id} className="border-l pl-3 text-[10px]"><p className="font-medium">{stateNames[s.state] || s.state} · {s.as_of || "日期不可用"}</p><p className="mt-1 line-clamp-2 text-muted-foreground">{s.trigger}</p><p className="mt-1 font-data text-[9px] text-muted-foreground">{new Date(s.created_at).toLocaleString("zh-CN")}</p></div>)}</div></section>; }
function RawLinks({ item }: { item: Opportunity }) { const href = item.domain === "macro" ? "/agent/capital/macro" : item.domain === "rates" ? "/agent/market/rates" : item.domain === "futures" ? "/agent/capital/futures" : item.domain === "options" ? "/agent/capital/options" : item.domain === "capital" ? "/agent/capital" : item.domain === "holder" ? "/agent/holders" : "/agent"; return <section className="mt-6 rounded-xl border border-dashed p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-xs font-semibold">源数据与完整历史</h3><p className="mt-1 text-[10px] text-muted-foreground">图表引用 {item.chart_refs?.length || 0} 个；进入对应数据台查看当前数据库全部可用原始历史。</p></div><Button asChild size="sm" variant="outline"><Link href={href}>打开源数据历史</Link></Button></div></section>; }
function SourceStatus({ status }: { status: OpportunityFeed["source_status"] }) { return <section className="rounded-xl border bg-card/60 p-4"><h2 className="text-xs font-semibold">物化状态</h2><div className="mt-3 flex flex-wrap gap-2">{Object.entries(status).map(([domain, value]) => <span key={domain} className="rounded-full border bg-background/60 px-3 py-1.5 font-data text-[9px]">{domainNames[domain] || domain} · {value.status} · {value.last_succeeded_at ? new Date(value.last_succeeded_at).toLocaleString("zh-CN") : "尚未成功"}</span>)}</div></section>; }
const labels = { direction: "方向（long / short）", instrument: "交易工具", entry_trigger: "进场触发条件", entry_price: "进场价", stop_price: "论点失效止损价", target_price: "目标价", horizon: "持有期限" };
