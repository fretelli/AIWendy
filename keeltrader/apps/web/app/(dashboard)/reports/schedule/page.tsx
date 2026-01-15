"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ArrowLeft, Save } from "lucide-react"

import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface ReportSchedule {
  daily_enabled: boolean
  daily_time: string
  weekly_enabled: boolean
  weekly_day: number
  weekly_time: string
  monthly_enabled: boolean
  monthly_day: number
  monthly_time: string
  email_notification?: boolean
  in_app_notification?: boolean
  include_ai_analysis?: boolean
  include_coach_feedback?: boolean
  include_charts?: boolean
  timezone?: string
  language?: string
  is_active?: boolean
}

export default function ReportSchedulePage() {
  const router = useRouter()
  const { t, locale } = useI18n()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [schedule, setSchedule] = useState<ReportSchedule | null>(null)

  const weekDayOptions = useMemo(() => {
    const weekDayKeys = [
      "reports.weekdays.mon",
      "reports.weekdays.tue",
      "reports.weekdays.wed",
      "reports.weekdays.thu",
      "reports.weekdays.fri",
      "reports.weekdays.sat",
      "reports.weekdays.sun",
    ] as const

    return Array.from({ length: 7 }).map((_, idx) => ({
      value: String(idx),
      label: t(weekDayKeys[idx]),
    }))
  }, [locale])

  const monthlyDayOptions = useMemo(() => {
    return Array.from({ length: 28 }).map((_, idx) => String(idx + 1))
  }, [])

  useEffect(() => {
    const fetchSchedule = async () => {
      setLoading(true)
      try {
        const token = localStorage.getItem("aiwendy_access_token")
        const res = await fetch(`${API_V1_PREFIX}/reports/schedule/current`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        })
        if (!res.ok) throw new Error("Failed to fetch schedule")
        const data = await res.json()
        setSchedule(data)
      } catch (error) {
        console.error("Error fetching schedule:", error)
        toast.error(t("reports.errors.loadSchedule"))
      } finally {
        setLoading(false)
      }
    }

    fetchSchedule()
  }, [locale])

  const update = (patch: Partial<ReportSchedule>) => {
    setSchedule((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  const save = async () => {
    if (!schedule) return
    setSaving(true)
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const res = await fetch(`${API_V1_PREFIX}/reports/schedule`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify(schedule),
      })
      if (!res.ok) throw new Error("Failed to update schedule")
      const data = await res.json()
      setSchedule(data)
      toast.success(t("reports.toasts.saved"))
    } catch (error) {
      console.error("Error updating schedule:", error)
      toast.error(t("reports.errors.saveSchedule"))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!schedule) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card className="max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle>{t("reports.schedulePage.unavailable")}</CardTitle>
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
    <div className="container mx-auto py-8 px-4 max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => router.push("/reports")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("common.back")}
        </Button>
        <Button onClick={save} disabled={saving}>
          <Save className="w-4 h-4 mr-2" />
          {saving ? t("reports.schedulePage.saving") : t("common.save")}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("reports.schedulePage.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Daily */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label className="text-base">{t("reports.type.daily")}</Label>
              <div className="text-sm text-muted-foreground">
                {t("reports.schedulePage.dailyDescription")}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="time"
                className="w-[140px]"
                value={schedule.daily_time}
                onChange={(e) => update({ daily_time: e.target.value })}
                disabled={!schedule.daily_enabled}
              />
              <Switch
                checked={schedule.daily_enabled}
                onCheckedChange={(v) => update({ daily_enabled: v })}
              />
            </div>
          </div>

          {/* Weekly */}
          <div className="flex flex-col gap-3 border-t pt-6">
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-1">
                <Label className="text-base">{t("reports.type.weekly")}</Label>
                <div className="text-sm text-muted-foreground">
                  {t("reports.schedulePage.weeklyDescription")}
                </div>
              </div>
              <Switch
                checked={schedule.weekly_enabled}
                onCheckedChange={(v) => update({ weekly_enabled: v })}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{t("reports.schedulePage.day")}</Label>
                <Select
                  value={String(schedule.weekly_day)}
                  onValueChange={(v) => update({ weekly_day: Number(v) })}
                  disabled={!schedule.weekly_enabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {weekDayOptions.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>{t("reports.schedulePage.time")}</Label>
                <Input
                  type="time"
                  value={schedule.weekly_time}
                  onChange={(e) => update({ weekly_time: e.target.value })}
                  disabled={!schedule.weekly_enabled}
                />
              </div>
            </div>
          </div>

          {/* Monthly */}
          <div className="flex flex-col gap-3 border-t pt-6">
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-1">
                <Label className="text-base">{t("reports.type.monthly")}</Label>
                <div className="text-sm text-muted-foreground">
                  {t("reports.schedulePage.monthlyDescription")}
                </div>
              </div>
              <Switch
                checked={schedule.monthly_enabled}
                onCheckedChange={(v) => update({ monthly_enabled: v })}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{t("reports.schedulePage.dayOfMonth")}</Label>
                <Select
                  value={String(schedule.monthly_day)}
                  onValueChange={(v) => update({ monthly_day: Number(v) })}
                  disabled={!schedule.monthly_enabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {monthlyDayOptions.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>{t("reports.schedulePage.time")}</Label>
                <Input
                  type="time"
                  value={schedule.monthly_time}
                  onChange={(e) => update({ monthly_time: e.target.value })}
                  disabled={!schedule.monthly_enabled}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

