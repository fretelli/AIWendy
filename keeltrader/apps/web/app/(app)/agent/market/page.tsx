"use client";

import dynamic from "next/dynamic";
import { Maximize2, Minus, Plus, RotateCcw, Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useState } from "react";
import useSWR from "swr";

import { DashboardPage, EmptyPanel, Panel } from "@/components/agentos/dashboard-ui";
import { MacroCard, macroLabel, macroSourceNote } from "@/components/agentos/macro-card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { marketsApi, type CorrelationBoard, type CorrelationHistory, type FactorBoard, type FactorHistory, type HeldIndustries, type HistoricalPositionWindow, type MacroCatalog, type MacroMetricSummary, type MacroSeriesDetail, type ValuationBoard, type ValuationItem } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

const RatesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.RatesDrilldown));
const FuturesDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.FuturesDrilldown));
const OptionsDrilldown = dynamic(() => import("@/components/agentos/market-drilldowns").then((module) => module.OptionsDrilldown));
const ValuationScatterChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.ValuationScatterChart), { ssr: false });
const TimeSeriesChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.TimeSeriesChart), { ssr: false });
const ValuationDrilldown = dynamic(() => import("@/components/agentos/valuation-drilldown").then((module) => module.ValuationDrilldown), { ssr: false });

type TopTab = "market" | "macro";
type Detail = "rates" | "futures" | "options";
type ValuationScope = "broad" | "industry" | "held";
const HISTORY_RANGES = ["1M", "3M", "1Y", "3Y", "5Y"] as const;
type HistoryRange = (typeof HISTORY_RANGES)[number];
const MACRO_RANGES = [...HISTORY_RANGES, "10Y", "ALL"] as const;
const HISTORICAL_POSITION_WINDOWS: HistoricalPositionWindow[] = ["5Y", "10Y", "20Y", "ALL"];

export default function MarketPage() {
  const params = useSearchParams();
  const router = useRouter();
  const { locale } = useI18n();
  const tab: TopTab = params.get("tab") === "macro" ? "macro" : "market";
  const detail = (["rates", "futures", "options"].includes(params.get("detail") || "") ? params.get("detail") : null) as Detail | null;
  const showMarket = !detail && tab === "market";
  const showMacro = !detail && tab === "macro";
  const { data: valuation = null } = useSWR<ValuationBoard>(showMarket ? "markets/valuation-board" : null, marketsApi.valuationBoard);
  const { data: correlations = null } = useSWR<CorrelationBoard>(showMarket ? "markets/correlations/60" : null, () => marketsApi.correlations(60));
  const { data: factors = null } = useSWR<FactorBoard>(showMarket ? "markets/factors" : null, marketsApi.factors);
  const { data: macro = null } = useSWR<MacroCatalog>(showMacro ? "markets/macro/catalog-v3" : null, marketsApi.macroCatalog);

  const closeDetail = () => {
    const next = new URLSearchParams(params.toString());
    next.delete("detail");
    next.delete("period");
    router.replace(`/agent/market?${next}`);
  };
  if (detail) return <DashboardPage className="max-w-none"><div className="mb-1"><Button variant="ghost" size="sm" onClick={closeDetail}>{locale === "zh" ? "返回市场与宏观" : "Back to Market & Macro"}</Button></div>{detail === "rates" ? <RatesDrilldown /> : detail === "futures" ? <FuturesDrilldown /> : <OptionsDrilldown />}</DashboardPage>;
  return <DashboardPage className="max-w-none gap-3 px-4 py-[22px]">
    {tab === "market" ? <MarketBoard valuation={valuation} correlations={correlations} factors={factors} locale={locale} /> : <MacroBoard data={macro} locale={locale} onOpenRates={() => router.push("/agent/market?tab=macro&detail=rates&period=1Y")} />}
  </DashboardPage>;
}

function MarketBoard({ valuation, correlations, factors, locale }: { valuation: ValuationBoard | null; correlations: CorrelationBoard | null; factors: FactorBoard | null; locale: "zh" | "en" }) {
  const [selectedValuation, setSelectedValuation] = useState<ValuationItem | null>(null);
  const [valuationScope, setValuationScope] = useState<ValuationScope>("broad");
  const { data: held = null, isLoading: heldLoading } = useSWR<HeldIndustries>(valuationScope === "held" ? "markets/valuation/held-industries" : null, marketsApi.heldIndustries);
  const isV3 = valuation?.metadata.methodology_key === "kt_valuation_percentile_v3";
  const heldCodes = new Set(held?.industry_codes || []);
  const valuationItems = (isV3 ? valuation?.items || [] : []).filter((item) => valuationScope === "broad"
    ? item.universe === "broad"
    : item.universe === "sw_l1" && (valuationScope === "industry" || heldCodes.has(item.code)));
  return <div className="flex min-h-[calc(100dvh-104px)] flex-col gap-3">
    <Panel className="flex flex-wrap items-center gap-3 py-2.5"><span className="text-[10px] text-agent-muted">{locale === "zh" ? "估值比较范围" : "Valuation comparison scope"}</span><ToggleGroup type="single" value={valuationScope} onValueChange={(value) => { if (value) setValuationScope(value as ValuationScope); }} variant="outline" size="sm" aria-label={locale === "zh" ? "估值比较范围" : "Valuation comparison scope"}>{([['broad', '宽基指数', 'Broad Indices'], ['industry', '申万一级', 'SW Level 1'], ['held', '我的持仓行业', 'Held Industries']] as const).map(([value, zh, en]) => <ToggleGroupItem key={value} value={value}>{locale === "zh" ? zh : en}</ToggleGroupItem>)}</ToggleGroup><span className="text-[9px] text-agent-dim">{valuationScope === "broad" ? (locale === "zh" ? "PE-TTM；仅在宽基组内比较" : "PE-TTM; broad-group comparison only") : (locale === "zh" ? "PE（申万源口径）；仅在申万一级组内比较" : "PE (SW source basis); SW L1 comparison only")}</span>{valuationScope === "broad" && valuation?.metadata.universe_coverage?.broad?.missing_codes.length ? <span className="text-[9px] text-agent-amber">{locale === "zh" ? `宽基覆盖 ${valuation.metadata.universe_coverage.broad.available}/${valuation.metadata.universe_coverage.broad.expected}；缺失 ${valuation.metadata.universe_coverage.broad.missing_codes.join("、")}` : `Broad coverage ${valuation.metadata.universe_coverage.broad.available}/${valuation.metadata.universe_coverage.broad.expected}; missing ${valuation.metadata.universe_coverage.broad.missing_codes.join(", ")}`}</span> : null}</Panel>
    <div className="grid min-h-0 flex-1 grid-rows-[minmax(390px,1.05fr)_minmax(330px,.95fr)] gap-3">
    <div className="grid min-h-0 gap-3 xl:grid-cols-[1.6fr_1fr]">
      <ValuationMatrix data={valuation} items={valuationItems} scope={valuationScope} held={held} heldLoading={heldLoading} locale={locale} onSelect={setSelectedValuation} />
      <CorrelationMatrix data={correlations} locale={locale} />
    </div>
    <div className="grid min-h-0 gap-3 xl:grid-cols-[1.35fr_1fr]">
      <ValuationRanking data={valuation} items={valuationItems} scope={valuationScope} locale={locale} onSelect={setSelectedValuation} />
      <FactorCrowding data={factors} locale={locale} />
    </div>
    </div>
    {selectedValuation ? <ValuationDrilldown key={`${selectedValuation.universe}-${selectedValuation.code}`} item={selectedValuation} locale={locale} onClose={() => setSelectedValuation(null)} /> : null}
  </div>;
}

function ValuationMatrix({ data, items: scopedItems, scope, held, heldLoading, locale, onSelect }: { data: ValuationBoard | null; items: ValuationItem[]; scope: ValuationScope; held: HeldIndustries | null; heldLoading: boolean; locale: "zh" | "en"; onSelect: (item: ValuationItem) => void }) {
  const items = scopedItems.filter((item) => item.percentile_change_3m != null && item.pe_percentile != null);
  const peLabel = valuationPeLabel(scope, locale);
  return <Panel className="flex min-h-0 flex-col overflow-hidden">
    <PanelTitle title={locale === "zh" ? "估值分位矩阵" : "Valuation Percentile Matrix"} note={locale === "zh" ? `纵轴 ${peLabel}五年分位 · 横轴同口径 Δ3M · 气泡 = 独立拥挤度` : `${peLabel} 5Y percentile · same-basis Δ3M · bubble = independent crowding`} />
    {scope === "held" && heldLoading ? <EmptyPanel title={locale === "zh" ? "正在映射持仓行业" : "Mapping held industries"} detail={locale === "zh" ? "只读取活跃账户的非零 A 股持仓。" : "Only non-zero A-share positions in active accounts are read."} /> : items.length ? <ValuationScatterChart items={items.map(item => ({ ...item, name: localizedMarketName(item.name, item.code, locale) }))} locale={locale} title={locale === "zh" ? "估值分位矩阵" : "Valuation Percentile Matrix"} peLabel={peLabel} asOf={data?.metadata.as_of} onSelect={onSelect} /> : <DataGap title={scope === "held" ? (locale === "zh" ? "持仓行业映射不可用" : "Held-industry mapping unavailable") : (locale === "zh" ? "估值矩阵不可用" : "Valuation matrix unavailable")} reason={scope === "held" ? "held_industry_mapping_unavailable" : data?.metadata.reason_code || "valuation_v3_pending"} locale={locale} />}
    {scope === "held" && held?.eligible ? <p className="mt-1 text-[9px] text-agent-dim">{locale === "zh" ? `持仓映射覆盖 ${held.covered}/${held.eligible}${held.missing_symbols.length ? `；缺失 ${held.missing_symbols.join("、")}` : ""}` : `Position mapping coverage ${held.covered}/${held.eligible}${held.missing_symbols.length ? `; missing ${held.missing_symbols.join(", ")}` : ""}`}</p> : null}
    <p className="mt-1 text-[9px] text-agent-dim">{locale === "zh" ? "气泡拥挤度是独立模型，不由页面展示的 PE 推导；其估值扩张组件按个股 pe_ttm → pb → ps_ttm 取值。" : "Bubble crowding is an independent model, not derived from displayed PE; its stock-level valuation-expansion input falls back pe_ttm → pb → ps_ttm."}</p>
    {items.some(item => item.crowding_status !== "available") ? <p className="mt-1 text-[9px] text-agent-amber">{locale === "zh" ? "部分或全部拥挤度尚未达到正式方法覆盖门槛，气泡保持中性，不使用成交活跃度代理。" : "Some crowding values do not meet the formal methodology threshold; neutral bubbles are shown without activity proxies."}</p> : null}
  </Panel>;
}

function CorrelationMatrix({ data, locale }: { data: CorrelationBoard | null; locale: "zh" | "en" }) {
  const [pair, setPair] = useState<[number, number] | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [range, setRange] = useState<HistoryRange>("1Y");
  const { data: history = null, isLoading, isValidating, error } = useSWR<CorrelationHistory>(
    pair ? `markets/correlations/60/history/${range}` : null,
    () => marketsApi.correlationHistory(60, periodLimit(range)),
    { keepPreviousData: true },
  );
  const pairKey = pair && data ? `${data.series[Math.min(...pair)].key}|${data.series[Math.max(...pair)].key}` : null;
  const pairDates = pairKey ? (history?.points || []).map(item => item.as_of || "—") : [];
  const pairValues = pairKey ? (history?.points || []).map(item => item.pairs[pairKey] ?? null) : [];
  return <Panel className="min-h-0 overflow-auto">
    <PanelTitle title={locale === "zh" ? "大类相关性 60 日滚动" : "60-Day Rolling Correlations"} note={locale === "zh" ? "小字为环比变化" : "Small figures show window-over-window change"} actions={data?.matrix.length ? <Button type="button" size="icon" variant="ghost" onClick={() => setFullscreen(true)} aria-label={locale === "zh" ? "全屏查看相关矩阵" : "View correlation matrix fullscreen"}><Maximize2 /></Button> : null} />
    {data?.matrix.length ? <CorrelationGrid data={data} locale={locale} fontSize={11} onSelect={(row, column) => { if (column !== row) setPair([row, column]); }} /> : <DataGap title={locale === "zh" ? "相关矩阵不可用" : "Correlation matrix unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
    <FullscreenDataView open={fullscreen} onOpenChange={setFullscreen} title={locale === "zh" ? "大类相关性矩阵" : "Cross-Asset Correlation Matrix"} locale={locale}>{(fontSize) => data ? <CorrelationGrid data={data} locale={locale} fontSize={fontSize} onSelect={(row, column) => { setFullscreen(false); if (column !== row) setPair([row, column]); }} /> : null}</FullscreenDataView>
    <Dialog open={Boolean(pair)} onOpenChange={(open) => { if (!open) setPair(null); }}><DialogContent className="w-[min(1100px,calc(100vw-32px))] max-w-none border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{pair && data ? `${data.series[pair[0]].label} ↔ ${data.series[pair[1]].label}` : "—"}</DialogTitle><DialogDescription>{locale === "zh" ? "正式 60 日滚动相关性历史；范围只控制当前图表。" : "Formal 60-day rolling correlation history; the range controls this chart only."}</DialogDescription></DialogHeader><HistoryRangeToggle value={range} values={HISTORY_RANGES} onChange={(value) => setRange(value as HistoryRange)} locale={locale} busy={isValidating && !isLoading} />{isLoading ? <EmptyPanel title={locale === "zh" ? "正在读取相关性历史" : "Loading correlation history"} detail={locale === "zh" ? "只加载当前下钻范围。" : "Only the current drilldown range is loaded."} /> : error || !pairValues.length ? <DataGap title={locale === "zh" ? "相关性历史不可用" : "Correlation history unavailable"} reason={history?.metadata.reason_code} locale={locale} /> : <TimeSeriesChart dates={pairDates} series={[{ name: locale === "zh" ? "相关系数" : "Correlation", values: pairValues }]} locale={locale} title={`${locale === "zh" ? "相关性历史" : "Correlation History"} · ${range}`} height={430} />}</DialogContent></Dialog>
  </Panel>;
}

function CorrelationGrid({ data, locale, fontSize, onSelect }: { data: CorrelationBoard; locale: "zh" | "en"; fontSize: number; onSelect: (row: number, column: number) => void }) {
  return <div className="grid gap-1" style={{ gridTemplateColumns: `88px repeat(${data.series.length}, minmax(64px,1fr))`, fontSize }}>
    <span />{data.series.map((item) => <span key={item.key} className="pb-2 text-center text-agent-dim">{locale === "zh" ? item.label : factorLabel(item.key, locale)}</span>)}
    {data.series.map((row, i) => <CorrelationRow key={row.key} row={row} index={i} data={data} locale={locale} fontSize={fontSize} onSelect={(column) => onSelect(i, column)} />)}
  </div>;
}

function CorrelationRow({ row, index, data, locale, fontSize, onSelect }: { row: CorrelationBoard["series"][number]; index: number; data: CorrelationBoard; locale: "zh" | "en"; fontSize: number; onSelect: (column: number) => void }) {
  return <><span className="flex items-center text-agent-muted" style={{ fontSize }}>{locale === "zh" ? row.label : factorLabel(row.key, locale)}</span>{data.matrix[index].map((value, column) => {
    const delta = data.delta_matrix[index]?.[column];
    return <button type="button" disabled={value == null || index === column} onClick={() => onSelect(column)} key={column} style={{ fontSize }} className={cn("flex min-h-10 flex-col items-center justify-center rounded-sm font-data disabled:cursor-default", value == null || index === column ? "bg-agent-raised text-agent-dim" : value >= 0 ? "bg-agent-up/15 text-agent-text hover:ring-1 hover:ring-agent-mint" : "bg-agent-mint/10 text-agent-text hover:ring-1 hover:ring-agent-mint")}>{value == null || index === column ? "—" : value.toFixed(2)}{delta != null && index !== column ? <span className={delta >= 0 ? "text-agent-up" : "text-agent-mint"}>{delta >= 0 ? "+" : ""}{delta.toFixed(2)}</span> : null}</button>;
  })}</>;
}

function ValuationRanking({ data, items: scopedItems, scope, locale, onSelect }: { data: ValuationBoard | null; items: ValuationItem[]; scope: ValuationScope; locale: "zh" | "en"; onSelect: (item: ValuationItem) => void }) {
  const items = scopedItems.slice(0, 9);
  const [fullscreen, setFullscreen] = useState(false);
  return <Panel className="min-h-0 overflow-hidden"><PanelTitle title={locale === "zh" ? "估值分位排序 · 带时间维度" : "Valuation Ranking · Time-Aware"} note={locale === "zh" ? `${valuationPeLabel(scope, locale)}五年分位；变化为分位百分点` : `${valuationPeLabel(scope, locale)} 5Y percentile; changes in points`} actions={items.length ? <Button type="button" size="icon" variant="ghost" onClick={() => setFullscreen(true)} aria-label={locale === "zh" ? "全屏查看估值排序" : "View valuation ranking fullscreen"}><Maximize2 /></Button> : null} />
    {items.length ? <ValuationTable items={items} scope={scope} locale={locale} fontSize={11} onSelect={onSelect} /> : <DataGap title={locale === "zh" ? "估值排序不可用" : "Valuation ranking unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
    <FullscreenDataView open={fullscreen} onOpenChange={setFullscreen} title={locale === "zh" ? "估值分位排序" : "Valuation Ranking"} locale={locale}>{(fontSize) => <ValuationTable items={scopedItems} scope={scope} locale={locale} fontSize={fontSize} onSelect={(item) => { setFullscreen(false); onSelect(item); }} />}</FullscreenDataView>
  </Panel>;
}

function ValuationTable({ items, scope, locale, fontSize, onSelect }: { items: ValuationBoard["items"]; scope: ValuationScope; locale: "zh" | "en"; fontSize: number; onSelect: (item: ValuationItem) => void }) {
  const peLabel = valuationPeLabel(scope, locale);
  return <div className="overflow-auto"><table className="w-full min-w-[800px] text-left" style={{ fontSize }}><thead className="font-data text-agent-dim"><tr><th className="pb-2 font-normal">{locale === "zh" ? "名称 / 代码" : "Name / Code"}</th><th className="pb-2 text-right font-normal">{peLabel}</th><th className="pb-2 text-right font-normal">{peLabel} %</th><th className="pb-2 text-right font-normal">Δ1M</th><th className="pb-2 text-right font-normal">Δ3M</th><th className="pb-2 text-right font-normal">{locale === "zh" ? "PB（源口径）%" : "PB (source basis) %"}</th><th className="pb-2 text-right font-normal">{locale === "zh" ? "换手" : "Turnover"}</th></tr></thead><tbody className="divide-y divide-agent-border">{items.map((item) => <tr key={`${item.source}-${item.code}`}><td className="py-2.5"><button type="button" onClick={() => onSelect(item)} className="rounded-sm text-left hover:text-agent-mint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint" aria-label={locale === "zh" ? `查看${localizedMarketName(item.name, item.code, locale)}估值详情` : `View valuation details for ${localizedMarketName(item.name, item.code, locale)}`}><span className="block text-agent-text">{localizedMarketName(item.name, item.code, locale)}</span><span className="font-data text-agent-dim" style={{ fontSize: Math.max(10, fontSize - 2) }}>{item.code}</span></button></td><NumberCell value={item.pe} /><PercentCell value={item.pe_percentile} /><SignedCell value={item.percentile_change_1m} /><SignedCell value={item.percentile_change_3m} /><PercentCell value={item.pb_percentile} /><NumberCell value={item.turnover_rate} suffix="%" /></tr>)}</tbody></table></div>;
}

function FullscreenDataView({ open, onOpenChange, title, locale, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; locale: "zh" | "en"; children: (fontSize: number) => ReactNode }) {
  const [fontSize, setFontSize] = useState(14);
  const resize = (delta: number) => setFontSize((current) => Math.max(10, Math.min(20, current + delta)));
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent tabIndex={0} onKeyDown={(event) => { if (event.key === "+" || event.key === "=") resize(2); if (event.key === "-") resize(-2); if (event.key === "0") setFontSize(14); }} className="grid h-[calc(100dvh-24px)] w-[calc(100vw-24px)] max-w-none grid-rows-[auto_auto_minmax(0,1fr)] border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>{locale === "zh" ? "使用 + / − 放大缩小，按 0 恢复默认。" : "Use + / − to resize; press 0 to reset."}</DialogDescription></DialogHeader><div className="flex items-center gap-2"><Button type="button" size="icon" variant="outline" onClick={() => resize(-2)} aria-label={locale === "zh" ? "缩小字体" : "Decrease font size"}><Minus /></Button><Button type="button" size="icon" variant="outline" onClick={() => resize(2)} aria-label={locale === "zh" ? "放大字体" : "Increase font size"}><Plus /></Button><Button type="button" size="icon" variant="outline" onClick={() => setFontSize(14)} aria-label={locale === "zh" ? "恢复默认字体" : "Reset font size"}><RotateCcw /></Button><span aria-live="polite" className="font-data text-agent-muted">{fontSize}px</span></div><div className="min-h-0 overflow-auto">{children(fontSize)}</div></DialogContent></Dialog>;
}

function FactorCrowding({ data, locale }: { data: FactorBoard | null; locale: "zh" | "en" }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [range, setRange] = useState<HistoryRange>("1Y");
  const { data: history = null, isLoading, isValidating, error } = useSWR<FactorHistory>(
    selected ? `markets/factors/history/${range}` : null,
    () => marketsApi.factorHistory(periodLimit(range)),
    { keepPreviousData: true },
  );
  const selectedDates = (history?.points || []).map(item => item.as_of || "—");
  const selectedValues = (history?.points || []).map(item => item.factors.find(factor => factor.key === selected)?.crowding ?? null);
  return <Panel className="min-h-0 overflow-auto"><PanelTitle title={locale === "zh" ? "因子收益与拥挤度" : "Factor Returns & Crowding"} note={`kt_factor_v1 · ${data?.crowding.methodology_key || "kt_crowding_v2"}`} />
    {data?.factors.length ? <div className="flex flex-col gap-2">{data.factors.map((factor) => { const crowding = factor.crowding; return <button type="button" onClick={() => setSelected(factor.key)} key={factor.key} className="grid grid-cols-[96px_1fr_48px] items-center gap-2 rounded-sm text-left hover:bg-agent-raised"><div><p className="text-[10px] text-agent-text">{factorLabel(factor.key, locale)}</p><p className="mt-1 font-data text-[8px] text-agent-dim">{formatSigned(factor.returns["1M"])} · {formatSigned(factor.returns["3M"])} · {formatSigned(factor.returns["1Y"])}</p></div><div className="h-1.5 overflow-hidden rounded bg-agent-border"><span className={cn("block h-full", crowding != null && crowding >= .75 ? "bg-agent-up" : crowding != null && crowding >= .5 ? "bg-agent-amber" : "bg-agent-mint")} style={{ width: `${Math.max(0, Math.min(100, Number(crowding || 0) * 100))}%` }} /></div><span className="text-right font-data text-[9px] text-agent-muted">{crowding == null ? "—" : `${Math.round(crowding * 100)}%`}</span></button>; })}</div> : <DataGap title={locale === "zh" ? "因子收益不可用" : "Factor returns unavailable"} reason={data?.metadata.reason_code} locale={locale} />}
    {data && data.crowding.status !== "available" ? <p className="mt-3 text-[9px] leading-4 text-agent-amber">{crowdingCoverageNote(data, locale)}</p> : null}
    <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null); }}><DialogContent className="w-[min(1100px,calc(100vw-32px))] max-w-none border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{selected ? factorLabel(selected, locale) : "—"}</DialogTitle><DialogDescription>{locale === "zh" ? "正式拥挤度历史；范围只控制当前图表，缺失快照保持空缺。" : "Formal crowding history; the range controls this chart only and missing snapshots remain blank."}</DialogDescription></DialogHeader><HistoryRangeToggle value={range} values={HISTORY_RANGES} onChange={(value) => setRange(value as HistoryRange)} locale={locale} busy={isValidating && !isLoading} />{isLoading ? <EmptyPanel title={locale === "zh" ? "正在读取因子历史" : "Loading factor history"} detail={locale === "zh" ? "只加载当前下钻范围。" : "Only the current drilldown range is loaded."} /> : error || !selectedValues.some(value => value != null) ? <DataGap title={locale === "zh" ? "因子历史不可用" : "Factor history unavailable"} reason={history?.metadata.reason_code} locale={locale} /> : <TimeSeriesChart dates={selectedDates} series={[{ name: locale === "zh" ? "拥挤度" : "Crowding", values: selectedValues.map(value => value == null ? null : value * 100) }]} locale={locale} title={`${locale === "zh" ? "因子拥挤度历史" : "Factor Crowding History"} · ${range}`} height={430} />}</DialogContent></Dialog>
  </Panel>;
}

type MacroRange = HistoryRange | "10Y" | "ALL";
type MacroMode = "analysis" | "structure";
type MacroAnalysisKind = "primary" | "mom" | "yoy" | "historical_position";

function MacroBoard({ data, locale, onOpenRates }: { data: MacroCatalog | null; locale: "zh" | "en"; onOpenRates: () => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [mode, setMode] = useState<MacroMode>("analysis");
  const [analysisKind, setAnalysisKind] = useState<MacroAnalysisKind>("primary");
  const [historyWindow, setHistoryWindow] = useState<HistoricalPositionWindow>("10Y");
  const [range, setRange] = useState<MacroRange>("1Y");
  const rows = data?.items || [];
  const selectedRow = rows.find(row => row.key === selected);
  const { data: detail = null, isLoading, isValidating, error } = useSWR<MacroSeriesDetail>(
    selected ? `markets/macro/series/${selected}/analysis-v4/${historyWindow}` : null,
    () => marketsApi.macroSeries(selected!, undefined, historyWindow),
  );
  const { data: fieldDetail = null, isLoading: fieldLoading } = useSWR<MacroSeriesDetail>(
    selected && selectedField ? `markets/macro/series/${selected}/field/${selectedField}` : null,
    () => marketsApi.macroSeries(selected!, selectedField!),
  );
  const themes = ["growth", "prices", "credit", "sentiment", "external", "rates", "fiscal"] as const;
  const openAnalysis = (key: string) => { setSelected(key); setSelectedField(null); setMode("analysis"); setAnalysisKind("primary"); };
  const openField = (key: string, field: string) => { setSelected(key); setSelectedField(field); setMode("structure"); };
  const openStructure = () => {
    setMode("structure");
    if (!selectedField) setSelectedField(detail?.featured_fields?.[0]?.key || detail?.field_catalog?.[0]?.key || null);
  };
  return <div className="flex min-h-[calc(100dvh-104px)] flex-col gap-3"><Panel><PanelTitle title={locale === "zh" ? "中国核心宏观全景" : "China Core Macro Dashboard"} note={locale === "zh" ? "结构化 Tushare 优先 · eco_cal 白名单补齐 · 禁止代理与合成" : "Structured Tushare first · gated eco_cal fallback · no proxies"} />
    {rows.length ? <div className="grid gap-3 xl:grid-cols-2">{themes.map(theme => <section key={theme} className="rounded-sm border border-agent-border bg-agent-raised/30 p-3"><div className="mb-2 flex items-center justify-between"><h3 className="text-[11px] font-medium text-agent-text">{macroThemeLabel(theme, locale)}</h3><span className="font-data text-[8px] text-agent-dim">{rows.filter(row => row.theme === theme && row.available).length}/{rows.filter(row => row.theme === theme).length}</span></div><div className="grid gap-2 sm:grid-cols-2">{rows.filter(row => row.theme === theme).map(row => {
      return <MacroCard key={row.key} row={row} locale={locale} onOpenAnalysis={() => row.domain === "rates" ? onOpenRates() : openAnalysis(row.key)} onOpenField={(field) => openField(row.key, field)} onOpenAll={() => row.domain === "rates" ? onOpenRates() : openStructureForRow(row, openField)} />;
    })}</div></section>)}</div> : <DataGap title={locale === "zh" ? "宏观数据不可用" : "Macro data unavailable"} locale={locale} />}
  </Panel><Panel className="grid grid-cols-[70px_1fr] items-start gap-4 py-3"><span className="font-data text-[9px] text-agent-mint">METHOD<br/>{locale === "zh" ? "口径" : "READ"}</span><p className="text-[10px] leading-5 text-agent-muted">{locale === "zh" ? "主序列与关键结构直接同屏展示；点击第一、第二、第三产业等结构值即可查看该官方字段历史。历史位置可切换5年、10年、20年或截至当时全部历史，展示范围只控制图表横轴；社融等季节性流量只与同历月比较，未接入项不使用代理或合成。" : "Headline series and key structures appear together. Historical position can use a 5Y, 10Y, 20Y, or expanding benchmark while the display range controls only the chart axis. Seasonal flows compare the same calendar month; unavailable data is never proxied or synthesized."}</p></Panel>
    <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) { setSelected(null); setSelectedField(null); setMode("analysis"); setAnalysisKind("primary"); setHistoryWindow("10Y"); } }}><DialogContent className="h-[min(920px,calc(100dvh-24px))] w-[min(1180px,calc(100vw-24px))] max-w-none overflow-y-auto border-agent-border bg-agent-surface text-agent-text"><DialogHeader><DialogTitle>{selected ? macroLabel(selected, locale) : "—"}</DialogTitle><DialogDescription>{selectedRow ? `${macroSourceNote(selectedRow, locale)} · ${selectedRow.start || "—"} → ${selectedRow.end || "—"} · ${selectedRow.points || 0} ${locale === "zh" ? "个观测" : "observations"}` : ""}</DialogDescription></DialogHeader><div className="flex flex-wrap items-end justify-between gap-3 border-b border-agent-border pb-3"><ToggleGroup type="single" value={mode} onValueChange={(value) => { if (value === "analysis") setMode("analysis"); if (value === "structure") openStructure(); }} variant="outline" size="sm" aria-label={locale === "zh" ? "宏观下钻模式" : "Macro drilldown mode"}><ToggleGroupItem value="analysis">{locale === "zh" ? "总览分析" : "Overview Analysis"}</ToggleGroupItem><ToggleGroupItem value="structure">{locale === "zh" ? "细分结构" : "Detailed Structure"}</ToggleGroupItem></ToggleGroup><div><p className="mb-1 font-data text-[8px] text-agent-dim">{locale === "zh" ? "展示范围" : "DISPLAY RANGE"}</p><HistoryRangeToggle value={range} values={MACRO_RANGES} onChange={(value) => setRange(value as MacroRange)} locale={locale} compact /></div></div>{isLoading ? <EmptyPanel title={locale === "zh" ? "正在读取正式历史" : "Loading formal history"} detail={locale === "zh" ? "只加载当前指标。" : "Only the selected indicator is loaded."} /> : error || !detail?.series ? <DataGap title={locale === "zh" ? "宏观序列不可用" : "Macro series unavailable"} reason={detail?.reason_code} locale={locale} /> : mode === "analysis" ? <MacroAnalysisView detail={detail} kind={analysisKind} setKind={setAnalysisKind} historyWindow={historyWindow} setHistoryWindow={setHistoryWindow} historyLoading={isValidating} range={range} locale={locale} /> : <MacroFieldDrilldown detail={detail} fieldDetail={fieldDetail} selectedField={selectedField} setSelectedField={setSelectedField} range={range} locale={locale} loading={fieldLoading} />}</DialogContent></Dialog>
  </div>;
}

function openStructureForRow(row: MacroCatalog["items"][number], openField: (key: string, field: string) => void) {
  const field = row.featured_fields?.[0]?.key || row.field_catalog?.[0]?.key;
  if (field) openField(row.key, field);
}

function MacroAnalysisView({ detail, kind, setKind, historyWindow, setHistoryWindow, historyLoading, range, locale }: { detail: MacroSeriesDetail; kind: MacroAnalysisKind; setKind: (kind: MacroAnalysisKind) => void; historyWindow: HistoricalPositionWindow; setHistoryWindow: (window: HistoricalPositionWindow) => void; historyLoading: boolean; range: MacroRange; locale: "zh" | "en" }) {
  const primaryLabel: [string, string] = detail.primary_alias === "yoy" ? ["同比走势", "YoY trend"] : ["主值走势", "Primary trend"];
  const choices: Array<[MacroAnalysisKind, string, string]> = [
    ["primary", ...primaryLabel],
    ["mom", detail.key === "gdp" ? "较上季变化" : "较上月变化", detail.key === "gdp" ? "Change vs prior quarter" : "Change vs prior month"],
    ["yoy", "较上年变化", "Change vs prior year"],
    ["historical_position", "历史位置", "Historical position"],
  ];
  const visibleChoices = choices.filter(([value]) => value === "primary" || value === "historical_position" || detail.summary?.[value]?.method !== "not_applicable");
  return <div className="mt-3"><ToggleGroup type="single" value={kind} onValueChange={(value) => { if (value) setKind(value as MacroAnalysisKind); }} variant="outline" size="sm" aria-label={locale === "zh" ? "分析指标" : "Analysis metric"} className="mb-3 flex-wrap justify-start">{visibleChoices.map(([value, zh, en]) => <ToggleGroupItem key={value} value={value}>{locale === "zh" ? zh : en}</ToggleGroupItem>)}</ToggleGroup>{kind === "historical_position" ? <div className="mb-3 flex flex-wrap items-end justify-between gap-3 rounded-sm border border-agent-border bg-agent-raised/35 p-3"><div><p className="font-data text-[8px] text-agent-dim">{locale === "zh" ? "历史比较基准" : "HISTORICAL BENCHMARK"}</p><p className="mt-1 max-w-[620px] text-[9px] leading-4 text-agent-muted">{locale === "zh" ? "每个时点只与其此前所选长度的历史比较；上方展示范围只控制图表横轴。" : "Each point only uses the selected amount of prior history; the display range above controls only the chart axis."}</p></div><HistoryRangeToggle value={historyWindow} values={HISTORICAL_POSITION_WINDOWS} onChange={(value) => setHistoryWindow(value as HistoricalPositionWindow)} locale={locale} busy={historyLoading} compact /></div> : null}<MacroChartPanel kind={kind} detail={detail} range={range} locale={locale} />{detail.latest_release ? <Panel tone="raised" className="mt-3"><PanelTitle title={locale === "zh" ? "最新发布与预期差" : "Latest Release & Surprise"} note={detail.latest_release.quality_state || undefined} /><div className="grid gap-3 text-[10px] sm:grid-cols-4"><MacroReleaseValue label={locale === "zh" ? "实际" : "Actual"} value={detail.latest_release.actual} /><MacroReleaseValue label={locale === "zh" ? "预期" : "Forecast"} value={detail.latest_release.forecast} /><MacroReleaseValue label={locale === "zh" ? "预期差" : "Surprise"} value={detail.latest_release.surprise} /><div><p className="text-agent-dim">{locale === "zh" ? "发布日期" : "Released"}</p><p className="mt-1 font-data text-agent-muted">{detail.latest_release.release_date || "—"}</p></div></div></Panel> : null}</div>;
}

function MacroFieldDrilldown({ detail, fieldDetail, selectedField, setSelectedField, range, locale, loading }: { detail: MacroSeriesDetail; fieldDetail: MacroSeriesDetail | null; selectedField: string | null; setSelectedField: (field: string | null) => void; range: MacroRange; locale: "zh" | "en"; loading: boolean }) {
  const fields = detail.field_catalog || [];
  const [query, setQuery] = useState("");
  if (!fields.length) return null;
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visibleFields = normalizedQuery ? fields.filter(field => `${field.label} ${field.key} ${field.group}`.toLocaleLowerCase().includes(normalizedQuery)) : fields;
  const groups = Array.from(new Set(visibleFields.map(field => field.group)));
  const rows = sliceMacroSeries(fieldDetail?.rows || [], detail.frequency, range);
  return <div className="mt-3 grid gap-3 lg:grid-cols-[300px_1fr]"><Panel tone="raised" className="max-h-[520px] overflow-hidden"><PanelTitle title={locale === "zh" ? `细分结构 · ${fields.length} 项` : `Detailed Structure · ${fields.length}`} note={locale === "zh" ? "官方字段白名单" : "Official allowlist"} />{fields.length > 12 ? <label className="mb-3 flex items-center gap-2 rounded-sm border border-agent-border bg-agent-canvas/40 px-2"><Search className="h-3.5 w-3.5 text-agent-dim" /><span className="sr-only">{locale === "zh" ? "搜索细分指标" : "Search subseries"}</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === "zh" ? "搜索名称或字段" : "Search name or field"} className="h-8 min-w-0 flex-1 bg-transparent text-[10px] text-agent-text outline-none placeholder:text-agent-dim" /></label> : null}<div className="max-h-[420px] overflow-y-auto pr-1">{groups.length ? groups.map(group => <div key={group} className="mb-3"><p className="mb-1 font-data text-[8px] text-agent-dim">{group}</p><div className="flex flex-wrap gap-1">{visibleFields.filter(field => field.group === group).map(field => <button type="button" key={field.key} onClick={() => setSelectedField(field.key)} className={cn("rounded-sm border px-2 py-1 text-[9px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint", selectedField === field.key ? "border-agent-mint bg-agent-mint text-agent-canvas" : "border-agent-border text-agent-muted hover:bg-agent-raised")}>{field.label}</button>)}</div></div>) : <p className="py-6 text-center text-[9px] text-agent-dim">{locale === "zh" ? "没有匹配字段" : "No matching fields"}</p>}</div></Panel><Panel tone="raised" className="min-h-[420px]">{loading ? <EmptyPanel title={locale === "zh" ? "正在读取细分序列" : "Loading subseries"} detail="" /> : selectedField && fieldDetail ? <><PanelTitle title={fieldDetail.field_meta?.label || selectedField} note={`${fieldDetail.field_meta?.unit || ""} · ${locale === "zh" ? "官方原始字段" : "official raw field"}`} /><p className="mb-2 text-[9px] leading-4 text-agent-amber">{selectedField === "gdp" || selectedField === "pi" || selectedField === "si" || selectedField === "ti" ? (locale === "zh" ? "年内累计值只用于观察规模和结构，不能跨季度直接计算普通历史分位。" : "Year-to-date cumulative values are for scale and structure only, not ordinary cross-quarter percentiles.") : locale === "zh" ? `字段 ${selectedField} · 不做合成` : `Field ${selectedField} · no synthesis`}</p>{rows.some(row => row.value != null) ? <TimeSeriesChart dates={rows.map(row => row.period)} series={[{ name: fieldDetail.field_meta?.label || selectedField, values: rows.map(row => row.value) }]} locale={locale} title={`${fieldDetail.field_meta?.label || selectedField} · ${range}`} height={330} /> : <DataGap title={locale === "zh" ? "细分历史不可用" : "Subseries unavailable"} locale={locale} />}</> : <EmptyPanel title={locale === "zh" ? "选择一个细分指标" : "Select a subseries"} detail={locale === "zh" ? "从左侧选择一个官方字段，右侧只展示这一条历史。" : "Choose one official field; the chart shows only that history."} />}</Panel></div>;
}

function MacroReleaseValue({ label, value }: { label: string; value?: number | null }) { return <div><p className="text-agent-dim">{label}</p><p className="mt-1 font-data text-[13px] text-agent-text">{value == null ? "—" : value.toLocaleString()}</p></div>; }

function MacroChartPanel({ kind, detail, range, locale }: { kind: MacroAnalysisKind; detail: MacroSeriesDetail; range: MacroRange; locale: "zh" | "en" }) {
  const series = detail.series?.[kind];
  const rows = sliceMacroSeries(series?.rows || [], detail.frequency, range);
  const historicalWindow = series?.meta.window === "ALL" ? (locale === "zh" ? "截至当时全部历史" : "expanding history") : `${series?.meta.window || "10Y"} ${locale === "zh" ? "滚动基准" : "rolling benchmark"}`;
  const labels: Record<typeof kind, [string, string]> = { primary: [detail.primary_alias === "yoy" ? "官方同比走势" : "官方主值走势", "Official primary trend"], mom: [detail.key === "gdp" ? "较上季变化" : "较上月变化", detail.key === "gdp" ? "Change vs prior quarter" : "Change vs prior month"], yoy: ["较上年变化", "Change vs prior year"], historical_position: [`历史位置（${historicalWindow}）`, `Historical position (${historicalWindow})`] };
  const title = labels[kind][locale === "zh" ? 0 : 1];
  if (series?.meta.method === "not_applicable") return <Panel tone="raised" className="min-h-[310px]"><PanelTitle title={title} note={locale === "zh" ? "不适用" : "Not applicable"} /><EmptyPanel title={locale === "zh" ? "该指标没有可靠官方环比口径" : "No reliable official MoM measure"} detail={locale === "zh" ? "保持不适用，不使用累计值反推或代理数据。" : "No cumulative-value inference or proxy is used."} /></Panel>;
  return <Panel tone="raised" className="min-h-[310px]"><PanelTitle title={title} note={`${series?.meta.unit || ""} · ${macroMethodLabel(series?.meta.method, locale)}`} />{rows.some(row => row.value != null) ? <TimeSeriesChart dates={rows.map(row => row.period)} series={[{ name: title, values: rows.map(row => row.value) }]} locale={locale} title={`${title} · ${range === "ALL" ? (locale === "zh" ? "全部" : "All") : range}`} height={250} /> : <EmptyPanel title={locale === "zh" ? "可比较历史不足" : "Insufficient comparable history"} detail={macroMetricExplanation(series?.meta as MacroMetricSummary | undefined, locale)} />}</Panel>;
}

function HistoryRangeToggle({ value, values, onChange, locale, busy = false, compact = false }: { value: string; values: readonly string[]; onChange: (value: string) => void; locale: "zh" | "en"; busy?: boolean; compact?: boolean }) {
  return <div className={cn("flex flex-wrap items-center gap-2", compact ? "" : "border-b border-agent-border pb-3")}>
    <ToggleGroup type="single" value={value} onValueChange={(next) => { if (next) onChange(next); }} variant="outline" size="sm" aria-label={locale === "zh" ? "当前图表范围" : "Current chart range"} className="flex-wrap justify-start">
      {values.map((item) => <ToggleGroupItem key={item} value={item} aria-label={item} className="font-data text-[10px] data-[state=on]:bg-agent-mint data-[state=on]:text-agent-canvas">{item === "ALL" ? (locale === "zh" ? "全部" : "All") : item}</ToggleGroupItem>)}
    </ToggleGroup>
    {busy ? <span aria-live="polite" className="text-[9px] text-agent-dim">{locale === "zh" ? "正在切换…" : "Switching…"}</span> : null}
  </div>;
}

function PanelTitle({ title, note, actions }: { title: string; note?: string; actions?: ReactNode }) { return <div className="mb-3 flex items-center gap-3"><h2 className="text-sm font-medium text-agent-text">{title}</h2>{note ? <span className="font-data text-[8px] text-agent-dim">{note}</span> : null}{actions ? <div className="ml-auto">{actions}</div> : null}</div>; }
function DataGap({ title, reason, locale }: { title: string; reason?: string; locale: "zh" | "en" }) { return <EmptyPanel title={title} detail={marketGapReason(reason, locale)} />; }
function NumberCell({ value, suffix = "" }: { value?: number; suffix?: string }) { return <td className="py-2.5 text-right font-data text-agent-muted">{value == null ? "—" : `${Number(value).toFixed(1)}${suffix}`}</td>; }
function PercentCell({ value }: { value?: number }) { return <td className="py-2.5 text-right font-data text-agent-muted">{value == null ? "—" : `${Math.round(Number(value) * 100)}%`}</td>; }
function SignedCell({ value }: { value?: number }) { return <td className={cn("py-2.5 text-right font-data", Number(value || 0) > 0 ? "text-agent-up" : Number(value || 0) < 0 ? "text-agent-mint" : "text-agent-dim")}>{value == null ? "—" : `${Number(value) > 0 ? "+" : ""}${(Number(value) * 100).toFixed(1)}`}</td>; }
function formatSigned(value?: number | null) { return value == null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`; }
function factorLabel(key: string, locale: "zh" | "en") { const labels: Record<string, [string, string]> = { value: ["价值", "Value"], momentum: ["动量", "Momentum"], low_vol: ["低波", "Low Vol"], quality: ["质量", "Quality"], growth: ["成长", "Growth"], size: ["规模", "Size"], dividend: ["红利", "Dividend"], cn_equity: ["A股", "CN Equity"], hk_equity: ["港股", "HK Equity"], us_equity: ["美股", "US Equity"], bond: ["债券", "Bonds"], commodity: ["商品", "Commodities"], fx: ["外汇", "FX"] }; return labels[key]?.[locale === "zh" ? 0 : 1] || key; }
function macroThemeLabel(theme: string, locale: "zh" | "en") { const labels: Record<string, [string, string]> = { growth: ["增长与需求", "Growth & Demand"], prices: ["物价", "Prices"], credit: ["信用与货币", "Credit & Money"], sentiment: ["景气与就业", "Business Climate & Jobs"], external: ["外贸与外储", "Trade & Reserves"], rates: ["利率与收益率", "Rates & Yields"], fiscal: ["财政", "Fiscal"] }; return labels[theme]?.[locale === "zh" ? 0 : 1] || theme; }
function localizedMarketName(name: string, code: string, locale: "zh" | "en") { return locale === "en" && /[\u3400-\u9fff]/.test(name) ? code : name; }
function valuationPeLabel(scope: ValuationScope, locale: "zh" | "en") { return scope === "broad" ? "PE-TTM" : locale === "zh" ? "PE（申万源口径）" : "PE (SW source basis)"; }
function periodLimit(period: HistoryRange) {
  return ({ "1M": 22, "3M": 66, "1Y": 252, "3Y": 756, "5Y": 1260 } as const)[period];
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
  const sample = metric.sample_count ? ` · ${metric.sample_count} ${locale === "zh" ? "个样本" : "samples"}${metric.window_complete === false ? (locale === "zh" ? `（不足完整${metric.window || "历史"}）` : ` (partial ${metric.window || "history"} window)`) : ""}` : "";
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
