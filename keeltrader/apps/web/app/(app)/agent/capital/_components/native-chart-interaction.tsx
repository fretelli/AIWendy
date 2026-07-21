'use client'

import { useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'

export type ChartCursor = { index: number; x: number; y: number }

export function chartCursorFromPointer(
  event: ReactPointerEvent<SVGRectElement>,
  dimensions: { width: number; height: number; marginLeft: number; plotWidth: number; points: number },
): ChartCursor | null {
  if (dimensions.points <= 0) return null
  const svg = event.currentTarget.ownerSVGElement
  if (!svg) return null
  const rect = svg.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return null
  const x = (event.clientX - rect.left) * dimensions.width / rect.width
  const y = (event.clientY - rect.top) * dimensions.height / rect.height
  const ratio = Math.max(0, Math.min(1, (x - dimensions.marginLeft) / dimensions.plotWidth))
  return { index: Math.round(ratio * Math.max(0, dimensions.points - 1)), x, y }
}

export function placeChartTooltip(
  cursor: Pick<ChartCursor, 'x' | 'y'>,
  container: { width: number; height: number },
  tooltip: { width: number; height: number },
  gap = 12,
  padding = 6,
): { left: number; top: number } {
  const maxLeft = Math.max(padding, container.width - tooltip.width - padding)
  const maxTop = Math.max(padding, container.height - tooltip.height - padding)
  const preferredLeft = cursor.x + gap
  const preferredTop = cursor.y + gap
  const left = preferredLeft + tooltip.width <= container.width - padding
    ? preferredLeft
    : cursor.x - tooltip.width - gap
  const top = preferredTop + tooltip.height <= container.height - padding
    ? preferredTop
    : cursor.y - tooltip.height - gap
  return {
    left: Math.max(padding, Math.min(maxLeft, left)),
    top: Math.max(padding, Math.min(maxTop, top)),
  }
}

export function NativeChartTooltip({ cursor, width, height, children }: {
  cursor: ChartCursor
  width: number
  height: number
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 208, height: 112 })
  useLayoutEffect(() => {
    const node = ref.current
    if (!node) return
    const rect = node.getBoundingClientRect()
    setSize(current => current.width === rect.width && current.height === rect.height
      ? current
      : { width: rect.width, height: rect.height })
  }, [children])
  const position = placeChartTooltip(cursor, { width, height }, size)
  const style: CSSProperties = { left: position.left, top: position.top }
  return <div ref={ref} className="pointer-events-none absolute z-10 min-w-48 rounded-xl border bg-popover/96 p-3 text-xs shadow-xl backdrop-blur" style={style}>{children}</div>
}
