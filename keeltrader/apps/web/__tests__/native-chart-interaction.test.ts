import { placeChartTooltip } from '../app/(app)/agent/capital/_components/native-chart-interaction'
import { formatSourceFreshness, sourceFreshnessTone } from '../lib/market-source-freshness'

describe('native chart tooltip placement', () => {
  it('stays near the cursor in the chart centre', () => {
    expect(placeChartTooltip({ x: 200, y: 120 }, { width: 500, height: 300 }, { width: 160, height: 80 }))
      .toEqual({ left: 212, top: 132 })
  })

  it('flips before the right and bottom edges', () => {
    expect(placeChartTooltip({ x: 480, y: 280 }, { width: 500, height: 300 }, { width: 160, height: 80 }))
      .toEqual({ left: 308, top: 188 })
  })

  it('clamps inside a chart smaller than the tooltip', () => {
    expect(placeChartTooltip({ x: 30, y: 20 }, { width: 120, height: 70 }, { width: 160, height: 80 }))
      .toEqual({ left: 6, top: 6 })
  })
})

describe('market source freshness labels', () => {
  it('uses trading-day language instead of a plus sign', () => {
    const source = { available: true, as_of: '2026-07-17', lag_days: 3, lag_calendar_days: 3, lag_trading_days: 1, freshness_state: 'lagged' as const }
    expect(formatSourceFreshness(source)).toContain('滞后1个交易日')
    expect(formatSourceFreshness(source)).not.toContain('+')
    expect(sourceFreshnessTone(source)).toBe('lagged')
  })

  it('distinguishes current, unavailable and invalid sources', () => {
    expect(formatSourceFreshness({ available: true, as_of: '2026-07-20', lag_trading_days: 0, freshness_state: 'current' })).toContain('已同步')
    expect(formatSourceFreshness({ available: false, freshness_state: 'unavailable' })).toBe('来源不可用')
    expect(formatSourceFreshness({ available: true, as_of: '2026-07-21', freshness_state: 'invalid' })).toContain('日期异常')
  })
})
