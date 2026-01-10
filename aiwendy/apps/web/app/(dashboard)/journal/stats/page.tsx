"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Target,
  Award,
  AlertTriangle,
  Brain,
  BarChart3,
  Calendar
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { journalApi } from "@/lib/api/journal"
import { JournalStatistics } from "@/lib/types/journal"
import { useToast } from "@/hooks/use-toast"
import { JournalResponse } from "@/lib/types/journal"
import { EquityCurve } from "@/components/charts/EquityCurve"
import { PnLDistribution } from "@/components/charts/PnLDistribution"
import { TradingCalendar } from "@/components/charts/TradingCalendar"
import { PsychologyMetrics } from "@/components/charts/PsychologyMetrics"
import { KLineChart } from "@/components/charts/KLineChart"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LineChart as ChartIcon, CandlestickChart } from "lucide-react"

export default function JournalStatsPage() {
  const { toast } = useToast()
  const [stats, setStats] = useState<JournalStatistics | null>(null)
  const [journals, setJournals] = useState<JournalResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzingPatterns, setAnalyzingPatterns] = useState(false)
  const [generatingPlan, setGeneratingPlan] = useState(false)
  const [patternAnalysis, setPatternAnalysis] = useState<any>(null)
  const [improvementPlan, setImprovementPlan] = useState<any>(null)
  const [selectedSymbol, setSelectedSymbol] = useState<string>('SPY')

  useEffect(() => {
    fetchStatistics()
  }, [])

  const fetchStatistics = async () => {
    try {
      setLoading(true)

      // Fetch statistics
      const statsData = await journalApi.getStatistics()
      setStats(statsData)

      // Fetch journal entries for charts
      const journalsData = await journalApi.list({ per_page: 100 })
      setJournals(journalsData.items)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load statistics",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const analyzePatterns = async () => {
    try {
      setAnalyzingPatterns(true)
      const analysis = await journalApi.analyzePatterns(20)
      setPatternAnalysis(analysis)
      toast({
        title: "Pattern Analysis Complete",
        description: "AI has analyzed your recent trading patterns"
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to analyze patterns",
        variant: "destructive"
      })
    } finally {
      setAnalyzingPatterns(false)
    }
  }

  const generateImprovementPlan = async () => {
    try {
      setGeneratingPlan(true)
      const plan = await journalApi.generateImprovementPlan()
      setImprovementPlan(plan)
      toast({
        title: "Improvement Plan Generated",
        description: "Your personalized 30-day plan is ready"
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to generate improvement plan",
        variant: "destructive"
      })
    } finally {
      setGeneratingPlan(false)
    }
  }

  const formatCurrency = (value?: number) => {
    if (!value) return "$0.00"
    const absValue = Math.abs(value)
    const formatted = absValue.toFixed(2)
    return value >= 0 ? `$${formatted}` : `-$${formatted}`
  }

  const formatPercentage = (value?: number) => {
    if (!value) return "0%"
    return `${value.toFixed(1)}%`
  }

  if (loading) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-10">
        <div className="text-center">Loading statistics...</div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-10">
        <div className="text-center">No statistics available</div>
      </div>
    )
  }

  const winRateColor = stats.win_rate >= 50 ? "text-green-500" : "text-red-500"
  const pnlColor = stats.total_pnl >= 0 ? "text-green-500" : "text-red-500"
  const streakColor = stats.current_streak >= 0 ? "text-green-500" : "text-red-500"

  return (
    <div className="container mx-auto max-w-7xl px-4 py-10 space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Link href="/journal">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Journal
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">Trading Statistics</h1>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={analyzePatterns}
            disabled={analyzingPatterns}
          >
            <Brain className="mr-2 h-4 w-4" />
            {analyzingPatterns ? "Analyzing..." : "Analyze Patterns"}
          </Button>
          <Button
            variant="outline"
            onClick={generateImprovementPlan}
            disabled={generatingPlan}
          >
            <Target className="mr-2 h-4 w-4" />
            {generatingPlan ? "Generating..." : "Get Improvement Plan"}
          </Button>
          <Link href="/journal/new">
            <Button>New Entry</Button>
          </Link>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${pnlColor}`}>
              {formatCurrency(stats.total_pnl)}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.total_trades} trades total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${winRateColor}`}>
              {formatPercentage(stats.win_rate)}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.winning_trades}W / {stats.losing_trades}L
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.profit_factor?.toFixed(2) || "0.00"}
            </div>
            <p className="text-xs text-muted-foreground">
              Risk/Reward Ratio
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Streak</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${streakColor}`}>
              {stats.current_streak > 0 ? `+${stats.current_streak}` : stats.current_streak}
            </div>
            <p className="text-xs text-muted-foreground">
              Best: {stats.best_streak} | Worst: {stats.worst_streak}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Trade Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" />
              Trade Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Average Win</span>
                <span className="font-medium text-green-500">
                  {formatCurrency(stats.average_win)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Average Loss</span>
                <span className="font-medium text-red-500">
                  {formatCurrency(Math.abs(stats.average_loss))}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Best Trade</span>
                <span className="font-medium text-green-600">
                  {formatCurrency(stats.best_trade)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Worst Trade</span>
                <span className="font-medium text-red-600">
                  {formatCurrency(stats.worst_trade)}
                </span>
              </div>
            </div>

            <div className="pt-4 border-t">
              <h4 className="text-sm font-medium mb-3">Trade Distribution</h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Winning ({stats.winning_trades})</span>
                    <span>{formatPercentage(stats.win_rate)}</span>
                  </div>
                  <Progress value={stats.win_rate} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Losing ({stats.losing_trades})</span>
                    <span>{formatPercentage((stats.losing_trades / stats.total_trades) * 100)}</span>
                  </div>
                  <Progress
                    value={(stats.losing_trades / stats.total_trades) * 100}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Breakeven ({stats.breakeven_trades})</span>
                    <span>{formatPercentage((stats.breakeven_trades / stats.total_trades) * 100)}</span>
                  </div>
                  <Progress
                    value={(stats.breakeven_trades / stats.total_trades) * 100}
                    className="h-2"
                  />
                </div>
                {stats.open_trades > 0 && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Open ({stats.open_trades})</span>
                      <span>{formatPercentage((stats.open_trades / stats.total_trades) * 100)}</span>
                    </div>
                    <Progress
                      value={(stats.open_trades / stats.total_trades) * 100}
                      className="h-2"
                    />
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Psychology Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Average Confidence</span>
                  <span className="text-sm font-medium">
                    {stats.average_confidence?.toFixed(1) || 0}/5
                  </span>
                </div>
                <Progress
                  value={(stats.average_confidence || 0) * 20}
                  className="h-2"
                />
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Average Stress</span>
                  <span className="text-sm font-medium">
                    {stats.average_stress?.toFixed(1) || 0}/5
                  </span>
                </div>
                <Progress
                  value={(stats.average_stress || 0) * 20}
                  className="h-2"
                />
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Rule Violation Rate</span>
                  <span className="text-sm font-medium text-red-500">
                    {formatPercentage(stats.rule_violation_rate)}
                  </span>
                </div>
                <Progress
                  value={stats.rule_violation_rate}
                  className="h-2"
                />
              </div>
            </div>

            <div className="pt-4 border-t">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <h4 className="text-sm font-medium">Trading Discipline</h4>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">
                    {Math.round((1 - stats.rule_violation_rate / 100) * stats.total_trades)}
                  </p>
                  <p className="text-xs text-green-700">Rules Followed</p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-600">
                    {Math.round((stats.rule_violation_rate / 100) * stats.total_trades)}
                  </p>
                  <p className="text-xs text-red-700">Rules Violated</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Performance Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {stats.win_rate < 50 && (
              <div className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-yellow-900">Win Rate Below 50%</p>
                  <p className="text-sm text-yellow-700">
                    Consider reviewing your entry criteria and risk management strategy.
                  </p>
                </div>
              </div>
            )}

            {stats.rule_violation_rate > 30 && (
              <div className="flex items-start gap-2 p-3 bg-red-50 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-900">High Rule Violation Rate</p>
                  <p className="text-sm text-red-700">
                    Focus on discipline and following your trading plan consistently.
                  </p>
                </div>
              </div>
            )}

            {stats.average_stress > 3.5 && (
              <div className="flex items-start gap-2 p-3 bg-orange-50 rounded-lg">
                <Brain className="h-5 w-5 text-orange-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-orange-900">Elevated Stress Levels</p>
                  <p className="text-sm text-orange-700">
                    Consider reducing position sizes or taking a break to reset mentally.
                  </p>
                </div>
              </div>
            )}

            {stats.profit_factor > 1.5 && stats.win_rate >= 50 && (
              <div className="flex items-start gap-2 p-3 bg-green-50 rounded-lg">
                <TrendingUp className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-900">Strong Performance</p>
                  <p className="text-sm text-green-700">
                    Your trading is showing positive results. Maintain your discipline and strategy.
                  </p>
                </div>
              </div>
            )}

            {stats.current_streak < -3 && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg">
                <Activity className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900">Losing Streak Alert</p>
                  <p className="text-sm text-blue-700">
                    Take time to review recent trades and identify any patterns or emotional factors.
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Charts Section */}
      {journals.length > 0 && (
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="charts">Charts</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="distribution">Distribution</TabsTrigger>
            <TabsTrigger value="psychology">Psychology</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <EquityCurve journals={journals} initialBalance={10000} />
            <TradingCalendar journals={journals} />
          </TabsContent>

          <TabsContent value="charts" className="space-y-6">
            <KLineChart
              journals={journals}
              symbol={selectedSymbol}
              onSymbolChange={setSelectedSymbol}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <EquityCurve journals={journals} initialBalance={10000} />
              <PnLDistribution journals={journals} />
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            <TradingCalendar journals={journals} />
            <PnLDistribution journals={journals} />
          </TabsContent>

          <TabsContent value="distribution" className="space-y-6">
            <PnLDistribution journals={journals} />
            <EquityCurve journals={journals} initialBalance={10000} />
          </TabsContent>

          <TabsContent value="psychology" className="space-y-6">
            <PsychologyMetrics journals={journals} />
          </TabsContent>
        </Tabs>
      )}

      {/* Pattern Analysis Card */}
      {patternAnalysis && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Pattern Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {patternAnalysis.patterns && patternAnalysis.patterns.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Recurring Patterns</h4>
                <ul className="space-y-1">
                  {patternAnalysis.patterns.map((pattern: string, idx: number) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-start">
                      <span className="mr-2">•</span>
                      <span>{pattern}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {patternAnalysis.strengths && (
              <div>
                <h4 className="font-semibold mb-2">Strengths</h4>
                <p className="text-sm text-muted-foreground">{patternAnalysis.strengths}</p>
              </div>
            )}

            {patternAnalysis.weaknesses && (
              <div>
                <h4 className="font-semibold mb-2">Critical Weaknesses</h4>
                <p className="text-sm text-muted-foreground">{patternAnalysis.weaknesses}</p>
              </div>
            )}

            {patternAnalysis.focus_areas && patternAnalysis.focus_areas.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Focus Areas</h4>
                <ul className="space-y-1">
                  {patternAnalysis.focus_areas.map((area: string, idx: number) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-start">
                      <span className="mr-2">•</span>
                      <span>{area}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Improvement Plan Card */}
      {improvementPlan && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              30-Day Improvement Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {improvementPlan.week1_goals && (
              <div>
                <h4 className="font-semibold mb-2">Week 1 Goals</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {improvementPlan.week1_goals}
                </p>
              </div>
            )}

            {improvementPlan.daily_routines && (
              <div>
                <h4 className="font-semibold mb-2">Daily Routines</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {improvementPlan.daily_routines}
                </p>
              </div>
            )}

            {improvementPlan.mental_exercises && (
              <div>
                <h4 className="font-semibold mb-2">Mental Game Exercises</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {improvementPlan.mental_exercises}
                </p>
              </div>
            )}

            {improvementPlan.risk_rules && (
              <div>
                <h4 className="font-semibold mb-2">Risk Management Rules</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {improvementPlan.risk_rules}
                </p>
              </div>
            )}

            {improvementPlan.success_metrics && improvementPlan.success_metrics.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Success Metrics</h4>
                <ul className="space-y-1">
                  {improvementPlan.success_metrics.map((metric: string, idx: number) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-start">
                      <span className="mr-2">•</span>
                      <span>{metric}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {improvementPlan.plan && (
              <div className="pt-4 border-t">
                <h4 className="font-semibold mb-2">Full Plan</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {improvementPlan.plan}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}