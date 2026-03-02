"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useI18n } from "@/lib/i18n/provider"

export function LanguageToggle({ className }: { className?: string }) {
  const { locale, setLocale, t } = useI18n()

  return (
    <div className={cn("fixed right-4 top-4 z-50 flex gap-2", className)}>
      <Button
        size="sm"
        variant={locale === "en" ? "default" : "outline"}
        onClick={() => setLocale("en")}
        aria-pressed={locale === "en"}
        type="button"
      >
        {t("landing.language.enShort" as any)}
      </Button>
      <Button
        size="sm"
        variant={locale === "zh" ? "default" : "outline"}
        onClick={() => setLocale("zh")}
        aria-pressed={locale === "zh"}
        type="button"
      >
        {t("landing.language.zhShort" as any)}
      </Button>
    </div>
  )
}
