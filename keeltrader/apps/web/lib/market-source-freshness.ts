export type SourceFreshnessState = 'current' | 'lagged' | 'unavailable' | 'invalid'

export type SourceFreshnessMeta = {
  available: boolean
  as_of?: string
  lag_days?: number
  lag_calendar_days?: number
  lag_trading_days?: number
  freshness_state?: SourceFreshnessState
}

const dateLabel = (value?: string) => value
  ? new Date(`${value}T00:00:00`).toLocaleDateString('zh-CN')
  : '—'

export function formatSourceFreshness(source?: SourceFreshnessMeta): string {
  if (!source?.available) return '来源不可用'
  const date = dateLabel(source.as_of)
  if (source.freshness_state === 'invalid') return `${date} · 日期异常`
  const tradingLag = source.lag_trading_days
  const calendarLag = source.lag_calendar_days ?? source.lag_days
  if (tradingLag === 0 || (tradingLag === undefined && calendarLag === 0)) return `${date} · 已同步`
  if (typeof tradingLag === 'number' && tradingLag > 0) return `${date} · 滞后${tradingLag}个交易日`
  if (typeof calendarLag === 'number' && calendarLag > 0) return `${date} · 滞后${calendarLag}个自然日`
  return date
}

export function sourceFreshnessTitle(source?: SourceFreshnessMeta): string | undefined {
  if (!source?.available) return undefined
  const calendarLag = source.lag_calendar_days ?? source.lag_days
  if (typeof calendarLag === 'number' && calendarLag > 0) return `相对市场基准日滞后 ${calendarLag} 个自然日`
  return undefined
}

export function sourceFreshnessTone(source?: SourceFreshnessMeta): 'current' | 'lagged' | 'error' {
  if (!source?.available || source.freshness_state === 'invalid') return 'error'
  if (source.freshness_state === 'lagged' || (source.lag_trading_days ?? source.lag_calendar_days ?? source.lag_days ?? 0) > 0) return 'lagged'
  return 'current'
}
