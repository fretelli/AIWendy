'use client'

import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'

import { chartCursorFromPointer, NativeChartTooltip, type ChartCursor } from './native-chart-interaction'

export type PlotSeries = { key: string; label: string; color: string; values: Array<number | null | undefined> }

export function NativeSeriesChart({ dates, series, height = 430, valueLabel = formatNumber }: {
  dates: string[]; series: PlotSeries[]; height?: number; valueLabel?: (value: number) => string
}) {
  const host = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  const [rangeStart, setRangeStart] = useState(0)
  const [rangeEnd, setRangeEnd] = useState(Math.max(0, dates.length - 1))
  const [hover, setHover] = useState<number | null>(null)
  useEffect(() => {
    const node = host.current
    if (!node) return
    const measure = () => setWidth(Math.floor(node.clientWidth))
    measure(); const observer = new ResizeObserver(measure); observer.observe(node)
    return () => observer.disconnect()
  }, [])
  const visibleDates = dates.slice(rangeStart, rangeEnd + 1)
  const visibleSeries = useMemo(() => series.map(item => ({ ...item, values: item.values.slice(rangeStart, rangeEnd + 1) })), [series, rangeStart, rangeEnd])
  return <div className="overflow-hidden rounded-2xl border bg-card/88 shadow-sm">
    <div ref={host} data-chart-canvas="raw-market-series" className="w-full p-2 md:p-5" style={{ height }}>
      <div className="relative h-full w-full">
        {width > 0 && visibleDates.length ? <ChartSvg width={Math.max(1, width - (width >= 768 ? 40 : 16))} height={height - (width >= 768 ? 40 : 16)} dates={visibleDates} series={visibleSeries} hover={hover} onHover={setHover} valueLabel={valueLabel} /> : <div className="grid h-full place-items-center text-xs text-muted-foreground">暂无可绘制数据</div>}
      </div>
    </div>
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 border-t px-4 py-3 text-[9px] text-muted-foreground">
      <label className="flex items-center gap-2"><span>起点</span><input aria-label="历史起点" className="w-full accent-[hsl(var(--copper-foreground))]" type="range" min={0} max={Math.max(0, dates.length - 1)} value={rangeStart} onChange={event => { setRangeStart(Math.min(Number(event.target.value), Math.max(0, rangeEnd - 1))); setHover(null) }} /></label>
      <span className="font-data">显示 {Math.max(0, rangeEnd - rangeStart + 1)} 点</span>
      <label className="flex items-center gap-2"><input aria-label="历史终点" className="w-full accent-[hsl(var(--copper-foreground))]" type="range" min={0} max={Math.max(0, dates.length - 1)} value={rangeEnd} onChange={event => { setRangeEnd(Math.max(Number(event.target.value), Math.min(dates.length - 1, rangeStart + 1))); setHover(null) }} /><span>终点</span></label>
    </div>
  </div>
}

function ChartSvg({ width, height, dates, series, hover, onHover, valueLabel }: { width: number; height: number; dates: string[]; series: PlotSeries[]; hover: number | null; onHover: (value: number | null) => void; valueLabel: (value: number) => string }) {
  const [cursor, setCursor] = useState<ChartCursor | null>(null)
  const margin = { left: width < 520 ? 52 : 68, right: 18, top: 24, bottom: 38 }
  const plotWidth = Math.max(1, width - margin.left - margin.right), plotHeight = Math.max(1, height - margin.top - margin.bottom)
  const values = series.flatMap(item => item.values).filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
  let min = values.length ? Math.min(...values) : 0, max = values.length ? Math.max(...values) : 1
  if (min === max) { min -= 1; max += 1 }
  const pad = (max - min) * .08; min -= pad; max += pad
  const x = (index: number) => margin.left + (dates.length <= 1 ? plotWidth / 2 : index / (dates.length - 1) * plotWidth)
  const y = (value: number) => margin.top + (max - value) / (max - min) * plotHeight
  const path = (valuesForSeries: PlotSeries['values']) => { let drawing = false; return valuesForSeries.map((value, index) => { if (typeof value !== 'number' || !Number.isFinite(value)) { drawing = false; return '' } const command = drawing ? 'L' : 'M'; drawing = true; return `${command}${x(index).toFixed(1)},${y(value).toFixed(1)}` }).join(' ') }
  const yTicks = Array.from({ length: 5 }, (_, index) => min + (max - min) * index / 4)
  const dateTicks = Array.from(new Set(Array.from({ length: Math.min(5, dates.length) }, (_, index) => Math.round(index * Math.max(0, dates.length - 1) / Math.max(1, Math.min(5, dates.length) - 1)))))
  const hovered = hover === null ? null : { date: dates[hover], rows: series.map(item => ({ ...item, value: item.values[hover] })) }
  const pointerMove = (event: ReactPointerEvent<SVGRectElement>) => {
    const next = chartCursorFromPointer(event, { width, height, marginLeft: margin.left, plotWidth, points: dates.length })
    if (!next) return
    setCursor(next)
    onHover(next.index)
  }
  const pointerLeave = () => { setCursor(null); onHover(null) }
  return <>
    <svg data-chart-series="raw-market-series" role="img" aria-label="原始市场数据历史图" width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block">
      {yTicks.map(tick => <g key={tick}><line x1={margin.left} x2={width-margin.right} y1={y(tick)} y2={y(tick)} stroke="hsl(var(--border))" strokeDasharray="3 5" /><text x={margin.left-8} y={y(tick)+3} textAnchor="end" fontSize="9" fill="hsl(var(--muted-foreground))">{valueLabel(tick)}</text></g>)}
      {dateTicks.map(index => <text key={index} x={x(index)} y={height-8} textAnchor={index === 0 ? 'start' : index === dates.length-1 ? 'end' : 'middle'} fontSize="9" fill="hsl(var(--muted-foreground))">{shortDate(dates[index])}</text>)}
      {series.map(item => <path key={item.key} d={path(item.values)} fill="none" stroke={item.color} strokeWidth="2" strokeLinejoin="round" />)}
      {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={margin.top} y2={height-margin.bottom} stroke="hsl(var(--copper-foreground))" strokeDasharray="3 3" />}
      <rect x={margin.left} y={margin.top} width={plotWidth} height={plotHeight} fill="transparent" onPointerMove={pointerMove} onPointerLeave={pointerLeave} />
    </svg>
    {hovered && hover !== null && cursor && <NativeChartTooltip cursor={cursor} width={width} height={height}><p className="font-data font-semibold">{hovered.date}</p><div className="mt-2 space-y-1.5">{hovered.rows.map(row => <div key={row.key} className="flex items-center justify-between gap-5"><span className="flex items-center gap-2 text-muted-foreground"><i className="h-2 w-2 rounded-full" style={{ background: row.color }} />{row.label}</span><span className="font-data">{typeof row.value === 'number' ? valueLabel(row.value) : '—'}</span></div>)}</div></NativeChartTooltip>}
  </>
}

export function formatNumber(value: number) { return Math.abs(value) >= 1e12 ? `${(value/1e12).toFixed(2)}万亿` : Math.abs(value) >= 1e8 ? `${(value/1e8).toFixed(2)}亿` : Math.abs(value) >= 1e4 ? `${(value/1e4).toFixed(2)}万` : value.toLocaleString('zh-CN', { maximumFractionDigits: 4 }) }
const shortDate = (value: string) => value.length >= 10 ? value.slice(2, 10).replaceAll('-', '/') : value
