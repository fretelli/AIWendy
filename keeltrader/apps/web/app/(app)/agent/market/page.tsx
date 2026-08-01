"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DashboardPage, EmptyPanel, MetricCard, MiniLine, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { agentPlatformApi, marketsApi, type MacroMarketSnapshot, type MarketCapabilities, type MarketCapitalSnapshot } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

const RatesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.RatesDrilldown));
const FuturesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.FuturesDrilldown));
const OptionsDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.OptionsDrilldown));

export default function MarketPage() {
  const params = useSearchParams();
  const router = useRouter();
  const { locale, formatNumber, formatCurrency } = useI18n();
  const [capital, setCapital] = useState<MarketCapitalSnapshot | null>(null);
  const [macro, setMacro] = useState<MacroMarketSnapshot | null>(null);
  const [capabilities, setCapabilities] = useState<MarketCapabilities | null>(null);
  useEffect(() => { void Promise.all([marketsApi.capital(), agentPlatformApi.macroMarket(), marketsApi.capabilities()]).then(([nextCapital, nextMacro, nextCapabilities]) => { setCapital(nextCapital); setMacro(nextMacro); setCapabilities(nextCapabilities); }).catch(() => undefined); }, []);
  const breadth = capital?.breadth;
  const period = ["1M", "3M", "1Y", "3Y"].includes(params.get("period") || "") ? params.get("period")! : "1Y";
  const historyWindow = period === "1M" ? 22 : period === "3M" ? 66 : period === "3Y" ? 756 : 252;
  const history = useMemo(() => (capital?.history ?? []).slice(-historyWindow), [capital, historyWindow]);
  const macroRows = useMemo(() => Object.entries(macro?.series ?? {}), [macro]);
  const defaultTab = ["valuation", "correlation", "factors", "macro", "capital", "rates", "futures", "options"].includes(params.get("tab") || "") ? params.get("tab")! : "valuation";
  const selectTab = (tab: string) => { const next = new URLSearchParams(params.toString()); next.set("tab", tab); router.replace(`/agent/market?${next}`); };
  return <DashboardPage>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="MARKET TURNOVER" value={capital?.liquidity.turnover_cny ? formatCurrency(capital.liquidity.turnover_cny, "CNY") : "—"} note={capital?.as_of || (locale === "zh" ? "数据不可用" : "Unavailable")} color="text-agent-up" />
      <MetricCard label="ADVANCE RATIO" value={breadth?.advance_ratio !== undefined ? `${(breadth.advance_ratio * (breadth.advance_ratio <= 1 ? 100 : 1)).toFixed(1)}%` : "—"} note={breadth ? `${breadth.advances} / ${breadth.declines}` : undefined} color="text-agent-mint" />
      <MetricCard label="MARGIN BALANCE" value={capital?.leverage.balance_cny ? formatCurrency(capital.leverage.balance_cny, "CNY") : "—"} note={capital?.leverage.coverage_label || capital?.leverage.freshness_state} color="text-agent-amber" />
      <MetricCard label="7D FUNDING" value={capital?.funding_rates.seven_day_pct !== undefined ? `${capital.funding_rates.seven_day_pct.toFixed(2)}%` : "—"} note={`${capital?.funding_rates.as_of || "—"} · cap ${capabilities?.version?.slice(0, 8) || "—"}`} color="text-agent-blue" />
    </div>
    <Tabs value={defaultTab} onValueChange={selectTab} className="flex flex-col gap-3">
      <TabsList className="h-auto w-fit max-w-full overflow-x-auto border border-agent-border bg-agent-chrome p-1"><TabsTrigger value="valuation">{locale === "zh" ? "估值" : "Valuation"}</TabsTrigger><TabsTrigger value="correlation">{locale === "zh" ? "相关性" : "Correlation"}</TabsTrigger><TabsTrigger value="factors">{locale === "zh" ? "因子" : "Factors"}</TabsTrigger><TabsTrigger value="macro">{locale === "zh" ? "宏观" : "Macro"}</TabsTrigger><TabsTrigger value="capital">{locale === "zh" ? "资金" : "Capital"}</TabsTrigger><TabsTrigger value="rates">{locale === "zh" ? "利率债券" : "Rates"}</TabsTrigger><TabsTrigger value="futures">{locale === "zh" ? "期货" : "Futures"}</TabsTrigger><TabsTrigger value="options">{locale === "zh" ? "期权" : "Options"}</TabsTrigger></TabsList>
      <TabsContent value="valuation" className="mt-0 grid gap-3 xl:grid-cols-[1.2fr_.8fr]">
        <Panel><SectionTitle title={locale === "zh" ? "全市场成交与广度" : "Turnover & Breadth"} en="RAW MARKET STATE" />{history.length ? <div className="h-[300px]"><MiniLine values={history.map((item) => item.turnover_cny)} color="var(--agent-up)" height={100} /></div> : <EmptyPanel title={locale === "zh" ? "没有市场历史" : "No market history"} detail={locale === "zh" ? "等待 Tushare 原子发布完成。" : "Waiting for the Tushare atomic publication."} />}</Panel>
        <Panel><SectionTitle title={locale === "zh" ? "估值状态" : "Valuation State"} en="NO SYNTHETIC CURVE" /><EmptyPanel title={locale === "zh" ? "统一估值分位尚未物化" : "Unified valuation percentiles not materialized"} detail={locale === "zh" ? "当前接口没有可靠的全市场 PE/PB 历史分位，页面明确不可用，不用指数代理或虚构曲线替代。" : "The current API has no reliable market-wide PE/PB percentile history. No proxy or fabricated curve is used."} /></Panel>
      </TabsContent>
      <TabsContent value="correlation" className="mt-0"><Panel><SectionTitle title={locale === "zh" ? "跨资产相关性" : "Cross-asset Correlation"} en="POINT-IN-TIME" /><EmptyPanel title={locale === "zh" ? "需要同频率资产收益序列" : "Aligned return series required"} detail={locale === "zh" ? "相关矩阵只会基于相同频率、相同截至日的正式收益序列生成；当前缺口不会用模拟矩阵填充。" : "The matrix requires formal return series with aligned frequency and as-of dates. Missing data is never replaced by a simulated matrix."} /></Panel></TabsContent>
      <TabsContent value="factors" className="mt-0 grid gap-3 xl:grid-cols-2">
        <Panel><SectionTitle title={locale === "zh" ? "市场拥挤代理" : "Crowding Proxies"} en="OBSERVED, NOT SCORED" /><div className="divide-y divide-agent-border">{[
          ["TOP 20 TURNOVER", capital?.liquidity.top20_turnover_share], ["TOP 50 TURNOVER", capital?.liquidity.top50_turnover_share], ["ETF FLOW COVERAGE", capital?.etf_flows.coverage_ratio], ["ADVANCE RATIO", breadth?.advance_ratio],
        ].map(([name, value]) => <div key={String(name)} className="grid grid-cols-[160px_1fr_64px] items-center gap-3 py-3"><span className="font-data text-[9px] text-agent-dim">{name}</span><div className="h-1.5 rounded bg-agent-border"><span className="block h-full rounded bg-agent-mint" style={{ width: `${Math.min(100, Number(value || 0) * (Number(value || 0) <= 1 ? 100 : 1))}%` }} /></div><span className="text-right font-data text-[10px] text-agent-muted">{value !== undefined ? `${(Number(value) * (Number(value) <= 1 ? 100 : 1)).toFixed(1)}%` : "—"}</span></div>)}</div></Panel>
        <Panel><SectionTitle title={locale === "zh" ? "因子模型" : "Factor Model"} en="MATERIALIZATION STATUS" /><EmptyPanel title={locale === "zh" ? "因子截面尚未正式发布" : "Factor cross-section not published"} detail={locale === "zh" ? "价值、动量、低波、质量和成长因子需要可审计截面与 IC 历史。现阶段只展示真实市场代理。" : "Value, momentum, low-vol, quality, and growth require auditable cross-sections and IC history. Only observed proxies are shown now."} /></Panel>
      </TabsContent>
      <TabsContent value="macro" className="mt-0"><Panel><SectionTitle title={locale === "zh" ? "宏观原始序列" : "Raw Macro Series"} en="NO LOCAL TRANSFORMS" />{macroRows.length ? <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">{macroRows.map(([key, item]) => { const last = item.rows?.[0]; return <div key={key} className="rounded-md border border-agent-border bg-agent-raised p-3"><div className="flex items-center gap-2"><StatusDot status={item.available ? "complete" : "unavailable"} /><span className="font-data text-[9px] uppercase text-agent-dim">{key}</span></div><p className="mt-3 truncate font-data text-lg text-agent-text">{last ? formatNumber(Number(Object.values(last).find((value) => typeof value === "number") ?? 0)) : "—"}</p><p className="mt-2 text-[9px] text-agent-dim">{item.start || "—"} → {item.end || "—"} · {item.points || 0} pts</p></div>; })}</div> : <EmptyPanel title={locale === "zh" ? "宏观序列不可用" : "Macro series unavailable"} detail={locale === "zh" ? "检查结构化数据发布状态。" : "Check structured-data publication status."} />}</Panel></TabsContent>
      <TabsContent value="capital" className="mt-0 grid gap-3 xl:grid-cols-2"><Panel><SectionTitle title={locale === "zh" ? "ETF 资金流" : "ETF Flows"} en="ESTIMATED FROM SHARES" />{capital?.etf_flows.available ? <div className="flex flex-col gap-4"><p className="font-data text-3xl text-agent-up">{formatCurrency(capital.etf_flows.estimated_net_flow_cny || 0, "CNY")}</p><p className="text-xs leading-6 text-agent-muted">{capital.etf_flows.note}</p><div className="grid grid-cols-2 gap-2">{Object.entries(capital.etf_flows.groups || {}).map(([key, value]) => <div key={key} className="rounded border border-agent-border bg-agent-raised p-3"><p className="text-[10px] text-agent-dim">{key}</p><p className={`mt-2 font-data text-sm ${value >= 0 ? "text-agent-up" : "text-agent-down"}`}>{formatCurrency(value, "CNY")}</p></div>)}</div></div> : <EmptyPanel title="ETF flow unavailable" detail={capital?.etf_flows.note || "No published ETF share-flow snapshot."} />}</Panel><Panel><SectionTitle title={locale === "zh" ? "数据解释" : "Interpretation"} en="SOURCE-AWARE" /><div className="flex flex-col gap-3">{capital?.interpretations.map((item) => <div key={item} className="rounded border border-agent-border bg-agent-raised p-3 text-xs leading-6 text-agent-muted">{item}</div>)}</div></Panel></TabsContent>
      <TabsContent value="rates" className="mt-0"><RatesDrilldown /></TabsContent>
      <TabsContent value="futures" className="mt-0"><FuturesDrilldown /></TabsContent>
      <TabsContent value="options" className="mt-0"><OptionsDrilldown /></TabsContent>
    </Tabs>
  </DashboardPage>;
}
