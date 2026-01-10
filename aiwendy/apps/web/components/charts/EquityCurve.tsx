'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { JournalResponse } from '@/lib/types/journal'
import { format } from 'date-fns'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'

interface EquityCurveProps {
  journals: JournalResponse[]
  initialBalance?: number
}

export function EquityCurve({ journals, initialBalance = 10000 }: EquityCurveProps) {
  // Calculate cumulative P&L
  const sortedJournals = [...journals].sort((a, b) => {
    const dateA = new Date(a.trade_date || a.created_at)
    const dateB = new Date(b.trade_date || b.created_at)
    return dateA.getTime() - dateB.getTime()
  })

  let cumulativePnL = 0
  let balance = initialBalance
  let maxDrawdown = 0
  let peak = initialBalance

  const data = sortedJournals.map((journal, index) => {
    const pnl = journal.pnl_amount || 0
    cumulativePnL += pnl
    balance += pnl

    // Calculate drawdown
    if (balance > peak) {
      peak = balance
    }
    const drawdown = ((peak - balance) / peak) * 100
    maxDrawdown = Math.max(maxDrawdown, drawdown)

    return {
      date: format(new Date(journal.trade_date || journal.created_at), 'MMM dd'),
      balance: parseFloat(balance.toFixed(2)),
      pnl: parseFloat(cumulativePnL.toFixed(2)),
      trade: journal.symbol,
      drawdown: parseFloat(drawdown.toFixed(2)),
      index: index + 1,
    }
  })

  // Add initial balance point
  if (data.length > 0) {
    data.unshift({
      date: 'Start',
      balance: initialBalance,
      pnl: 0,
      trade: '',
      drawdown: 0,
      index: 0,
    })
  }

  const finalBalance = data[data.length - 1]?.balance || initialBalance
  const totalReturn = ((finalBalance - initialBalance) / initialBalance) * 100
  const isProfit = finalBalance >= initialBalance

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-semibold">{label}</p>
          <p className="text-sm">
            Balance: <span className="font-mono">${payload[0].value.toLocaleString()}</span>
          </p>
          {payload[0].payload.trade && (
            <p className="text-sm text-muted-foreground">
              Trade: {payload[0].payload.trade}
            </p>
          )}
          <p className="text-sm">
            Drawdown: <span className="text-red-500">{payload[0].payload.drawdown}%</span>
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Equity Curve</CardTitle>
            <CardDescription>Your trading account balance over time</CardDescription>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2">
              {isProfit ? (
                <TrendingUp className="h-5 w-5 text-green-500" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-500" />
              )}
              <span className={`text-2xl font-bold ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                {totalReturn > 0 ? '+' : ''}{totalReturn.toFixed(2)}%
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Max Drawdown: {maxDrawdown.toFixed(2)}%
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {data.length > 1 ? (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isProfit ? "#10b981" : "#ef4444"} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={isProfit ? "#10b981" : "#ef4444"} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tick={{ fill: 'currentColor' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'currentColor' }}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={initialBalance}
                stroke="currentColor"
                strokeDasharray="3 3"
                opacity={0.5}
                label="Initial"
              />
              <Area
                type="monotone"
                dataKey="balance"
                stroke={isProfit ? "#10b981" : "#ef4444"}
                strokeWidth={2}
                fill="url(#colorBalance)"
                animationDuration={1000}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[400px] text-muted-foreground">
            <div className="text-center">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No trading data available</p>
              <p className="text-sm">Start journaling your trades to see the equity curve</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}