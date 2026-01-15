"use client"

import * as React from "react"

import {
  defaultLanguage,
  isLanguage,
  type Language,
  type MessageKey,
  translate,
} from "@/lib/i18n"

type I18nContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  t: (key: MessageKey, vars?: Record<string, string | number>) => string
}

const I18nContext = React.createContext<I18nContextValue | null>(null)

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const value = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1]
  return value ? decodeURIComponent(value) : null
}

export function LanguageProvider({
  children,
  initialLanguage,
}: {
  children: React.ReactNode
  initialLanguage?: Language
}) {
  const [language, setLanguage] = React.useState<Language>(
    initialLanguage ?? defaultLanguage
  )

  React.useEffect(() => {
    if (initialLanguage) return

    const fromStorage =
      typeof window !== "undefined"
        ? window.localStorage.getItem("keeltrader_lang")
        : null
    if (fromStorage && isLanguage(fromStorage)) {
      setLanguage(fromStorage)
      return
    }

    const fromCookie = readCookie("keeltrader_lang")
    if (fromCookie && isLanguage(fromCookie)) {
      setLanguage(fromCookie)
    }
  }, [initialLanguage])

  React.useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.lang = language
    document.cookie = `keeltrader_lang=${encodeURIComponent(
      language
    )}; Path=/; Max-Age=31536000; SameSite=Lax`
    try {
      window.localStorage.setItem("keeltrader_lang", language)
    } catch {
      // ignore
    }
  }, [language])

  const t = React.useCallback(
    (key: MessageKey, vars?: Record<string, string | number>) =>
      translate(language, key, vars),
    [language]
  )

  const value = React.useMemo<I18nContextValue>(
    () => ({ language, setLanguage, t }),
    [language, t]
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = React.useContext(I18nContext)
  if (!context) {
    throw new Error("useI18n must be used within <LanguageProvider />")
  }
  return context
}

