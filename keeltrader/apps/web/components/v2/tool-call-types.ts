export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[] | undefined
export interface JsonObject {
  [key: string]: JsonValue
}

export interface ToolCallData {
  name: string
  args: JsonObject
  result?: JsonObject
}

export interface PositionData extends JsonObject {
  exchange: string
  symbol: string
  side: string
  size: number
  entry_price: number
  mark_price: number
  unrealized_pnl: number
  leverage: number
  error?: string
}

export interface PnLDailyData extends JsonObject {
  date: string
  pnl: number
}

export interface PnLData extends JsonObject {
  period: string
  total_pnl: number
  wins: number
  losses: number
  trade_count: number
  daily_pnl: PnLDailyData[]
}

export interface BacktestStats extends JsonObject {
  total_trades: number
  wins: number
  losses: number
  win_rate: number
  total_return_pct: number
  avg_win_pct: number
  avg_loss_pct: number
  max_drawdown_pct: number
  profit_factor: number
  sharpe_ratio: number
}

export interface BacktestData extends JsonObject {
  symbol: string
  strategy: string
  params?: JsonObject
  period_days: number
  stats: BacktestStats
  equity_curve?: number[]
  trades?: JsonObject[]
}

export interface OrderData extends JsonObject {
  symbol: string
  side: string
  amount: number
  order_type: string
  price?: number
  stop_loss?: number
  take_profit?: number
  estimated_value_usd?: number
}

export interface PendingConfirmationResult extends JsonObject {
  status: 'pending_confirmation'
  order: JsonObject
  message: string
}

export function isJsonObject(value: unknown): value is JsonObject {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number'
}

function isString(value: unknown): value is string {
  return typeof value === 'string'
}

function isNumberArray(value: unknown): value is number[] {
  return Array.isArray(value) && value.every(isNumber)
}

function isObjectArray(value: unknown): value is JsonObject[] {
  return Array.isArray(value) && value.every(isJsonObject)
}

export function getString(value: unknown, fallback = ''): string {
  return isString(value) ? value : fallback
}

export function getNumber(value: unknown, fallback = 0): number {
  return isNumber(value) ? value : fallback
}

export function isPositionData(value: unknown): value is PositionData {
  if (!isJsonObject(value)) return false
  return (
    isString(value.exchange) &&
    isString(value.symbol) &&
    isString(value.side) &&
    isNumber(value.size) &&
    isNumber(value.entry_price) &&
    isNumber(value.mark_price) &&
    isNumber(value.unrealized_pnl) &&
    isNumber(value.leverage) &&
    (value.error === undefined || isString(value.error))
  )
}

export function isPnLData(value: JsonObject): value is PnLData {
  return (
    isString(value.period) &&
    isNumber(value.total_pnl) &&
    isNumber(value.wins) &&
    isNumber(value.losses) &&
    isNumber(value.trade_count) &&
    Array.isArray(value.daily_pnl) &&
    value.daily_pnl.every(item => {
      if (!isJsonObject(item)) return false
      return isString(item.date) && isNumber(item.pnl)
    })
  )
}

export function isBacktestData(value: JsonObject): value is BacktestData {
  if (!isJsonObject(value.stats)) return false
  return (
    isString(value.symbol) &&
    isString(value.strategy) &&
    isNumber(value.period_days) &&
    isNumber(value.stats.total_trades) &&
    isNumber(value.stats.wins) &&
    isNumber(value.stats.losses) &&
    isNumber(value.stats.win_rate) &&
    isNumber(value.stats.total_return_pct) &&
    isNumber(value.stats.avg_win_pct) &&
    isNumber(value.stats.avg_loss_pct) &&
    isNumber(value.stats.max_drawdown_pct) &&
    isNumber(value.stats.profit_factor) &&
    isNumber(value.stats.sharpe_ratio) &&
    (value.equity_curve === undefined || isNumberArray(value.equity_curve)) &&
    (value.trades === undefined || isObjectArray(value.trades)) &&
    (value.params === undefined || isJsonObject(value.params))
  )
}

export function isOrderData(value: unknown): value is OrderData {
  if (!isJsonObject(value)) return false
  return (
    isString(value.symbol) &&
    isString(value.side) &&
    isNumber(value.amount) &&
    isString(value.order_type) &&
    (value.price === undefined || isNumber(value.price)) &&
    (value.stop_loss === undefined || isNumber(value.stop_loss)) &&
    (value.take_profit === undefined || isNumber(value.take_profit)) &&
    (value.estimated_value_usd === undefined || isNumber(value.estimated_value_usd))
  )
}

export function isPendingConfirmationResult(
  value: JsonObject | undefined
): value is PendingConfirmationResult {
  return (
    isJsonObject(value) &&
    value.status === 'pending_confirmation' &&
    isJsonObject(value.order) &&
    isString(value.message)
  )
}
