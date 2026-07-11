'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/lib/i18n/provider'
import { AuthShell } from '@/components/auth-shell'

export default function ForgotPasswordPage() {
  const { t } = useI18n()

  return (
    <AuthShell>
      <Link
        href="/auth/login"
        className="mb-5 inline-flex text-sm text-muted-foreground hover:text-foreground"
      >
        <Icons.chevronLeft className="mr-2 h-4 w-4 inline" />
        {t('landing.auth.forgot.backToLogin')}
      </Link>

      <div className="flex w-full flex-col justify-center space-y-6">
        <Card className="border-border/70 bg-card/90 shadow-[0_18px_60px_hsl(var(--deep-sounding)/.10)]">
          <CardHeader className="space-y-1">
            <CardTitle className="font-display text-center text-3xl">{t('landing.auth.forgot.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('landing.auth.forgot.unavailable.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Alert>
              <Icons.mail className="h-4 w-4" />
              <AlertDescription>
                {t('landing.auth.forgot.unavailable.body')}
              </AlertDescription>
            </Alert>
            <Link href="/auth/login">
              <Button variant="outline" className="w-full">
                {t('landing.auth.forgot.backToLogin')}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </AuthShell>
  )
}
