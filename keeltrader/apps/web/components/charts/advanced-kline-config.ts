import { ColorType, CrosshairMode, LineStyle } from 'lightweight-charts'

export type AdvancedKLineInterval = '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w'

export interface IndicatorParams {
  period?: number
  stdDev?: number
}

export interface TechnicalIndicator {
  name: string
  enabled: boolean
  params?: IndicatorParams
}

export const ADVANCED_KLINE_INTERVALS: AdvancedKLineInterval[] = [
  '1m',
  '5m',
  '15m',
  '1h',
  '4h',
  '1d',
  '1w',
]

export const DEFAULT_ADVANCED_KLINE_INDICATORS: TechnicalIndicator[] = [
  { name: 'SMA 20', enabled: false, params: { period: 20 } },
  { name: 'SMA 50', enabled: false, params: { period: 50 } },
  { name: 'EMA 20', enabled: false, params: { period: 20 } },
  { name: 'EMA 50', enabled: false, params: { period: 50 } },
  { name: 'Bollinger Bands', enabled: false, params: { period: 20, stdDev: 2 } },
  { name: 'Volume', enabled: true },
]

export function indicatorColor(name: string): string {
  if (name === 'SMA 20') return '#8b5cf6'
  if (name === 'SMA 50') return '#f59e0b'
  if (name === 'EMA 20') return '#3b82f6'
  if (name === 'EMA 50') return '#ec4899'
  return '#6b7280'
}

export function createAdvancedKLineChartOptions({
  width,
  height,
  darkMode,
  showGrid,
  showCrosshair,
  symbol,
}: {
  width: number
  height: number
  darkMode: boolean
  showGrid: boolean
  showCrosshair: boolean
  symbol: string
}) {
  return {
    width,
    height,
    layout: {
      background: { type: ColorType.Solid, color: darkMode ? '#1a1a1a' : '#ffffff' },
      textColor: darkMode ? '#d1d5db' : '#71717a',
    },
    grid: {
      vertLines: {
        color: darkMode ? '#2a2a2a' : '#e5e7eb',
        visible: showGrid,
      },
      horzLines: {
        color: darkMode ? '#2a2a2a' : '#e5e7eb',
        visible: showGrid,
      },
    },
    crosshair: {
      mode: showCrosshair ? CrosshairMode.Normal : CrosshairMode.Hidden,
      vertLine: {
        width: 1 as 1,
        color: darkMode ? '#666' : '#999',
        style: LineStyle.Dashed,
      },
      horzLine: {
        width: 1 as 1,
        color: darkMode ? '#666' : '#999',
        style: LineStyle.Dashed,
      },
    },
    rightPriceScale: {
      borderColor: darkMode ? '#2a2a2a' : '#e5e7eb',
      visible: true,
    },
    timeScale: {
      borderColor: darkMode ? '#2a2a2a' : '#e5e7eb',
      timeVisible: true,
      secondsVisible: false,
    },
    watermark: {
      visible: true,
      fontSize: 24,
      horzAlign: 'center',
      vertAlign: 'center',
      color: darkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
      text: symbol,
    },
  }
}
