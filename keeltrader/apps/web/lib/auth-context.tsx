"use client"

import * as React from "react"

type ApiErrorPayload =
  | {
      error?: {
        message?: string
      }
    }
  | {
      detail?: unknown
    }

function getErrorMessage(payload: ApiErrorPayload): string | null {
  if ("error" in payload) {
    const msg = payload.error?.message
    if (msg && typeof msg === "string") return msg
  }

  if ("detail" in payload) {
    const detail = payload.detail

    if (typeof detail === "string") return detail

    if (Array.isArray(detail)) {
      const first = detail[0]
      if (first && typeof first === "object") {
        const msg = (first as { msg?: unknown }).msg
        if (typeof msg === "string") return msg
      }
    }
  }

  return null
}

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init)
  const contentType = response.headers.get("content-type") ?? ""
  const isJson = contentType.includes("application/json")
  const payload: unknown = isJson ? await response.json().catch(() => null) : null

  if (!response.ok) {
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null
    throw new Error(message ?? response.statusText ?? "Request failed")
  }

  return payload as T
}

type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

type RegisterResponse = {
  id: string
  email: string
  full_name: string | null
  subscription_tier: string
  created_at: string
}

type User = {
  id: string
  email: string
  full_name: string | null
  subscription_tier: string
}

export function useAuth() {
  const [user, setUser] = React.useState<User | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)

  React.useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("keeltrader_access_token")

      const fetchMe = async (headers?: Record<string, string>) => {
        try {
          return await fetch("/api/proxy/v1/users/me", headers ? { headers } : undefined)
        } catch (error) {
          console.error("Auth check failed:", error)
          return null
        }
      }

      // 1) Try with token if present.
      const firstHeaders: Record<string, string> | undefined = token
        ? { Authorization: `Bearer ${token}` }
        : undefined
      const first = await fetchMe(firstHeaders)

      if (first?.ok) {
        const userData = await first.json()
        setUser(userData)
        setIsLoading(false)
        return
      }

      // 2) If token is invalid/expired, clear it and retry once without token (guest mode).
      if (token) {
        localStorage.removeItem("keeltrader_access_token")
        localStorage.removeItem("keeltrader_refresh_token")

        const second = await fetchMe(undefined)
        if (second?.ok) {
          const guestUser = await second.json()
          setUser(guestUser)
        }
      }

      setIsLoading(false)
    }

    checkAuth()
  }, [])

  const login = React.useCallback(async (email: string, password: string) => {
    const data = await fetchJson<LoginResponse>("/api/proxy/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    if (typeof window !== "undefined") {
      localStorage.setItem("keeltrader_access_token", data.access_token)
      localStorage.setItem("keeltrader_refresh_token", data.refresh_token)
    }

    try {
      const profile = await fetchJson<User>("/api/proxy/v1/users/me", {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      })
      setUser(profile)
    } catch {
      // If profile fetch fails, leave `user` as-is; caller can handle navigation.
    }

    return data
  }, [])

  const register = React.useCallback(
    async (email: string, password: string, fullName?: string) => {
      return fetchJson<RegisterResponse>("/api/proxy/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null,
        }),
      })
    },
    []
  )

  const logout = React.useCallback(() => {
    localStorage.removeItem("keeltrader_access_token")
    localStorage.removeItem("keeltrader_refresh_token")
    setUser(null)
  }, [])

  return { user, isLoading, login, register, logout }
}
