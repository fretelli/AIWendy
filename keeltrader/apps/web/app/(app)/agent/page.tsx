"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DashboardPage, EmptyPanel, MetricCard, MiniLine, Panel, SectionTitle, StatusDot, TextLink } from "@/components/agentos/dashboard-ui";
import { agentOSApi, type AgentOSOverview } from "@/lib/api/agentos";
import { agentPlatformApi, marketsApi, type AgentRun, type Opportunity, type SaaPolicyVersion, type TaaOverlay } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

type DeckData = {
  overview: AgentOSOverview;
  opportunities: Opportunity[];
  saa?: SaaPolicyVersion;
  taa?: TaaOverlay;
  runs: AgentRun[];
};

export default function AgentOSOverviewPage() {
  const router = useRouter();
  const { locale, formatCurrency, formatNumber } = useI18n();
  const [data, setData] = useState<DeckData | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      agentOSApi.overview(),
      marketsApi.opportunities({ limit: 6, offset: 0 }),
      agentPlatformApi.saaPolicyVersions(),
      agentPlatformApi.taaOverlays(),
      agentPlatformApi.runs(),
    ]).then(([overview, opportunities, saa, taa, runs]) => {
      if (!cancelled) setData({ overview, opportunities: opportunities.items, saa: saa.items[0], taa: taa.items.find((item) => item.status === "confirmed") ?? taa.items[0], runs: runs.items });
    }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, []);
  const portfolio = data?.overview.portfolio && "total_value" in data.overview.portfolio ? data.overview.portfolio : null;
  const positions = portfolio?.positions ?? [];
  const pnl = positions.reduce((sum, item) => sum + (item.unrealized_pnl ?? 0), 0);
  const allocation = useMemo(() => data?.saa?.targets ?? [], [data?.saa]);
  if (error) return <DashboardPage><EmptyPanel title={locale === "zh" ? "指挥舱暂时无法加载" : "Command deck unavailable"} detail={locale === "zh" ? "检查 API 与数据发布状态后重试。" : "Check API and publication status, then retry."} /></DashboardPage>;
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="PORTFOLIO NAV" value={portfolio ? formatCurrency(portfolio.total_value, portfolio.base_currency) : "—"} note={portfolio ? `${portfolio.positions.length} ${locale === "zh" ? "项持仓" : "positions"} · ${portfolio.as_of}` : (locale === "zh" ? "等待创建组合账户" : "Create a portfolio account")} color="text-agent-up" progress={portfolio ? 72 : 0} />
      <MetricCard label="UNREALIZED P&L" value={portfolio ? formatCurrency(pnl, portfolio.base_currency) : "—"} note={portfolio?.data_status === "partial" ? (locale === "zh" ? "缺少价格或直接汇率，汇总不完整" : "Missing prices or direct FX") : (locale === "zh" ? "基于可追溯估值价格" : "Based on traceable prices")} color={pnl >= 0 ? "text-agent-up" : "text-agent-down"} progress={portfolio ? Math.min(100, Math.abs(pnl / Math.max(portfolio.total_value, 1)) * 500) : 0} />
      <MetricCard label="ACTIVE DECISIONS" value={formatNumber(data?.overview.research.decisions ?? 0)} note={`${data?.overview.research.hypotheses ?? 0} ${locale === "zh" ? "条研究假设" : "research hypotheses"}`} color="text-agent-amber" progress={Math.min(100, (data?.overview.research.decisions ?? 0) * 12)} />
      <MetricCard label="AGENT JOBS" value={formatNumber(data?.runs.filter((run) => !["completed", "failed", "cancelled"].includes(run.status)).length ?? 0)} note={`${data?.runs.length ?? 0} ${locale === "zh" ? "项历史任务" : "historical runs"}`} color="text-agent-mint" progress={(data?.runs.some((run) => run.status === "running") ? 64 : 0)} />
    </div>
    <div className="grid gap-3 xl:grid-cols-[1.35fr_.9fr]">
      <Panel className="min-h-[280px]">
        <SectionTitle title={locale === "zh" ? "Agent 早报" : "Agent Morning Brief"} en="MORNING BRIEF" action={<TextLink onClick={() => router.push("/agent/decisions")}>{locale === "zh" ? "查看决策条件" : "Decision conditions"}</TextLink>} />
        <div className="grid gap-3 lg:grid-cols-[1.2fr_.8fr]">
          <div className="rounded-md border border-agent-border bg-agent-raised p-4">
            <div className="mb-4 flex items-center gap-2 font-data text-[9px] text-agent-dim"><StatusDot status={data?.overview.data_status} />{data?.overview.as_of || "—"} · AGENTOS DATA SNAPSHOT</div>
            <p className="text-[13px] leading-7 text-agent-muted">{portfolio ? (locale === "zh" ? `组合当前可估值资产为 ${formatCurrency(portfolio.total_value, portfolio.base_currency)}，共 ${positions.length} 项持仓。${portfolio.missing.length ? `有 ${portfolio.missing.length} 项数据缺口，所有相关指标已标记为不完整。` : "价格来源完整，可以继续检查配置偏离与决策条件。"}` : `Portfolio value is ${formatCurrency(portfolio.total_value, portfolio.base_currency)} across ${positions.length} positions. ${portfolio.missing.length ? `${portfolio.missing.length} data gaps remain and affected metrics are marked partial.` : "Pricing sources are complete; review allocation drift and decision conditions next."}`) : (locale === "zh" ? "尚未建立真实组合账本。创建账户或导入 CSV 后，早报会基于真实持仓、市场和研报证据生成。" : "No real portfolio ledger yet. Create an account or import CSV to generate a brief from holdings, market data, and report evidence.")}</p>
            <div className="mt-4 flex flex-wrap gap-2">{[
              ["/agent/holdings", locale === "zh" ? "看持仓" : "Holdings"],
              ["/agent/allocation", locale === "zh" ? "看配置" : "Allocation"],
              ["/agent/opportunities", locale === "zh" ? "看机会" : "Opportunities"],
            ].map(([href, label]) => <button key={href} type="button" onClick={() => router.push(href)} className="rounded border border-agent-border-strong px-3 py-1.5 text-[10px] text-agent-muted hover:border-agent-mint hover:text-agent-mint">{label}</button>)}</div>
          </div>
          <div className="h-[190px] rounded-md border border-agent-border bg-agent-surface p-3"><p className="font-data text-[9px] tracking-[.08em] text-agent-dim">PORTFOLIO VALUE TRACE</p><div className="mt-4 h-[140px]"><MiniLine values={positions.length ? positions.map((item) => item.market_value ?? 0) : [0, 0]} color="var(--agent-up)" height={100} /></div></div>
        </div>
      </Panel>
      <Panel>
        <SectionTitle title={locale === "zh" ? "配置偏离" : "Allocation Drift"} en="SAA / TAA" action={<TextLink onClick={() => router.push("/agent/allocation")}>{locale === "zh" ? "资产配置" : "Allocation"}</TextLink>} />
        {allocation.length ? <div className="flex flex-col gap-3">{allocation.slice(0, 7).map((item) => { const tactical = data?.taa?.deltas?.[item.key] ?? 0; return <div key={item.key} className="grid grid-cols-[100px_1fr_52px] items-center gap-3 text-[10px]"><span className="truncate text-agent-muted">{item.label}</span><div className="h-1.5 overflow-hidden rounded bg-agent-border"><span className="block h-full bg-agent-mint" style={{ width: `${Math.min(100, item.target_weight * 100)}%` }} /></div><span className={`text-right font-data ${tactical ? "text-agent-amber" : "text-agent-dim"}`}>{(item.target_weight * 100).toFixed(1)}%{tactical ? ` ${tactical > 0 ? "+" : ""}${(tactical * 100).toFixed(0)}` : ""}</span></div>; })}</div> : <EmptyPanel title={locale === "zh" ? "没有已确认 SAA" : "No confirmed SAA"} detail={locale === "zh" ? "从财富框架或配置研究账户生成第一版战略配置。" : "Generate the first strategic allocation from the wealth framework."} />}
      </Panel>
    </div>
    <div className="grid gap-3 xl:grid-cols-2">
      <Panel>
        <SectionTitle title={locale === "zh" ? "机会信号" : "Opportunity Signals"} en="SIGNALS / RELATIVE VALUE" action={<TextLink onClick={() => router.push("/agent/opportunities")}>{locale === "zh" ? "全部机会" : "All opportunities"}</TextLink>} />
        {data?.opportunities.length ? <div className="divide-y divide-agent-border">{data.opportunities.slice(0, 5).map((item) => <button key={item.id} type="button" onClick={() => router.push(`/agent/opportunities?entity=${item.id}`)} className="grid w-full grid-cols-[74px_1fr_80px] items-center gap-3 py-3 text-left"><span className="font-data text-[9px] uppercase text-agent-mint">{item.domain}</span><span className="min-w-0"><span className="block truncate text-xs text-agent-text">{item.title}</span><span className="mt-1 block truncate text-[10px] text-agent-dim">{item.trigger}</span></span><span className="text-right font-data text-[9px] text-agent-muted">{item.state}</span></button>)}</div> : <EmptyPanel title={locale === "zh" ? "没有可用机会信号" : "No opportunity signals"} detail={locale === "zh" ? "等待市场和股东数据完成下一次扫描。" : "Waiting for the next market and holder scan."} />}
      </Panel>
      <Panel>
        <SectionTitle title={locale === "zh" ? "研究与任务" : "Research & Tasks"} en="RESEARCH LOOP" action={<TextLink onClick={() => router.push("/agent/research")}>{locale === "zh" ? "研究中心" : "Research"}</TextLink>} />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{[
          ["HYPOTHESES", data?.overview.research.hypotheses ?? 0, "text-agent-blue"],
          ["DECISIONS", data?.overview.research.decisions ?? 0, "text-agent-amber"],
          ["EXPERIMENTS", data?.overview.research.experiments ?? 0, "text-agent-mint"],
          ["REPORTS", data?.overview.research.documents ?? 0, "text-agent-text"],
        ].map(([label, value, color]) => <div key={String(label)} className="rounded-md border border-agent-border bg-agent-raised p-3"><p className="font-data text-[8px] text-agent-dim">{label}</p><p className={`mt-2 font-data text-xl ${color}`}>{value}</p></div>)}</div>
        <div className="mt-3 divide-y divide-agent-border">{data?.runs.slice(0, 4).map((run) => <div key={run.id} className="flex items-center gap-3 py-2.5 text-[10px]"><StatusDot status={run.status} /><span className="min-w-0 flex-1 truncate text-agent-muted">{run.prompt}</span><span className="font-data text-agent-dim">{run.status}</span></div>)}</div>
      </Panel>
    </div>
  </DashboardPage>;
}
