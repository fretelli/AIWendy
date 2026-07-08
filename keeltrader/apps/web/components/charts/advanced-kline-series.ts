import {
  CandlestickData,
  IChartApi,
  LineSeries,
  LineStyle,
  Time,
} from 'lightweight-charts'

import {
  calculateBollingerBands,
  calculateEMA,
  calculateSMA,
} from '@/lib/charts/kline-data'

import { indicatorColor, type TechnicalIndicator } from './advanced-kline-config'

export function applyAdvancedIndicatorSeries(
  chart: IChartApi,
  data: CandlestickData<Time>[],
  indicators: TechnicalIndicator[]
) {
  indicators.forEach(indicator => {
    if (!indicator.enabled || indicator.name === 'Volume') return

    if (indicator.name.startsWith('SMA')) {
      const period = indicator.params?.period || 20
      const smaData = calculateSMA(data, period)
      const smaSeries = chart.addSeries(LineSeries, {
        color: indicatorColor(indicator.name),
        lineWidth: 2,
        title: indicator.name,
      })
      smaSeries.setData(smaData)
      return
    }

    if (indicator.name.startsWith('EMA')) {
      const period = indicator.params?.period || 20
      const emaData = calculateEMA(data, period)
      const emaSeries = chart.addSeries(LineSeries, {
        color: indicatorColor(indicator.name),
        lineWidth: 2,
        title: indicator.name,
        lineStyle: LineStyle.Solid,
      })
      emaSeries.setData(emaData)
      return
    }

    if (indicator.name === 'Bollinger Bands') {
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
  })
}
