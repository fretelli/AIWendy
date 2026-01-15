"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useI18n } from "@/components/language-provider"

export function LanguageToggle({ className }: { className?: string }) {
  const { language, setLanguage, t } = useI18n()

  return (
    <div className={cn("fixed right-4 top-4 z-50 flex gap-2", className)}>
      <Button
        size="sm"
        variant={language === "en" ? "default" : "outline"}
        onClick={() => setLanguage("en")}
        aria-pressed={language === "en"}
        type="button"
      >
        {t("language.enShort")}
      </Button>
      <Button
        size="sm"
        variant={language === "zh" ? "default" : "outline"}
        onClick={() => setLanguage("zh")}
        aria-pressed={language === "zh"}
        type="button"
      >
        {t("language.zhShort")}
      </Button>
    </div>
  )
}

