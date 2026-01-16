"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Icons } from "@/components/icons"
import { toast } from "@/hooks/use-toast"
import { useAuth } from "@/lib/auth-context"
import { API_V1_PREFIX } from "@/lib/config"
import { Badge } from "@/components/ui/badge"

interface Notification {
  id: string
  type: string
  title: string
  body: string
  channel: string
  priority: string
  is_read: boolean
  created_at: string
  data?: any
}

export default function NotificationsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadOnly, setUnreadOnly] = useState(false)

  useEffect(() => {
    if (user) {
      loadNotifications()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, unreadOnly])

  const loadNotifications = async () => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(
        `${API_V1_PREFIX}/notifications?unread_only=${unreadOnly}`,
        {
          headers: {
            Authorization: token ? `Bearer ${token}` : "",
          },
        }
      )

      if (!response.ok) throw new Error("Failed to load notifications")

      const data = await response.json()
      setNotifications(data)
    } catch (error) {
      console.error("Failed to load notifications:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load notifications",
      })
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (notificationId: string) => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(
        `${API_V1_PREFIX}/notifications/${notificationId}/read`,
        {
          method: "POST",
          headers: {
            Authorization: token ? `Bearer ${token}` : "",
          },
        }
      )

      if (!response.ok) throw new Error("Failed to mark as read")

      setNotifications(
        notifications.map((n) =>
          n.id === notificationId ? { ...n, is_read: true } : n
        )
      )
    } catch (error) {
      console.error("Failed to mark as read:", error)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "bg-red-500"
      case "high":
        return "bg-orange-500"
      case "normal":
        return "bg-blue-500"
      case "low":
        return "bg-gray-500"
      default:
        return "bg-gray-500"
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "pattern_detected":
        return <Icons.alertTriangle className="h-5 w-5" />
      case "risk_alert":
        return <Icons.alertCircle className="h-5 w-5" />
      case "daily_summary":
        return <Icons.barChart className="h-5 w-5" />
      case "weekly_report":
        return <Icons.fileText className="h-5 w-5" />
      default:
        return <Icons.bell className="h-5 w-5" />
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
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Notifications</h1>
          <p className="text-muted-foreground mt-2">
            View your alerts and updates
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => setUnreadOnly(!unreadOnly)}
        >
          {unreadOnly ? "Show All" : "Show Unread"}
        </Button>
      </div>

      {notifications.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <Icons.bell className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              {unreadOnly ? "No unread notifications" : "No notifications yet"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <Card
              key={notification.id}
              className={notification.is_read ? "opacity-60" : ""}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="mt-1">{getTypeIcon(notification.type)}</div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <CardTitle className="text-lg">
                          {notification.title}
                        </CardTitle>
                        <Badge
                          className={getPriorityColor(notification.priority)}
                        >
                          {notification.priority}
                        </Badge>
                        {!notification.is_read && (
                          <Badge variant="secondary">New</Badge>
                        )}
                      </div>
                      <CardDescription className="mt-1">
                        {new Date(notification.created_at).toLocaleString()}
                      </CardDescription>
                    </div>
                  </div>
                  {!notification.is_read && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => markAsRead(notification.id)}
                    >
                      Mark as read
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{notification.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
