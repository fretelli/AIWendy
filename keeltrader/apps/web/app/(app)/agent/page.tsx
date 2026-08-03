"use client";

import { Pin, PinOff } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  DashboardPage,
  EmptyPanel,
  MetricCard,
  Panel,
  SectionTitle,
  StatusDot,
  TextLink,
} from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import {
  agentOSApi,
  type AgentOSOverview,
  type PortfolioAnalytics,
} from "@/lib/api/agentos";
import {
  agentPlatformApi,
  type AgentRun,
  type AgentRunTrace,
  type SaaPolicyVersion,
  type TaaOverlay,
} from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

type DeckData = {
  overview: AgentOSOverview;
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
    try {
      return JSON.parse(
        window.localStorage.getItem(PIN_KEY) || "[]",
      ) as string[];
    } catch {
      return [];
    }
  });
  const period = (
    ["1M", "3M", "1Y", "3Y"].includes(params.get("period") || "")
      ? params.get("period")
      : "1Y"
  ) as "1M" | "3M" | "1Y" | "3Y";

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      agentOSApi.overview(),
      agentPlatformApi.saaPolicyVersions(),
      agentPlatformApi.taaOverlays(),
      agentPlatformApi.runs(),
    ])
      .then(async ([overview, saa, taa, runs]) => {
        const traces = (
          await Promise.allSettled(
            runs.items
              .slice(0, 5)
              .map((run) => agentPlatformApi.runTrace(run.id)),
          )
        ).flatMap((result) =>
          result.status === "fulfilled" ? [result.value] : [],
        );
        if (!cancelled)
          setData({
            overview,
            saa:
              saa.items.find((item) => item.status === "confirmed") ??
              saa.items[0],
            taa:
              taa.items.find((item) => item.status === "confirmed") ??
              taa.items[0],
            runs: runs.items,
            traces,
          });
      })
      .catch((reason) => {
        if (!cancelled)
          setError(
            reason instanceof Error ? reason.message : "overview_unavailable",
          );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const portfolio =
    data?.overview.portfolio && "total_value" in data.overview.portfolio
      ? data.overview.portfolio
      : null;
  const analytics =
    data?.overview.analytics && "total_value" in data.overview.analytics
      ? (data.overview.analytics as PortfolioAnalytics)
      : null;
  const allocation = useMemo(() => data?.saa?.targets ?? [], [data?.saa]);
  const artifacts = useMemo(
    () => data?.traces.flatMap((trace) => trace.artifacts) ?? [],
    [data?.traces],
  );
  const togglePin = (id: string) => {
    const next = pins.includes(id)
      ? pins.filter((item) => item !== id)
      : [...pins, id];
    setPins(next);
    window.localStorage.setItem(PIN_KEY, JSON.stringify(next));
  };

  if (error)
    return (
      <DashboardPage>
        <EmptyPanel
          title={locale === "zh" ? "总览暂时无法加载" : "OVERVIEW UNAVAILABLE"}
          detail={error}
        />
      </DashboardPage>
    );
  const snapshotText = portfolio
    ? locale === "zh"
      ? `组合可估值资产 ${formatCurrency(portfolio.total_value, portfolio.base_currency)}，现金 ${analytics?.cash.value != null ? formatCurrency(analytics.cash.value, portfolio.base_currency) : "不可用"}。${portfolio.missing.length ? `存在 ${portfolio.missing.length} 项真实数据缺口，相关数字保持不可用或不完整。` : "价格与直接汇率完整。"}${analytics?.today_pnl.value != null ? ` 最新日盈亏 ${formatCurrency(analytics.today_pnl.value, portfolio.base_currency)}，数据日 ${analytics.today_pnl.as_of}。` : " 今日盈亏需要连续净值记录。"}`
      : `Valuable assets are ${formatCurrency(portfolio.total_value, portfolio.base_currency)} with ${analytics?.cash.value != null ? formatCurrency(analytics.cash.value, portfolio.base_currency) : "cash unavailable"}. ${portfolio.missing.length ? `${portfolio.missing.length} real data gaps remain explicit.` : "Prices and direct FX are complete."}`
    : locale === "zh"
      ? "尚未建立真实组合账本；原型中的演示数字不会进入生产。"
      : "No real portfolio ledger exists; prototype values are never inserted into production.";

  return (
    <DashboardPage>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label={locale === "zh" ? "组合净值" : "PORTFOLIO NAV"}
          value={
            portfolio
              ? formatCurrency(portfolio.total_value, portfolio.base_currency)
              : "—"
          }
          note={
            portfolio
              ? `${portfolio.positions.length} ${locale === "zh" ? "项持仓" : "positions"} · ${portfolio.as_of}`
              : locale === "zh"
                ? "等待真实组合账本"
                : "Awaiting a real ledger"
          }
        />
        <MetricCard
          label={locale === "zh" ? "配置偏离度" : "ALLOCATION DRIFT"}
          value={
            analytics?.allocation_drift.status === "complete"
              ? formatNumber(analytics.allocation_drift.items.length)
              : "—"
          }
          note={
            analytics?.allocation_drift.reason ||
            (locale === "zh"
              ? "已确认目标与真实持仓的偏离"
              : "Real drift from confirmed targets")
          }
          color="text-agent-amber"
        />
        <MetricCard
          label={locale === "zh" ? "风险预算使用" : "RISK BUDGET"}
          value={
            analytics?.risk_budget.used != null
              ? `${(analytics.risk_budget.used * 100).toFixed(1)}%`
              : "—"
          }
          note={
            analytics?.risk_budget.reason ||
            (locale === "zh" ? "正式政策风险预算" : "Formal policy risk budget")
          }
          color="text-agent-mint"
        />
        <MetricCard
          label={locale === "zh" ? "回撤水位" : "DRAWDOWN LEVEL"}
          value={
            analytics?.drawdown.current != null
              ? `${(analytics.drawdown.current * 100).toFixed(1)}%`
              : "—"
          }
          note={
            analytics?.drawdown.status === "complete"
              ? `${period} · ${locale === "zh" ? "最大" : "max"} ${((analytics.drawdown.maximum || 0) * 100).toFixed(1)}%`
              : analytics?.drawdown.reason
          }
          color={
            (analytics?.drawdown.current || 0) < 0
              ? "text-agent-down"
              : "text-agent-mint"
          }
        />
      </div>

      <Panel className="min-h-[360px] overflow-hidden">
        <SectionTitle
          title={locale === "zh" ? "Agent 早报" : "AGENT MORNING BRIEF"}
          action={
            <TextLink
              onClick={() =>
                router.push(`/agent/decisions?period=${period}&tab=conditions`)
              }
            >
              {locale === "zh" ? "查看决策条件" : "DECISION CONDITIONS"}
            </TextLink>
          }
        />
        <div className="mb-4 flex items-center gap-2 border-b border-agent-border pb-3 font-data text-[9px] text-agent-dim">
          <StatusDot status={data?.overview.data_status} />
          {data?.overview.as_of || "—"} ·{" "}
          {locale === "zh" ? "不可变事实快照" : "IMMUTABLE FACT SNAPSHOT"}
        </div>
        <p className="max-w-[1180px] text-[13px] leading-7 text-agent-muted">
          {snapshotText}
        </p>
        {artifacts.length ? (
          <div className="mt-6 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {artifacts.slice(0, 4).map((artifact) => (
              <div
                key={artifact.id}
                className="flex items-center gap-2 rounded border border-agent-border bg-agent-raised px-3 py-2"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[10px] text-agent-text">
                    {artifact.title}
                  </span>
                  <span className="font-data text-[8px] text-agent-dim">
                    {artifact.artifact_type}
                  </span>
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => togglePin(artifact.id)}
                  title={
                    pins.includes(artifact.id)
                      ? locale === "zh"
                        ? "取消钉住"
                        : "Unpin"
                      : locale === "zh"
                        ? "钉住"
                        : "Pin"
                  }
                >
                  {pins.includes(artifact.id) ? <PinOff /> : <Pin />}
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </Panel>

      <div className="grid min-h-[360px] gap-3 xl:grid-cols-[1.1fr_.9fr]">
        <Panel>
          <SectionTitle
            title={
              locale === "zh"
                ? "相对目标的偏离 · 主动倾斜与被动漂移"
                : "DRIFT VS TARGET · ACTIVE / PASSIVE"
            }
            action={
              <TextLink
                onClick={() =>
                  router.push(`/agent/allocation?period=${period}&tab=saa`)
                }
              >
                {locale === "zh" ? "前往资产配置" : "OPEN ALLOCATION"}
              </TextLink>
            }
          />
          <div className="mb-4 grid grid-cols-2 gap-2">
            <Fact
              label={locale === "zh" ? "主动倾斜" : "ACTIVE TILT"}
              value={analytics?.drift_decomposition.active_tilt ?? undefined}
              reason={analytics?.drift_decomposition.reason}
            />
            <Fact
              label={locale === "zh" ? "被动漂移" : "PASSIVE DRIFT"}
              value={analytics?.drift_decomposition.passive_drift ?? undefined}
              reason={analytics?.drift_decomposition.reason}
            />
          </div>
          {allocation.length ? (
            <div className="flex flex-col gap-3">
              {allocation.slice(0, 8).map((item) => {
                const tactical = data?.taa?.deltas?.[item.key] ?? 0;
                return (
                  <div
                    key={item.key}
                    className="grid grid-cols-[90px_1fr_76px] items-center gap-3 text-[10px]"
                  >
                    <span className="truncate text-agent-muted">
                      {item.label}
                    </span>
                    <div className="h-1.5 overflow-hidden rounded bg-agent-border">
                      <span
                        className="block h-full bg-agent-mint"
                        style={{
                          width: `${Math.min(100, Math.max(0, item.target_weight * 100))}%`,
                        }}
                      />
                    </div>
                    <span className="text-right font-data text-agent-text">
                      {(item.target_weight * 100).toFixed(1)}%
                      {tactical
                        ? ` ${tactical > 0 ? "+" : ""}${(tactical * 100).toFixed(1)}`
                        : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyPanel
              title={
                locale === "zh" ? "没有已确认的战略配置" : "NO CONFIRMED SAA"
              }
              detail={
                locale === "zh"
                  ? "生成中的方案不会被视为正式财富政策。"
                  : "Draft allocations are not formal wealth policy."
              }
            />
          )}
        </Panel>
        <Panel>
          <SectionTitle
            title={locale === "zh" ? "后台任务" : "BACKGROUND JOBS"}
          />
          {data?.runs.length ? (
            <div className="divide-y divide-agent-border">
              {data.runs.slice(0, 7).map((run) => (
                <div
                  key={run.id}
                  className="grid grid-cols-[1fr_90px] items-center gap-3 py-3"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-xs text-agent-text">
                      {run.prompt}
                    </span>
                    <span className="mt-1 block font-data text-[9px] text-agent-dim">
                      {run.created_at.slice(0, 16)} · {run.current_step}{" "}
                      {locale === "zh" ? "步" : "steps"}
                    </span>
                  </span>
                  <span className="text-right font-data text-[9px] text-agent-mint">
                    {run.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyPanel
              title={locale === "zh" ? "暂无后台任务" : "NO BACKGROUND JOBS"}
              detail={
                locale === "zh"
                  ? "任务启动后显示真实进度。"
                  : "Real progress appears after a job starts."
              }
            />
          )}
        </Panel>
      </div>
    </DashboardPage>
  );
}

function Fact({
  label,
  value,
  reason,
}: {
  label: string;
  value?: number;
  reason?: string;
}) {
  return (
    <div className="rounded border border-agent-border bg-agent-raised p-3">
      <p className="font-data text-[8px] text-agent-dim">{label}</p>
      <p className="mt-2 font-data text-sm text-agent-text">
        {value !== undefined
          ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}pct`
          : "—"}
      </p>
      {value === undefined ? (
        <p className="mt-1 text-[9px] text-agent-dim">{reason}</p>
      ) : null}
    </div>
  );
}
