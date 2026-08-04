"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { DashboardPage, EmptyPanel, MiniLine, Panel } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { marketsApi, type CorrelationBoard, type CorrelationHistory, type FactorBoard, type FactorHistory, type MacroCatalog, type MacroMetricSummary, type MacroSeriesDetail, type ValuationBoard } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

const RatesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.RatesDrilldown));
const FuturesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.FuturesDrilldown));
const OptionsDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.OptionsDrilldown));
const ValuationScatterChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.ValuationScatterChart), { ssr: false });
const TimeSeriesChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.TimeSeriesChart), { ssr: false });

type TopTab = "market" | "macro";
type Detail = "rates" | "futures" | "options";
type Period = "1M" | "3M" | "1Y" | "3Y";

export default function MarketPage() {
  const params = useSearchParams();
  const router = useRouter();
  const { locale } = useI18n();
  const tab: TopTab = params.get("tab") === "macro" ? "macro" : "market";
  const detail = (["rates", "futures", "options"].includes(params.get("detail") || "") ? params.get("detail") : null) as Detail | null;
  const period = (["1M", "3M", "1Y", "3Y"].includes(params.get("period") || "") ? params.get("period") : "1Y") as Period;
  const showMarket = !detail && tab === "market";
  const showMacro = !detail && tab === "macro";
  const { data: valuation = null } = useSWR<ValuationBoard>(showMarket ? "markets/valuation-board" : null, marketsApi.valuationBoard);
  const { data: correlations = null } = useSWR<CorrelationBoard>(showMarket ? "markets/correlations/60" : null, () => marketsApi.correlations(60));
  const { data: correlationHistory = null } = useSWR<CorrelationHistory>(showMarket ? `markets/correlations/60/history/${period}` : null, () => marketsApi.correlationHistory(60, periodLimit(period)));
  const { data: factors = null } = useSWR<FactorBoard>(showMarket ? "markets/factors" : null, marketsApi.factors);
  const { data: factorHistory = null } = useSWR<FactorHistory>(showMarket ? `markets/factors/history/${period}` : null, () => marketsApi.factorHistory(periodLimit(period)));
  const { data: macro = null } = useSWR<MacroCatalog>(showMacro ? "markets/macro/catalog-v1" : null, marketsApi.macroCatalog);

  const closeDetail = () => {
    const next = new URLSearchParams(params.toString());
    next.delete("detail");
    router.replace(`/agent/market?${next}`);
  };
  if (detail) return <DashboardPage className="max-w-none"><div className="mb-1"><Button variant="ghost" size="sm" onClick={closeDetail}>{locale === "zh" ? "返回市场与宏观" : "Back to Market & Macro"}</Button></div>{detail === "rates" ? <RatesDrilldown /> : detail === "futures" ? <FuturesDrilldown period={period} /> : <OptionsDrilldown />}</DashboardPage>;
  return <DashboardPage className="max-w-none gap-3 px-4 py-[22px]">
    {tab === "market" ? <MarketBoard valuation={valuation} correlations={correlations} correlationHistory={correlationHistory} factors={factors} factorHistory={factorHistory} locale={locale} /> : <MacroBoard data={macro} locale={locale} period={period} />}
  </DashboardPage>;
}

function MarketBoard({ valuation, correlations, correlationHistory, factors, factorHistory, locale }: { valuation: ValuationBoard | null; correlations: CorrelationBoard | null; correlationHistory: CorrelationHistory | null; factors: FactorBoard | null; factorHistory: FactorHistory | null; locale: "zh" | "en" }) {
  return <div className="grid min-h-[calc(100dvh-104px)] grid-rows-[minmax(390px,1.05fr)_minmax(330px,.95fr)] gap-3">
    <div className="grid min-h-0 gap-3 xl:grid-cols-[1.6fr_1fr]">
      <ValuationMatrix data={valuation} locale={locale} />
      <CorrelationMatrix data={correlations} history={correlationHistory} locale={locale} />
    </div>
    <div className="grid min-h-0 gap-3 xl:grid-cols-[1.35fr_1fr]">
      <ValuationRanking data={valuation} locale={locale} />
      <FactorCrowding data={factors} history={factorHistory} locale={locale} />
    </div>
  </div>;
}

function ValuationMatrix({ data, locale }: { data: ValuationBoard | null; locale: "zh" | "en" }) {
  const [kind, setKind] = useState<"all" | "broad" | "industry" | "held">("all");
  const isV2 = data?.metadata.methodology_key === "kt_valuation_percentile_v2";
  const scopedItems = (isV2 ? data?.items || [] : []).filter((item) => kind === "all" || (kind === "broad" ? item.universe === "broad" : kind === "industry" ? item.universe === "sw_l1" : false));
  const items = scopedItems.filter((item) => item.percentile_change_3m != null && item.pe_percentile != null);
  return <Panel className="flex min-h-0 flex-col overflow-hidden">
    <div className="mb-2 flex flex-wrap items-baseline gap-3"><PanelTitle title={locale === "zh" ? "估值分位矩阵" : "Valuation Percentile Matrix"} note={locale === "zh" ? "纵轴 PE 分位 · 横轴 Δ3M · 气泡 = 正式拥挤度；行业名悬停查看" : "PE percentile · Δ3M · bubble = formal crowding; hover for industry labels"} /><div className="ml-auto flex flex-wrap gap-1">{([['all', '全部', 'All'], ['broad', '宽基指数', 'Broad Indices'], ['industry', '申万一级', 'SW Level 1'], ['held', '我的持仓行业', 'Held Industries']] as const).map(([value, zh, en]) => <Button key={value} type="button" size="sm" variant={kind === value ? "secondary" : "outline"} onClick={() => setKind(value)}>{locale === "zh" ? zh : en}</Button>)}</div></div>
    {items.length ? <ValuationScatterChart items={items.map(item => ({ ...item, name: localizedMarketName(item.name, item.code, locale) }))} locale={locale} title={locale === "zh" ? "估值分位矩阵" : "Valuation Percentile Matrix"} asOf={data?.metadata.as_of} /> : <DataGap title={kind === "held" ? (locale === "zh" ? "持仓行业映射不可用" : "Held-industry mapping unavailable") : (locale === "zh" ? "估值矩阵不可用" : "Valuation matrix unavailable")} reason={kind === "held" ? "held_industry_mapping_unavailable" : isV2 ? data?.metadata.reason_code : "valuation_v2_pending"} locale={locale} />}
    {items.some(item => item.crowding_status !== "available") ? <p className="mt-1 text-[9px] text-agent-amber">{locale === "zh" ? "部分或全部拥挤度尚未达到正式方法覆盖门槛，气泡保持中性，不使用成交活跃度代理。" : "Some crowding values do not meet the formal methodology threshold; neutral bubbles are shown without activity proxies."}</p> : null}
  </Panel>;
}

function CorrelationMatrix({ data, history, locale }: { data: CorrelationBoard | null; history: CorrelationHistory | null; locale: "zh" | "en" }) {
  const [pair, setPair] = useState<[number, number] | null>(null);
  const pairKey = pair && data ? `${data.series[Math.min(...pair)].key}|${data.series[Math.max(...pair)].key}` : null;
  const pairDates = pairKey ? (history?.points || []).map(item => item.as_of || "—") : [];
  const pairValues = pairKey ? (history?.points || []).map(item => item.pairs[pairKey] ?? null) : [];
  return <Panel className="min-h-0 overflow-auto">
    <PanelTitle title={locale === "zh" ? "大类相关性 60 日滚动" : "60-Day Rolling Correlations"} note={locale === "zh" ? "小字为环比变化" : "Small figures show window-over-window change"} />
    {data?.matrix.length ? <div className="grid gap-1" style={{ gridTemplateColumns: `68px repeat(${data.series.length}, minmax(48px,1fr))` }}>
      <span />{data.series.map((item) => <span key={item.key} className="pb-2 text-center text-[9px] text-agent-dim">{locale === "zh" ? item.label : factorLabel(item.key, locale)}</span>)}
      {data.series.map((row, i) => <CorrelationRow key={row.key} row={row} index={i} data={data} locale={locale} onSelect={(column) => { if (column !== i) setPair([i, column]); }} />)}
    </div> : <DataGap title={locale === "zh" ? "相关矩阵不可用" : "Correlation matrix unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
    <Dialog open={Boolean(pair)} onOpenChange={(open) => { if (!open) setPair(null); }}><DialogContent className="w-[min(1100px,calc(100vw-32px))] max-w-none border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{pair && data ? `${data.series[pair[0]].label} ↔ ${data.series[pair[1]].label}` : "—"}</DialogTitle><DialogDescription>{locale === "zh" ? "正式 60 日滚动相关性历史" : "Formal 60-day rolling correlation history"}</DialogDescription></DialogHeader>{pairValues.length ? <TimeSeriesChart dates={pairDates} series={[{ name: locale === "zh" ? "相关系数" : "Correlation", values: pairValues }]} locale={locale} title={locale === "zh" ? "相关性历史" : "Correlation History"} height={430} /> : <DataGap title={locale === "zh" ? "相关性历史不可用" : "Correlation history unavailable"} reason={history?.metadata.reason_code} locale={locale} />}</DialogContent></Dialog>
  </Panel>;
}

function CorrelationRow({ row, index, data, locale, onSelect }: { row: CorrelationBoard["series"][number]; index: number; data: CorrelationBoard; locale: "zh" | "en"; onSelect: (column: number) => void }) {
  return <><span className="flex items-center text-[9px] text-agent-muted">{locale === "zh" ? row.label : factorLabel(row.key, locale)}</span>{data.matrix[index].map((value, column) => {
    const delta = data.delta_matrix[index]?.[column];
    return <button type="button" disabled={value == null || index === column} onClick={() => onSelect(column)} key={column} className={cn("flex min-h-10 flex-col items-center justify-center rounded-sm font-data text-[9px] disabled:cursor-default", value == null || index === column ? "bg-agent-raised text-agent-dim" : value >= 0 ? "bg-agent-up/15 text-agent-text hover:ring-1 hover:ring-agent-mint" : "bg-agent-mint/10 text-agent-text hover:ring-1 hover:ring-agent-mint")}>{value == null || index === column ? "—" : value.toFixed(2)}{delta != null && index !== column ? <span className={delta >= 0 ? "text-agent-up" : "text-agent-mint"}>{delta >= 0 ? "+" : ""}{delta.toFixed(2)}</span> : null}</button>;
  })}</>;
}

function ValuationRanking({ data, locale }: { data: ValuationBoard | null; locale: "zh" | "en" }) {
  const items = (data?.items || []).slice(0, 9);
  return <Panel className="min-h-0 overflow-hidden"><PanelTitle title={locale === "zh" ? "估值分位排序 · 带时间维度" : "Valuation Ranking · Time-Aware"} note={locale === "zh" ? "点表头排序 · 变化为分位百分点" : "Percentile changes in points"} />
    {items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-[9px]"><thead className="font-data text-agent-dim"><tr><th className="pb-2 font-normal">{locale === "zh" ? "名称 / 代码" : "Name / Code"}</th><th className="pb-2 text-right font-normal">PE</th><th className="pb-2 text-right font-normal">PE %</th><th className="pb-2 text-right font-normal">Δ1M</th><th className="pb-2 text-right font-normal">Δ3M</th><th className="pb-2 text-right font-normal">PB %</th><th className="pb-2 text-right font-normal">{locale === "zh" ? "换手" : "Turnover"}</th></tr></thead><tbody className="divide-y divide-agent-border">{items.map((item) => <tr key={`${item.source}-${item.code}`}><td className="py-2.5"><span className="block text-[11px] text-agent-text">{localizedMarketName(item.name, item.code, locale)}</span><span className="font-data text-[8px] text-agent-dim">{item.code}</span></td><NumberCell value={item.pe} /><PercentCell value={item.pe_percentile} /><SignedCell value={item.percentile_change_1m} /><SignedCell value={item.percentile_change_3m} /><PercentCell value={item.pb_percentile} /><NumberCell value={item.turnover_rate} suffix="%" /></tr>)}</tbody></table></div> : <DataGap title={locale === "zh" ? "估值排序不可用" : "Valuation ranking unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
  </Panel>;
}

function FactorCrowding({ data, history, locale }: { data: FactorBoard | null; history: FactorHistory | null; locale: "zh" | "en" }) {
  const [selected, setSelected] = useState<string | null>(null);
  const selectedDates = (history?.points || []).map(item => item.as_of || "—");
  const selectedValues = (history?.points || []).map(item => item.factors.find(factor => factor.key === selected)?.crowding ?? null);
  return <Panel className="min-h-0 overflow-auto"><PanelTitle title={locale === "zh" ? "因子收益与拥挤度" : "Factor Returns & Crowding"} note={`kt_factor_v1 · ${data?.crowding.methodology_key || "kt_crowding_v2"}`} />
    {data?.factors.length ? <div className="flex flex-col gap-2">{data.factors.map((factor) => { const crowding = factor.crowding; return <button type="button" onClick={() => setSelected(factor.key)} key={factor.key} className="grid grid-cols-[96px_1fr_48px] items-center gap-2 rounded-sm text-left hover:bg-agent-raised"><div><p className="text-[10px] text-agent-text">{factorLabel(factor.key, locale)}</p><p className="mt-1 font-data text-[8px] text-agent-dim">{formatSigned(factor.returns["1M"])} · {formatSigned(factor.returns["3M"])} · {formatSigned(factor.returns["1Y"])}</p></div><div className="h-1.5 overflow-hidden rounded bg-agent-border"><span className={cn("block h-full", crowding != null && crowding >= .75 ? "bg-agent-up" : crowding != null && crowding >= .5 ? "bg-agent-amber" : "bg-agent-mint")} style={{ width: `${Math.max(0, Math.min(100, Number(crowding || 0) * 100))}%` }} /></div><span className="text-right font-data text-[9px] text-agent-muted">{crowding == null ? "—" : `${Math.round(crowding * 100)}%`}</span></button>; })}</div> : <DataGap title={locale === "zh" ? "因子收益不可用" : "Factor returns unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
    {data && data.crowding.status !== "available" ? <p className="mt-3 text-[9px] leading-4 text-agent-amber">{crowdingCoverageNote(data, locale)}</p> : null}
    <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null); }}><DialogContent className="w-[min(1100px,calc(100vw-32px))] max-w-none border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{selected ? factorLabel(selected, locale) : "—"}</DialogTitle><DialogDescription>{locale === "zh" ? "正式拥挤度历史；历史快照不足时保持空缺" : "Formal crowding history; missing snapshots remain blank"}</DialogDescription></DialogHeader>{selectedValues.some(value => value != null) ? <TimeSeriesChart dates={selectedDates} series={[{ name: locale === "zh" ? "拥挤度" : "Crowding", values: selectedValues.map(value => value == null ? null : value * 100) }]} locale={locale} title={locale === "zh" ? "因子拥挤度历史" : "Factor Crowding History"} height={430} /> : <DataGap title={locale === "zh" ? "因子历史不可用" : "Factor history unavailable"} reason={history?.metadata.reason_code} locale={locale} />}</DialogContent></Dialog>
  </Panel>;
}

type MacroRange = Period | "5Y" | "10Y" | "ALL";

function MacroBoard({ data, locale, period }: { data: MacroCatalog | null; locale: "zh" | "en"; period: Period }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [range, setRange] = useState<MacroRange>(period);
  const rows = data?.items || [];
  const selectedRow = rows.find(row => row.key === selected);
  const { data: detail = null, isLoading, error } = useSWR<MacroSeriesDetail>(
    selected ? `markets/macro/series/${selected}/analysis-v1` : null,
    () => marketsApi.macroSeries(selected!),
  );
  return <div className="grid min-h-[calc(100dvh-104px)] grid-rows-[1fr_auto] gap-3"><Panel className="min-h-0 overflow-hidden"><PanelTitle title={locale === "zh" ? "宏观指标面板 · 环比 / 同比 / 历史分位 / 趋势" : "Macro Indicators · Changes / Percentiles / Trends"} note={locale === "zh" ? "官方字段优先 · 计算值标明口径 · 点任一行查看四组历史" : "Official fields first · calculated values disclose their method"} />
    {rows.length ? <div className="overflow-x-auto"><div className="min-w-[980px]"><div className="grid grid-cols-[minmax(170px,1.4fr)_105px_92px_92px_105px_minmax(160px,1fr)_145px] gap-2 border-b border-agent-border pb-2 font-data text-[8px] text-agent-dim"><span>{locale === "zh" ? "指标 / 正式来源" : "Indicator / Source"}</span><span className="text-right">{locale === "zh" ? "最新值" : "Latest"}</span><span className="text-right">{locale === "zh" ? "环比" : "MoM"}</span><span className="text-right">{locale === "zh" ? "同比" : "YoY"}</span><span className="text-right">{locale === "zh" ? "近10年分位" : "10Y Percentile"}</span><span>{locale === "zh" ? "主值趋势" : "Primary Trend"}</span><span className="text-right">{locale === "zh" ? "原始数据范围" : "Raw Coverage"}</span></div>{rows.map((row) => {
      const summary = row.summary;
      const sparkline = (row.sparkline?.values || []).filter((value): value is number => typeof value === "number");
      return <button type="button" onClick={() => { setSelected(row.key); setRange(period); }} key={row.key} className="grid min-h-[76px] w-full grid-cols-[minmax(170px,1.4fr)_105px_92px_92px_105px_minmax(160px,1fr)_145px] items-center gap-2 border-b border-agent-border text-left text-[9px] transition-colors hover:bg-agent-raised focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint"><div><p className="text-[11px] text-agent-text">{macroLabel(row.key, locale)}</p><p className="mt-1 font-data text-[8px] text-agent-dim">{row.source || row.table}</p></div><MacroMetricCell metric={summary?.primary} locale={locale} emphasis /><MacroMetricCell metric={summary?.mom} locale={locale} signed /><MacroMetricCell metric={summary?.yoy} locale={locale} signed /><MacroMetricCell metric={summary?.percentile_10y} locale={locale} percentile /><div className="h-9">{sparkline.length > 1 ? <MiniLine values={sparkline} color="var(--agent-blue)" height={38} /> : <span className="font-data text-agent-dim">—</span>}</div><span className="text-right font-data text-agent-dim">{row.start || "—"} → {row.end || "—"}</span></button>;
    })}</div></div> : <DataGap title={locale === "zh" ? "宏观数据不可用" : "Macro data unavailable"} locale={locale} />}
  </Panel><Panel className="grid grid-cols-[70px_1fr] items-start gap-4 py-3"><span className="font-data text-[9px] text-agent-mint">METHOD<br/>{locale === "zh" ? "口径" : "READ"}</span><p className="text-[10px] leading-5 text-agent-muted">{locale === "zh" ? "环比、同比优先读取官方字段；社融、PMI 与利率只做透明且单位安全的计算。历史分位基于主值滚动十年，样本不足十年时明确标记实际窗口。" : "Official changes are preferred. Social financing, PMI and rates use transparent unit-safe calculations. Percentiles use the primary series over a rolling ten-year window."}</p></Panel><Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null); }}><DialogContent className="h-[min(900px,calc(100dvh-24px))] w-[min(1380px,calc(100vw-24px))] max-w-none overflow-y-auto border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{selected ? macroLabel(selected, locale) : "—"}</DialogTitle><DialogDescription>{selectedRow ? `${selectedRow.source || selectedRow.table} · ${selectedRow.start || "—"} → ${selectedRow.end || "—"} · ${selectedRow.points || 0} ${locale === "zh" ? "个原始观测" : "raw observations"}` : ""}</DialogDescription></DialogHeader><div className="flex flex-wrap gap-1 border-b border-agent-border pb-3">{(["1M", "3M", "1Y", "3Y", "5Y", "10Y", "ALL"] as MacroRange[]).map(value => <Button key={value} type="button" size="sm" variant={range === value ? "secondary" : "outline"} onClick={() => setRange(value)}>{value === "ALL" ? (locale === "zh" ? "全部" : "All") : value}</Button>)}</div>{isLoading ? <EmptyPanel title={locale === "zh" ? "正在读取正式历史" : "Loading formal history"} detail={locale === "zh" ? "只加载当前指标，不再下载全部宏观表。" : "Only the selected indicator is loaded."} /> : error || !detail?.series ? <DataGap title={locale === "zh" ? "宏观序列不可用" : "Macro series unavailable"} locale={locale} /> : <div className="grid gap-3 lg:grid-cols-2"><MacroChartPanel kind="primary" detail={detail} range={range} locale={locale} /><MacroChartPanel kind="mom" detail={detail} range={range} locale={locale} /><MacroChartPanel kind="yoy" detail={detail} range={range} locale={locale} /><MacroChartPanel kind="percentile_10y" detail={detail} range={range} locale={locale} /></div>}</DialogContent></Dialog></div>;
}

function MacroMetricCell({ metric, locale, emphasis = false, signed = false, percentile = false }: { metric?: MacroMetricSummary; locale: "zh" | "en"; emphasis?: boolean; signed?: boolean; percentile?: boolean }) {
  const value = formatMacroMetric(metric, locale, signed, percentile);
  const method = metric?.method === "official" ? (locale === "zh" ? "官" : "OFF") : metric?.method === "calculated" ? (locale === "zh" ? "算" : "CALC") : null;
  const title = macroMetricExplanation(metric, locale);
  return <span title={title} className={cn("flex items-center justify-end gap-1 text-right font-data", emphasis ? "text-[13px] text-agent-text" : metric?.value != null && Number(metric.value) >= 0 ? "text-agent-muted" : "text-agent-mint")}><span>{value}</span>{method ? <span className={cn("rounded-sm border px-1 py-px text-[7px]", metric?.method === "official" ? "border-agent-blue/30 text-agent-blue" : "border-agent-amber/30 text-agent-amber")}>{method}</span> : null}</span>;
}

function MacroChartPanel({ kind, detail, range, locale }: { kind: "primary" | "mom" | "yoy" | "percentile_10y"; detail: MacroSeriesDetail; range: MacroRange; locale: "zh" | "en" }) {
  const series = detail.series?.[kind];
  const rows = sliceMacroSeries(series?.rows || [], detail.frequency, range);
  const labels: Record<typeof kind, [string, string]> = { primary: [detail.primary_alias === "yoy" ? "官方主值（同比）" : "主值", "Primary"], mom: ["环比", "MoM"], yoy: ["同比", "YoY"], percentile_10y: ["近10年历史分位", "10Y Historical Percentile"] };
  const title = labels[kind][locale === "zh" ? 0 : 1];
  if (series?.meta.method === "not_applicable") return <Panel tone="raised" className="min-h-[310px]"><PanelTitle title={title} note={locale === "zh" ? "不适用" : "Not applicable"} /><EmptyPanel title={locale === "zh" ? "该指标没有可靠官方环比口径" : "No reliable official MoM measure"} detail={locale === "zh" ? "保持不适用，不使用累计值反推或代理数据。" : "No cumulative-value inference or proxy is used."} /></Panel>;
  return <Panel tone="raised" className="min-h-[310px]"><PanelTitle title={title} note={`${series?.meta.unit || ""} · ${macroMethodLabel(series?.meta.method, locale)}`} />{rows.some(row => row.value != null) ? <TimeSeriesChart dates={rows.map(row => row.period)} series={[{ name: title, values: rows.map(row => row.value) }]} locale={locale} title={`${title} · ${range === "ALL" ? (locale === "zh" ? "全部" : "All") : range}`} height={250} /> : <EmptyPanel title={locale === "zh" ? "可比较历史不足" : "Insufficient comparable history"} detail={macroMetricExplanation(series?.meta as MacroMetricSummary | undefined, locale)} />}</Panel>;
}

function PanelTitle({ title, note }: { title: string; note?: string }) { return <div className="mb-3 flex items-baseline gap-3"><h2 className="text-sm font-medium text-agent-text">{title}</h2>{note ? <span className="font-data text-[8px] text-agent-dim">{note}</span> : null}</div>; }
function DataGap({ title, reason, locale }: { title: string; reason?: string; locale: "zh" | "en" }) { return <EmptyPanel title={title} detail={marketGapReason(reason, locale)} />; }
function NumberCell({ value, suffix = "" }: { value?: number; suffix?: string }) { return <td className="py-2.5 text-right font-data text-agent-muted">{value == null ? "—" : `${Number(value).toFixed(1)}${suffix}`}</td>; }
function PercentCell({ value }: { value?: number }) { return <td className="py-2.5 text-right font-data text-agent-muted">{value == null ? "—" : `${Math.round(Number(value) * 100)}%`}</td>; }
function SignedCell({ value }: { value?: number }) { return <td className={cn("py-2.5 text-right font-data", Number(value || 0) > 0 ? "text-agent-up" : Number(value || 0) < 0 ? "text-agent-mint" : "text-agent-dim")}>{value == null ? "—" : `${Number(value) > 0 ? "+" : ""}${(Number(value) * 100).toFixed(1)}`}</td>; }
function formatSigned(value?: number | null) { return value == null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`; }
function factorLabel(key: string, locale: "zh" | "en") { const labels: Record<string, [string, string]> = { value: ["价值", "Value"], momentum: ["动量", "Momentum"], low_vol: ["低波", "Low Vol"], quality: ["质量", "Quality"], growth: ["成长", "Growth"], size: ["规模", "Size"], dividend: ["红利", "Dividend"], cn_equity: ["A股", "CN Equity"], hk_equity: ["港股", "HK Equity"], us_equity: ["美股", "US Equity"], bond: ["债券", "Bonds"], commodity: ["商品", "Commodities"], fx: ["外汇", "FX"] }; return labels[key]?.[locale === "zh" ? 0 : 1] || key; }
function macroLabel(key: string, locale: "zh" | "en") { const labels: Record<string, [string, string]> = { gdp: ["GDP", "GDP"], cpi: ["居民消费价格", "CPI"], ppi: ["工业生产者价格", "PPI"], money_supply: ["货币供应量", "Money Supply"], social_financing: ["社会融资规模", "Social Financing"], pmi: ["采购经理指数", "PMI"], shibor: ["上海银行间同业拆放利率", "SHIBOR"], lpr: ["贷款市场报价利率", "LPR"], us_treasury: ["美国国债收益率", "US Treasury"], us_real_treasury: ["美国实际国债收益率", "US Real Treasury"] }; return labels[key]?.[locale === "zh" ? 0 : 1] || key; }
function localizedMarketName(name: string, code: string, locale: "zh" | "en") { return locale === "en" && /[\u3400-\u9fff]/.test(name) ? code : name; }
function periodLimit(period: Period) {
  return ({ "1M": 31, "3M": 92, "1Y": 366, "3Y": 1096 } as const)[period];
}
function sliceMacroSeries<T extends { period: string; value: number | null }>(rows: T[], frequency: string | undefined, period: MacroRange) {
  if (period === "ALL") return rows;
  const normalized = (frequency || "daily").toLowerCase();
  const pointsByFrequency: Record<string, Record<Exclude<MacroRange, "ALL">, number>> = {
    daily: { "1M": 22, "3M": 66, "1Y": 252, "3Y": 756, "5Y": 1260, "10Y": 2520 },
    weekly: { "1M": 5, "3M": 14, "1Y": 52, "3Y": 156, "5Y": 260, "10Y": 520 },
    monthly: { "1M": 1, "3M": 3, "1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120 },
    quarterly: { "1M": 1, "3M": 1, "1Y": 4, "3Y": 12, "5Y": 20, "10Y": 40 },
  };
  const bucket = normalized.includes("quarter") ? "quarterly" : normalized.includes("month") ? "monthly" : normalized.includes("week") ? "weekly" : "daily";
  return rows.slice(-pointsByFrequency[bucket][period]);
}
function formatMacroMetric(metric: MacroMetricSummary | undefined, locale: "zh" | "en", signed = false, percentile = false) {
  if (!metric || metric.value == null) return metric?.method === "not_applicable" ? (locale === "zh" ? "不适用" : "N/A") : "—";
  const prefix = signed && metric.value > 0 ? "+" : "";
  const value = new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits: 2 }).format(metric.value);
  const unit = percentile ? "%" : metric.unit;
  return `${prefix}${value}${unit === "%" || unit === "bp" ? unit : unit ? ` ${unit}` : ""}`;
}
function macroMethodLabel(method: string | undefined, locale: "zh" | "en") {
  if (method === "official") return locale === "zh" ? "官方" : "Official";
  if (method === "calculated") return locale === "zh" ? "透明计算" : "Calculated";
  return locale === "zh" ? "不适用" : "Not applicable";
}
function macroMetricExplanation(metric: MacroMetricSummary | undefined, locale: "zh" | "en") {
  if (!metric) return locale === "zh" ? "等待正式数据。" : "Waiting for formal data.";
  if (metric.method === "not_applicable") return locale === "zh" ? "该口径不适用；不使用代理或反推值。" : "Not applicable; no proxy or inferred value is used.";
  const method = macroMethodLabel(metric.method, locale);
  const field = metric.source_field ? `${locale === "zh" ? "字段" : "field"} ${metric.source_field}` : metric.formula || "";
  const sample = metric.sample_count ? ` · ${metric.sample_count} ${locale === "zh" ? "个样本" : "samples"}${metric.window_complete === false ? (locale === "zh" ? "（不足完整10年）" : " (partial 10Y window)") : ""}` : "";
  return `${method}${field ? ` · ${field}` : ""}${sample}`;
}
function crowdingCoverageNote(data: FactorBoard, locale: "zh" | "en") {
  const coverage = data.crowding.coverage == null ? "—" : `${(data.crowding.coverage * 100).toFixed(1)}%`;
  const count = data.crowding.covered != null && data.crowding.eligible != null ? `${data.crowding.covered}/${data.crowding.eligible} · ` : "";
  const threshold = `${((data.crowding.threshold ?? .8) * 100).toFixed(0)}%`;
  return locale === "zh"
    ? `拥挤度有效覆盖 ${count}${coverage}，低于 ${threshold} 门槛；固定权重未重分配。估值扩张按两期同口径 PE → PB → PS 选择。`
    : `Crowding coverage is ${count}${coverage}, below the ${threshold} gate. Fixed weights are not redistributed; valuation expansion uses same-period PE → PB → PS fallback.`;
}
function marketGapReason(reason: string | undefined, locale: "zh" | "en") {
  const messages: Record<string, [string, string]> = {
    publication_pending: ["等待正式数据发布。", "Waiting for the formal data publication."],
    historical_daily_basic_coverage_partial: ["日度估值历史覆盖不足，缺失期限保持空缺。", "Daily valuation history is incomplete; missing horizons remain blank."],
    historical_coverage_partial: ["历史覆盖不足，暂不能绘制真实三个月估值变化。", "Historical coverage is insufficient to plot a real three-month valuation change."],
    insufficient_aligned_history: ["可对齐的正式历史不足，无法计算该窗口。", "Insufficient aligned formal history for this window."],
    capability_unavailable: ["所需正式数据能力当前不可用。", "The required formal data capability is unavailable."],
    dataset_unavailable: ["所需正式数据集当前不可用。", "The required formal dataset is unavailable."],
    held_industry_mapping_unavailable: ["当前组合没有可审计的申万一级行业映射。", "The current portfolio has no auditable SW Level 1 industry mapping."],
  };
  return (messages[reason || "publication_pending"] || ["正式数据暂不可用。", "Formal data is currently unavailable."])[locale === "zh" ? 0 : 1];
}
