"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Calendar, FileText, TrendingUp, TrendingDown,
  ChevronRight, Settings, BarChart3,
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

export default function ReportsPage() {
  const router = useRouter()
  const { t, locale } = useI18n()
  const { projectId, ready } = useActiveProjectId()
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string>("all")
  const dateFnsLocale = locale === "zh" ? zhCN : undefined

  const reportTypeLabel = (type: string): string => {
    if (type === "daily") return t("reports.type.daily")
    if (type === "weekly") return t("reports.type.weekly")
    if (type === "monthly") return t("reports.type.monthly")
    return type
  }

  const statusLabel = (status: string): string => {
    if (status === "pending") return t("reports.status.pending")
    if (status === "generating") return t("reports.status.generating")
    if (status === "completed") return t("reports.status.completed")
    if (status === "failed") return t("reports.status.failed")
    if (status === "sent") return t("reports.status.sent")
    return status
  }

  useEffect(() => {
    if (!ready) return
    fetchReports()
  }, [ready, projectId])

  const fetchReports = async () => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
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
      toast.error(t("reports.errors.loadReports"))
    } finally {
      setLoading(false)
    }
  }

  const generateReport = async (reportType: string) => {
    setGenerating(reportType)
    try {
      const token = localStorage.getItem("keeltrader_access_token")
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
        const detail = typeof data?.detail === "string" ? data.detail : t("reports.errors.queueReportTask")
        throw new Error(detail)
      }

      const queued = await response.json()
      if (!queued?.task_id) {
        throw new Error(t("reports.errors.missingTaskId"))
      }

      toast.info(t("reports.toasts.queuedGenerating"))
      const result = await tasksAPI.waitForCompletion(queued.task_id, {
        timeoutMs: 8 * 60 * 1000,
      })

      const reportId = result?.report_id
      if (!reportId) {
        throw new Error(result?.error || t("reports.status.failed"))
      }

      toast.success(t("reports.toasts.generateSuccess", { type: reportTypeLabel(reportType) }))

      await fetchReports()
      router.push(`/reports/${reportId}`)
    } catch (error) {
      console.error("Error generating report:", error)
      const message = (error as any)?.message || ""
      toast.error(t("reports.toasts.generateFailed", { type: reportTypeLabel(reportType), message }))
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
              {t("reports.list.subtitle")}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => router.push("/reports/schedule")}
          >
            <Settings className="w-4 h-4 mr-2" />
            {t("reports.list.scheduleSettings")}
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-primary" />
                  <CardTitle>{reportTypeLabel("daily")}</CardTitle>
                </div>
                <Button
                  size="sm"
                  disabled={generating === "daily"}
                  onClick={() => generateReport("daily")}
                >
                  {generating === "daily" ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      {t("reports.actions.generating")}
                    </>
                  ) : (
                    <>
                      <BarChart3 className="w-4 h-4 mr-2" />
                      {t("reports.actions.generate")}
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {getRecentReports("daily") ? (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">{t("reports.list.latestReport")}</p>
                  <p className="font-medium">
                    {format(
                      parseISO(getRecentReports("daily").created_at),
                      locale === "zh" ? "MM月dd日" : "MMM dd",
                      { locale: dateFnsLocale }
                    )}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("reports.list.noDaily")}</p>
              )}
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="w-5 h-5 text-primary" />
                    <CardTitle>{reportTypeLabel("weekly")}</CardTitle>
                  </div>
                  <Button
                    size="sm"
                    disabled={generating === "weekly"}
                    onClick={() => generateReport("weekly")}
                  >
                    {generating === "weekly" ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        {t("reports.actions.generating")}
                      </>
                    ) : (
                      <>
                        <BarChart3 className="w-4 h-4 mr-2" />
                        {t("reports.actions.generate")}
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {getRecentReports("weekly") ? (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">{t("reports.list.latestReport")}</p>
                    <p className="font-medium">
                      {t("reports.list.weekOfYear", { week: new Date(getRecentReports("weekly").period_start).getWeek() })}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">{t("reports.list.noWeekly")}</p>
                )}
              </CardContent>
            </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CalendarRange className="w-5 h-5 text-primary" />
                    <CardTitle>{reportTypeLabel("monthly")}</CardTitle>
                  </div>
                  <Button
                    size="sm"
                    disabled={generating === "monthly"}
                    onClick={() => generateReport("monthly")}
                  >
                    {generating === "monthly" ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        {t("reports.actions.generating")}
                      </>
                    ) : (
                      <>
                        <BarChart3 className="w-4 h-4 mr-2" />
                        {t("reports.actions.generate")}
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {getRecentReports("monthly") ? (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">{t("reports.list.latestReport")}</p>
                    <p className="font-medium">
                      {format(
                        parseISO(getRecentReports("monthly").period_start),
                        locale === "zh" ? "yyyy年MM月" : "MMM yyyy",
                        { locale: dateFnsLocale }
                      )}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">{t("reports.list.noMonthly")}</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Report List */}
          <Tabs value={selectedType} onValueChange={setSelectedType}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="all">{t("common.all")}</TabsTrigger>
              <TabsTrigger value="daily">{reportTypeLabel("daily")}</TabsTrigger>
              <TabsTrigger value="weekly">{reportTypeLabel("weekly")}</TabsTrigger>
              <TabsTrigger value="monthly">{reportTypeLabel("monthly")}</TabsTrigger>
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
                              {statusLabel(report.status)}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            {report.subtitle}
                          </p>
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1">
                              <FileText className="w-4 h-4" />
                              {t("reports.list.tradesCount", { count: report.total_trades })}
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
                                {t("reports.detail.winRate")} {report.win_rate.toFixed(1)}%
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <p className="text-sm text-muted-foreground">
                          {format(parseISO(report.created_at), "yyyy-MM-dd HH:mm", { locale: dateFnsLocale })}
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
                    {selectedType === "all"
                      ? t("reports.list.emptyAll")
                      : t("reports.list.emptyType", { type: reportTypeLabel(selectedType) })}
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
                    {t("reports.generateFirst")}
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
