"use client";

import {
  AlertTriangle,
  Anchor,
  Check,
  Database,
  Loader2,
  Route,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  Plus,
  Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { toast } from "sonner";

import { KeelMark, ThemeMenu } from "@/components/keel-brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  agentPlatformApi,
  type AllocationAccount,
  type AllocationDataStatus,
  type AllocationPolicyVersion,
  type AllocationSeriesStatus,
  type AllocationSeriesHistory,
  type AllocationSleeve,
} from "@/lib/api/agent-platform";

const LAST_ACCOUNT = "keeltrader:allocation:last-account";
const money = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 });
const pct = (value?: number) => value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;

type Draft = {
  name: string; capital: number; horizon_months: number; liquidity_reserve: number;
  max_drawdown: number; max_leverage: number; allowed_markets: string[];
  allowed_instruments: string[]; hard_restrictions: string[];
  future_cash_needs: Array<{ date: string; amount: number; note?: string }>;
};

const emptyDraft: Draft = {
  name: "长期配置资金池", capital: 1_000_000, horizon_months: 120,
  liquidity_reserve: 100_000, max_drawdown: 0.20, max_leverage: 1,
  allowed_markets: ["CN"], allowed_instruments: ["fund", "etf"], hard_restrictions: [],
  future_cash_needs: [],
};

export default function AllocationPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<AllocationAccount[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [status, setStatus] = useState<AllocationDataStatus>();
  const [versions, setVersions] = useState<AllocationPolicyVersion[]>([]);
  const [policy, setPolicy] = useState<AllocationPolicyVersion>();
  const [loading, setLoading] = useState(true), [saving, setSaving] = useState(false), [generating, setGenerating] = useState(false);

  const selected = accounts.find((item) => item.id === selectedId);
  const syncDraft = useCallback((item: AllocationAccount) => setDraft({
    name: item.name, capital: item.capital, horizon_months: item.horizon_months,
    liquidity_reserve: item.liquidity_reserve, max_drawdown: item.max_drawdown,
    max_leverage: item.max_leverage, allowed_markets: item.allowed_markets,
    allowed_instruments: item.allowed_instruments, hard_restrictions: item.hard_restrictions,
    future_cash_needs: item.future_cash_needs,
  }), []);

  const loadVersions = useCallback(async (account: AllocationAccount) => {
    const result = await agentPlatformApi.allocationPolicyVersions(account.id);
    setVersions(result.items);
    const preferred = account.current_policy_version_id || result.items[0]?.id;
    setPolicy(preferred ? await agentPlatformApi.allocationPolicyVersion(preferred) : undefined);
  }, []);

  const load = useCallback(async () => {
    const [accountResult, dataResult] = await Promise.all([
      agentPlatformApi.allocationAccounts(), agentPlatformApi.allocationDataStatus(),
    ]);
    setAccounts(accountResult.items); setStatus(dataResult);
    const remembered = window.localStorage.getItem(LAST_ACCOUNT);
    const account = accountResult.items.find((item) => item.id === remembered) || accountResult.items.find((item) => item.status === "active");
    if (account) { setSelectedId(account.id); syncDraft(account); await loadVersions(account); }
    setLoading(false);
  }, [loadVersions, syncDraft]);

  useEffect(() => { void load().catch((error) => { setLoading(false); toast.error(error instanceof Error ? error.message : "资产配置加载失败"); }); }, [load]);

  const choose = async (id: string) => {
    const account = accounts.find((item) => item.id === id); if (!account) return;
    setSelectedId(id); syncDraft(account); window.localStorage.setItem(LAST_ACCOUNT, id); await loadVersions(account);
  };
  const startNew = () => { setSelectedId(undefined); setPolicy(undefined); setVersions([]); setDraft(emptyDraft); };
  const save = async () => {
    setSaving(true);
    try {
      const body = { ...draft, base_currency: "CNY" as const };
      const item = selected ? await agentPlatformApi.updateAllocationAccount(selected.id, body) : await agentPlatformApi.createAllocationAccount(body);
      toast.success(selected ? "资金约束已保存" : "资产配置研究账户已创建");
      window.localStorage.setItem(LAST_ACCOUNT, item.id); await load(); setSelectedId(item.id); syncDraft(item); await loadVersions(item);
    } catch (error) { toast.error(error instanceof Error ? error.message : "保存失败"); } finally { setSaving(false); }
  };
  const generate = async () => {
    if (!selected || !status?.formal_ready) return;
    setGenerating(true);
    try { const result = await agentPlatformApi.generateAllocationPolicy(selected.id); setPolicy(result); await loadVersions(selected); toast.success("已生成不可变配置版本"); }
    catch (error) { toast.error(error instanceof Error ? error.message : "配置生成失败"); } finally { setGenerating(false); }
  };
  const remove = async () => {
    if (!selected || !window.confirm(`删除“${selected.name}”及其全部配置版本？此操作不能撤销。`)) return;
    await agentPlatformApi.deleteAllocationAccount(selected.id); window.localStorage.removeItem(LAST_ACCOUNT);
    setSelectedId(undefined); setPolicy(undefined); setVersions([]); setDraft(emptyDraft); await load(); toast.success("资产配置研究账户已删除");
  };
  const confirm = async () => {
    if (!selected || !policy) return;
    const result = await agentPlatformApi.confirmAllocationPolicy(selected.id, policy.id); setPolicy(result); await load(); toast.success("已确认当前配置版本");
  };
  const bring = async () => {
    if (!policy) return;
    const snapshot = await agentPlatformApi.createContextSnapshot({
      resource_type: "allocation_policy", resource_id: policy.id,
      visible_start: String((policy.data_snapshot?.common_history as { start?: string } | undefined)?.start || ""),
      visible_end: String((policy.data_snapshot?.common_history as { end?: string } | undefined)?.end || ""),
      selected_point: { version: policy.version, feasibility_status: policy.feasibility_status, quality_status: policy.quality_status,
        content_hash: policy.content_hash, sleeves: policy.sleeves, risk_summary: policy.risk_summary, stress_results: policy.stress_results },
      source: "KeelTrader immutable allocation policy",
      methodology: "人民币总回报共同历史上的受约束等风险贡献；现金需求优先；不使用预期收益、评分、因子、均线或百分位。",
    });
    router.push(`/agent?context_snapshot=${snapshot.id}&context_label=${encodeURIComponent(`${selected?.name || "资产配置"}·v${policy.version}`)}`);
  };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  return <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
    <header className="research-bearing border-b bg-card/95 shadow-sm">
      <div className="flex min-h-16 items-center gap-3 px-3 sm:px-5"><div className="hidden border-r pr-4 sm:block"><KeelMark /></div><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><Route className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h1 className="font-display text-lg font-semibold">资产配置</h1></div><p className="truncate text-[10px] text-muted-foreground">把人民币资金沿约束、战略资产与实施工具形成可审计航路</p></div>
        <Badge variant="outline" className={status?.formal_ready ? "border-emerald-500/45 text-emerald-700 dark:text-emerald-300" : "border-amber-500/45 text-amber-700 dark:text-amber-300"}>{status?.formal_ready ? "数据门禁通过" : "正式配置未开放"}</Badge>
        <Button size="sm" variant="outline" disabled={!policy} onClick={() => void bring()}><Send className="mr-1.5 h-3.5 w-3.5" />带入研究</Button><ThemeMenu />
      </div>
      <div className="evidence-rail flex min-h-8 items-center gap-3 overflow-x-auto border-t px-4 text-[9px] text-muted-foreground"><span className="font-semibold uppercase tracking-[.18em] text-[hsl(var(--copper-foreground))]">配置航迹</span><span>{selected?.name || "尚未建立资金池"}</span><span>基础币种 CNY</span><span>不连接券商 · 不自动调仓</span><span className="ml-auto">数据不足时拒绝生成，不使用代理替代</span></div>
    </header>
    <div className="min-h-0 flex-1 p-3 md:p-5">
      <PanelGroup direction="horizontal" autoSaveId="allocation-workbench" className="hidden h-full overflow-hidden rounded-2xl border bg-card/55 lg:flex">
        <Panel defaultSize={23} minSize={18} maxSize={34}><ConstraintPanel accounts={accounts} selectedId={selectedId} draft={draft} setDraft={setDraft} onChoose={choose} onNew={startNew} onSave={save} onDelete={remove} saving={saving} /></Panel>
        <PanelResizeHandle className="w-1 bg-border transition hover:bg-[hsl(var(--copper))]" />
        <Panel defaultSize={52} minSize={38}><RoutePanel account={selected} draft={draft} status={status} policy={policy} versions={versions} onSelectVersion={async (id) => setPolicy(await agentPlatformApi.allocationPolicyVersion(id))} onGenerate={generate} generating={generating} /></Panel>
        <PanelResizeHandle className="w-1 bg-border transition hover:bg-[hsl(var(--copper))]" />
        <Panel defaultSize={25} minSize={20} maxSize={36}><RiskPanel status={status} policy={policy} onConfirm={confirm} /></Panel>
      </PanelGroup>
      <div className="h-full space-y-4 overflow-y-auto lg:hidden"><ConstraintPanel accounts={accounts} selectedId={selectedId} draft={draft} setDraft={setDraft} onChoose={choose} onNew={startNew} onSave={save} onDelete={remove} saving={saving} /><RoutePanel account={selected} draft={draft} status={status} policy={policy} versions={versions} onSelectVersion={async (id) => setPolicy(await agentPlatformApi.allocationPolicyVersion(id))} onGenerate={generate} generating={generating} /><RiskPanel status={status} policy={policy} onConfirm={confirm} /></div>
    </div>
  </div>;
}

function ConstraintPanel({ accounts, selectedId, draft, setDraft, onChoose, onNew, onSave, onDelete, saving }: { accounts: AllocationAccount[]; selectedId?: string; draft: Draft; setDraft: (value: Draft) => void; onChoose: (id: string) => Promise<void>; onNew: () => void; onSave: () => Promise<void>; onDelete: () => Promise<void>; saving: boolean }) {
  const number = (key: keyof Draft, scale = 1) => (event: React.ChangeEvent<HTMLInputElement>) => setDraft({ ...draft, [key]: Number(event.target.value) / scale });
  const toggle = (key: "allowed_markets" | "allowed_instruments", value: string) => setDraft({ ...draft, [key]: draft[key].includes(value) ? draft[key].filter((item) => item !== value) : [...draft[key], value] });
  const addCashNeed = () => { const future = new Date(); future.setFullYear(future.getFullYear() + 1); setDraft({ ...draft, future_cash_needs: [...draft.future_cash_needs, { date: future.toISOString().slice(0, 10), amount: 100_000, note: "" }] }); };
  return <aside className="h-full overflow-y-auto p-4"><div className="flex items-center justify-between"><div><p className="font-data text-[9px] uppercase tracking-[.2em] text-[hsl(var(--copper-foreground))]">Capital orders</p><h2 className="mt-1 font-display text-xl font-semibold">资金约束</h2></div><Anchor className="h-5 w-5 text-muted-foreground" /></div>
    {accounts.length > 0 && <div className="mt-4 flex gap-2"><select value={selectedId || ""} onChange={(event) => void onChoose(event.target.value)} className="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-xs"><option value="" disabled>新资金池</option>{accounts.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select><Button size="icon" variant="outline" aria-label="新建资金池" onClick={onNew}><Plus className="h-4 w-4" /></Button></div>}
    <div className="mt-4 space-y-3"><Field label="资金池名称"><Input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></Field><Field label="总资金（人民币）"><Input type="number" min={1} value={draft.capital} onChange={number("capital")} /></Field><Field label="配置期限（月）"><Input type="number" min={1} value={draft.horizon_months} onChange={number("horizon_months")} /></Field><Field label="流动性储备"><Input type="number" min={0} value={draft.liquidity_reserve} onChange={number("liquidity_reserve")} /></Field><Field label="最大可承受回撤"><Input type="number" min={1} max={100} step={1} value={draft.max_drawdown * 100} onChange={number("max_drawdown", 100)} /></Field><Field label="最大底层杠杆"><Input type="number" min={0.1} max={5} step={0.1} value={draft.max_leverage} onChange={number("max_leverage")} /></Field></div>
    <div className="mt-5"><div className="flex items-center justify-between"><p className="text-[10px] text-muted-foreground">未来现金需求</p><Button size="sm" variant="ghost" onClick={addCashNeed}><Plus className="mr-1 h-3.5 w-3.5" />添加</Button></div><div className="mt-2 space-y-2">{draft.future_cash_needs.map((item, index) => <div key={`${item.date}-${index}`} className="grid grid-cols-[1fr_1fr_auto] gap-1.5"><Input type="date" value={item.date} onChange={(event) => setDraft({ ...draft, future_cash_needs: draft.future_cash_needs.map((row, i) => i === index ? { ...row, date: event.target.value } : row) })} /><Input type="number" min={1} value={item.amount} onChange={(event) => setDraft({ ...draft, future_cash_needs: draft.future_cash_needs.map((row, i) => i === index ? { ...row, amount: Number(event.target.value) } : row) })} /><Button size="icon" variant="ghost" aria-label="删除现金需求" onClick={() => setDraft({ ...draft, future_cash_needs: draft.future_cash_needs.filter((_, i) => i !== index) })}><Trash2 className="h-4 w-4" /></Button></div>)}</div></div>
    <ToggleGroup label="允许市场" values={["CN", "HK", "US", "GLOBAL"]} selected={draft.allowed_markets} onToggle={(value) => toggle("allowed_markets", value)} />
    <ToggleGroup label="允许工具" values={["fund", "etf", "fx_cash", "future", "option"]} selected={draft.allowed_instruments} onToggle={(value) => toggle("allowed_instruments", value)} />
    <Field label="法律、账户或伦理硬限制（用逗号分隔）"><Input value={draft.hard_restrictions.join("，")} onChange={(event) => setDraft({ ...draft, hard_restrictions: event.target.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean) })} placeholder="例如：账户不能交易境外衍生品" /></Field>
    <div className="mt-5 rounded-xl border bg-background/65 p-3 text-[10px] leading-5 text-muted-foreground"><ShieldCheck className="mr-1 inline h-3.5 w-3.5" />普通机会偏好不作为排除条件；这里只保存法律、账户与伦理硬限制。期货和期权属于实施工具，不增加资产类别。</div>
    <Button className="mt-4 w-full" disabled={saving} onClick={() => void onSave()}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}{selectedId ? "保存资金约束" : "建立研究账户"}</Button>
    {selectedId && <Button className="mt-2 w-full" variant="destructive" onClick={() => void onDelete()}><Trash2 className="mr-2 h-4 w-4" />删除研究账户</Button>}
  </aside>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-[10px] text-muted-foreground">{label}</span>{children}</label>; }
function ToggleGroup({ label, values, selected, onToggle }: { label: string; values: string[]; selected: string[]; onToggle: (value: string) => void }) { return <div className="mt-4"><p className="mb-2 text-[10px] text-muted-foreground">{label}</p><div className="flex flex-wrap gap-1.5">{values.map((value) => <button type="button" key={value} onClick={() => onToggle(value)} className={`rounded-lg border px-2.5 py-1.5 font-data text-[9px] ${selected.includes(value) ? "border-[hsl(var(--copper))] bg-[hsl(var(--accent)/.12)] text-foreground" : "text-muted-foreground"}`}>{value}</button>)}</div></div>; }

function RoutePanel({ account, draft, status, policy, versions, onSelectVersion, onGenerate, generating }: { account?: AllocationAccount; draft: Draft; status?: AllocationDataStatus; policy?: AllocationPolicyVersion; versions: AllocationPolicyVersion[]; onSelectVersion: (id: string) => Promise<void>; onGenerate: () => Promise<void>; generating: boolean }) {
  return <section className="h-full overflow-y-auto p-4 md:p-6"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="font-data text-[9px] uppercase tracking-[.22em] text-[hsl(var(--copper-foreground))]">Capital routing chart</p><h2 className="mt-2 font-display text-2xl font-semibold">资本航路</h2><p className="mt-1 text-[10px] text-muted-foreground">资本金额与底层风险分层显示；衍生品只沿底层航线实施。</p></div><div className="flex items-center gap-2">{versions.length > 0 && <select value={policy?.id || ""} onChange={(event) => void onSelectVersion(event.target.value)} className="h-9 rounded-lg border bg-background px-2 font-data text-[10px]">{versions.map((item) => <option key={item.id} value={item.id}>v{item.version} · {item.feasibility_status}</option>)}</select>}<Button size="sm" disabled={!account || !status?.formal_ready || generating} onClick={() => void onGenerate()}>{generating ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Sparkles className="mr-1.5 h-3.5 w-3.5" />}生成新版本</Button></div></div>
    {!status?.formal_ready && <div className="mt-5 flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/[.05] p-4"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" /><div><p className="text-xs font-medium">正式配置暂未开放</p><p className="mt-1 text-[10px] leading-5 text-muted-foreground">{status?.missing_required?.length ? `缺少：${status.missing_required.map((key) => status.series.find((item) => item.sleeve_key === key)?.name || key).join("、")}` : "数据目录尚未就绪"}。可以先保存资金约束，系统不会用价格指数、国债期货或合成曲线替代。</p></div></div>}
    <CapitalRouteChart capital={draft.capital} reserve={draft.liquidity_reserve + draft.future_cash_needs.reduce((sum, item) => sum + item.amount, 0)} status={status} sleeves={policy?.sleeves} />
    <div className="mt-5 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-4"><Ledger label="共同历史" value={String((policy?.data_snapshot?.common_history as { months?: number } | undefined)?.months || "未通过门禁")} /><Ledger label="方法" value="等风险贡献" /><Ledger label="预期收益" value="不使用" /><Ledger label="自动调仓" value="关闭" /></div>
  </section>;
}

function CapitalRouteChart({ capital, reserve, status, sleeves }: { capital: number; reserve: number; status?: AllocationDataStatus; sleeves?: AllocationSleeve[] }) {
  const [tip, setTip] = useState<{ x: number; y: number; title: string; body: string }>();
  const shown = sleeves?.length ? sleeves : (status?.series || []).map((item) => ({ sleeve_key: item.sleeve_key, label: item.name, target_weight: 0, amount_cny: 0, risk_contribution: 0, min_weight: 0, max_weight: 0, currency_exposure: {}, source_series_id: item.series_id, id: item.series_id || item.sleeve_key }));
  const risky = Math.max(0, capital - reserve);
  const move = (event: React.PointerEvent | React.FocusEvent, title: string, body: string) => { const chart = event.currentTarget.closest("[data-route-chart]")?.getBoundingClientRect(), node = event.currentTarget.getBoundingClientRect(); if (!chart) return; const clientX = "clientX" in event ? event.clientX : node.right, clientY = "clientY" in event ? event.clientY : node.top; setTip({ x: Math.min(chart.width - 220, Math.max(8, clientX - chart.left + 12)), y: Math.max(8, clientY - chart.top + 12), title, body }); };
  return <div data-route-chart className="relative mt-6 overflow-hidden rounded-2xl border bg-[linear-gradient(135deg,hsl(var(--card)),hsl(var(--secondary)/.48))] p-4 md:p-6" onPointerLeave={() => setTip(undefined)}><div className="grid gap-5 md:grid-cols-[.8fr_1fr_1.4fr] md:items-center"><RouteNode title="总资金" value={money.format(capital)} state="source" onMove={move} body="用户输入的人民币研究资金总额；不代表券商账户余额。" /><div className="space-y-3 border-l border-dashed border-[hsl(var(--copper)/.45)] pl-5"><RouteNode title="流动性与现金需求" value={money.format(reserve)} state="cash" onMove={move} body="优先保留，不参与风险预算。" /><RouteNode title="可投资资金" value={money.format(risky)} state="flow" onMove={move} body="只有数据门禁通过后才沿战略资产分配。" /></div><div className="grid gap-2 border-l border-dashed border-[hsl(var(--copper)/.45)] pl-5 sm:grid-cols-2">{shown.map((item) => <RouteNode key={item.sleeve_key} title={item.label} value={item.target_weight ? `${pct(item.target_weight)} · ${money.format(item.amount_cny)}` : "等待总回报数据"} state={item.target_weight ? "ready" : "blocked"} onMove={move} body={item.target_weight ? `允许范围 ${pct(item.min_weight)}—${pct(item.max_weight)}；风险贡献 ${pct(item.risk_contribution)}` : status?.series.find((row) => row.sleeve_key === item.sleeve_key)?.quality_reason || "来源尚未通过门禁"} />)}</div></div>{tip && <div role="tooltip" className="pointer-events-none absolute z-20 w-52 rounded-lg border bg-popover p-2.5 text-[10px] shadow-xl" style={{ left: tip.x, top: tip.y }}><p className="font-medium text-foreground">{tip.title}</p><p className="mt-1 leading-4 text-muted-foreground">{tip.body}</p></div>}</div>;
}

function RouteNode({ title, value, state, body, onMove }: { title: string; value: string; state: string; body: string; onMove: (event: React.PointerEvent | React.FocusEvent, title: string, body: string) => void }) { return <button type="button" onPointerMove={(event) => onMove(event, title, body)} onFocus={(event) => onMove(event, title, body)} className={`w-full rounded-xl border p-3 text-left outline-none transition focus-visible:ring-2 focus-visible:ring-ring ${state === "source" ? "border-[hsl(var(--copper)/.65)] bg-[hsl(var(--accent)/.13)]" : state === "blocked" ? "border-dashed bg-background/45" : "bg-background/75 hover:border-[hsl(var(--copper)/.55)]"}`}><span className="block text-[9px] text-muted-foreground">{title}</span><span className="mt-1 block font-data text-xs font-medium">{value}</span></button>; }

function Ledger({ label, value }: { label: string; value: string }) { return <div className="bg-card px-3 py-2.5"><p className="text-[9px] text-muted-foreground">{label}</p><p className="mt-1 truncate font-data text-[10px]" title={value}>{value}</p></div>; }

function RiskPanel({ status, policy, onConfirm }: { status?: AllocationDataStatus; policy?: AllocationPolicyVersion; onConfirm: () => Promise<void> }) {
  const series = useMemo(() => status?.series || [], [status]);
  const [history, setHistory] = useState<AllocationSeriesHistory>();
  const [historyLoading, setHistoryLoading] = useState(false);
  const selectSeries = async (item: AllocationSeriesStatus) => { if (!item.series_id) return; setHistoryLoading(true); try { setHistory(await agentPlatformApi.allocationSeriesHistory(item.series_id)); } catch (error) { toast.error(error instanceof Error ? error.message : "历史序列加载失败"); } finally { setHistoryLoading(false); } };
  return <aside className="h-full overflow-y-auto p-4"><div className="flex items-center gap-2"><Database className="h-4 w-4 text-[hsl(var(--copper-foreground))]" /><h2 className="font-display text-xl font-semibold">风险与证据</h2></div>
    {policy?.risk_summary && <section className="mt-4 rounded-xl border bg-background/60 p-3"><p className="text-[10px] font-medium">组合风险</p><div className="mt-3 space-y-2"><RiskLine label="年化波动" value={pct(policy.risk_summary.annualized_volatility)} /><RiskLine label="最差固定压力" value={pct(policy.risk_summary.worst_stress_return)} /><RiskLine label="底层总敞口" value={pct(policy.risk_summary.gross_underlying_exposure)} /></div></section>}
    {policy?.stress_results?.length ? <section className="mt-4"><p className="text-[10px] font-medium">固定压力情景</p><div className="mt-2 space-y-2">{policy.stress_results.map((row) => <div key={row.scenario}><div className="flex justify-between font-data text-[9px]"><span>{row.scenario}</span><span>{pct(row.return)}</span></div><div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary"><div className="h-full bg-[hsl(var(--copper))]" style={{ width: `${Math.min(100, Math.abs(row.return) * 300)}%` }} /></div></div>)}</div></section> : null}
    <section className="mt-5"><p className="text-[10px] font-medium">源数据门禁</p><div className="mt-2 space-y-2">{series.map((item) => <SourceRow key={item.series_id || item.sleeve_key} item={item} onSelect={selectSeries} />)}</div>{historyLoading && <div className="mt-3 grid h-24 place-items-center"><Loader2 className="h-4 w-4 animate-spin" /></div>}{history && <SourceHistoryChart history={history} />}</section>
    {policy?.feasibility_status === "feasible" && !policy.confirmed && <Button className="mt-5 w-full" onClick={() => void onConfirm()}><Check className="mr-2 h-4 w-4" />确认当前版本</Button>}
    {policy?.confirmed && <div className="mt-5 rounded-xl border border-emerald-500/35 bg-emerald-500/[.05] p-3 text-[10px] text-emerald-700 dark:text-emerald-300"><Check className="mr-1 inline h-3.5 w-3.5" />这是账户当前确认版本；历史内容不可覆盖。</div>}
  </aside>;
}

function RiskLine({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between text-[10px]"><span className="text-muted-foreground">{label}</span><span className="font-data">{value}</span></div>; }
function SourceRow({ item, onSelect }: { item: AllocationSeriesStatus; onSelect: (item: AllocationSeriesStatus) => Promise<void> }) { return <button type="button" onClick={() => void onSelect(item)} disabled={!item.series_id} className="w-full rounded-lg border bg-background/55 p-2.5 text-left hover:border-[hsl(var(--copper)/.5)] disabled:pointer-events-none"><div className="flex items-center justify-between gap-2"><span className="text-[10px] font-medium">{item.name}</span><span className={`font-data text-[8px] ${item.quality_state === "ready" ? "text-emerald-600" : "text-amber-600"}`}>{item.quality_state}</span></div><p className="mt-1 text-[9px] leading-4 text-muted-foreground">{item.observation_months || 0}个月 · {item.first_month || "—"}—{item.last_month || "—"}</p><p className="mt-1 text-[9px] leading-4 text-muted-foreground">{item.quality_reason}</p></button>; }

function SourceHistoryChart({ history }: { history: AllocationSeriesHistory }) {
  const [hover, setHover] = useState<{ index: number; x: number; y: number }>();
  const points = history.points;
  const values = points.map((item) => item.cny_total_return_index);
  const min = values.length ? Math.min(...values) : 0, max = values.length ? Math.max(...values) : 1, span = Math.max(1e-9, max - min);
  const x = (index: number) => 18 + (index / Math.max(1, points.length - 1)) * 564;
  const y = (value: number) => 138 - ((value - min) / span) * 112;
  const path = points.map((item, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(item.cny_total_return_index).toFixed(1)}`).join(" ");
  const move = (event: React.PointerEvent<HTMLDivElement>) => { if (!points.length) return; const box = event.currentTarget.getBoundingClientRect(); const relative = Math.max(0, Math.min(box.width, event.clientX - box.left)); const index = Math.round((relative / Math.max(1, box.width)) * (points.length - 1)); setHover({ index, x: Math.min(box.width - 164, relative + 10), y: Math.max(6, event.clientY - box.top + 8) }); };
  return <div className="relative mt-3 rounded-xl border bg-background/60 p-2.5"><div className="mb-2 flex items-center justify-between"><p className="font-data text-[9px]">{history.series_id}</p><span className="text-[8px] text-muted-foreground">全量 · 未降采样</span></div>{points.length ? <div className="relative" onPointerMove={move} onPointerLeave={() => setHover(undefined)}><svg role="img" aria-label="人民币总回报全量月度历史" viewBox="0 0 600 156" className="h-36 w-full overflow-visible"><path d={path} fill="none" stroke="hsl(var(--copper-foreground))" strokeWidth="2" />{hover && <><line x1={x(hover.index)} x2={x(hover.index)} y1="20" y2="140" stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" /><circle cx={x(hover.index)} cy={y(points[hover.index].cny_total_return_index)} r="4" fill="hsl(var(--background))" stroke="hsl(var(--copper-foreground))" strokeWidth="2" /></>}</svg>{hover && <div className="pointer-events-none absolute z-10 w-40 rounded-lg border bg-popover p-2 text-[9px] shadow-lg" style={{ left: hover.x, top: hover.y }}><p className="font-data">{points[hover.index].month_end}</p><p className="mt-1">总回报指数 {points[hover.index].cny_total_return_index.toFixed(4)}</p><p className="text-muted-foreground">月回报 {pct(points[hover.index].monthly_return)}</p></div>}</div> : <div className="grid h-24 place-items-center text-center text-[9px] leading-4 text-muted-foreground">该序列尚无通过物化的历史点；不会绘制替代数据。</div>}<p className="mt-2 text-[8px] leading-4 text-muted-foreground">{history.methodology}</p></div>;
}
