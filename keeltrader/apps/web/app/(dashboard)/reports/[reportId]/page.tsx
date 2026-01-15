"use client"

import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { toast } from "sonner"
import { format, parseISO } from "date-fns"
import { zhCN } from "date-fns/locale"
import { ArrowLeft, CalendarDays, FileText } from "lucide-react"

import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ReportDetail {
  id: string
  project_id?: string | null
  report_type: string
  title: string
  subtitle?: string | null
  period_start: string
  period_end: string
  summary?: string | null
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate?: number | null
  total_pnl: number
  avg_pnl?: number | null
  max_profit?: number | null
  max_loss?: number | null
  avg_mood_before?: number | null
  avg_mood_after?: number | null
  mood_improvement?: number | null
  top_mistakes: Array<{ mistake: string; frequency: number }>
  top_successes: string[]
  improvements: string[]
  ai_analysis?: string | null
  ai_recommendations: string[]
  key_insights: string[]
  action_items: string[]
  status: string
  created_at: string
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  generating: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  sent: "bg-purple-100 text-purple-800",
}

export default function ReportDetailPage() {
  const router = useRouter()
  const params = useParams<{ reportId: string }>()
  const { t, locale } = useI18n()
  const reportId = params?.reportId

  const [loading, setLoading] = useState(true)
  const [report, setReport] = useState<ReportDetail | null>(null)
  const dateFnsLocale = locale === "zh" ? zhCN : undefined

  const statusLabel = (status: string): string => {
    if (status === "pending") return t("reports.status.pending")
    if (status === "generating") return t("reports.status.generating")
    if (status === "completed") return t("reports.status.completed")
    if (status === "failed") return t("reports.status.failed")
    if (status === "sent") return t("reports.status.sent")
    return status
  }

  useEffect(() => {
    if (!reportId) return
    const fetchReport = async () => {
      setLoading(true)
      try {
        const token = localStorage.getItem("aiwendy_access_token")
        const response = await fetch(`${API_V1_PREFIX}/reports/${reportId}`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        })

        if (!response.ok) {
          throw new Error("Failed to fetch report")
        }

        const data = await response.json()
        setReport(data)
      } catch (error) {
        console.error("Error fetching report:", error)
        toast.error(t("reports.errors.loadReport"))
      } finally {
        setLoading(false)
      }
    }

    fetchReport()
  }, [reportId, locale])

  const createdAt = useMemo(() => {
    if (!report?.created_at) return null
    return format(parseISO(report.created_at), "yyyy-MM-dd HH:mm", {
      locale: dateFnsLocale,
    })
  }, [report?.created_at, dateFnsLocale])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card className="max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle>{t("reports.detail.notFound")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => router.push("/reports")}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t("reports.actions.backToReports")}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => router.push("/reports")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("common.back")}
        </Button>
        <Badge className={statusColors[report.status] || "bg-gray-100 text-gray-800"}>
          {statusLabel(report.status)}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                {report.title}
              </CardTitle>
              {report.subtitle ? (
                <p className="text-muted-foreground mt-1">{report.subtitle}</p>
              ) : null}
            </div>
            <div className="text-sm text-muted-foreground flex items-center gap-2">
              <CalendarDays className="w-4 h-4" />
              {createdAt || "-"}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {report.summary ? (
            <div className="text-sm leading-relaxed">{report.summary}</div>
          ) : null}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="shadow-none border">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">{t("reports.detail.trades")}</div>
                <div className="text-xl font-semibold">{report.total_trades}</div>
              </CardContent>
            </Card>
            <Card className="shadow-none border">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">{t("reports.detail.winRate")}</div>
                <div className="text-xl font-semibold">
                  {report.win_rate != null ? `${report.win_rate}%` : "-"}
                </div>
              </CardContent>
            </Card>
            <Card className="shadow-none border">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">{t("reports.detail.totalPnl")}</div>
                <div className={`text-xl font-semibold ${report.total_pnl >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {report.total_pnl}
                </div>
              </CardContent>
            </Card>
            <Card className="shadow-none border">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">{t("reports.detail.avgPnl")}</div>
                <div className="text-xl font-semibold">{report.avg_pnl != null ? report.avg_pnl : "-"}</div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("reports.detail.keyInsights")}</CardTitle>
          </CardHeader>
          <CardContent>
            {report.key_insights?.length ? (
              <ul className="list-disc pl-5 space-y-2 text-sm">
                {report.key_insights.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-muted-foreground">{t("reports.detail.none")}</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("reports.detail.actionItems")}</CardTitle>
          </CardHeader>
          <CardContent>
            {report.action_items?.length ? (
              <ul className="list-disc pl-5 space-y-2 text-sm">
                {report.action_items.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-muted-foreground">{t("reports.detail.none")}</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("reports.detail.recommendations")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {report.ai_analysis ? (
            <div className="text-sm leading-relaxed whitespace-pre-wrap">{report.ai_analysis}</div>
          ) : null}

          {report.ai_recommendations?.length ? (
            <ul className="list-disc pl-5 space-y-2 text-sm">
              {report.ai_recommendations.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          ) : report.improvements?.length ? (
            <ul className="list-disc pl-5 space-y-2 text-sm">
              {report.improvements.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-muted-foreground">{t("reports.detail.none")}</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("reports.detail.topMistakes")}</CardTitle>
        </CardHeader>
        <CardContent>
          {report.top_mistakes?.length ? (
            <div className="space-y-2 text-sm">
              {report.top_mistakes.map((m, idx) => (
                <div key={idx} className="flex items-center justify-between border rounded-md px-3 py-2">
                  <span className="font-medium">{m.mistake}</span>
                  <Badge variant="secondary">{m.frequency}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">{t("reports.detail.none")}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

