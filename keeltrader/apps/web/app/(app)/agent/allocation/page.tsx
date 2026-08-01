"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardPage, Donut, EmptyPanel, MetricCard, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { agentOSApi, type PortfolioValuation } from "@/lib/api/agentos";
import { agentPlatformApi, type AllocationPolicyVersion, type SaaPolicyVersion, type TaaOverlay, type WealthAggregate } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

type AllocationData = { wealth?: WealthAggregate; saa?: SaaPolicyVersion; taa?: TaaOverlay; policy?: AllocationPolicyVersion; portfolio?: PortfolioValuation };
const COLORS = ["var(--agent-mint)", "var(--agent-blue)", "var(--agent-amber)", "var(--agent-up)", "#c7a0ff", "#8a97a3", "#3d5568"];

export default function AllocationPage() {
  const { locale, formatCurrency } = useI18n();
  const [data, setData] = useState<AllocationData>({});
  useEffect(() => {
    let cancelled = false;
    void Promise.allSettled([
      agentPlatformApi.wealthProfile(),
      agentPlatformApi.saaPolicyVersions(),
      agentPlatformApi.taaOverlays(),
      agentPlatformApi.allocationAccounts(),
      agentOSApi.accounts(),
    ]).then(async (results) => {
      if (cancelled) return;
      const wealth = results[0].status === "fulfilled" ? results[0].value : undefined;
      const saa = results[1].status === "fulfilled" ? results[1].value.items.find((item) => item.status === "confirmed") ?? results[1].value.items[0] : undefined;
      const taa = results[2].status === "fulfilled" ? results[2].value.items.find((item) => item.status === "confirmed") ?? results[2].value.items[0] : undefined;
      const allocationAccount = results[3].status === "fulfilled" ? results[3].value.items[0] : undefined;
      const portfolioAccount = results[4].status === "fulfilled" ? results[4].value.items[0] : undefined;
      const [policyResult, portfolioResult] = await Promise.allSettled([
        allocationAccount ? agentPlatformApi.allocationPolicyVersions(allocationAccount.id).then(async (versions) => versions.items[0] ? agentPlatformApi.allocationPolicyVersion(versions.items[0].id) : undefined) : Promise.resolve(undefined),
        portfolioAccount ? agentOSApi.valuation(portfolioAccount.id) : Promise.resolve(undefined),
      ]);
      if (!cancelled) setData({ wealth, saa, taa, policy: policyResult.status === "fulfilled" ? policyResult.value : undefined, portfolio: portfolioResult.status === "fulfilled" ? portfolioResult.value : undefined });
    });
    return () => { cancelled = true; };
  }, []);
  const targets = data.saa?.targets ?? data.policy?.sleeves?.map((item) => ({ key: item.sleeve_key, label: item.label, layer: "market" as const, target_weight: item.target_weight, min_weight: item.min_weight, max_weight: item.max_weight })) ?? [];
  const targetTotal = targets.reduce((sum, item) => sum + item.target_weight, 0);
  const risk = data.policy?.risk_summary ?? {};
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="ALLOCATABLE WEALTH" value={data.wealth ? formatCurrency(data.wealth.framework.summary.allocatable_wealth_cny, "CNY") : "—"} note={data.wealth ? `${data.wealth.goals.length} ${locale === "zh" ? "项目标" : "goals"}` : (locale === "zh" ? "财富档案尚未完成" : "Wealth profile incomplete")} />
      <MetricCard label="SAA VERSION" value={data.saa ? `v${data.saa.version}` : "—"} note={data.saa?.name || (locale === "zh" ? "没有已确认战略配置" : "No confirmed SAA")} color="text-agent-mint" progress={targetTotal * 100} />
      <MetricCard label="TACTICAL OVERLAY" value={data.taa ? Object.values(data.taa.deltas).filter(Boolean).length.toString() : "0"} note={data.taa?.title || (locale === "zh" ? "当前按 SAA 运行" : "Running at SAA")} color="text-agent-amber" />
      <MetricCard label="EXPECTED VOL" value={risk.expected_volatility !== undefined ? `${(risk.expected_volatility * (risk.expected_volatility < 1 ? 100 : 1)).toFixed(1)}%` : "—"} note={data.policy?.quality_status || (locale === "zh" ? "等待正式配置计算" : "Awaiting allocation run")} color="text-agent-blue" />
    </div>
    <Tabs defaultValue="saa" className="flex flex-col gap-3">
      <TabsList className="h-auto w-fit border border-agent-border bg-agent-chrome p-1">
        <TabsTrigger value="saa">SAA</TabsTrigger><TabsTrigger value="taa">TAA</TabsTrigger><TabsTrigger value="rebalance">{locale === "zh" ? "再平衡" : "Rebalance"}</TabsTrigger><TabsTrigger value="stress">{locale === "zh" ? "情景压力" : "Stress"}</TabsTrigger>
      </TabsList>
      <TabsContent value="saa" className="mt-0 grid gap-3 xl:grid-cols-[360px_1fr]">
        <Panel className="flex min-h-[360px] flex-col items-center justify-center"><SectionTitle title={locale === "zh" ? "战略资产配置" : "Strategic Allocation"} en="LONG-TERM POLICY" />{targets.length ? <Donut values={targets.map((item, index) => ({ value: item.target_weight, color: COLORS[index % COLORS.length] }))} center={`${(targetTotal * 100).toFixed(0)}%`} label="ALLOCATED" /> : <EmptyPanel title={locale === "zh" ? "尚无 SAA" : "No SAA"} detail={locale === "zh" ? "先完成财富框架，再生成并确认战略配置。" : "Complete the wealth framework, then confirm an SAA."} />}</Panel>
        <Panel><SectionTitle title={locale === "zh" ? "目标权重与容忍带" : "Targets & Tolerance Bands"} en="POLICY WEIGHTS" />{targets.length ? <div className="divide-y divide-agent-border">{targets.map((item, index) => <div key={item.key} className="grid grid-cols-[14px_120px_1fr_64px_110px] items-center gap-3 py-3 text-[10px]"><span className="size-2 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} /><span className="truncate text-agent-muted">{item.label}</span><div className="relative h-2 rounded bg-agent-border"><span className="absolute h-full rounded bg-agent-mint/70" style={{ left: `${item.min_weight * 100}%`, width: `${Math.max(1, (item.max_weight - item.min_weight) * 100)}%` }} /><span className="absolute top-[-3px] h-3.5 w-px bg-agent-text" style={{ left: `${item.target_weight * 100}%` }} /></div><span className="text-right font-data text-agent-text">{(item.target_weight * 100).toFixed(1)}%</span><span className="text-right font-data text-agent-dim">{(item.min_weight * 100).toFixed(0)}–{(item.max_weight * 100).toFixed(0)}%</span></div>)}</div> : <EmptyPanel title={locale === "zh" ? "目标配置不可用" : "Targets unavailable"} detail={locale === "zh" ? "不会用演示权重填充生产页面。" : "Production is not populated with demo weights."} />}</Panel>
      </TabsContent>
      <TabsContent value="taa" className="mt-0 grid gap-3 xl:grid-cols-[1fr_.8fr]">
        <Panel><SectionTitle title={locale === "zh" ? "战术偏离" : "Tactical Tilts"} en="ACTIVE VIEWS" />{data.taa ? <div className="divide-y divide-agent-border">{Object.entries(data.taa.deltas).map(([key, value]) => <div key={key} className="grid grid-cols-[1fr_80px_80px] items-center py-3 text-xs"><span className="text-agent-muted">{targets.find((item) => item.key === key)?.label || key}</span><span className="text-right font-data text-agent-dim">SAA {(targets.find((item) => item.key === key)?.target_weight ?? 0) * 100}%</span><span className={`text-right font-data ${value > 0 ? "text-agent-up" : value < 0 ? "text-agent-down" : "text-agent-dim"}`}>{value > 0 ? "+" : ""}{(value * 100).toFixed(1)}pct</span></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有生效的 TAA" : "No active TAA"} detail={locale === "zh" ? "没有证据支持战术偏离时，组合保持 SAA。" : "The portfolio stays at SAA without evidence for a tactical tilt."} />}</Panel>
        <Panel><SectionTitle title={locale === "zh" ? "观点与到期" : "View & Expiry"} en="FALSIFIABLE OVERLAY" />{data.taa ? <div className="flex flex-col gap-4 text-xs leading-6 text-agent-muted"><p>{data.taa.rationale}</p><div className="rounded-md border border-agent-border bg-agent-raised p-3"><p className="font-data text-[9px] text-agent-dim">REVIEW / EXPIRY</p><p className="mt-2 text-agent-text">{data.taa.review_at} / {data.taa.expires_at}</p></div>{data.taa.falsifiers.map((item) => <div key={item} className="flex gap-2"><StatusDot status="partial" /><span>{item}</span></div>)}</div> : null}</Panel>
      </TabsContent>
      <TabsContent value="rebalance" className="mt-0"><Rebalance portfolio={data.portfolio} targets={targets} locale={locale} /></TabsContent>
      <TabsContent value="stress" className="mt-0"><Stress policy={data.policy} locale={locale} /></TabsContent>
    </Tabs>
  </DashboardPage>;
}

function Rebalance({ portfolio, targets, locale }: { portfolio?: PortfolioValuation; targets: Array<{ key: string; label: string; target_weight: number }>; locale: string }) {
  const current = new Map<string, number>();
  if (portfolio) for (const item of portfolio.positions) current.set(item.asset_class, (current.get(item.asset_class) || 0) + (item.market_value || 0));
  const total = portfolio?.total_value || 0;
  return <Panel><SectionTitle title={locale === "zh" ? "再平衡研究清单" : "Rebalance Research List"} en="NO ORDER EXECUTION" />{portfolio && targets.length ? <div className="divide-y divide-agent-border">{targets.map((item) => { const actual = total ? (current.get(item.key) || 0) / total : 0; const drift = actual - item.target_weight; return <div key={item.key} className="grid grid-cols-[140px_1fr_90px_90px_100px] items-center gap-3 py-3 text-xs"><span className="text-agent-muted">{item.label}</span><div className="h-1.5 rounded bg-agent-border"><span className="block h-full rounded bg-agent-blue" style={{ width: `${Math.min(100, actual * 100)}%` }} /></div><span className="text-right font-data text-agent-dim">{(actual * 100).toFixed(1)}%</span><span className="text-right font-data text-agent-text">{(item.target_weight * 100).toFixed(1)}%</span><span className={`text-right font-data ${Math.abs(drift) > .02 ? "text-agent-amber" : "text-agent-mint"}`}>{drift > 0 ? "+" : ""}{(drift * 100).toFixed(1)}pct</span></div>; })}<p className="pt-4 text-[10px] text-agent-dim">{locale === "zh" ? "此处只生成研究建议，不连接券商或创建订单。" : "Research suggestions only. No broker connection or order creation."}</p></div> : <EmptyPanel title={locale === "zh" ? "无法计算再平衡" : "Cannot calculate rebalance"} detail={locale === "zh" ? "需要真实持仓估值和已确认目标权重。" : "A real portfolio valuation and confirmed targets are required."} />}</Panel>;
}

function Stress({ policy, locale }: { policy?: AllocationPolicyVersion; locale: string }) {
  return <Panel><SectionTitle title={locale === "zh" ? "情景压力测试" : "Scenario Stress Test"} en="LOSS PATHS" />{policy?.stress_results?.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{policy.stress_results.map((item) => <div key={item.scenario} className="rounded-md border border-agent-border bg-agent-raised p-4"><p className="text-xs text-agent-muted">{item.scenario}</p><p className={`mt-5 font-data text-2xl ${item.return < 0 ? "text-agent-down" : "text-agent-up"}`}>{item.return > 0 ? "+" : ""}{(item.return * (Math.abs(item.return) < 1 ? 100 : 1)).toFixed(1)}%</p><div className="mt-4 h-1 rounded bg-agent-border"><span className="block h-full bg-current" style={{ width: `${Math.min(100, Math.abs(item.return) * (Math.abs(item.return) < 1 ? 300 : 3))}%` }} /></div></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有正式压力结果" : "No formal stress results"} detail={locale === "zh" ? "运行资产配置计算后展示真实情景损失，不使用占位数字。" : "Run allocation analysis to show real scenario losses without placeholders."} />}</Panel>;
}
