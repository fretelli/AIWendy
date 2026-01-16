/**
 * Notification API client
 */

import { API_V1_PREFIX } from "@/lib/config"

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
  data?: any
}

export interface DeviceToken {
  token: string
  platform: "ios" | "android" | "web"
  device_name?: string
}

export const notificationApi = {
  async getNotifications(unreadOnly: boolean = false): Promise<Notification[]> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(
      `${API_V1_PREFIX}/notifications?unread_only=${unreadOnly}`,
      {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      }
    )

    if (!response.ok) {
      throw new Error("Failed to fetch notifications")
    }

    return response.json()
  },

  async markAsRead(notificationId: string): Promise<void> {
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

    if (!response.ok) {
      throw new Error("Failed to mark notification as read")
    }
  },

  async registerDeviceToken(deviceToken: DeviceToken): Promise<void> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(`${API_V1_PREFIX}/notifications/device-tokens`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify(deviceToken),
    })

    if (!response.ok) {
      throw new Error("Failed to register device token")
    }
  },

  async unregisterDeviceToken(token: string): Promise<void> {
    const authToken = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(
      `${API_V1_PREFIX}/notifications/device-tokens/${token}`,
      {
        method: "DELETE",
        headers: {
          Authorization: authToken ? `Bearer ${authToken}` : "",
        },
      }
    )

    if (!response.ok) {
      throw new Error("Failed to unregister device token")
    }
  },
}
