"use client"

import Link from "next/link"

import { useI18n } from "@/lib/i18n/provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AuthShell } from "@/components/auth-shell"

export default function OnboardingPage() {
  const { t } = useI18n()

  return (
    <AuthShell eyebrow="Open the research desk">
      <Card className="border-border/70 bg-card/90 shadow-[0_18px_60px_hsl(var(--deep-sounding)/.10)]">
        <CardHeader>
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--copper-foreground))]">KeelTrader onboarding</div>
          <CardTitle className="font-display text-3xl">{t("landing.app.onboarding.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <Link href="/agent">
            <Button className="w-full">{t("landing.app.onboarding.toDashboard")}</Button>
          </Link>
          <Link href="/auth/login">
            <Button className="w-full" variant="outline">{t("landing.app.onboarding.toLogin")}</Button>
          </Link>
        </CardContent>
      </Card>
    </AuthShell>
  )
}
