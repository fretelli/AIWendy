'use client'

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { JournalResponse } from '@/lib/types/journal'
import { format } from 'date-fns'
import { Brain, Heart, AlertTriangle } from 'lucide-react'
import { Progress } from '@/components/ui/progress'

interface PsychologyMetricsProps {
  journals: JournalResponse[]
}

export function PsychologyMetrics({ journals }: PsychologyMetricsProps) {
  // Calculate average psychology metrics
  const validJournals = journals.filter(j =>
    j.emotion_before || j.emotion_during || j.emotion_after ||
    j.confidence_level || j.stress_level
  )

  if (validJournals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Psychology Metrics
          </CardTitle>
          <CardDescription>Track your emotional and psychological patterns</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <div className="text-center">
              <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No psychological data available</p>
              <p className="text-sm">Start tracking your emotions to see insights</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Prepare radar chart data
  const avgEmotionBefore = validJournals.reduce((sum, j) => sum + (j.emotion_before || 0), 0) / validJournals.length
  const avgEmotionDuring = validJournals.reduce((sum, j) => sum + (j.emotion_during || 0), 0) / validJournals.length
  const avgEmotionAfter = validJournals.reduce((sum, j) => sum + (j.emotion_after || 0), 0) / validJournals.length
  const avgConfidence = validJournals.reduce((sum, j) => sum + (j.confidence_level || 0), 0) / validJournals.length
  const avgStress = validJournals.reduce((sum, j) => sum + (j.stress_level || 0), 0) / validJournals.length

  const radarData = [
    { metric: 'Pre-Trade Emotion', value: avgEmotionBefore * 20, fullMark: 100 },
    { metric: 'During Trade', value: avgEmotionDuring * 20, fullMark: 100 },
    { metric: 'Post-Trade', value: avgEmotionAfter * 20, fullMark: 100 },
    { metric: 'Confidence', value: avgConfidence * 20, fullMark: 100 },
    { metric: 'Stress (Inverted)', value: (5 - avgStress) * 20, fullMark: 100 },
  ]

  // Prepare time series data for emotions
  const sortedJournals = [...validJournals].sort((a, b) => {
    const dateA = new Date(a.trade_date || a.created_at)
    const dateB = new Date(b.trade_date || b.created_at)
    return dateA.getTime() - dateB.getTime()
  })

  const timeSeriesData = sortedJournals.slice(-20).map(j => ({
    date: format(new Date(j.trade_date || j.created_at), 'MMM dd'),
    confidence: j.confidence_level || 0,
    stress: j.stress_level || 0,
    emotion: ((j.emotion_before || 0) + (j.emotion_during || 0) + (j.emotion_after || 0)) / 3,
  }))

  // Calculate correlations
  const profitableTradesWithHighConfidence = journals.filter(j =>
    j.pnl_amount && j.pnl_amount > 0 && j.confidence_level && j.confidence_level >= 4
  ).length

  const lossesWithHighStress = journals.filter(j =>
    j.pnl_amount && j.pnl_amount < 0 && j.stress_level && j.stress_level >= 4
  ).length

  const ruleViolationsWithLowConfidence = journals.filter(j =>
    !j.followed_rules && j.confidence_level && j.confidence_level <= 2
  ).length

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-semibold text-sm">{label}</p>
          {payload.map((entry: any) => (
            <p key={entry.name} className="text-sm">
              {entry.name}:
              <span className="font-mono ml-1">{entry.value.toFixed(1)}</span>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Psychology Radar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Psychology Profile
          </CardTitle>
          <CardDescription>Your average psychological metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid className="stroke-muted" />
                <PolarAngleAxis
                  dataKey="metric"
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <Radar
                  name="Psychology"
                  dataKey="value"
                  stroke="#8b5cf6"
                  fill="#8b5cf6"
                  fillOpacity={0.3}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>

            <div className="space-y-4">
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Confidence Level</span>
                    <span className="text-sm">{avgConfidence.toFixed(1)}/5</span>
                  </div>
                  <Progress value={avgConfidence * 20} className="h-2" />
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Stress Level</span>
                    <span className="text-sm">{avgStress.toFixed(1)}/5</span>
                  </div>
                  <Progress
                    value={avgStress * 20}
                    className="h-2"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Emotional Control</span>
                    <span className="text-sm">{avgEmotionDuring.toFixed(1)}/5</span>
                  </div>
                  <Progress value={avgEmotionDuring * 20} className="h-2" />
                </div>
              </div>

              <div className="pt-4 border-t space-y-2">
                <p className="text-xs font-semibold text-muted-foreground">Key Insights</p>
                <div className="space-y-1 text-xs">
                  <p>• {profitableTradesWithHighConfidence} profitable trades with high confidence</p>
                  <p>• {lossesWithHighStress} losses during high stress periods</p>
                  <p>• {ruleViolationsWithLowConfidence} rule violations with low confidence</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Psychology Time Series */}
      <Card>
        <CardHeader>
          <CardTitle>Psychology Trends</CardTitle>
          <CardDescription>How your psychological metrics change over time</CardDescription>
        </CardHeader>
        <CardContent>
          {timeSeriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <YAxis
                  domain={[0, 5]}
                  ticks={[0, 1, 2, 3, 4, 5]}
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="confidence"
                  name="Confidence"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: '#10b981' }}
                />
                <Line
                  type="monotone"
                  dataKey="stress"
                  name="Stress"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ fill: '#ef4444' }}
                />
                <Line
                  type="monotone"
                  dataKey="emotion"
                  name="Avg Emotion"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              <p>Not enough data for trends</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}