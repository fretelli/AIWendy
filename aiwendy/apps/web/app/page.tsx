"use client"

import Link from "next/link"
import { Brain, MessageCircle, Shield, TrendingUp } from "lucide-react"

import { useI18n } from "@/components/language-provider"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export default function HomePage() {
  const { t } = useI18n()

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            {t("home.hero.title")}
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            {t("home.hero.subtitle")}
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/dashboard">
              <Button size="lg" variant="secondary" className="px-8">
                {t("home.hero.cta.tryDemo")}
              </Button>
            </Link>
            <Link href="/auth/register">
              <Button size="lg" className="px-8">
                {t("home.hero.cta.startFree")}
              </Button>
            </Link>
            <Link href="/auth/login">
              <Button size="lg" variant="outline" className="px-8">
                {t("home.hero.cta.signIn")}
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          {t("home.features.title")}
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <MessageCircle className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("home.features.realtime.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("home.features.realtime.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Brain className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("home.features.patterns.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("home.features.patterns.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <TrendingUp className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("home.features.review.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("home.features.review.desc")}</CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Shield className="w-10 h-10 text-primary mb-2" />
              <CardTitle>{t("home.features.risk.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{t("home.features.risk.desc")}</CardDescription>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container mx-auto px-4 py-20">
        <div className="text-center bg-primary/10 rounded-2xl p-12">
          <h2 className="text-3xl font-bold mb-4">{t("home.cta.title")}</h2>
          <p className="text-xl text-muted-foreground mb-8">
            {t("home.cta.subtitle")}
          </p>
          <Link href="/auth/register">
            <Button size="lg" className="px-12">
              {t("home.cta.button")}
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}

