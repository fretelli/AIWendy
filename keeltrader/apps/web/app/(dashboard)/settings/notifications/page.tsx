"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Icons } from "@/components/icons"
import { toast } from "@/hooks/use-toast"
import { useAuth } from "@/lib/auth-context"
import { API_V1_PREFIX } from "@/lib/config"

interface NotificationPreferences {
  push_notifications: boolean
  email_notifications: boolean
  email_daily_summary: boolean
  email_weekly_report: boolean
  sms_alerts: boolean
}

export default function NotificationsSettingsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    push_notifications: true,
    email_notifications: true,
    email_daily_summary: false,
    email_weekly_report: true,
    sms_alerts: false,
  })

  useEffect(() => {
    if (user) {
      loadPreferences()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const loadPreferences = async () => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(`${API_V1_PREFIX}/users/me`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      })

      if (!response.ok) throw new Error("Failed to load preferences")

      const data = await response.json()
      if (data.notification_preferences) {
        setPreferences(data.notification_preferences)
      }
    } catch (error) {
      console.error("Failed to load preferences:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load notification preferences",
      })
    } finally {
      setLoading(false)
    }
  }

  const savePreferences = async () => {
    setSaving(true)
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(`${API_V1_PREFIX}/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          notification_preferences: preferences,
        }),
      })

      if (!response.ok) throw new Error("Failed to save preferences")

      toast({
        title: "Success",
        description: "Notification preferences saved",
      })
    } catch (error) {
      console.error("Failed to save preferences:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to save notification preferences",
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Icons.spinner className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Notification Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure how you receive alerts and updates
        </p>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Push Notifications</CardTitle>
            <CardDescription>
              Receive real-time alerts on your device
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="push-notifications" className="flex-1">
                Enable push notifications
              </Label>
              <Switch
                id="push-notifications"
                checked={preferences.push_notifications}
                onCheckedChange={(checked) =>
                  setPreferences({ ...preferences, push_notifications: checked })
                }
              />
            </div>
            <p className="text-sm text-muted-foreground">
              Get instant alerts for pattern detection, risk warnings, and trading reminders
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Email Notifications</CardTitle>
            <CardDescription>
              Receive updates via email
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="email-notifications" className="flex-1">
                Enable email notifications
              </Label>
              <Switch
                id="email-notifications"
                checked={preferences.email_notifications}
                onCheckedChange={(checked) =>
                  setPreferences({ ...preferences, email_notifications: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="email-daily-summary" className="flex-1">
                Daily trading summary
              </Label>
              <Switch
                id="email-daily-summary"
                checked={preferences.email_daily_summary}
                onCheckedChange={(checked) =>
                  setPreferences({ ...preferences, email_daily_summary: checked })
                }
                disabled={!preferences.email_notifications}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="email-weekly-report" className="flex-1">
                Weekly performance report
              </Label>
              <Switch
                id="email-weekly-report"
                checked={preferences.email_weekly_report}
                onCheckedChange={(checked) =>
                  setPreferences({ ...preferences, email_weekly_report: checked })
                }
                disabled={!preferences.email_notifications}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>SMS Alerts</CardTitle>
            <CardDescription>
              Receive urgent alerts via SMS
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="sms-alerts" className="flex-1">
                Enable SMS alerts
              </Label>
              <Switch
                id="sms-alerts"
                checked={preferences.sms_alerts}
                onCheckedChange={(checked) =>
                  setPreferences({ ...preferences, sms_alerts: checked })
                }
              />
            </div>
            <p className="text-sm text-muted-foreground">
              Only for critical risk alerts and daily loss limit warnings
            </p>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={savePreferences} disabled={saving}>
            {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  )
}
