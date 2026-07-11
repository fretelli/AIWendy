'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/lib/i18n/provider'
import { AuthShell } from '@/components/auth-shell'

export default function ResetPasswordPage() {
  const { t } = useI18n()

  return (
    <AuthShell>
      <div className="flex w-full flex-col justify-center space-y-6">
        <Card className="border-border/70 bg-card/90 shadow-[0_18px_60px_hsl(var(--deep-sounding)/.10)]">
          <CardHeader className="space-y-1">
            <CardTitle className="font-display text-center text-3xl">{t('landing.auth.reset.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('landing.auth.reset.unavailable.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Alert>
              <Icons.mail className="h-4 w-4" />
              <AlertDescription>
                {t('landing.auth.reset.unavailable.body')}
              </AlertDescription>
            </Alert>
            <Link href="/auth/login">
              <Button variant="outline" className="w-full">
                {t('landing.auth.reset.backToLogin')}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </AuthShell>
  )
}
