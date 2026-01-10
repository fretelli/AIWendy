"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Calendar, Clock, FileText, TrendingUp, TrendingDown,
  ChevronRight, Download, Mail, Settings, BarChart3,
  CalendarDays, CalendarRange, RefreshCw, AlertCircle
} from "lucide-react"
import { toast } from "sonner"
import { format, parseISO } from "date-fns"
import { zhCN } from "date-fns/locale"
import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"
import { useActiveProjectId } from "@/lib/active-project"
import { tasksAPI } from "@/lib/api/tasks"

interface Report {
  id: string
  report_type: string
  title: string
  subtitle?: string
  period_start: string
  period_end: string
  summary?: string
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate?: number
  total_pnl: number
  avg_pnl?: number
  status: string
  created_at: string
}

interface ReportSchedule {
  daily_enabled: boolean
  daily_time: string
  weekly_enabled: boolean
  weekly_day: number
  weekly_time: string
  monthly_enabled: boolean
  monthly_day: number
  monthly_time: string
}

const reportTypeNames: Record<string, string> = {
  daily: "日报",
  weekly: "周报",
  monthly: "月报"
}

const reportTypeIcons: Record<string, any> = {
  daily: Calendar,
  weekly: CalendarDays,
  monthly: CalendarRange
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  generating: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  sent: "bg-purple-100 text-purple-800"
}

const statusNames: Record<string, string> = {
  pending: "待生成",
  generating: "生成中",
  completed: "已完成",
  failed: "失败",
  sent: "已发送"
}

export default function ReportsPage() {
  const router = useRouter()
  const { t, locale } = useI18n()
  const { projectId, ready } = useActiveProjectId()
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string>("all")
  const [schedule, setSchedule] = useState<ReportSchedule | null>(null)

  useEffect(() => {
    if (!ready) return
    fetchReports()
    fetchSchedule()
  }, [ready, projectId])

  const fetchReports = async () => {
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const params = new URLSearchParams({ limit: "30" })
      if (projectId) params.set("project_id", projectId)

      const response = await fetch(`${API_V1_PREFIX}/reports?${params.toString()}`, {
        headers: {
          "Authorization": token ? `Bearer ${token}` : ""
        }
      })

      if (!response.ok) {
        throw new Error("Failed to fetch reports")
      }

      const data = await response.json()
      setReports(data)
    } catch (error) {
      console.error("Error fetching reports:", error)
      toast.error(locale === 'zh' ? "无法加载报告列表" : "Failed to load reports")
    } finally {
      setLoading(false)
    }
  }

  const fetchSchedule = async () => {
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/reports/schedule/current`, {
        headers: {
          "Authorization": token ? `Bearer ${token}` : ""
        }
      })

      if (!response.ok) {
        throw new Error("Failed to fetch schedule")
      }

      const data = await response.json()
      setSchedule(data)
    } catch (error) {
      console.error("Error fetching schedule:", error)
    }
  }

  const generateReport = async (reportType: string) => {
    setGenerating(reportType)
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const params = new URLSearchParams()
      if (projectId) params.set("project_id", projectId)

      const endpoint =
        reportType === "daily"
          ? "generate-daily"
          : reportType === "weekly"
            ? "generate-weekly"
            : "generate-monthly"

      const url = params.toString()
        ? `${API_V1_PREFIX}/tasks/reports/${endpoint}?${params.toString()}`
        : `${API_V1_PREFIX}/tasks/reports/${endpoint}`

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Authorization": token ? `Bearer ${token}` : ""
        }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        const detail = typeof data?.detail === "string" ? data.detail : "Failed to queue report task"
        throw new Error(detail)
      }

      const queued = await response.json()
      if (!queued?.task_id) {
        throw new Error(locale === "zh" ? "任务返回缺少 task_id" : "Missing task_id")
      }

      toast.info(locale === "zh" ? "已加入队列，生成中…" : "Queued, generating…")
      const result = await tasksAPI.waitForCompletion(queued.task_id, {
        timeoutMs: 8 * 60 * 1000,
      })

      const reportId = result?.report_id
      if (!reportId) {
        throw new Error(result?.error || (locale === "zh" ? "生成失败" : "Generation failed"))
      }

      toast.success(`${reportTypeNames[reportType]}生成成功`)

      await fetchReports()
      router.push(`/reports/${reportId}`)
    } catch (error) {
      console.error("Error generating report:", error)
      toast.error(
        locale === "zh"
          ? `生成${reportTypeNames[reportType]}失败：${(error as any)?.message || ""}`
          : `Failed to generate ${reportType}: ${(error as any)?.message || ""}`
      )
    } finally {
      setGenerating(null)
    }
  }

  const viewReport = (reportId: string) => {
    router.push(`/reports/${reportId}`)
  }

  const filteredReports = selectedType === "all"
    ? reports
    : reports.filter(report => report.report_type === selectedType)

  const getRecentReports = (type: string) => {
    return reports
      .filter(r => r.report_type === type)
      .slice(0, 1)[0]
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">{t('reports.title')}</h1>
            <p className="text-muted-foreground">
              {locale === 'zh' ? '查看和生成您的交易分析报告' : 'View and generate your trading analysis reports'}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => router.push("/reports/schedule")}
          >
            <Settings className="w-4 h-4 mr-2" />
            {locale === 'zh' ? '定时设置' : 'Schedule Settings'}
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-primary" />
                  <CardTitle>日报</CardTitle>
                </div>
                <Button
                  size="sm"
                  disabled={generating === "daily"}
                  onClick={() => generateReport("daily")}
                >
                  {generating === "daily" ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      生成中
                    </>
                  ) : (
                    <>
                      <BarChart3 className="w-4 h-4 mr-2" />
                      生成
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {getRecentReports("daily") ? (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">最新报告</p>
                  <p className="font-medium">
                    {format(parseISO(getRecentReports("daily").created_at), "MM月dd日", { locale: zhCN })}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">暂无日报</p>
              )}
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CalendarDays className="w-5 h-5 text-primary" />
                  <CardTitle>周报</CardTitle>
                </div>
                <Button
                  size="sm"
                  disabled={generating === "weekly"}
                  onClick={() => generateReport("weekly")}
                >
                  {generating === "weekly" ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      生成中
                    </>
                  ) : (
                    <>
                      <BarChart3 className="w-4 h-4 mr-2" />
                      生成
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {getRecentReports("weekly") ? (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">最新报告</p>
                  <p className="font-medium">
                    第{new Date(getRecentReports("weekly").period_start).getWeek()}周
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">暂无周报</p>
              )}
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CalendarRange className="w-5 h-5 text-primary" />
                  <CardTitle>月报</CardTitle>
                </div>
                <Button
                  size="sm"
                  disabled={generating === "monthly"}
                  onClick={() => generateReport("monthly")}
                >
                  {generating === "monthly" ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      生成中
                    </>
                  ) : (
                    <>
                      <BarChart3 className="w-4 h-4 mr-2" />
                      生成
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {getRecentReports("monthly") ? (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">最新报告</p>
                  <p className="font-medium">
                    {format(parseISO(getRecentReports("monthly").period_start), "yyyy年MM月", { locale: zhCN })}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">暂无月报</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Report List */}
        <Tabs value={selectedType} onValueChange={setSelectedType}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="all">全部</TabsTrigger>
            <TabsTrigger value="daily">日报</TabsTrigger>
            <TabsTrigger value="weekly">周报</TabsTrigger>
            <TabsTrigger value="monthly">月报</TabsTrigger>
          </TabsList>

          <TabsContent value={selectedType} className="mt-6 space-y-4">
            {filteredReports.length > 0 ? (
              filteredReports.map((report) => {
                const IconComponent = reportTypeIcons[report.report_type] || FileText
                return (
                  <Card
                    key={report.id}
                    className="hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => viewReport(report.id)}
                  >
                    <CardContent className="flex items-center justify-between p-6">
                      <div className="flex items-start gap-4">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <IconComponent className="w-6 h-6 text-primary" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-lg">{report.title}</h3>
                            <Badge className={statusColors[report.status]}>
                              {statusNames[report.status]}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            {report.subtitle}
                          </p>
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1">
                              <FileText className="w-4 h-4" />
                              {report.total_trades} 笔交易
                            </div>
                            <div className="flex items-center gap-1">
                              {report.total_pnl >= 0 ? (
                                <TrendingUp className="w-4 h-4 text-green-600" />
                              ) : (
                                <TrendingDown className="w-4 h-4 text-red-600" />
                              )}
                              <span className={report.total_pnl >= 0 ? "text-green-600" : "text-red-600"}>
                                {report.total_pnl >= 0 ? "+" : ""}{report.total_pnl.toFixed(2)}
                              </span>
                            </div>
                            {report.win_rate && (
                              <div>
                                胜率 {report.win_rate.toFixed(1)}%
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <p className="text-sm text-muted-foreground">
                          {format(parseISO(report.created_at), "yyyy-MM-dd HH:mm", { locale: zhCN })}
                        </p>
                        <ChevronRight className="w-5 h-5 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>
                )
              })
            ) : (
              <Card className="text-center py-12">
                <CardContent>
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground mb-4">
                    暂无{selectedType === "all" ? "" : reportTypeNames[selectedType]}报告
                  </p>
                  <Button
                    onClick={() => {
                      if (selectedType === "all") {
                        generateReport("daily")
                      } else {
                        generateReport(selectedType)
                      }
                    }}
                  >
                    生成第一份报告
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

// Extension to Date prototype for week number
declare global {
  interface Date {
    getWeek(): number
  }
}

Date.prototype.getWeek = function() {
  const d = new Date(Date.UTC(this.getFullYear(), this.getMonth(), this.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1))
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1)/7)
}
