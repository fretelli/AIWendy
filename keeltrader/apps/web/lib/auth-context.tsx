"use client"

import * as React from "react"
import { apiFetch, apiJson } from "@/lib/api/client"
import { logClientError } from "@/lib/client-log"

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
      try {
        const userData = await apiJson<User>("/users/me")
        setUser(userData)
      } catch (error) {
        logClientError("auth.check", error)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = React.useCallback(async (email: string, password: string) => {
    const data = await apiJson<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    })

    try {
      const profile = await apiJson<User>("/users/me")
      setUser(profile)
    } catch {
      // If profile fetch fails, leave `user` as-is; caller can handle navigation.
    }

    return data
  }, [])

  const register = React.useCallback(
    async (email: string, password: string, fullName?: string) => {
      return apiJson<RegisterResponse>("/auth/register", {
        method: "POST",
        body: {
          email,
          password,
          full_name: fullName || null,
        },
      })
    },
    []
  )

  const logout = React.useCallback(async () => {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
      })
    } catch {
      // Local logout still clears browser state even if the server session is already gone.
    }

    setUser(null)
  }, [])

  return { user, isLoading, login, register, logout }
}
