'use client'

import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  createSeriesMarkers,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  HistogramSeries,
} from 'lightweight-charts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  BarChart3,
  AlertCircle,
} from 'lucide-react'
import { JournalResponse } from '@/lib/types/journal'
import { format } from 'date-fns'
import { marketDataApi } from '@/lib/api/market-data'
import {
  intervalToMarketDataInterval,
  journalTradeMarkers,
  priceDataToCandlesticks,
  priceDataToVolume,
} from '@/lib/charts/kline-data'
import { logClientError } from '@/lib/client-log'
import {
  DEFAULT_ADVANCED_KLINE_INDICATORS,
  createAdvancedKLineChartOptions,
  indicatorColor,
  type AdvancedKLineInterval,
  type TechnicalIndicator,
} from './advanced-kline-config'
import { applyAdvancedIndicatorSeries } from './advanced-kline-series'
import { AdvancedKLineToolbar } from './AdvancedKLineToolbar'

interface AdvancedKLineChartProps {
  journals?: JournalResponse[]
  symbol?: string
  interval?: AdvancedKLineInterval
  height?: number
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

  const [intervalSelection, setIntervalSelection] = useState(() => ({
    propInterval: interval,
    value: interval,
  }))
  const selectedInterval = intervalSelection.propInterval === interval
    ? intervalSelection.value
    : interval
  const [indicators, setIndicators] = useState<TechnicalIndicator[]>(
    DEFAULT_ADVANCED_KLINE_INDICATORS
  )
  const [showGrid, setShowGrid] = useState(true)
  const [showCrosshair, setShowCrosshair] = useState(true)
  const [darkMode, setDarkMode] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)

  const setSelectedInterval = (value: AdvancedKLineInterval) => {
    setIntervalSelection({ propInterval: interval, value })
  }

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container) return
    setLoadError(null)

    const chartOptions = createAdvancedKLineChartOptions({
      width: container.clientWidth || 800,
      height,
      darkMode,
      showGrid,
      showCrosshair,
      symbol,
    })

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
        const marketData = await marketDataApi.getHistoricalData(
          symbol,
          intervalToMarketDataInterval(selectedInterval),
          90
        )

        if (cancelled) return
        if (marketData.length === 0) {
          candlestickSeries.setData([])
          if (volumeSeries) volumeSeries.setData([])
          seriesMarkers.setMarkers([])
          setLoadError(`No market data available for ${symbol}.`)
          return
        }

        const data = priceDataToCandlesticks(marketData)

        candlestickSeries.setData(data)

        if (volumeSeries) {
          volumeSeries.setData(priceDataToVolume(marketData, data))
        }

        applyAdvancedIndicatorSeries(chart, data, indicators)

        seriesMarkers.setMarkers(journalTradeMarkers(journals, symbol, { textMode: 'pnl' }))

        chart.timeScale().fitContent()
      } catch (error) {
        if (cancelled) return
        logClientError('chart.advancedKline.load', error)
        candlestickSeries.setData([])
        if (volumeSeries) volumeSeries.setData([])
        seriesMarkers.setMarkers([])
        setLoadError(`Unable to load market data for ${symbol}.`)
      }
    }

    void loadChartData()

    const handleResize = () => {
      const current = chartContainerRef.current
      if (current) {
        chart.applyOptions({ width: current.clientWidth })
      }
    }

    let resizeObserver: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(handleResize)
      resizeObserver.observe(container)
    } else {
      window.addEventListener('resize', handleResize)
    }

    return () => {
      cancelled = true
      if (resizeObserver) {
        resizeObserver.disconnect()
      } else {
        window.removeEventListener('resize', handleResize)
      }
      seriesMarkers.detach()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [
    indicators,
    darkMode,
    showGrid,
    showCrosshair,
    symbol,
    selectedInterval,
    height,
    journals,
    retryNonce,
  ])

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

          <AdvancedKLineToolbar
            interval={selectedInterval}
            onIntervalChange={setSelectedInterval}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onReset={handleResetChart}
            onExport={handleExportImage}
            indicators={indicators}
            onToggleIndicator={toggleIndicator}
            showGrid={showGrid}
            onShowGridChange={setShowGrid}
            showCrosshair={showCrosshair}
            onShowCrosshairChange={setShowCrosshair}
            darkMode={darkMode}
            onDarkModeChange={setDarkMode}
          />
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="relative">
          <div ref={chartContainerRef} className="w-full" />
          {loadError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/80 text-center">
              <AlertCircle className="h-8 w-8 text-muted-foreground" />
              <p className="max-w-sm text-sm text-muted-foreground">{loadError}</p>
              <Button variant="outline" size="sm" onClick={() => setRetryNonce(value => value + 1)}>
                Retry
              </Button>
            </div>
          )}
        </div>

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
                        indicatorColor(indicator.name),
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
