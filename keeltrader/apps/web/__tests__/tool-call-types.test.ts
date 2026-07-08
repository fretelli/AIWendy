import {
  getNumber,
  getString,
  isBacktestData,
  isOrderData,
  isPendingConfirmationResult,
  isPnLData,
  isPositionData,
} from '@/components/v2/tool-call-types'

describe('tool-call type guards', () => {
  it('reads primitive values with stable fallbacks', () => {
    expect(getString('SPY')).toBe('SPY')
    expect(getString(42, 'fallback')).toBe('fallback')
    expect(getNumber(42)).toBe(42)
    expect(getNumber('42', 0)).toBe(0)
  })

  it('validates position payloads', () => {
    expect(
      isPositionData({
        exchange: 'binance',
        symbol: 'BTCUSDT',
        side: 'long',
        size: 1,
        entry_price: 100,
        mark_price: 110,
        unrealized_pnl: 10,
        leverage: 2,
      })
    ).toBe(true)

    expect(isPositionData({ symbol: 'BTCUSDT' })).toBe(false)
  })

  it('validates PnL payloads', () => {
    expect(
      isPnLData({
        period: 'today',
        total_pnl: 12.5,
        wins: 2,
        losses: 1,
        trade_count: 3,
        daily_pnl: [{ date: '2026-01-01', pnl: 12.5 }],
      })
    ).toBe(true)

    expect(
      isPnLData({
        period: 'today',
        total_pnl: 12.5,
        wins: 2,
        losses: 1,
        trade_count: 3,
        daily_pnl: [{ date: '2026-01-01', pnl: '12.5' }],
      })
    ).toBe(false)
  })

  it('validates backtest payloads', () => {
    expect(
      isBacktestData({
        symbol: 'SPY',
        strategy: 'sma_cross',
        period_days: 90,
        stats: {
          total_trades: 10,
          wins: 6,
          losses: 4,
          win_rate: 60,
          total_return_pct: 3.2,
          avg_win_pct: 1.1,
          avg_loss_pct: -0.6,
          max_drawdown_pct: 2.4,
          profit_factor: 1.8,
          sharpe_ratio: 1.2,
        },
        equity_curve: [0, 1, 2],
      })
    ).toBe(true)

    expect(
      isBacktestData({
        symbol: 'SPY',
        strategy: 'sma_cross',
        period_days: 90,
        stats: { total_trades: 10 },
      })
    ).toBe(false)
  })

  it('validates pending confirmation orders', () => {
    const payload = {
      status: 'pending_confirmation',
      message: 'Confirm?',
      order: {
        symbol: 'ETHUSDT',
        side: 'buy',
        amount: 1,
        order_type: 'market',
      },
    }

    expect(isPendingConfirmationResult(payload)).toBe(true)
    expect(isOrderData(payload.order)).toBe(true)
    expect(isOrderData({ symbol: 'ETHUSDT', side: 'buy' })).toBe(false)
  })
})
