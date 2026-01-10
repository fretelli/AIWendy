'use client'

import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  createSeriesMarkers,
  CandlestickData,
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
} from 'lightweight-charts'
import type { SeriesMarker } from 'lightweight-charts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Activity, TrendingUp, TrendingDown, BarChart3, Loader2 } from 'lucide-react'
import { JournalResponse } from '@/lib/types/journal'
import { format } from 'date-fns'
import { marketDataApi } from '@/lib/api/market-data'

interface KLineChartProps {
  journals?: JournalResponse[]
  symbol?: string
  onSymbolChange?: (symbol: string) => void
}

interface MarketData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

// Mock data generator for demonstration
function generateMockData(basePrice: number = 100, days: number = 60): CandlestickData[] {
  const data: CandlestickData[] = []
  const now = new Date()
  let currentPrice = basePrice

  for (let i = days; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)

    // Generate realistic OHLC data
    const volatility = 0.02
    const trend = Math.random() > 0.5 ? 1 : -1
    const open = currentPrice
    const close = open * (1 + trend * volatility * Math.random())
    const high = Math.max(open, close) * (1 + volatility * Math.random() * 0.5)
    const low = Math.min(open, close) * (1 - volatility * Math.random() * 0.5)

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

export function KLineChart({ journals = [], symbol = 'SPY', onSymbolChange }: KLineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [timeframe, setTimeframe] = useState('1D')
  const [chartType, setChartType] = useState<'candles' | 'line'>('candles')
  const [isLoading, setIsLoading] = useState(true)

  // Get unique symbols from journals
  const symbols = Array.from(new Set(journals.map(j => j.symbol).filter(Boolean)))

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container) return

    setIsLoading(true)

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#71717a',
      },
      grid: {
        vertLines: { color: '#e5e7eb30' },
        horzLines: { color: '#e5e7eb30' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#e5e7eb',
      },
      timeScale: {
        borderColor: '#e5e7eb',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    })
    seriesRef.current = candlestickSeries

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    const tradeMarkers = createSeriesMarkers(candlestickSeries)

    const days = timeframe === '1M' ? 30 : timeframe === '1W' ? 7 : 60
    let cancelled = false

    const loadChartData = async () => {
      try {
        const marketData = await marketDataApi.getHistoricalData(symbol, '1day', days)
        if (cancelled) return

        const chartData: CandlestickData[] = marketData.map(d => ({
          time: format(new Date(d.time), 'yyyy-MM-dd') as any,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))
        candlestickSeries.setData(chartData)

        const volumeData = marketData.map(d => ({
          time: format(new Date(d.time), 'yyyy-MM-dd') as any,
          value: d.volume || Math.random() * 1000000,
          color: d.close >= d.open ? '#10b98150' : '#ef444450',
        }))
        volumeSeries.setData(volumeData)

        const markers = journals
          .filter(j => j.symbol === symbol && j.trade_date && j.entry_price)
          .map((j): SeriesMarker<any> => {
            const isProfit = j.pnl_amount && j.pnl_amount > 0
            return {
              time: format(new Date(j.trade_date!), 'yyyy-MM-dd') as any,
              position: isProfit ? 'aboveBar' : 'belowBar',
              color: isProfit ? '#10b981' : '#ef4444',
              shape: isProfit ? 'arrowUp' : 'arrowDown',
              text: `${j.symbol}: ${isProfit ? '+' : ''}${j.pnl_amount?.toFixed(2)}`,
            }
          })
        tradeMarkers.setMarkers(markers)

        chart.timeScale().fitContent()
      } catch (error) {
        if (cancelled) return
        console.error('Error loading chart data:', error)

        const mockData = generateMockData(100, days)
        candlestickSeries.setData(mockData)

        const volumeData = mockData.map(d => ({
          time: d.time,
          value: Math.random() * 1000000,
          color: d.close >= d.open ? '#10b98150' : '#ef444450',
        }))
        volumeSeries.setData(volumeData)

        const markers = journals
          .filter(j => j.symbol === symbol && j.trade_date && j.entry_price)
          .map((j): SeriesMarker<any> => {
            const isProfit = j.pnl_amount && j.pnl_amount > 0
            return {
              time: format(new Date(j.trade_date!), 'yyyy-MM-dd') as any,
              position: isProfit ? 'aboveBar' : 'belowBar',
              color: isProfit ? '#10b981' : '#ef4444',
              shape: isProfit ? 'arrowUp' : 'arrowDown',
              text: `${j.symbol}: ${isProfit ? '+' : ''}${j.pnl_amount?.toFixed(2)}`,
            }
          })
        tradeMarkers.setMarkers(markers)

        chart.timeScale().fitContent()
      } finally {
        if (!cancelled) setIsLoading(false)
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
      tradeMarkers.detach()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [journals, symbol, chartType, timeframe])

  const handleTimeframeChange = (tf: string) => {
    setTimeframe(tf)
  }

  const handleChartTypeToggle = () => {
    setChartType(chartType === 'candles' ? 'line' : 'candles')
  }

  // Calculate statistics from journals
  const stats = {
    totalTrades: journals.filter(j => j.symbol === symbol).length,
    winRate: journals.filter(j => j.symbol === symbol && j.pnl_amount && j.pnl_amount > 0).length /
              journals.filter(j => j.symbol === symbol).length * 100 || 0,
    avgWin: journals
      .filter(j => j.symbol === symbol && j.pnl_amount && j.pnl_amount > 0)
      .reduce((sum, j) => sum + (j.pnl_amount || 0), 0) /
      journals.filter(j => j.symbol === symbol && j.pnl_amount && j.pnl_amount > 0).length || 0,
    avgLoss: journals
      .filter(j => j.symbol === symbol && j.pnl_amount && j.pnl_amount < 0)
      .reduce((sum, j) => sum + (j.pnl_amount || 0), 0) /
      journals.filter(j => j.symbol === symbol && j.pnl_amount && j.pnl_amount < 0).length || 0,
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Price Chart
            </CardTitle>
            <CardDescription>Technical analysis and trade visualization</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {/* Symbol Selector */}
            {symbols.length > 0 && (
              <Select value={symbol} onValueChange={onSymbolChange}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {symbols.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            {/* Timeframe Selector */}
            <div className="flex gap-1">
              {['1D', '1W', '1M'].map(tf => (
                <Button
                  key={tf}
                  variant={timeframe === tf ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleTimeframeChange(tf)}
                >
                  {tf}
                </Button>
              ))}
            </div>

            {/* Chart Type Toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleChartTypeToggle}
            >
              {chartType === 'candles' ? 'Line' : 'Candles'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="chart" className="space-y-4">
          <TabsList>
            <TabsTrigger value="chart">Chart</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
          </TabsList>

          <TabsContent value="chart" className="space-y-4">
            <div className="relative h-[400px] w-full">
              <div ref={chartContainerRef} className="h-full w-full" />
              {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-background/50">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              )}
            </div>

            {/* Trade Markers Legend */}
            {journals.length > 0 && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <span>Profitable Trade</span>
                </div>
                <div className="flex items-center gap-1">
                  <TrendingDown className="h-4 w-4 text-red-500" />
                  <span>Loss Trade</span>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="stats" className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Total Trades</p>
                <p className="text-2xl font-bold">{stats.totalTrades}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Win Rate</p>
                <p className="text-2xl font-bold">{stats.winRate.toFixed(1)}%</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Avg Win</p>
                <p className="text-2xl font-bold text-green-500">
                  ${stats.avgWin.toFixed(2)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Avg Loss</p>
                <p className="text-2xl font-bold text-red-500">
                  ${stats.avgLoss.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Recent Trades on this Symbol */}
            <div className="space-y-2">
              <h4 className="font-medium">Recent Trades</h4>
              <div className="space-y-1">
                {journals
                  .filter(j => j.symbol === symbol)
                  .slice(0, 5)
                  .map(journal => (
                    <div key={journal.id} className="flex items-center justify-between p-2 border rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          {format(new Date(journal.trade_date || journal.created_at), 'MMM dd')}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {journal.direction.toUpperCase()}
                        </span>
                      </div>
                      <span className={`text-sm font-medium ${
                        journal.pnl_amount && journal.pnl_amount > 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        {journal.pnl_amount && journal.pnl_amount > 0 ? '+' : ''}
                        ${journal.pnl_amount?.toFixed(2) || '0.00'}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
