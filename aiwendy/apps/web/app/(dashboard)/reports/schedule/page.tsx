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

const weekDayNamesZh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

export default function ReportSchedulePage() {
  const router = useRouter()
  const { locale } = useI18n()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [schedule, setSchedule] = useState<ReportSchedule | null>(null)

  const weekDayOptions = useMemo(() => {
    return Array.from({ length: 7 }).map((_, idx) => ({
      value: String(idx),
      label: locale === "zh" ? weekDayNamesZh[idx] : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx],
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
        toast.error(locale === "zh" ? "无法加载定时设置" : "Failed to load schedule")
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
      toast.success(locale === "zh" ? "已保存" : "Saved")
    } catch (error) {
      console.error("Error updating schedule:", error)
      toast.error(locale === "zh" ? "保存失败" : "Failed to save")
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
            <CardTitle>{locale === "zh" ? "定时设置不可用" : "Schedule unavailable"}</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => router.push("/reports")}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              {locale === "zh" ? "返回报告列表" : "Back to reports"}
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
          {locale === "zh" ? "返回" : "Back"}
        </Button>
        <Button onClick={save} disabled={saving}>
          <Save className="w-4 h-4 mr-2" />
          {saving ? (locale === "zh" ? "保存中" : "Saving") : (locale === "zh" ? "保存" : "Save")}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "zh" ? "报告定时生成" : "Report schedule"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Daily */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label className="text-base">{locale === "zh" ? "日报" : "Daily"}</Label>
              <div className="text-sm text-muted-foreground">
                {locale === "zh" ? "每天固定时间生成昨日日报" : "Generate daily report at a fixed time"}
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
                <Label className="text-base">{locale === "zh" ? "周报" : "Weekly"}</Label>
                <div className="text-sm text-muted-foreground">
                  {locale === "zh" ? "每周生成上一周周报" : "Generate weekly report"}
                </div>
              </div>
              <Switch
                checked={schedule.weekly_enabled}
                onCheckedChange={(v) => update({ weekly_enabled: v })}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{locale === "zh" ? "星期" : "Day"}</Label>
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
                <Label>{locale === "zh" ? "时间" : "Time"}</Label>
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
                <Label className="text-base">{locale === "zh" ? "月报" : "Monthly"}</Label>
                <div className="text-sm text-muted-foreground">
                  {locale === "zh" ? "每月生成上个月月报" : "Generate monthly report"}
                </div>
              </div>
              <Switch
                checked={schedule.monthly_enabled}
                onCheckedChange={(v) => update({ monthly_enabled: v })}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{locale === "zh" ? "每月第几天" : "Day of month"}</Label>
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
                <Label>{locale === "zh" ? "时间" : "Time"}</Label>
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

