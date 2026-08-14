"use client";

import {
  BarChart,
  CandlestickChart,
  HeatmapChart,
  LineChart,
  ScatterChart,
} from "echarts/charts";
import {
  AriaComponent,
  DataZoomComponent,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption, EChartsType } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

echarts.use([
  AriaComponent,
  BarChart,
  CandlestickChart,
  CanvasRenderer,
  DataZoomComponent,
  DatasetComponent,
  GridComponent,
  HeatmapChart,
  LegendComponent,
  LineChart,
  MarkLineComponent,
  ScatterChart,
  TooltipComponent,
  VisualMapComponent,
]);

export type ChartZoomMode = "none" | "x" | "xy";
export type ChartItemClick = { data?: unknown; seriesType?: string; seriesName?: string; dataIndex?: number };

export function InteractiveChart({
  option,
  title,
  description,
  locale,
  height = 300,
  zoomMode = "x",
  className,
  onItemClick,
}: {
  option: EChartsCoreOption;
  title: string;
  description?: string;
  locale: "zh" | "en";
  height?: number;
  zoomMode?: ChartZoomMode;
  className?: string;
  onItemClick?: (params: ChartItemClick) => void;
}) {
  const embeddedRef = useRef<EChartsType | null>(null);
  const fullscreenRef = useRef<EChartsType | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const fullscreenStateRef = useRef(fullscreen);
  const itemClickRef = useRef(onItemClick);
  useEffect(() => { fullscreenStateRef.current = fullscreen; }, [fullscreen]);
  useEffect(() => { itemClickRef.current = onItemClick; }, [onItemClick]);
  const chartClickRef = useRef((params: ChartItemClick) => {
    if (fullscreenStateRef.current) setFullscreen(false);
    itemClickRef.current?.(params);
  });
  const [status, setStatus] = useState("");
  const labels = locale === "zh"
    ? { zoomIn: "放大", zoomOut: "缩小", reset: "复位", expand: "全屏查看", hint: "Ctrl 或 Command + 滚轮缩放，拖拽平移，双击复位" }
    : { zoomIn: "Zoom in", zoomOut: "Zoom out", reset: "Reset", expand: "Expand", hint: "Ctrl or Command + wheel to zoom, drag to pan, double-click to reset" };

  const operate = useCallback((action: "in" | "out" | "reset" | "left" | "right") => {
    for (const chart of [embeddedRef.current, fullscreenRef.current]) {
      if (!chart || chart.isDisposed() || zoomMode === "none") continue;
      const dataZoom = (chart.getOption().dataZoom || []) as Array<{ start?: number; end?: number }>;
      const axes = zoomMode === "xy" ? Math.min(2, dataZoom.length) : Math.min(1, dataZoom.length);
      for (let index = 0; index < axes; index += 1) {
        const current = dataZoom[index] || {};
        const start = Number(current.start ?? 0);
        const end = Number(current.end ?? 100);
        const span = Math.max(2, end - start);
        const centre = (start + end) / 2;
        let nextStart = start;
        let nextEnd = end;
        if (action === "reset") {
          nextStart = 0;
          nextEnd = 100;
        } else if (action === "in" || action === "out") {
          const nextSpan = Math.max(2, Math.min(100, span * (action === "in" ? 0.72 : 1.38)));
          nextStart = Math.max(0, centre - nextSpan / 2);
          nextEnd = Math.min(100, nextStart + nextSpan);
          nextStart = Math.max(0, nextEnd - nextSpan);
        } else {
          const shift = span * 0.12 * (action === "left" ? -1 : 1);
          nextStart = Math.max(0, Math.min(100 - span, start + shift));
          nextEnd = nextStart + span;
        }
        chart.dispatchAction({ type: "dataZoom", dataZoomIndex: index, start: nextStart, end: nextEnd });
      }
    }
    setStatus(action === "reset" ? labels.reset : action === "in" ? labels.zoomIn : action === "out" ? labels.zoomOut : "");
  }, [labels.reset, labels.zoomIn, labels.zoomOut, zoomMode]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "+" || event.key === "=") { event.preventDefault(); operate("in"); }
    if (event.key === "-") { event.preventDefault(); operate("out"); }
    if (event.key === "0") { event.preventDefault(); operate("reset"); }
    if (event.key === "ArrowLeft") { event.preventDefault(); operate("left"); }
    if (event.key === "ArrowRight") { event.preventDefault(); operate("right"); }
  };

  return <>
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <ChartToolbar labels={labels} zoomMode={zoomMode} onAction={operate} onExpand={() => setFullscreen(true)} />
      <ChartCanvas chartRef={embeddedRef} option={option} title={title} height={height} zoomMode={zoomMode} fullscreen={false} onKeyDown={onKeyDown} onReset={() => operate("reset")} onItemClickRef={chartClickRef} />
      <p className="mt-1 font-data text-[8px] text-agent-dim">{labels.hint}</p>
      <span className="sr-only" aria-live="polite">{status}</span>
    </div>
    <Dialog open={fullscreen} onOpenChange={setFullscreen}>
      <DialogContent className="h-[calc(100dvh-32px)] w-[calc(100vw-32px)] max-w-none gap-3 overflow-hidden border-agent-border bg-agent-surface p-5 text-agent-text">
        <DialogHeader className="pr-10">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description || labels.hint}</DialogDescription>
        </DialogHeader>
        <ChartToolbar labels={labels} zoomMode={zoomMode} onAction={operate} />
        <ChartCanvas chartRef={fullscreenRef} option={option} title={title} height={Math.max(420, typeof window === "undefined" ? 680 : window.innerHeight - 170)} zoomMode={zoomMode} fullscreen onKeyDown={onKeyDown} onReset={() => operate("reset")} onItemClickRef={chartClickRef} />
      </DialogContent>
    </Dialog>
  </>;
}

function ChartToolbar({ labels, zoomMode, onAction, onExpand }: {
  labels: { zoomIn: string; zoomOut: string; reset: string; expand: string };
  zoomMode: ChartZoomMode;
  onAction: (action: "in" | "out" | "reset") => void;
  onExpand?: () => void;
}) {
  return <div className="mb-2 flex justify-end gap-1">
    {zoomMode !== "none" ? <>
      <Button type="button" size="sm" variant="ghost" title={labels.zoomIn} aria-label={labels.zoomIn} onClick={() => onAction("in")}><Plus data-icon="inline-start" /></Button>
      <Button type="button" size="sm" variant="ghost" title={labels.zoomOut} aria-label={labels.zoomOut} onClick={() => onAction("out")}><Minus data-icon="inline-start" /></Button>
      <Button type="button" size="sm" variant="ghost" title={labels.reset} aria-label={labels.reset} onClick={() => onAction("reset")}><RotateCcw data-icon="inline-start" /></Button>
    </> : null}
    {onExpand ? <Button type="button" size="sm" variant="ghost" title={labels.expand} aria-label={labels.expand} onClick={onExpand}><Maximize2 data-icon="inline-start" /></Button> : null}
  </div>;
}

function ChartCanvas({ chartRef, option, title, height, zoomMode, fullscreen, onKeyDown, onReset, onItemClickRef }: {
  chartRef: React.MutableRefObject<EChartsType | null>;
  option: EChartsCoreOption;
  title: string;
  height: number;
  zoomMode: ChartZoomMode;
  fullscreen: boolean;
  onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => void;
  onReset: () => void;
  onItemClickRef: React.MutableRefObject<(params: ChartItemClick) => void>;
}) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const chart = echarts.init(node, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const zoom = (option.dataZoom || []) as Array<Record<string, unknown>>;
    const next = { ...option, dataZoom: zoom.map(item => ({
      ...item,
      zoomOnMouseWheel: fullscreen ? true : "ctrl",
      moveOnMouseMove: true,
      moveOnMouseWheel: false,
      preventDefaultMouseMove: fullscreen,
    })) } as EChartsCoreOption;
    chart.setOption(next, { notMerge: true });
    const onClick = (params: ChartItemClick) => onItemClickRef.current(params);
    chart.on("click", onClick);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(node);
    return () => {
      observer.disconnect();
      chartRef.current = null;
      chart.off("click", onClick);
      chart.dispose();
    };
  }, [chartRef, fullscreen, onItemClickRef, option]);
  return <div
    ref={host}
    data-interactive-chart={title}
    role="img"
    aria-label={title}
    tabIndex={zoomMode === "none" ? -1 : 0}
    className="min-h-0 w-full outline-none focus-visible:ring-1 focus-visible:ring-agent-mint"
    style={{ height }}
    onKeyDown={onKeyDown}
    onDoubleClick={onReset}
  />;
}

export type { EChartsCoreOption };
