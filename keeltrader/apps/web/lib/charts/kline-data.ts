import { format } from 'date-fns'
import type {
  CandlestickData,
  HistogramData,
  LineData,
  SeriesMarker,
  Time,
} from 'lightweight-charts'

import type { PriceData } from '@/lib/api/market-data'
import type { JournalResponse } from '@/lib/types/journal'

export type ChartTime = Time

export interface TradeStats {
  totalTrades: number
  winRate: number
  avgWin: number
  avgLoss: number
}

export interface BollingerBandsData {
  sma: LineData<Time>[]
  upper: LineData<Time>[]
  lower: LineData<Time>[]
}

export function toChartDay(value: string | Date): Time {
  return format(new Date(value), 'yyyy-MM-dd') as Time
}

export function priceDataToCandlesticks(data: PriceData[]): CandlestickData<Time>[] {
  return data.map(d => ({
    time: toChartDay(d.time),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }))
}

export function priceDataToVolume(
  data: PriceData[],
  candlesticks: CandlestickData<Time>[] = priceDataToCandlesticks(data)
): HistogramData<Time>[] {
  return data.map((d, index) => ({
    time: candlesticks[index]?.time ?? toChartDay(d.time),
    value: d.volume ?? 0,
    color: d.close >= d.open ? '#10b98150' : '#ef444450',
  }))
}

export function journalTradeMarkers(
  journals: JournalResponse[],
  symbol: string,
  opts: { textMode?: 'symbol-pnl' | 'pnl' } = {}
): SeriesMarker<Time>[] {
  const textMode = opts.textMode ?? 'symbol-pnl'

  return journals
    .filter(j => j.symbol === symbol && j.trade_date && (textMode === 'pnl' || j.entry_price))
    .map(j => {
      const pnl = j.pnl_amount ?? 0
      const isProfit = pnl > 0
      const pnlText = textMode === 'pnl' ? j.pnl_amount?.toFixed(0) : j.pnl_amount?.toFixed(2)

      return {
        time: toChartDay(j.trade_date!),
        position: isProfit ? 'aboveBar' : 'belowBar',
        color: isProfit ? '#10b981' : '#ef4444',
        shape: isProfit ? 'arrowUp' : 'arrowDown',
        text: textMode === 'pnl' ? `${pnlText}` : `${j.symbol}: ${isProfit ? '+' : ''}${pnlText}`,
      }
    })
}

export function calculateTradeStats(journals: JournalResponse[], symbol: string): TradeStats {
  const symbolJournals = journals.filter(j => j.symbol === symbol)
  const winningTrades = symbolJournals.filter(j => j.pnl_amount && j.pnl_amount > 0)
  const losingTrades = symbolJournals.filter(j => j.pnl_amount && j.pnl_amount < 0)

  return {
    totalTrades: symbolJournals.length,
    winRate: (winningTrades.length / symbolJournals.length) * 100 || 0,
    avgWin:
      winningTrades.reduce((sum, j) => sum + (j.pnl_amount || 0), 0) / winningTrades.length || 0,
    avgLoss:
      losingTrades.reduce((sum, j) => sum + (j.pnl_amount || 0), 0) / losingTrades.length || 0,
  }
}

export function calculateSMA(data: CandlestickData<Time>[], period: number): LineData<Time>[] {
  if (period <= 0 || data.length < period) return []

  const sma: LineData<Time>[] = []
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

export function calculateEMA(data: CandlestickData<Time>[], period: number): LineData<Time>[] {
  if (period <= 0 || data.length < period) return []

  const ema: LineData<Time>[] = []
  const multiplier = 2 / (period + 1)

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

export function calculateRSI(
  data: CandlestickData<Time>[],
  period: number = 14
): LineData<Time>[] {
  if (period <= 0 || data.length <= period + 1) return []

  const rsi: LineData<Time>[] = []
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
    const rsiValue = 100 - 100 / (1 + rs)

    rsi.push({
      time: data[i + 1].time,
      value: rsiValue,
    })
  }

  return rsi
}

export function calculateBollingerBands(
  data: CandlestickData<Time>[],
  period: number = 20,
  stdDev: number = 2
): BollingerBandsData {
  const sma = calculateSMA(data, period)
  const upper: LineData<Time>[] = []
  const lower: LineData<Time>[] = []

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
      value: sma[i].value + standardDeviation * stdDev,
    })

    lower.push({
      time: sma[i].time,
      value: sma[i].value - standardDeviation * stdDev,
    })
  }

  return { sma, upper, lower }
}

export function intervalToMarketDataInterval(interval: string): string {
  const intervalMap: Record<string, string> = {
    '1m': '1min',
    '5m': '5min',
    '15m': '15min',
    '1h': '1h',
    '4h': '1h',
    '1d': '1day',
    '1w': '1week',
  }

  return intervalMap[interval] || '1day'
}
