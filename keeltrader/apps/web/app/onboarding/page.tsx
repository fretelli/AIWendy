"use client"

import Link from "next/link"

import { useI18n } from "@/components/language-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function OnboardingPage() {
  const { t } = useI18n()

  return (
    <div className="container mx-auto max-w-3xl px-4 py-10 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("app.onboarding.title")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Link href="/dashboard">
            <Button>{t("app.onboarding.toDashboard")}</Button>
          </Link>
          <Link href="/auth/login">
            <Button variant="outline">{t("app.onboarding.toLogin")}</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}

