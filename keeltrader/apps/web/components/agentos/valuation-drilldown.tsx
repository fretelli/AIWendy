"use client";

import { useState } from "react";
import useSWR from "swr";

import { TimeSeriesChart } from "@/components/agentos/market-charts";
import { EmptyPanel } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { marketsApi, type ValuationHistory, type ValuationItem } from "@/lib/api/agent-platform";

type Range = "1M" | "3M" | "1Y" | "3Y" | "5Y";
const RANGES: Range[] = ["1M", "3M", "1Y", "3Y", "5Y"];
const RANGE_LIMITS: Record<Range, number> = { "1M": 22, "3M": 66, "1Y": 252, "3Y": 756, "5Y": 1260 };

export function ValuationDrilldown({ item, locale, onClose }: {
  item: ValuationItem;
  locale: "zh" | "en";
  onClose: () => void;
}) {
  const [range, setRange] = useState<Range>("1Y");
  const universe = item.universe === "broad" ? "broad" : "sw_l1";
  const limit = RANGE_LIMITS[range];
  const { data: history = null, isLoading, isValidating, error } = useSWR<ValuationHistory>(
    `markets/valuation/history/${universe}/${item.code}/${limit}`,
    () => marketsApi.valuationHistory(item.code, universe, limit),
    { keepPreviousData: true },
  );
  const points = history?.points || [];
  const dates = points.map(point => point.as_of);
  const availablePoints = history?.available_points_total;
  const visiblePoints = availablePoints == null ? points.length : Math.min(availablePoints, limit);
  const partial = history?.metadata.status === "partial" || (availablePoints != null && availablePoints < limit);
  const peLabel = item.universe === "broad" ? "PE-TTM" : locale === "zh" ? "PE（申万源口径）" : "PE (SW source basis)";
  const pePercentileLabel = locale === "zh" ? `${peLabel} 五年分位` : `${peLabel} 5Y percentile`;
  return <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
    <DialogContent className="h-[min(920px,calc(100dvh-24px))] w-[min(1280px,calc(100vw-24px))] max-w-none overflow-y-auto border-agent-border bg-agent-surface text-agent-text">
      <DialogHeader>
        <DialogTitle>{item.name} <span className="font-data text-sm text-agent-dim">{item.code}</span></DialogTitle>
        <DialogDescription>{locale === "zh" ? "点时估值、历史分位、拥挤度与可审计成分" : "Point-in-time valuation, percentiles, crowding and auditable constituents"}</DialogDescription>
      </DialogHeader>
      <div className="flex flex-wrap items-stretch gap-1 border-b border-agent-border pb-3">{RANGES.map(value => {
        const target = RANGE_LIMITS[value];
        const completed = availablePoints != null && availablePoints >= target;
        const progress = availablePoints == null ? `…/${target}` : `${Math.min(availablePoints, target)}/${target}`;
        const status = completed ? progress : `${progress} · ${locale === "zh" ? "补录中" : "Backfilling"}`;
        return <Button key={value} type="button" size="sm" variant={range === value ? "secondary" : "outline"} onClick={() => setRange(value)} aria-label={`${value} ${status}`} className="h-auto min-w-[72px] flex-col gap-1 px-2 py-1.5"><span>{value}</span><span className={completed ? "font-data text-[8px] text-agent-muted" : "font-data text-[8px] text-agent-amber"}>{status}</span></Button>;
      })}{isValidating && !isLoading ? <span aria-live="polite" className="self-center pl-2 text-[9px] text-agent-dim">{locale === "zh" ? "正在切换…" : "Switching…"}</span> : null}</div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label={peLabel} value={number(item.pe)} />
        <Metric label={locale === "zh" ? "PB（源口径）" : "PB (source basis)"} value={number(item.pb)} />
        <Metric label={pePercentileLabel} value={percent(item.pe_percentile)} />
        <Metric label={locale === "zh" ? "PB（源口径）五年分位" : "PB (source basis) 5Y percentile"} value={percent(item.pb_percentile)} />
        <Metric label="Δ1M" value={signedPercentile(item.percentile_change_1m)} />
        <Metric label="Δ3M" value={signedPercentile(item.percentile_change_3m)} />
        <Metric label={locale === "zh" ? "拥挤度" : "Crowding"} value={percent(item.crowding_percentile)} />
        <Metric label={locale === "zh" ? "拥挤覆盖" : "Crowding coverage"} value={percent(item.crowding_coverage)} />
      </div>
      {partial && points.length ? <p className="rounded-sm border border-agent-amber/30 bg-agent-amber/5 px-3 py-2 text-[10px] text-agent-amber">{locale === "zh" ? `${range} 历史补录中；当前 ${visiblePoints}/${limit} 个交易日，真实可用范围 ${history?.available_start || dates[0]} → ${history?.available_end || dates[dates.length - 1]}，不插值、不合成。` : `${range} history backfill in progress: ${visiblePoints}/${limit} trading days. Real available range: ${history?.available_start || dates[0]} → ${history?.available_end || dates[dates.length - 1]}; no interpolation or synthesis.`}</p> : null}
      {isLoading ? <EmptyPanel title={locale === "zh" ? "正在读取估值历史" : "Loading valuation history"} detail={locale === "zh" ? "只读取已发布的版本化快照。" : "Only published versioned snapshots are read."} /> : error || !points.length ? <EmptyPanel title={locale === "zh" ? "估值历史暂不可用" : "Valuation history unavailable"} detail={locale === "zh" ? "历史快照正在补录；当前值和方法信息仍可查看。" : "Historical snapshots are being backfilled; current values and methodology remain available."} /> : <div className="grid gap-3 lg:grid-cols-2">
        <TimeSeriesChart dates={dates} series={[{ name: peLabel, values: points.map(point => point.pe ?? null) }, { name: locale === "zh" ? "PB（源口径）" : "PB (source basis)", values: points.map(point => point.pb ?? null) }]} locale={locale} title={`${peLabel} / PB · ${range}`} height={300} />
        <TimeSeriesChart dates={dates} series={[{ name: pePercentileLabel, values: points.map(point => point.pe_percentile == null ? null : point.pe_percentile * 100) }, { name: locale === "zh" ? "PB（源口径）五年分位" : "PB (source basis) 5Y percentile", values: points.map(point => point.pb_percentile == null ? null : point.pb_percentile * 100) }, { name: locale === "zh" ? "独立拥挤度" : "Independent crowding", values: points.map(point => point.crowding_percentile == null ? null : point.crowding_percentile * 100) }]} locale={locale} title={locale === "zh" ? `历史分位 / 独立拥挤度 · ${range}` : `Percentiles / Independent Crowding · ${range}`} height={300} />
      </div>}
      <div className="grid gap-3 lg:grid-cols-[1.2fr_1fr]">
        <section className="rounded-sm border border-agent-border bg-agent-raised p-3"><h3 className="mb-2 text-xs text-agent-text">{locale === "zh" ? "前十大成分" : "Top 10 Constituents"}</h3>{item.top_constituents?.length ? <div className="divide-y divide-agent-border">{item.top_constituents.map(constituent => <div key={constituent.code} className="grid grid-cols-[1fr_auto] gap-3 py-2 text-[10px]"><span><span className="text-agent-text">{constituent.name}</span><span className="ml-2 font-data text-agent-dim">{constituent.code}</span></span><span className="font-data text-agent-muted">{(constituent.weight * 100).toFixed(2)}%</span></div>)}</div> : <p className="text-[10px] text-agent-dim">{item.constituent_reason === "official_index_weight_not_published" ? (locale === "zh" ? "该宽基的官方成分权重尚未发布；不使用推导权重替代。" : "Official constituent weights are not published for this index; derived weights are not substituted.") : (locale === "zh" ? "当前自由流通市值组件不足，成分保持不可用。" : "Current free-float components are insufficient; constituents remain unavailable.")}</p>}</section>
        <section className="rounded-sm border border-agent-border bg-agent-raised p-3"><h3 className="mb-2 text-xs text-agent-text">{locale === "zh" ? "来源与方法" : "Source & Methodology"}</h3><dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-2 text-[10px]"><dt className="text-agent-dim">As of</dt><dd className="font-data text-agent-muted">{item.trade_date}</dd><dt className="text-agent-dim">Method</dt><dd className="font-data text-agent-muted">kt_valuation_percentile_v3</dd><dt className="text-agent-dim">PE basis</dt><dd className="font-data text-agent-muted">{item.pe_basis || "—"}</dd><dt className="text-agent-dim">PE source field</dt><dd className="font-data text-agent-muted">{item.pe_source_field || "—"}</dd><dt className="text-agent-dim">PB basis</dt><dd className="font-data text-agent-muted">{item.pb_basis || "—"}</dd><dt className="text-agent-dim">PB source field</dt><dd className="font-data text-agent-muted">{item.pb_source_field || "—"}</dd><dt className="text-agent-dim">Comparison group</dt><dd className="font-data text-agent-muted">{item.comparison_group || "—"}</dd><dt className="text-agent-dim">Weight</dt><dd className="font-data text-agent-muted">{item.constituent_weight_basis || "—"}</dd><dt className="text-agent-dim">Crowding</dt><dd className="font-data text-agent-muted">{item.crowding_methodology_key || "kt_market_crowding_v3"}</dd></dl><p className="mt-3 text-[9px] leading-4 text-agent-dim">{locale === "zh" ? "估值分位只与同一代码截至当日的五年真实历史比较；宽基 PE 展示 index_dailybasic.pe_ttm，申万一级 PE 展示 sw_daily.pe，二者不横向混排。PB 为数据源口径。拥挤度是独立模型，不由页面展示 PE 推导：换手 30%、20 日动量 25%、约 60 个交易日估值扩张 20%、5 日官方资金流/自由流通市值 25%；其中个股估值扩张按 pe_ttm → pb → ps_ttm 回退，组件覆盖低于 80% 时不可用。" : "Percentiles compare only with the same code's real five-year history through the as-of date. Broad PE displays index_dailybasic.pe_ttm; SW L1 PE displays sw_daily.pe, and the groups are never mixed. PB is source-basis. Crowding is independent of displayed PE: turnover 30%, 20-day momentum 25%, roughly 60-trading-day valuation expansion 20%, and 5-day official flow/free-float market cap 25%. Stock-level valuation expansion falls back pe_ttm → pb → ps_ttm and is unavailable below 80% component coverage."}</p></section>
      </div>
    </DialogContent>
  </Dialog>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-sm border border-agent-border bg-agent-raised px-3 py-2"><p className="text-[9px] text-agent-dim">{label}</p><p className="mt-1 font-data text-base text-agent-text">{value}</p></div>;
}

function number(value?: number | null) { return value == null ? "—" : Number(value).toFixed(2); }
function percent(value?: number | null) { return value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`; }
function signedPercentile(value?: number | null) { return value == null ? "—" : `${value > 0 ? "+" : ""}${(Number(value) * 100).toFixed(1)} pct`; }
