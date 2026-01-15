'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ComposedChart,
  Line,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { JournalResponse } from '@/lib/types/journal'
import { format, startOfWeek, startOfMonth, endOfWeek, endOfMonth } from 'date-fns'
import { Calendar, TrendingUp, TrendingDown } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface TradingCalendarProps {
  journals: JournalResponse[]
}

export function TradingCalendar({ journals }: TradingCalendarProps) {
  // Group trades by day
  const dailyData = new Map<string, { date: string; pnl: number; trades: number; wins: number; losses: number }>()

  journals.forEach(journal => {
    const date = format(new Date(journal.trade_date || journal.created_at), 'yyyy-MM-dd')
    const existing = dailyData.get(date) || { date, pnl: 0, trades: 0, wins: 0, losses: 0 }

    existing.pnl += journal.pnl_amount || 0
    existing.trades++
    if (journal.pnl_amount && journal.pnl_amount > 0) existing.wins++
    if (journal.pnl_amount && journal.pnl_amount < 0) existing.losses++

    dailyData.set(date, existing)
  })

  const sortedDailyData = Array.from(dailyData.values())
    .sort((a, b) => a.date.localeCompare(b.date))
    .map(d => ({
      ...d,
      date: format(new Date(d.date), 'MMM dd'),
      pnl: parseFloat(d.pnl.toFixed(2)),
      winRate: d.trades > 0 ? (d.wins / d.trades) * 100 : 0,
    }))

  // Group trades by week
  const weeklyData = new Map<string, { week: string; pnl: number; trades: number; wins: number; losses: number }>()

  journals.forEach(journal => {
    const date = new Date(journal.trade_date || journal.created_at)
    const weekStart = startOfWeek(date, { weekStartsOn: 1 })
    const weekKey = format(weekStart, 'yyyy-MM-dd')
    const existing = weeklyData.get(weekKey) || {
      week: format(weekStart, 'MMM dd'),
      pnl: 0,
      trades: 0,
      wins: 0,
      losses: 0,
    }

    existing.pnl += journal.pnl_amount || 0
    existing.trades++
    if (journal.pnl_amount && journal.pnl_amount > 0) existing.wins++
    if (journal.pnl_amount && journal.pnl_amount < 0) existing.losses++

    weeklyData.set(weekKey, existing)
  })

  const sortedWeeklyData = Array.from(weeklyData.values())
    .sort((a, b) => a.week.localeCompare(b.week))
    .map(d => ({
      ...d,
      pnl: parseFloat(d.pnl.toFixed(2)),
      avgPnl: parseFloat((d.pnl / d.trades).toFixed(2)),
      winRate: d.trades > 0 ? (d.wins / d.trades) * 100 : 0,
    }))

  // Group trades by month
  const monthlyData = new Map<string, { month: string; pnl: number; trades: number; wins: number; losses: number }>()

  journals.forEach(journal => {
    const date = new Date(journal.trade_date || journal.created_at)
    const monthKey = format(date, 'yyyy-MM')
    const existing = monthlyData.get(monthKey) || {
      month: format(date, 'MMM yyyy'),
      pnl: 0,
      trades: 0,
      wins: 0,
      losses: 0,
    }

    existing.pnl += journal.pnl_amount || 0
    existing.trades++
    if (journal.pnl_amount && journal.pnl_amount > 0) existing.wins++
    if (journal.pnl_amount && journal.pnl_amount < 0) existing.losses++

    monthlyData.set(monthKey, existing)
  })

  const sortedMonthlyData = Array.from(monthlyData.values())
    .sort((a, b) => a.month.localeCompare(b.month))
    .map(d => ({
      ...d,
      pnl: parseFloat(d.pnl.toFixed(2)),
      avgPnl: parseFloat((d.pnl / d.trades).toFixed(2)),
      winRate: d.trades > 0 ? (d.wins / d.trades) * 100 : 0,
    }))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-semibold">{label}</p>
          <p className="text-sm">
            P&L:
            <span className={`font-mono ml-1 ${payload[0].value >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${payload[0].value.toLocaleString()}
            </span>
          </p>
          <p className="text-sm">Trades: {payload[0].payload.trades}</p>
          <p className="text-sm">Win Rate: {payload[0].payload.winRate.toFixed(1)}%</p>
        </div>
      )
    }
    return null
  }

  const renderChart = (data: any[], timeframe: string) => (
    <ResponsiveContainer width="100%" height={350}>
      <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey={timeframe === 'daily' ? 'date' : timeframe === 'weekly' ? 'week' : 'month'}
          className="text-xs"
          tick={{ fill: 'currentColor' }}
        />
        <YAxis
          yAxisId="left"
          className="text-xs"
          tick={{ fill: 'currentColor' }}
          tickFormatter={(value) => `$${value}`}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          className="text-xs"
          tick={{ fill: 'currentColor' }}
          tickFormatter={(value) => `${value}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar yAxisId="left" dataKey="pnl" name="P&L">
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'}
            />
          ))}
        </Bar>
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="winRate"
          name="Win Rate %"
          stroke="#8b5cf6"
          strokeWidth={2}
          dot={{ fill: '#8b5cf6' }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          Trading Performance Timeline
        </CardTitle>
        <CardDescription>Your trading performance over different time periods</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="daily" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="daily">Daily</TabsTrigger>
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
          </TabsList>

          <TabsContent value="daily">
            {sortedDailyData.length > 0 ? (
              renderChart(sortedDailyData.slice(-30), 'daily') // Show last 30 days
            ) : (
              <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                <p>No daily data available</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="weekly">
            {sortedWeeklyData.length > 0 ? (
              renderChart(sortedWeeklyData.slice(-12), 'weekly') // Show last 12 weeks
            ) : (
              <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                <p>No weekly data available</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="monthly">
            {sortedMonthlyData.length > 0 ? (
              renderChart(sortedMonthlyData, 'monthly')
            ) : (
              <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                <p>No monthly data available</p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Summary Statistics */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Best Day</p>
            <p className="text-lg font-semibold text-green-500">
              ${Math.max(...sortedDailyData.map(d => d.pnl), 0).toFixed(2)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Worst Day</p>
            <p className="text-lg font-semibold text-red-500">
              ${Math.min(...sortedDailyData.map(d => d.pnl), 0).toFixed(2)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Avg Daily P&L</p>
            <p className="text-lg font-semibold">
              ${sortedDailyData.length > 0
                ? (sortedDailyData.reduce((sum, d) => sum + d.pnl, 0) / sortedDailyData.length).toFixed(2)
                : '0.00'
              }
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}