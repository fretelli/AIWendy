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
  ReferenceLine,
  PieChart,
  Pie,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { JournalResponse, TradeResult } from '@/lib/types/journal'
import { DollarSign, TrendingUp, TrendingDown } from 'lucide-react'

interface PnLDistributionProps {
  journals: JournalResponse[]
}

export function PnLDistribution({ journals }: PnLDistributionProps) {
  // Group trades by P&L ranges
  const pnlRanges = [
    { range: '< -$500', min: -Infinity, max: -500, count: 0, total: 0 },
    { range: '-$500 to -$200', min: -500, max: -200, count: 0, total: 0 },
    { range: '-$200 to -$100', min: -200, max: -100, count: 0, total: 0 },
    { range: '-$100 to $0', min: -100, max: 0, count: 0, total: 0 },
    { range: '$0 to $100', min: 0, max: 100, count: 0, total: 0 },
    { range: '$100 to $200', min: 100, max: 200, count: 0, total: 0 },
    { range: '$200 to $500', min: 200, max: 500, count: 0, total: 0 },
    { range: '> $500', min: 500, max: Infinity, count: 0, total: 0 },
  ]

  journals.forEach(journal => {
    const pnl = journal.pnl_amount || 0
    const range = pnlRanges.find(r => pnl >= r.min && pnl < r.max)
    if (range) {
      range.count++
      range.total += pnl
    }
  })

  const distributionData = pnlRanges
    .filter(r => r.count > 0)
    .map(r => ({
      range: r.range,
      count: r.count,
      total: parseFloat(r.total.toFixed(2)),
      avgPnL: parseFloat((r.total / r.count).toFixed(2)),
    }))

  // Calculate win/loss statistics
  const wins = journals.filter(j => j.result === TradeResult.WIN)
  const losses = journals.filter(j => j.result === TradeResult.LOSS)
  const breakeven = journals.filter(j => j.result === TradeResult.BREAKEVEN)

  const winTotal = wins.reduce((sum, j) => sum + (j.pnl_amount || 0), 0)
  const lossTotal = losses.reduce((sum, j) => sum + (j.pnl_amount || 0), 0)

  const pieData = [
    { name: 'Wins', value: wins.length, pnl: winTotal },
    { name: 'Losses', value: losses.length, pnl: lossTotal },
    { name: 'Breakeven', value: breakeven.length, pnl: 0 },
  ].filter(d => d.value > 0)

  const COLORS = {
    Wins: '#10b981',
    Losses: '#ef4444',
    Breakeven: '#6b7280',
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-semibold">{payload[0].payload.range}</p>
          <p className="text-sm">Trades: {payload[0].value}</p>
          <p className="text-sm">
            Total P&L:
            <span className={`font-mono ml-1 ${payload[0].payload.total >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${payload[0].payload.total.toLocaleString()}
            </span>
          </p>
          <p className="text-sm">
            Avg P&L:
            <span className={`font-mono ml-1 ${payload[0].payload.avgPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${payload[0].payload.avgPnL.toLocaleString()}
            </span>
          </p>
        </div>
      )
    }
    return null
  }

  const PieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-semibold">{payload[0].name}</p>
          <p className="text-sm">Count: {payload[0].value}</p>
          <p className="text-sm">
            Total P&L:
            <span className={`font-mono ml-1 ${payload[0].payload.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${payload[0].payload.pnl.toFixed(2)}
            </span>
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* P&L Distribution Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            P&L Distribution
          </CardTitle>
          <CardDescription>Distribution of profits and losses</CardDescription>
        </CardHeader>
        <CardContent>
          {distributionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={distributionData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="range"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="currentColor" opacity={0.5} />
                <Bar dataKey="count" name="Trades">
                  {distributionData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.total >= 0 ? '#10b981' : '#ef4444'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              <p>No data available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Win/Loss Pie Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Win/Loss Ratio</CardTitle>
          <CardDescription>Trade outcome distribution</CardDescription>
        </CardHeader>
        <CardContent>
          {pieData.length > 0 ? (
            <div className="space-y-4">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    animationBegin={0}
                    animationDuration={800}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>

              {/* Legend with Statistics */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span>Wins</span>
                  </div>
                  <p className="font-semibold">{wins.length}</p>
                  <p className="text-xs text-muted-foreground">
                    ${winTotal.toFixed(2)}
                  </p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span>Losses</span>
                  </div>
                  <p className="font-semibold">{losses.length}</p>
                  <p className="text-xs text-muted-foreground">
                    ${lossTotal.toFixed(2)}
                  </p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <div className="w-3 h-3 rounded-full bg-gray-500" />
                    <span>Breakeven</span>
                  </div>
                  <p className="font-semibold">{breakeven.length}</p>
                  <p className="text-xs text-muted-foreground">$0.00</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[250px] text-muted-foreground">
              <p>No data available</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}