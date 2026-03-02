"use client"

import Link from "next/link"
import { Brain, MessageCircle, Shield, TrendingUp } from "lucide-react"

import { useI18n } from "@/lib/i18n/provider"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

const authRequired = process.env.NEXT_PUBLIC_AUTH_REQUIRED === "1"

export default function HomePage() {
  const { t } = useI18n()

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            {t("landing.hero.title")}
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            {t("landing.hero.subtitle")}
          </p>
          <div className="flex gap-4 justify-center">
            {authRequired ? (
              <>
                <Link href="/dashboard">
                  <Button size="lg" variant="secondary" className="px-8">
                    {t("landing.hero.cta.tryDemo")}
                  </Button>
                </Link>
                <Link href="/auth/register">
                  <Button size="lg" className="px-8">
                    {t("landing.hero.cta.startFree")}
                  </Button>
                </Link>
                <Link href="/auth/login">
                  <Button size="lg" variant="outline" className="px-8">
                    {t("landing.hero.cta.signIn")}
                  </Button>
                </Link>
              </>
            ) : (
              <Link href="/dashboard">
                <Button size="lg" className="px-8">
                  {t("landing.hero.cta.getStarted")}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>

      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          {t("landing.features.title")}
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <MessageCircle className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("landing.features.realtime.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("landing.features.realtime.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Brain className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("landing.features.patterns.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("landing.features.patterns.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <TrendingUp className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("landing.features.review.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("landing.features.review.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Shield className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("landing.features.risk.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("landing.features.risk.desc")}</CardDescription>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container mx-auto px-4 py-20">
        <div className="text-center bg-primary/10 rounded-2xl p-12">
          <h2 className="text-3xl font-bold mb-4">{t("landing.cta.title")}</h2>
          <p className="text-xl text-muted-foreground mb-8">
            {t("landing.cta.subtitle")}
          </p>
          <Link href={authRequired ? "/auth/register" : "/dashboard"}>
            <Button size="lg" className="px-12">
              {authRequired ? t("landing.cta.button") : t("landing.hero.cta.getStarted")}
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}

