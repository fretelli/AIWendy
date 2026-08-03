"use client";

import { useMemo } from "react";

import { InteractiveChart, type EChartsCoreOption } from "@/components/agentos/interactive-chart";
import type { ValuationBoard } from "@/lib/api/agent-platform";

const COLORS = { grid: "#1A222A", text: "#8A97A3", dim: "#5C6873", mint: "#5FE3B5", amber: "#E8A34D", up: "#FF5A52", blue: "#67A8FF" };

export function ValuationScatterChart({ items, locale, title, asOf }: {
  items: ValuationBoard["items"];
  locale: "zh" | "en";
  title: string;
  asOf?: string;
}) {
  const option = useMemo<EChartsCoreOption>(() => {
    const data = items.map((item, index) => {
      const crowding = item.crowding_status === "available" ? item.crowding_percentile : null;
      return {
        name: item.name || item.code,
        value: [Number(item.percentile_change_3m) * 100, Number(item.pe_percentile) * 100, crowding == null ? null : Number(crowding) * 100],
        code: item.code,
        universe: item.universe,
        crowdingStatus: item.crowding_status,
        crowdingReason: item.crowding_reason,
        crowdingCoverage: item.crowding_coverage,
        itemStyle: {
          color: crowding == null ? "rgba(138,151,163,.18)" : crowding >= .7 ? "rgba(255,90,82,.28)" : crowding >= .4 ? "rgba(232,163,77,.24)" : "rgba(95,227,181,.24)",
          borderColor: crowding == null ? COLORS.text : crowding >= .7 ? COLORS.up : crowding >= .4 ? COLORS.amber : COLORS.mint,
        },
        label: { show: item.universe === "broad", position: index % 2 ? "left" : "right" },
      };
    });
    return {
      animationDuration: 180,
      aria: { enabled: true, decal: { show: false } },
      grid: { left: 54, right: 34, top: 24, bottom: 46, containLabel: false },
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(14,19,24,.96)", borderColor: "#26313A", textStyle: { color: "#E8EDF2", fontFamily: "IBM Plex Mono" },
        formatter: (params: { data?: { name?: string; code?: string; value?: Array<number | null>; crowdingStatus?: string; crowdingReason?: string; crowdingCoverage?: number } }) => {
          const item = params.data;
          const values = item?.value || [];
          const crowding = values[2] == null ? (locale === "zh" ? "不可用" : "Unavailable") : `${Number(values[2]).toFixed(0)}%`;
          const coverage = item?.crowdingCoverage == null ? "—" : `${(item.crowdingCoverage * 100).toFixed(0)}%`;
          const reasonText = item?.crowdingReason === "component_coverage_below_threshold"
            ? (locale === "zh" ? "正式组件覆盖率低于 80%" : "Formal component coverage is below 80%")
            : item?.crowdingReason;
          const reason = reasonText ? `<br/><span style="color:${COLORS.amber}">${reasonText}</span>` : "";
          return `${item?.name || "—"}<br/><span style="color:${COLORS.dim}">${item?.code || ""}</span><br/>PE ${locale === "zh" ? "分位" : "percentile"} ${Number(values[1] || 0).toFixed(0)}%<br/>Δ3M ${Number(values[0] || 0) >= 0 ? "+" : ""}${Number(values[0] || 0).toFixed(1)} pct<br/>${locale === "zh" ? "拥挤度" : "Crowding"} ${crowding}<br/>${locale === "zh" ? "覆盖率" : "Coverage"} ${coverage}${reason}`;
        },
      },
      xAxis: {
        type: "value", name: locale === "zh" ? "三个月估值分位变化（pct）" : "3M percentile change (pct)", nameLocation: "middle", nameGap: 28,
        axisLabel: { color: COLORS.dim, fontSize: 9 }, nameTextStyle: { color: COLORS.dim, fontSize: 9 },
        axisLine: { lineStyle: { color: COLORS.grid } }, splitLine: { lineStyle: { color: COLORS.grid, type: "dashed" } },
      },
      yAxis: {
        type: "value", min: 0, max: 100, name: locale === "zh" ? "PE 分位" : "PE percentile",
        axisLabel: { color: COLORS.dim, fontSize: 9, formatter: "{value}%" }, nameTextStyle: { color: COLORS.dim, fontSize: 9 },
        axisLine: { lineStyle: { color: COLORS.grid } }, splitLine: { lineStyle: { color: COLORS.grid, type: "dashed" } },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "none", start: 0, end: 100 },
        { type: "inside", yAxisIndex: 0, filterMode: "none", start: 0, end: 100 },
      ],
      series: [{
        type: "scatter", data,
        symbolSize: (value: Array<number | null>) => value[2] == null ? 13 : 13 + Number(value[2]) * .17,
        label: { show: true, color: COLORS.text, fontSize: 10, formatter: (params: { data?: { name?: string } }) => params.data?.name || "" },
        labelLayout: { hideOverlap: true, moveOverlap: "shiftY" },
        emphasis: { focus: "self", label: { show: true, color: "#E8EDF2", fontWeight: "bold" }, scale: 1.15 },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: COLORS.grid }, data: [{ xAxis: 0 }, { yAxis: 50 }] },
      }],
    };
  }, [items, locale]);
  return <InteractiveChart option={option} title={title} description={`${asOf || "—"} · ${items.length} points`} locale={locale} height={310} zoomMode="xy" />;
}

export function TimeSeriesChart({ dates, series, locale, title, height = 300 }: {
  dates: string[];
  series: Array<{ name: string; values: Array<number | null>; color?: string }>;
  locale: "zh" | "en";
  title: string;
  height?: number;
}) {
  const option = useMemo<EChartsCoreOption>(() => ({
    animationDuration: 160,
    aria: { enabled: true, decal: { show: false } },
    color: series.map((item, index) => item.color || [COLORS.mint, COLORS.blue, COLORS.amber, COLORS.up][index % 4]),
    grid: { left: 62, right: 24, top: 26, bottom: 52 },
    legend: { show: series.length > 1, top: 0, textStyle: { color: COLORS.text, fontSize: 9 } },
    tooltip: { trigger: "axis", backgroundColor: "rgba(14,19,24,.96)", borderColor: "#26313A", textStyle: { color: "#E8EDF2", fontFamily: "IBM Plex Mono" } },
    xAxis: { type: "category", data: dates, boundaryGap: false, axisLabel: { color: COLORS.dim, fontSize: 9 }, axisLine: { lineStyle: { color: COLORS.grid } } },
    yAxis: { type: "value", scale: true, axisLabel: { color: COLORS.dim, fontSize: 9 }, splitLine: { lineStyle: { color: COLORS.grid, type: "dashed" } } },
    dataZoom: [{ type: "inside", xAxisIndex: 0, filterMode: "filter", start: 0, end: 100 }, { type: "slider", xAxisIndex: 0, height: 14, bottom: 8, borderColor: COLORS.grid, fillerColor: "rgba(95,227,181,.12)", handleStyle: { color: COLORS.mint }, textStyle: { color: COLORS.dim, fontSize: 8 } }],
    series: series.map(item => ({ name: item.name, type: "line", data: item.values, showSymbol: false, connectNulls: false, lineStyle: { width: 1.8 }, sampling: "lttb" })),
  }), [dates, series]);
  return <InteractiveChart option={option} title={title} locale={locale} height={height} zoomMode="x" />;
}
