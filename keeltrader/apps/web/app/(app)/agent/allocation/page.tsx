"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { DashboardPage, Donut, EmptyPanel, MetricCard, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUrlTab } from "@/hooks/use-url-tab";
import { agentOSApi, type PortfolioValuation } from "@/lib/api/agentos";
import { agentPlatformApi, type AllocationAccount, type AllocationDataStatus, type AllocationPolicyVersion, type SaaPolicyVersion, type TaaOverlay, type WealthAggregate } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

type MethodKey = "black_litterman" | "core_satellite" | "risk_parity" | "all_weather" | "lifecycle";
type Data = { wealth?: WealthAggregate; account?: AllocationAccount; status?: AllocationDataStatus; saa?: SaaPolicyVersion; taa?: TaaOverlay; policy?: AllocationPolicyVersion; portfolio?: PortfolioValuation };
const COLORS = ["var(--agent-mint)", "var(--agent-blue)", "var(--agent-amber)", "var(--agent-up)", "#c7a0ff", "#8a97a3", "#3d5568"];
const methods: Array<{ key: MethodKey; zh: string; en: string }> = [
  { key: "black_litterman", zh: "Black-Litterman", en: "Black-Litterman" }, { key: "core_satellite", zh: "核心卫星", en: "Core-Satellite" },
  { key: "risk_parity", zh: "风险平价", en: "Risk Parity" }, { key: "all_weather", zh: "全天候", en: "All Weather" }, { key: "lifecycle", zh: "生命周期", en: "Lifecycle" },
];

export default function AllocationPage() {
  const { locale, formatCurrency } = useI18n();
  const [tab, setTab] = useUrlTab(["saa", "taa", "rebalance", "stress"], "saa");
  const [data, setData] = useState<Data>({});
  const [method, setMethod] = useState<MethodKey>("risk_parity");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ capital: "", horizon: "", drawdown: "", liquidity: "" });

  const load = async () => {
    const [wealthResult, accountResult, statusResult, saaResult, taaResult, portfolioAccounts] = await Promise.allSettled([
      agentPlatformApi.wealthProfile(), agentPlatformApi.allocationAccounts(), agentPlatformApi.allocationDataStatus(), agentPlatformApi.saaPolicyVersions(), agentPlatformApi.taaOverlays(), agentOSApi.accounts(),
    ]);
    const wealth = wealthResult.status === "fulfilled" ? wealthResult.value : undefined;
    const account = accountResult.status === "fulfilled" ? accountResult.value.items[0] : undefined;
    const status = statusResult.status === "fulfilled" ? statusResult.value : undefined;
    const saa = saaResult.status === "fulfilled" ? saaResult.value.items.find((item) => item.status === "confirmed") ?? saaResult.value.items[0] : undefined;
    const taa = taaResult.status === "fulfilled" ? taaResult.value.items.find((item) => item.status === "confirmed") ?? taaResult.value.items[0] : undefined;
    const portfolioAccount = portfolioAccounts.status === "fulfilled" ? portfolioAccounts.value.items[0] : undefined;
    const [versions, valuation] = await Promise.allSettled([
      account ? agentPlatformApi.allocationPolicyVersions(account.id) : Promise.resolve({ items: [] as AllocationPolicyVersion[] }),
      portfolioAccount ? agentOSApi.valuation(portfolioAccount.id) : Promise.resolve(undefined),
    ]);
    const first = versions.status === "fulfilled" ? versions.value.items[0] : undefined;
    const policy = first ? await agentPlatformApi.allocationPolicyVersion(first.id).catch(() => first) : undefined;
    setData({ wealth, account, status, saa, taa, policy, portfolio: valuation.status === "fulfilled" ? valuation.value : undefined });
    if (account) setForm({ capital: String(account.capital), horizon: String(account.horizon_months), drawdown: String(account.max_drawdown * 100), liquidity: String(account.liquidity_reserve) });
  };
  useEffect(() => { void (async () => { await load(); })().catch(() => undefined); }, []);

  const generate = async () => {
    setBusy(true);
    try {
      let account = data.account;
      const payload = { name: locale === "zh" ? "正式资产配置账户" : "Formal allocation account", base_currency: "CNY" as const, capital: Number(form.capital), horizon_months: Number(form.horizon), liquidity_reserve: Number(form.liquidity), max_drawdown: Number(form.drawdown) / 100, max_leverage: 1, future_cash_needs: [], allowed_markets: ["CN", "HK", "FX"], allowed_instruments: ["fund", "etf", "futures", "options"], hard_restrictions: ["no_broker_execution", "no_synthetic_data"] };
      if (!payload.capital || !payload.horizon_months || !payload.max_drawdown) throw new Error(locale === "zh" ? "请填写金额、期限和最大回撤。" : "Capital, horizon and max drawdown are required.");
      account = account ? await agentPlatformApi.updateAllocationAccount(account.id, payload) : await agentPlatformApi.createAllocationAccount(payload);
      const policy = await agentPlatformApi.generateAllocationPolicyWithMethod(account.id, { methodology_key: method });
      setData((current) => ({ ...current, account, policy }));
      toast.success(policy.feasibility_status === "feasible" ? (locale === "zh" ? "已生成正式预览" : "Formal preview generated") : (locale === "zh" ? "输入或历史不足，已保留不可用原因" : "Unavailable state recorded"));
    } catch (error) { toast.error(error instanceof Error ? error.message : "Generation failed"); } finally { setBusy(false); }
  };
  const publish = async () => {
    if (!data.account || !data.policy) return;
    setBusy(true);
    try {
      const confirmed = data.policy.confirmed ? data.policy : await agentPlatformApi.confirmAllocationPolicy(data.account.id, data.policy.id);
      const frameworks = await agentPlatformApi.wealthFrameworkVersions();
      const framework = frameworks.items[0] ?? await agentPlatformApi.createWealthFrameworkVersion();
      const now = new Date(); const review = new Date(now); review.setFullYear(review.getFullYear() + 1);
      await agentPlatformApi.publishAllocationPolicyAsSaa(confirmed.id, { framework_version_id: framework.id, name: `${methods.find((item) => item.key === method)?.zh} SAA`, effective_date: now.toISOString().slice(0, 10), review_date: review.toISOString().slice(0, 10) });
      await load(); toast.success(locale === "zh" ? "已确认并发布为 SAA；未创建任何订单。" : "Confirmed and published as SAA; no orders created.");
    } catch (error) { toast.error(error instanceof Error ? error.message : "Publish failed"); } finally { setBusy(false); }
  };

  const targets = data.policy?.sleeves?.map((item) => ({ key: item.sleeve_key, label: item.label, target_weight: item.target_weight, min_weight: item.min_weight, max_weight: item.max_weight })) ?? data.saa?.targets ?? [];
  const total = targets.reduce((sum, item) => sum + item.target_weight, 0);
  const risk = data.policy?.risk_summary ?? {};
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="ALLOCATABLE WEALTH" value={data.wealth ? formatCurrency(data.wealth.framework.summary.allocatable_wealth_cny, "CNY") : "—"} note={data.wealth?.framework.ready ? (locale === "zh" ? "财富框架已就绪" : "Wealth framework ready") : (locale === "zh" ? "财富框架不完整" : "Wealth framework incomplete")} />
      <MetricCard label="METHODOLOGY" value={methods.find((item) => item.key === method)?.en || "—"} note={locale === "zh" ? "版本化正式收益序列" : "Versioned formal return series"} color="text-agent-mint" />
      <MetricCard label="DATA READINESS" value={data.status?.formal_ready ? "READY" : "UNAVAILABLE"} note={data.status ? `${data.status.series.filter((item) => item.quality_state === "ready").length}/${data.status.series.length} series` : "—"} color={data.status?.formal_ready ? "text-agent-mint" : "text-agent-amber"} />
      <MetricCard label="EXPECTED VOL" value={risk.expected_volatility != null ? `${(risk.expected_volatility * (risk.expected_volatility < 1 ? 100 : 1)).toFixed(1)}%` : "—"} note={data.policy?.quality_status || (locale === "zh" ? "等待正式计算" : "Awaiting formal run")} color="text-agent-blue" />
    </div>
    <Tabs value={tab} onValueChange={setTab} className="flex flex-col gap-3">
      <TabsList className="h-auto w-fit max-w-full overflow-x-auto border border-agent-border bg-agent-chrome p-1 lg:hidden"><TabsTrigger value="saa">SAA</TabsTrigger><TabsTrigger value="taa">TAA</TabsTrigger><TabsTrigger value="rebalance">{locale === "zh" ? "再平衡" : "Rebalance"}</TabsTrigger><TabsTrigger value="stress">{locale === "zh" ? "压力测试" : "Stress"}</TabsTrigger></TabsList>
      <TabsContent value="saa" className="mt-0 grid gap-3 xl:grid-cols-[320px_1fr]">
        <Panel><SectionTitle title={locale === "zh" ? "真实输入" : "Formal Inputs"} en="CONSTRAINTS" /><div className="grid gap-4"><Field label={locale === "zh" ? "可配置金额（CNY）" : "Capital (CNY)"} value={form.capital} onChange={(capital) => setForm((item) => ({ ...item, capital }))} /><Field label={locale === "zh" ? "投资期限（月）" : "Horizon (months)"} value={form.horizon} onChange={(horizon) => setForm((item) => ({ ...item, horizon }))} /><Field label={locale === "zh" ? "最大可承受回撤（%）" : "Max drawdown (%)"} value={form.drawdown} onChange={(drawdown) => setForm((item) => ({ ...item, drawdown }))} /><Field label={locale === "zh" ? "流动性保留（CNY）" : "Liquidity reserve"} value={form.liquidity} onChange={(liquidity) => setForm((item) => ({ ...item, liquidity }))} /><div><Label>{locale === "zh" ? "方法论" : "Methodology"}</Label><Select value={method} onValueChange={(value) => setMethod(value as MethodKey)}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent>{methods.map((item) => <SelectItem key={item.key} value={item.key}>{locale === "zh" ? item.zh : item.en}</SelectItem>)}</SelectContent></Select></div><Button onClick={() => void generate()} disabled={busy}>{busy ? (locale === "zh" ? "计算中…" : "Running…") : (locale === "zh" ? "生成配置预览" : "Generate preview")}</Button></div></Panel>
        <div className="grid gap-3"><Panel><SectionTitle title={locale === "zh" ? "生成 / 预览 / 确认" : "Generate / Preview / Confirm"} en="VERSIONED POLICY" />{targets.length ? <div className="grid gap-5 lg:grid-cols-[220px_1fr]"><div className="flex items-center justify-center"><Donut values={targets.map((item, index) => ({ value: item.target_weight, color: COLORS[index % COLORS.length] }))} center={`${(total * 100).toFixed(0)}%`} label="ALLOCATED" /></div><div className="divide-y divide-agent-border">{targets.map((item, index) => <div key={item.key} className="grid grid-cols-[12px_1fr_70px_94px] items-center gap-3 py-3 text-[10px]"><span className="size-2 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} /><span className="text-agent-muted">{item.label}</span><span className="text-right font-data text-agent-text">{(item.target_weight * 100).toFixed(1)}%</span><span className="text-right font-data text-agent-dim">{(item.min_weight * 100).toFixed(0)}–{(item.max_weight * 100).toFixed(0)}%</span></div>)}<div className="flex items-center gap-3 pt-4"><StatusDot status={data.policy?.feasibility_status === "feasible" ? "complete" : "unavailable"} /><span className="text-xs text-agent-muted">{data.policy?.quality_status}</span><Button className="ml-auto" onClick={() => void publish()} disabled={busy || data.policy?.feasibility_status !== "feasible"}>{locale === "zh" ? "确认并发布 SAA" : "Confirm & publish SAA"}</Button></div></div></div> : <EmptyPanel title={locale === "zh" ? "尚无正式配置" : "No formal allocation"} detail={data.status?.missing_required?.length ? `${locale === "zh" ? "缺少：" : "Missing: "}${data.status.missing_required.join("、")}` : (locale === "zh" ? "填写真实输入并选择方法；历史不足时不会产生示例权重。" : "Provide real inputs and choose a method. Insufficient history never produces sample weights.")} />}</Panel>{data.policy?.infeasible_reasons?.length ? <Panel><SectionTitle title={locale === "zh" ? "不可用原因" : "Unavailable Reasons"} en="HARD GAPS" /><div className="space-y-2">{data.policy.infeasible_reasons.map((item) => <div key={item} className="rounded border border-agent-border bg-agent-raised p-3 text-xs text-agent-amber">{item}</div>)}</div></Panel> : null}</div>
      </TabsContent>
      <TabsContent value="taa" className="mt-0 grid gap-3 xl:grid-cols-[1fr_.8fr]"><Panel><SectionTitle title={locale === "zh" ? "战术偏离" : "Tactical Tilts"} en="ACTIVE VIEWS" />{data.taa ? <div className="divide-y divide-agent-border">{Object.entries(data.taa.deltas).map(([key, value]) => <div key={key} className="grid grid-cols-[1fr_90px] py-3 text-xs"><span className="text-agent-muted">{key}</span><span className={`text-right font-data ${value > 0 ? "text-agent-up" : value < 0 ? "text-agent-down" : "text-agent-dim"}`}>{value > 0 ? "+" : ""}{(value * 100).toFixed(1)}pct</span></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有生效的 TAA" : "No active TAA"} detail={locale === "zh" ? "没有可证伪观点时，组合保持已确认 SAA。" : "Without falsifiable views, the portfolio remains at confirmed SAA."} />}</Panel><Panel><SectionTitle title={locale === "zh" ? "观点、复核与到期" : "View, Review & Expiry"} en="FALSIFIABLE" />{data.taa ? <div className="space-y-3 text-xs leading-6 text-agent-muted"><p>{data.taa.rationale}</p><p className="font-data text-agent-text">{data.taa.review_at} / {data.taa.expires_at}</p>{data.taa.falsifiers.map((item) => <p key={item}>· {item}</p>)}</div> : null}</Panel></TabsContent>
      <TabsContent value="rebalance" className="mt-0"><Rebalance portfolio={data.portfolio} targets={targets} locale={locale} /></TabsContent>
      <TabsContent value="stress" className="mt-0"><Panel><SectionTitle title={locale === "zh" ? "情景压力测试" : "Scenario Stress Test"} en="LOSS PATHS" />{data.policy?.stress_results?.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{data.policy.stress_results.map((item) => <div key={item.scenario} className="rounded-md border border-agent-border bg-agent-raised p-4"><p className="text-xs text-agent-muted">{item.scenario}</p><p className={`mt-5 font-data text-2xl ${item.return < 0 ? "text-agent-down" : "text-agent-up"}`}>{item.return > 0 ? "+" : ""}{(item.return * (Math.abs(item.return) < 1 ? 100 : 1)).toFixed(1)}%</p></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有正式压力结果" : "No formal stress results"} detail={locale === "zh" ? "压力结果只来自同一版本收益序列和硬约束。" : "Stress results only use the same versioned return series and hard constraints."} />}</Panel></TabsContent>
    </Tabs>
  </DashboardPage>;
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <div><Label>{label}</Label><Input className="mt-2 font-data" inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)} /></div>; }
function Rebalance({ portfolio, targets, locale }: { portfolio?: PortfolioValuation; targets: Array<{ key: string; label: string; target_weight: number }>; locale: string }) {
  const current = new Map<string, number>(); if (portfolio) for (const item of portfolio.positions) current.set(item.asset_class, (current.get(item.asset_class) || 0) + (item.market_value || 0)); const total = portfolio?.total_value || 0;
  return <Panel><SectionTitle title={locale === "zh" ? "再平衡研究清单" : "Rebalance Research List"} en="NO ORDER EXECUTION" />{portfolio && targets.length ? <div className="divide-y divide-agent-border">{targets.map((item) => { const actual = total ? (current.get(item.key) || 0) / total : 0; const drift = actual - item.target_weight; return <div key={item.key} className="grid grid-cols-[1fr_80px_80px_90px] gap-3 py-3 text-xs"><span className="text-agent-muted">{item.label}</span><span className="text-right font-data">{(actual * 100).toFixed(1)}%</span><span className="text-right font-data text-agent-dim">{(item.target_weight * 100).toFixed(1)}%</span><span className={`text-right font-data ${Math.abs(drift) > .02 ? "text-agent-amber" : "text-agent-mint"}`}>{drift > 0 ? "+" : ""}{(drift * 100).toFixed(1)}pct</span></div>; })}<p className="pt-4 text-[10px] text-agent-dim">{locale === "zh" ? "仅生成研究建议，不连接券商、不创建订单。" : "Research suggestions only; no broker connection or orders."}</p></div> : <EmptyPanel title={locale === "zh" ? "无法计算再平衡" : "Cannot calculate rebalance"} detail={locale === "zh" ? "需要真实持仓估值和已确认目标权重。" : "A real valuation and confirmed targets are required."} />}</Panel>;
}
