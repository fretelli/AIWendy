'use client'

import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  createSeriesMarkers,
  ColorType,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  LineStyle,
  LineData,
  CrosshairMode,
} from 'lightweight-charts'
import type { SeriesMarker } from 'lightweight-charts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  BarChart3,
  Settings,
  TrendingUp,
  TrendingDown,
  Activity,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  MoreVertical,
} from 'lucide-react'
import { JournalResponse } from '@/lib/types/journal'
import { format } from 'date-fns'
import { marketDataApi } from '@/lib/api/market-data'

interface AdvancedKLineChartProps {
  journals?: JournalResponse[]
  symbol?: string
  interval?: '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w'
  height?: number
}

interface TechnicalIndicator {
  name: string
  enabled: boolean
  series?: ISeriesApi<'Line'>
  params?: any
}

// Calculate Simple Moving Average
function calculateSMA(data: CandlestickData[], period: number): LineData[] {
  const sma: LineData[] = []
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close
    }
    sma.push({
      time: data[i].time,
      value: sum / period,
    })
  }
  return sma
}

// Calculate Exponential Moving Average
function calculateEMA(data: CandlestickData[], period: number): LineData[] {
  const ema: LineData[] = []
  const multiplier = 2 / (period + 1)

  // Start with SMA for the first EMA value
  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += data[i].close
  }
  let prevEMA = sum / period

  ema.push({
    time: data[period - 1].time,
    value: prevEMA,
  })

  for (let i = period; i < data.length; i++) {
    const currentEMA = (data[i].close - prevEMA) * multiplier + prevEMA
    ema.push({
      time: data[i].time,
      value: currentEMA,
    })
    prevEMA = currentEMA
  }

  return ema
}

// Calculate RSI
function calculateRSI(data: CandlestickData[], period: number = 14): LineData[] {
  const rsi: LineData[] = []
  const changes: number[] = []

  for (let i = 1; i < data.length; i++) {
    changes.push(data[i].close - data[i - 1].close)
  }

  for (let i = period; i < changes.length; i++) {
    const gains: number[] = []
    const losses: number[] = []

    for (let j = i - period; j < i; j++) {
      if (changes[j] > 0) {
        gains.push(changes[j])
        losses.push(0)
      } else {
        gains.push(0)
        losses.push(Math.abs(changes[j]))
      }
    }

    const avgGain = gains.reduce((a, b) => a + b, 0) / period
    const avgLoss = losses.reduce((a, b) => a + b, 0) / period

    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
    const rsiValue = 100 - (100 / (1 + rs))

    rsi.push({
      time: data[i + 1].time,
      value: rsiValue,
    })
  }

  return rsi
}

// Calculate Bollinger Bands
function calculateBollingerBands(data: CandlestickData[], period: number = 20, stdDev: number = 2) {
  const sma = calculateSMA(data, period)
  const upper: LineData[] = []
  const lower: LineData[] = []

  for (let i = 0; i < sma.length; i++) {
    const dataIndex = i + period - 1
    let sumSquaredDiff = 0

    for (let j = 0; j < period; j++) {
      const diff = data[dataIndex - j].close - sma[i].value
      sumSquaredDiff += diff * diff
    }

    const variance = sumSquaredDiff / period
    const standardDeviation = Math.sqrt(variance)

    upper.push({
      time: sma[i].time,
      value: sma[i].value + (standardDeviation * stdDev),
    })

    lower.push({
      time: sma[i].time,
      value: sma[i].value - (standardDeviation * stdDev),
    })
  }

  return { sma, upper, lower }
}

// Generate more realistic mock data
function generateRealisticMockData(basePrice: number = 100, days: number = 90): CandlestickData[] {
  const data: CandlestickData[] = []
  const now = new Date()
  let currentPrice = basePrice

  for (let i = days; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)

    // Add trend and volatility
    const trend = Math.sin(i / 10) * 0.02
    const volatility = 0.015 + Math.random() * 0.01
    const gap = (Math.random() - 0.5) * volatility

    const open = currentPrice * (1 + gap)
    const change = trend + (Math.random() - 0.5) * volatility * 2
    const close = open * (1 + change)
    const high = Math.max(open, close) * (1 + Math.random() * volatility)
    const low = Math.min(open, close) * (1 - Math.random() * volatility)

    data.push({
      time: format(date, 'yyyy-MM-dd') as any,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
    })

    currentPrice = close
  }

  return data
}

export function AdvancedKLineChart({
  journals = [],
  symbol = 'SPY',
  interval = '1d',
  height = 500,
}: AdvancedKLineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  const [indicators, setIndicators] = useState<TechnicalIndicator[]>([
    { name: 'SMA 20', enabled: false, params: { period: 20 } },
    { name: 'SMA 50', enabled: false, params: { period: 50 } },
    { name: 'EMA 20', enabled: false, params: { period: 20 } },
    { name: 'EMA 50', enabled: false, params: { period: 50 } },
    { name: 'Bollinger Bands', enabled: false, params: { period: 20, stdDev: 2 } },
    { name: 'Volume', enabled: true },
  ])

  const [chartType, setChartType] = useState<'candles' | 'line' | 'area'>('candles')
  const [showGrid, setShowGrid] = useState(true)
  const [showCrosshair, setShowCrosshair] = useState(true)
  const [darkMode, setDarkMode] = useState(false)

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container) return

    const chartOptions = {
      width: container.clientWidth || 800,
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

    const chart = createChart(container, chartOptions)
    chartRef.current = chart

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    })
    candleSeriesRef.current = candlestickSeries

    const volumeIndicator = indicators.find(i => i.name === 'Volume')
    const volumeSeries = volumeIndicator?.enabled
      ? chart.addSeries(HistogramSeries, {
          color: '#26a69a',
          priceFormat: { type: 'volume' },
          priceScaleId: '',
        })
      : null

    if (volumeSeries) {
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      })
      volumeSeriesRef.current = volumeSeries
    } else {
      volumeSeriesRef.current = null
    }

    const seriesMarkers = createSeriesMarkers(candlestickSeries)

    let cancelled = false

    const loadChartData = async () => {
      try {
        const intervalMap: Record<string, string> = {
          '1m': '1min',
          '5m': '5min',
          '15m': '15min',
          '1h': '1h',
          '4h': '1h',
          '1d': '1day',
          '1w': '1week',
        }

        const marketData = await marketDataApi.getHistoricalData(
          symbol,
          intervalMap[interval] || '1day',
          90
        )

        if (cancelled) return

        const data: CandlestickData[] = marketData.map(d => ({
          time: format(new Date(d.time), 'yyyy-MM-dd') as any,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))

        candlestickSeries.setData(data)

        if (volumeSeries) {
          const volumeData = marketData.map((d, i) => ({
            time: data[i].time,
            value: d.volume || Math.random() * 1000000,
            color: d.close >= d.open ? '#10b98150' : '#ef444450',
          }))
          volumeSeries.setData(volumeData)
        }

        indicators.forEach(indicator => {
          if (indicator.enabled && indicator.name !== 'Volume') {
            if (indicator.name.startsWith('SMA')) {
              const period = indicator.params?.period || 20
              const smaData = calculateSMA(data, period)
              const smaSeries = chart.addSeries(LineSeries, {
                color: period === 20 ? '#8b5cf6' : '#f59e0b',
                lineWidth: 2,
                title: indicator.name,
              })
              smaSeries.setData(smaData)
            } else if (indicator.name.startsWith('EMA')) {
              const period = indicator.params?.period || 20
              const emaData = calculateEMA(data, period)
              const emaSeries = chart.addSeries(LineSeries, {
                color: period === 20 ? '#3b82f6' : '#ec4899',
                lineWidth: 2,
                title: indicator.name,
                lineStyle: LineStyle.Solid,
              })
              emaSeries.setData(emaData)
            } else if (indicator.name === 'Bollinger Bands') {
              const { sma, upper, lower } = calculateBollingerBands(
                data,
                indicator.params?.period || 20,
                indicator.params?.stdDev || 2
              )

              const middleSeries = chart.addSeries(LineSeries, {
                color: '#6b7280',
                lineWidth: 1,
                title: 'BB Middle',
              })
              middleSeries.setData(sma)

              const upperSeries = chart.addSeries(LineSeries, {
                color: '#10b981',
                lineWidth: 1,
                lineStyle: LineStyle.Dashed,
                title: 'BB Upper',
              })
              upperSeries.setData(upper)

              const lowerSeries = chart.addSeries(LineSeries, {
                color: '#ef4444',
                lineWidth: 1,
                lineStyle: LineStyle.Dashed,
                title: 'BB Lower',
              })
              lowerSeries.setData(lower)
            }
          }
        })

        if (journals.length > 0) {
          const markers = journals
            .filter(j => j.trade_date && j.symbol === symbol)
            .map((j): SeriesMarker<any> => {
              const isProfit = j.pnl_amount && j.pnl_amount > 0
              return {
                time: format(new Date(j.trade_date!), 'yyyy-MM-dd') as any,
                position: isProfit ? 'aboveBar' : 'belowBar',
                color: isProfit ? '#10b981' : '#ef4444',
                shape: isProfit ? 'arrowUp' : 'arrowDown',
                text: `${j.pnl_amount?.toFixed(0)}`,
              }
            })
          seriesMarkers.setMarkers(markers)
        } else {
          seriesMarkers.setMarkers([])
        }

        chart.timeScale().fitContent()
      } catch (error) {
        if (cancelled) return
        console.error('Error loading chart data:', error)

        const data = generateRealisticMockData(100, 90)
        candlestickSeries.setData(data)

        if (volumeSeries) {
          const volumeData = data.map(d => ({
            time: d.time,
            value: Math.random() * 1000000,
            color: d.close >= d.open ? '#10b98150' : '#ef444450',
          }))
          volumeSeries.setData(volumeData)
        }

        chart.timeScale().fitContent()
      }
    }

    void loadChartData()

    const handleResize = () => {
      const current = chartContainerRef.current
      if (current) {
        chart.applyOptions({ width: current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelled = true
      window.removeEventListener('resize', handleResize)
      seriesMarkers.detach()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [indicators, darkMode, showGrid, showCrosshair, symbol, height, journals, chartType])

  const toggleIndicator = (indicatorName: string) => {
    setIndicators(prev =>
      prev.map(ind =>
        ind.name === indicatorName
          ? { ...ind, enabled: !ind.enabled }
          : ind
      )
    )
  }

  const handleZoomIn = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().applyOptions({
        rightOffset: chartRef.current.timeScale().options().rightOffset + 5,
      })
    }
  }

  const handleZoomOut = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().applyOptions({
        rightOffset: Math.max(0, chartRef.current.timeScale().options().rightOffset - 5),
      })
    }
  }

  const handleResetChart = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }

  const handleExportImage = () => {
    if (chartRef.current) {
      const canvas = chartRef.current.takeScreenshot()
      const link = document.createElement('a')
      link.download = `${symbol}_chart_${format(new Date(), 'yyyyMMdd_HHmmss')}.png`
      link.href = canvas.toDataURL()
      link.click()
    }
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Advanced Price Chart
            </CardTitle>
            <CardDescription>Technical analysis with indicators</CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {/* Interval Selector */}
            <Select value={interval}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1m">1m</SelectItem>
                <SelectItem value="5m">5m</SelectItem>
                <SelectItem value="15m">15m</SelectItem>
                <SelectItem value="1h">1h</SelectItem>
                <SelectItem value="4h">4h</SelectItem>
                <SelectItem value="1d">1d</SelectItem>
                <SelectItem value="1w">1w</SelectItem>
              </SelectContent>
            </Select>

            {/* Chart Controls */}
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" onClick={handleZoomIn}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleZoomOut}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleResetChart}>
                <RotateCcw className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleExportImage}>
                <Download className="h-4 w-4" />
              </Button>
            </div>

            {/* Settings Sheet */}
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <Settings className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Chart Settings</SheetTitle>
                  <SheetDescription>
                    Customize indicators and appearance
                  </SheetDescription>
                </SheetHeader>

                <div className="space-y-6 mt-6">
                  {/* Indicators */}
                  <div>
                    <h3 className="font-medium mb-4">Technical Indicators</h3>
                    <div className="space-y-3">
                      {indicators.map(indicator => (
                        <div key={indicator.name} className="flex items-center justify-between">
                          <Label htmlFor={indicator.name} className="font-normal">
                            {indicator.name}
                          </Label>
                          <Switch
                            id={indicator.name}
                            checked={indicator.enabled}
                            onCheckedChange={() => toggleIndicator(indicator.name)}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  {/* Appearance */}
                  <div>
                    <h3 className="font-medium mb-4">Appearance</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="grid" className="font-normal">Show Grid</Label>
                        <Switch
                          id="grid"
                          checked={showGrid}
                          onCheckedChange={setShowGrid}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label htmlFor="crosshair" className="font-normal">Show Crosshair</Label>
                        <Switch
                          id="crosshair"
                          checked={showCrosshair}
                          onCheckedChange={setShowCrosshair}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label htmlFor="dark" className="font-normal">Dark Mode</Label>
                        <Switch
                          id="dark"
                          checked={darkMode}
                          onCheckedChange={setDarkMode}
                        />
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Chart Type */}
                  <div>
                    <h3 className="font-medium mb-4">Chart Type</h3>
                    <div className="grid grid-cols-3 gap-2">
                      <Button
                        variant={chartType === 'candles' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setChartType('candles')}
                      >
                        Candles
                      </Button>
                      <Button
                        variant={chartType === 'line' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setChartType('line')}
                      >
                        Line
                      </Button>
                      <Button
                        variant={chartType === 'area' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setChartType('area')}
                      >
                        Area
                      </Button>
                    </div>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div ref={chartContainerRef} className="w-full" />

        {/* Indicator Legend */}
        <div className="px-6 py-3 border-t bg-muted/30">
          <div className="flex items-center gap-4 text-xs">
            <span className="text-muted-foreground">Indicators:</span>
            {indicators
              .filter(i => i.enabled)
              .map(indicator => (
                <div key={indicator.name} className="flex items-center gap-1">
                  <div
                    className="w-3 h-[2px]"
                    style={{
                      backgroundColor:
                        indicator.name === 'SMA 20'
                          ? '#8b5cf6'
                          : indicator.name === 'SMA 50'
                          ? '#f59e0b'
                          : indicator.name === 'EMA 20'
                          ? '#3b82f6'
                          : indicator.name === 'EMA 50'
                          ? '#ec4899'
                          : '#6b7280',
                    }}
                  />
                  <span>{indicator.name}</span>
                </div>
              ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
