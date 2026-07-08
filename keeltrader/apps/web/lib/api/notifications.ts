/**
 * Notification API client
 */

import { apiFetch, apiJson } from "@/lib/api/client"
import type { JsonValue } from "@/lib/types/json"

export interface Notification {
  id: string
  type: string
  title: string
  body: string
  channel: string
  priority: string
  is_read: boolean
  is_sent: boolean
  sent_at: string | null
  read_at: string | null
  created_at: string
  data?: JsonValue
}

export interface DeviceToken {
  token: string
  platform: "ios" | "android" | "web"
  device_name?: string
}

export const notificationApi = {
  async getNotifications(unreadOnly: boolean = false): Promise<Notification[]> {
    return apiJson<Notification[]>(`/notifications?unread_only=${unreadOnly}`)
  },

  async markAsRead(notificationId: string): Promise<void> {
    const response = await apiFetch(`/notifications/${notificationId}/read`, {
      method: "POST",
    })

    if (!response.ok) {
      throw new Error("Failed to mark notification as read")
    }
  },

  async registerDeviceToken(deviceToken: DeviceToken): Promise<void> {
    const response = await apiFetch("/notifications/device-tokens", {
      method: "POST",
      body: deviceToken,
    })

    if (!response.ok) {
      throw new Error("Failed to register device token")
    }
  },

  async unregisterDeviceToken(token: string): Promise<void> {
    const response = await apiFetch(`/notifications/device-tokens/${token}`, {
      method: "DELETE",
    })

    if (!response.ok) {
      throw new Error("Failed to unregister device token")
    }
  },
}
