'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/components/language-provider'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const router = useRouter()
  const { t } = useI18n()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      // TODO: Implement password reset API call
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        throw new Error(t('auth.forgot.error'))
      }

      setIsSubmitted(true)
    } catch (err: any) {
      setError(err.message || t('auth.forgot.error'))
    } finally {
      setIsLoading(false)
    }
  }

  if (isSubmitted) {
    return (
      <div className="container flex h-screen w-screen flex-col items-center justify-center">
        <Card className="sm:w-[450px]">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.forgot.success.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.forgot.success.subtitle', { email })}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Alert>
              <Icons.mail className="h-4 w-4" />
              <AlertDescription>
                {t('auth.forgot.success.body', { email })}
              </AlertDescription>
            </Alert>
            <div className="text-center space-y-2">
              <p className="text-sm text-muted-foreground">
                {t('auth.forgot.success.noEmail')}
              </p>
              <Button
                variant="ghost"
                onClick={() => {
                  setIsSubmitted(false)
                  setEmail('')
                }}
              >
                {t('auth.forgot.success.tryDifferent')}
              </Button>
            </div>
            <Link href="/auth/login">
              <Button variant="outline" className="w-full">
                {t('auth.forgot.backToLogin')}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container flex h-screen w-screen flex-col items-center justify-center">
      <Link
        href="/auth/login"
        className="absolute left-4 top-4 md:left-8 md:top-8"
      >
        <Icons.chevronLeft className="mr-2 h-4 w-4 inline" />
        {t('auth.forgot.backToLogin')}
      </Link>

      <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.forgot.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.forgot.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {error && (
              <Alert className="alert-error">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <div className="grid gap-1">
                  <Label htmlFor="email">{t('auth.email')}</Label>
                  <Input
                    id="email"
                    placeholder="name@example.com"
                    type="email"
                    autoCapitalize="none"
                    autoComplete="email"
                    autoCorrect="off"
                    disabled={isLoading}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <Button disabled={isLoading} type="submit" className="w-full">
                  {isLoading && (
                    <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {t('auth.forgot.submit')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
