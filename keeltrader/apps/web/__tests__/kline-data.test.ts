import type { CandlestickData, Time } from 'lightweight-charts'

import type { PriceData } from '@/lib/api/market-data'
import {
  calculateBollingerBands,
  calculateEMA,
  calculateRSI,
  calculateSMA,
  calculateTradeStats,
  intervalToMarketDataInterval,
  journalTradeMarkers,
  priceDataToCandlesticks,
  priceDataToVolume,
} from '@/lib/charts/kline-data'
import type { JournalResponse } from '@/lib/types/journal'
import { TradeDirection, TradeResult } from '@/lib/types/journal'

function makeJournal(overrides: Partial<JournalResponse>): JournalResponse {
  return {
    id: 'journal-1',
    user_id: 'user-1',
    symbol: 'SPY',
    direction: TradeDirection.LONG,
    trade_date: '2026-01-03T09:30:00Z',
    entry_price: 100,
    result: TradeResult.WIN,
    pnl_amount: 10,
    followed_rules: true,
    rule_violations: [],
    tags: [],
    screenshots: [],
    created_at: '2026-01-03T10:00:00Z',
    updated_at: '2026-01-03T10:00:00Z',
    is_winner: true,
    is_rule_violation: false,
    ...overrides,
  }
}

const priceData: PriceData[] = [
  {
    time: '2026-01-01T00:00:00Z',
    open: 100,
    high: 110,
    low: 95,
    close: 108,
    volume: 1000,
  },
  {
    time: '2026-01-02T00:00:00Z',
    open: 108,
    high: 109,
    low: 98,
    close: 101,
    volume: 2000,
  },
  {
    time: '2026-01-03T00:00:00Z',
    open: 101,
    high: 112,
    low: 100,
    close: 111,
    volume: 3000,
  },
]

const candleData: CandlestickData<Time>[] = [
  { time: '2026-01-01' as Time, open: 100, high: 110, low: 95, close: 108 },
  { time: '2026-01-02' as Time, open: 108, high: 109, low: 98, close: 101 },
  { time: '2026-01-03' as Time, open: 101, high: 112, low: 100, close: 111 },
  { time: '2026-01-04' as Time, open: 111, high: 113, low: 104, close: 106 },
  { time: '2026-01-05' as Time, open: 106, high: 115, low: 105, close: 114 },
]

describe('kline-data helpers', () => {
  it('handles empty inputs', () => {
    expect(priceDataToCandlesticks([])).toEqual([])
    expect(priceDataToVolume([])).toEqual([])
    expect(journalTradeMarkers([], 'SPY')).toEqual([])
    expect(calculateTradeStats([], 'SPY')).toEqual({
      totalTrades: 0,
      winRate: 0,
      avgWin: 0,
      avgLoss: 0,
    })
    expect(calculateSMA([], 20)).toEqual([])
    expect(calculateEMA([], 20)).toEqual([])
    expect(calculateRSI([], 14)).toEqual([])
    expect(calculateBollingerBands([], 20)).toEqual({ sma: [], upper: [], lower: [] })
  })

  it('converts market prices to candlestick chart data', () => {
    expect(priceDataToCandlesticks(priceData)).toEqual([
      { time: '2026-01-01', open: 100, high: 110, low: 95, close: 108 },
      { time: '2026-01-02', open: 108, high: 109, low: 98, close: 101 },
      { time: '2026-01-03', open: 101, high: 112, low: 100, close: 111 },
    ])
  })

  it('converts volume with matching candle time and direction colors', () => {
    const candlesticks = priceDataToCandlesticks(priceData)

    expect(priceDataToVolume(priceData, candlesticks)).toEqual([
      { time: '2026-01-01', value: 1000, color: '#10b98150' },
      { time: '2026-01-02', value: 2000, color: '#ef444450' },
      { time: '2026-01-03', value: 3000, color: '#10b98150' },
    ])
  })

  it('creates profitable and losing trade markers', () => {
    const markers = journalTradeMarkers(
      [
        makeJournal({ id: 'win', pnl_amount: 12.345 }),
        makeJournal({ id: 'loss', pnl_amount: -5, trade_date: '2026-01-04T09:30:00Z' }),
        makeJournal({ id: 'other-symbol', symbol: 'QQQ' }),
        makeJournal({ id: 'missing-entry', entry_price: undefined }),
      ],
      'SPY'
    )

    expect(markers).toEqual([
      {
        time: '2026-01-03',
        position: 'aboveBar',
        color: '#10b981',
        shape: 'arrowUp',
        text: 'SPY: +12.35',
      },
      {
        time: '2026-01-04',
        position: 'belowBar',
        color: '#ef4444',
        shape: 'arrowDown',
        text: 'SPY: -5.00',
      },
    ])
  })

  it('supports pnl-only marker text for the advanced chart', () => {
    const markers = journalTradeMarkers(
      [makeJournal({ pnl_amount: -4.6, entry_price: undefined })],
      'SPY',
      { textMode: 'pnl' }
    )

    expect(markers).toEqual([
      {
        time: '2026-01-03',
        position: 'belowBar',
        color: '#ef4444',
        shape: 'arrowDown',
        text: '-5',
      },
    ])
  })

  it('calculates trade statistics', () => {
    expect(
      calculateTradeStats(
        [
          makeJournal({ id: 'win-1', pnl_amount: 10 }),
          makeJournal({ id: 'win-2', pnl_amount: 20 }),
          makeJournal({ id: 'loss-1', pnl_amount: -5 }),
          makeJournal({ id: 'flat', pnl_amount: 0 }),
          makeJournal({ id: 'other', symbol: 'QQQ', pnl_amount: 100 }),
        ],
        'SPY'
      )
    ).toEqual({
      totalTrades: 4,
      winRate: 50,
      avgWin: 15,
      avgLoss: -5,
    })
  })

  it('calculates SMA values', () => {
    expect(calculateSMA(candleData, 3)).toEqual([
      { time: '2026-01-03', value: (108 + 101 + 111) / 3 },
      { time: '2026-01-04', value: (101 + 111 + 106) / 3 },
      { time: '2026-01-05', value: (111 + 106 + 114) / 3 },
    ])
  })

  it('calculates EMA values', () => {
    const ema = calculateEMA(candleData, 3)

    expect(ema).toHaveLength(3)
    expect(ema[0]).toEqual({ time: '2026-01-03', value: (108 + 101 + 111) / 3 })
    expect(ema[1]).toEqual({ time: '2026-01-04', value: 106.33333333333334 })
    expect(ema[2]).toEqual({ time: '2026-01-05', value: 110.16666666666667 })
  })

  it('calculates RSI values', () => {
    const rsi = calculateRSI(candleData, 3)

    expect(rsi).toHaveLength(1)
    expect(rsi[0].time).toBe('2026-01-05')
    expect(rsi[0].value).toBeCloseTo(45.4545, 4)
  })

  it('calculates Bollinger Bands', () => {
    const bands = calculateBollingerBands(candleData, 3, 2)

    expect(bands.sma).toHaveLength(3)
    expect(bands.upper).toHaveLength(3)
    expect(bands.lower).toHaveLength(3)
    expect(bands.sma[0]).toEqual({ time: '2026-01-03', value: (108 + 101 + 111) / 3 })
    expect(bands.upper[0].value).toBeCloseTo(115.0465, 4)
    expect(bands.lower[0].value).toBeCloseTo(98.2868, 4)
  })

  it('maps UI intervals to market data intervals', () => {
    expect(intervalToMarketDataInterval('1m')).toBe('1min')
    expect(intervalToMarketDataInterval('5m')).toBe('5min')
    expect(intervalToMarketDataInterval('15m')).toBe('15min')
    expect(intervalToMarketDataInterval('1h')).toBe('1h')
    expect(intervalToMarketDataInterval('4h')).toBe('1h')
    expect(intervalToMarketDataInterval('1d')).toBe('1day')
    expect(intervalToMarketDataInterval('1w')).toBe('1week')
    expect(intervalToMarketDataInterval('unknown')).toBe('1day')
  })
})
