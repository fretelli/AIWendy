"use client";

import { Pin, PinOff } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DashboardPage, EmptyPanel, MetricCard, MiniLine, Panel, SectionTitle, StatusDot, TextLink } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { agentOSApi, type AgentOSOverview, type PortfolioAnalytics } from "@/lib/api/agentos";
import { agentPlatformApi, marketsApi, type AgentRun, type AgentRunTrace, type Opportunity, type SaaPolicyVersion, type TaaOverlay } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

type DeckData = {
  overview: AgentOSOverview;
  opportunities: Opportunity[];
  saa?: SaaPolicyVersion;
  taa?: TaaOverlay;
  runs: AgentRun[];
  traces: AgentRunTrace[];
};

const PIN_KEY = "keeltrader:overview-pins:v1";

export default function AgentOSOverviewPage() {
  const router = useRouter();
  const params = useSearchParams();
  const { locale, formatCurrency, formatNumber } = useI18n();
  const [data, setData] = useState<DeckData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pins, setPins] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try { return JSON.parse(window.localStorage.getItem(PIN_KEY) || "[]") as string[]; } catch { return []; }
  });
  const period = (["1M", "3M", "1Y", "3Y"].includes(params.get("period") || "") ? params.get("period") : "1Y") as "1M" | "3M" | "1Y" | "3Y";
  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      agentOSApi.overview(), marketsApi.opportunities({ limit: 6, offset: 0 }),
      agentPlatformApi.saaPolicyVersions(), agentPlatformApi.taaOverlays(), agentPlatformApi.runs(),
    ]).then(async ([overview, opportunities, saa, taa, runs]) => {
      const traces = (await Promise.allSettled(runs.items.slice(0, 5).map((run) => agentPlatformApi.runTrace(run.id))))
        .flatMap((result) => result.status === "fulfilled" ? [result.value] : []);
      if (!cancelled) setData({
        overview, opportunities: opportunities.items, saa: saa.items.find((item) => item.status === "confirmed") ?? saa.items[0],
        taa: taa.items.find((item) => item.status === "confirmed") ?? taa.items[0], runs: runs.items, traces,
      });
    }).catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "overview_unavailable"); });
    return () => { cancelled = true; };
  }, []);
  const portfolio = data?.overview.portfolio && "total_value" in data.overview.portfolio ? data.overview.portfolio : null;
  const analytics = data?.overview.analytics && "total_value" in data.overview.analytics ? data.overview.analytics as PortfolioAnalytics : null;
  const allocation = useMemo(() => data?.saa?.targets ?? [], [data?.saa]);
  const artifacts = useMemo(() => data?.traces.flatMap((trace) => trace.artifacts.map((artifact) => ({ ...artifact, runId: trace.run.id }))) ?? [], [data?.traces]);
  const togglePin = (id: string) => {
    const next = pins.includes(id) ? pins.filter((item) => item !== id) : [...pins, id];
    setPins(next);
    window.localStorage.setItem(PIN_KEY, JSON.stringify(next));
  };
  if (error) return <DashboardPage><EmptyPanel title={locale === "zh" ? "指挥舱暂时无法加载" : "Command deck unavailable"} detail={error} /></DashboardPage>;
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="PORTFOLIO NAV" value={portfolio ? formatCurrency(portfolio.total_value, portfolio.base_currency) : "—"} note={portfolio ? `${portfolio.positions.length} ${locale === "zh" ? "项持仓" : "positions"} · ${portfolio.as_of}` : (locale === "zh" ? "等待真实组合账本" : "Awaiting a real ledger")} color="text-agent-text" />
      <MetricCard label="ALLOCATION DRIFT" value={analytics?.allocation_drift.status === "complete" ? formatNumber(analytics.allocation_drift.items.length) : "—"} note={analytics?.allocation_drift.reason || (locale === "zh" ? "已确认 SAA 与映射后的真实偏离" : "Real drift after confirmed SAA mapping")} color="text-agent-amber" />
      <MetricCard label="RISK BUDGET" value={analytics?.risk_budget.used != null ? `${(analytics.risk_budget.used * 100).toFixed(1)}%` : "—"} note={analytics?.risk_budget.reason || (locale === "zh" ? "正式政策风险预算" : "Formal policy risk budget")} color="text-agent-blue" />
      <MetricCard label="DRAWDOWN LEVEL" value={analytics?.drawdown.current != null ? `${(analytics.drawdown.current * 100).toFixed(1)}%` : "—"} note={analytics?.drawdown.status === "complete" ? `${period} · max ${((analytics.drawdown.maximum || 0) * 100).toFixed(1)}%` : analytics?.drawdown.reason} color={(analytics?.drawdown.current || 0) < 0 ? "text-agent-down" : "text-agent-mint"} />
    </div>
    <div className="grid gap-3 xl:grid-cols-[1.35fr_.9fr]">
      <Panel className="min-h-[300px]">
        <SectionTitle title={locale === "zh" ? "Agent 早报" : "Agent Morning Brief"} en="MORNING BRIEF" action={<TextLink onClick={() => router.push(`/agent/decisions?period=${period}&tab=conditions`)}>{locale === "zh" ? "查看决策条件" : "Decision conditions"}</TextLink>} />
        <div className="grid gap-3 lg:grid-cols-[1.2fr_.8fr]">
          <div className="rounded-md border border-agent-border bg-agent-raised p-4">
            <div className="mb-4 flex items-center gap-2 font-data text-[9px] text-agent-dim"><StatusDot status={data?.overview.data_status} />{data?.overview.as_of || "—"} · IMMUTABLE FACT SNAPSHOT</div>
            <p className="text-[13px] leading-7 text-agent-muted">{portfolio ? (locale === "zh"
              ? `组合可估值资产 ${formatCurrency(portfolio.total_value, portfolio.base_currency)}，现金 ${analytics?.cash.value != null ? formatCurrency(analytics.cash.value, portfolio.base_currency) : "不可用"}。${portfolio.missing.length ? `存在 ${portfolio.missing.length} 项数据缺口；相关指标保持不可用或不完整。` : "价格与直接汇率完整。"}${analytics?.today_pnl.value != null ? ` 最新日盈亏 ${formatCurrency(analytics.today_pnl.value, portfolio.base_currency)}（${analytics.today_pnl.as_of}）。` : " 今日盈亏需要连续净值记录。"}`
              : `Valuable assets are ${formatCurrency(portfolio.total_value, portfolio.base_currency)} with ${analytics?.cash.value != null ? formatCurrency(analytics.cash.value, portfolio.base_currency) : "cash unavailable"}. ${portfolio.missing.length ? `${portfolio.missing.length} data gaps remain explicit.` : "Prices and direct FX are complete."}`)
              : (locale === "zh" ? "尚未建立真实组合账本；页面不会填充原型示例数字。" : "No real portfolio ledger exists; prototype values are never inserted.")}</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <Fact label={locale === "zh" ? "主动倾斜" : "Active tilt"} value={analytics?.drift_decomposition.active_tilt ?? undefined} reason={analytics?.drift_decomposition.reason} />
              <Fact label={locale === "zh" ? "被动漂移" : "Passive drift"} value={analytics?.drift_decomposition.passive_drift ?? undefined} reason={analytics?.drift_decomposition.reason} />
            </div>
          </div>
          <div className="h-[210px] rounded-md border border-agent-border bg-agent-surface p-3"><p className="font-data text-[9px] tracking-[.08em] text-agent-dim">PORTFOLIO NAV · {period}</p><div className="mt-4 h-[158px]">{analytics?.nav.history_available ? <MiniLine values={analytics.nav.items.map((item) => item.nav)} color="var(--agent-up)" height={100} /> : <EmptyPanel title={locale === "zh" ? "净值历史不足" : "NAV history unavailable"} detail={locale === "zh" ? "导入真实 NAV 或积累每日快照后显示。" : "Import real NAV or accumulate daily snapshots."} />}</div></div>
        </div>
      </Panel>
      <Panel>
        <SectionTitle title={locale === "zh" ? "配置偏离" : "Allocation Drift"} en="SAA / TAA" action={<TextLink onClick={() => router.push(`/agent/allocation?period=${period}&tab=saa`)}>{locale === "zh" ? "资产配置" : "Allocation"}</TextLink>} />
        {allocation.length ? <div className="flex flex-col gap-3">{allocation.slice(0, 7).map((item) => { const tactical = data?.taa?.deltas?.[item.key] ?? 0; return <div key={item.key} className="grid grid-cols-[100px_1fr_62px] items-center gap-3 text-[10px]"><span className="truncate text-agent-muted">{item.label}</span><div className="h-1.5 overflow-hidden rounded bg-agent-border"><span className="block h-full bg-agent-mint" style={{ width: `${Math.min(100, item.target_weight * 100)}%` }} /></div><span className="text-right font-data text-agent-text">{(item.target_weight * 100).toFixed(1)}%{tactical ? ` ${tactical > 0 ? "+" : ""}${(tactical * 100).toFixed(0)}` : ""}</span></div>; })}</div> : <EmptyPanel title={locale === "zh" ? "没有已确认 SAA" : "No confirmed SAA"} detail={locale === "zh" ? "配置生成层不会被当作正式财富政策。" : "Generated allocation is not treated as formal wealth policy."} />}
      </Panel>
    </div>
    <div className="grid gap-3 xl:grid-cols-2">
      <Panel><SectionTitle title={locale === "zh" ? "机会信号" : "Opportunity Signals"} en="SIGNALS / RELATIVE VALUE" action={<TextLink onClick={() => router.push(`/agent/opportunities?period=${period}&tab=signals`)}>{locale === "zh" ? "全部机会" : "All opportunities"}</TextLink>} />{data?.opportunities.length ? <div className="divide-y divide-agent-border">{data.opportunities.slice(0, 5).map((item) => <button key={item.id} type="button" onClick={() => router.push(`/agent/opportunities?period=${period}&tab=signals&entity=${item.id}`)} className="grid w-full grid-cols-[74px_1fr_80px] items-center gap-3 py-3 text-left"><span className="font-data text-[9px] uppercase text-agent-mint">{item.domain}</span><span className="min-w-0"><span className="block truncate text-xs text-agent-text">{item.title}</span><span className="mt-1 block truncate text-[10px] text-agent-dim">{item.trigger}</span></span><span className="text-right font-data text-[9px] text-agent-muted">{item.state}</span></button>)}</div> : <EmptyPanel title={locale === "zh" ? "没有可用机会信号" : "No opportunity signals"} detail={locale === "zh" ? "等待正式数据扫描。" : "Waiting for formal data scans."} />}</Panel>
      <Panel><SectionTitle title={locale === "zh" ? "可钉住的 Agent 产物" : "Pinnable Agent Artifacts"} en="SAFE ARTIFACT REFERENCES" action={<TextLink onClick={() => router.push(`/agent/workspace?period=${period}`)}>{locale === "zh" ? "Agent 工作台" : "Agent Workspace"}</TextLink>} />{artifacts.length ? <div className="divide-y divide-agent-border">{artifacts.slice(0, 8).sort((a, b) => Number(pins.includes(b.id)) - Number(pins.includes(a.id))).map((artifact) => <div key={artifact.id} className="flex items-center gap-3 py-3"><span className="min-w-0 flex-1"><span className="block truncate text-xs text-agent-text">{artifact.title}</span><span className="mt-1 block font-data text-[9px] text-agent-dim">{artifact.artifact_type} · {artifact.created_at.slice(0, 16)}</span></span><Button variant="ghost" size="icon" onClick={() => togglePin(artifact.id)} title={pins.includes(artifact.id) ? (locale === "zh" ? "取消钉住" : "Unpin") : (locale === "zh" ? "钉住" : "Pin")}>{pins.includes(artifact.id) ? <PinOff /> : <Pin />}</Button></div>)}</div> : <EmptyPanel title={locale === "zh" ? "暂无 Agent 产物" : "No Agent artifacts"} detail={locale === "zh" ? "任务产出表格或报告后可在此钉住引用。" : "Tables and reports produced by runs can be pinned here."} />}</Panel>
    </div>
  </DashboardPage>;
}

function Fact({ label, value, reason }: { label: string; value?: number; reason?: string }) {
  return <div className="rounded border border-agent-border bg-agent-surface p-3"><p className="font-data text-[8px] text-agent-dim">{label}</p><p className="mt-2 font-data text-sm text-agent-text">{value !== undefined ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}pct` : "—"}</p>{value === undefined ? <p className="mt-1 text-[9px] text-agent-dim">{reason}</p> : null}</div>;
}
