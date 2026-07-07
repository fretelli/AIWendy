'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/lib/i18n/provider'

export default function ForgotPasswordPage() {
  const { t } = useI18n()

  return (
    <div className="container flex h-screen w-screen flex-col items-center justify-center">
      <Link
        href="/auth/login"
        className="absolute left-4 top-4 md:left-8 md:top-8"
      >
        <Icons.chevronLeft className="mr-2 h-4 w-4 inline" />
        {t('landing.auth.forgot.backToLogin')}
      </Link>

      <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('landing.auth.forgot.title')}</CardTitle>
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
    </div>
  )
}
