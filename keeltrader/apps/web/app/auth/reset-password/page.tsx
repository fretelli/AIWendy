'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/components/language-provider'

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)

  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useI18n()

  useEffect(() => {
    const tokenParam = searchParams?.get('token')
    if (!tokenParam) {
      setError(t('auth.reset.missingToken'))
    } else {
      setToken(tokenParam)
    }
  }, [searchParams, t])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError(t('auth.reset.passwordMismatch'))
      return
    }

    if (password.length < 8) {
      setError(t('auth.reset.passwordTooShort'))
      return
    }

    if (!token) {
      setError(t('auth.reset.missingToken'))
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token,
          new_password: password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || t('auth.reset.error'))
      }

      setIsSuccess(true)

      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/auth/login')
      }, 3000)
    } catch (err: any) {
      setError(err.message || t('auth.reset.error'))
    } finally {
      setIsLoading(false)
    }
  }

  if (isSuccess) {
    return (
      <div className="container flex h-screen w-screen flex-col items-center justify-center">
        <Card className="sm:w-[450px]">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.reset.success.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.reset.success.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Alert>
              <Icons.check className="h-4 w-4" />
              <AlertDescription>
                {t('auth.reset.success.body')}
              </AlertDescription>
            </Alert>
            <Link href="/auth/login">
              <Button className="w-full">
                {t('auth.reset.success.goToLogin')}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!token) {
    return (
      <div className="container flex h-screen w-screen flex-col items-center justify-center">
        <Card className="sm:w-[450px]">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.reset.invalidTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Alert className="alert-error">
              <AlertDescription>{error || t('auth.reset.missingToken')}</AlertDescription>
            </Alert>
            <Link href="/auth/forgot-password">
              <Button variant="outline" className="w-full">
                {t('auth.reset.requestNew')}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container flex h-screen w-screen flex-col items-center justify-center">
      <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.reset.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.reset.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {error && (
              <Alert className="alert-error">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="password">{t('auth.reset.newPassword')}</Label>
                  <Input
                    id="password"
                    type="password"
                    autoCapitalize="none"
                    autoCorrect="off"
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="confirm-password">{t('auth.reset.confirmPassword')}</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    autoCapitalize="none"
                    autoCorrect="off"
                    disabled={isLoading}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </div>
                <Button disabled={isLoading} type="submit" className="w-full">
                  {isLoading && (
                    <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {t('auth.reset.submit')}
                </Button>
              </div>
            </form>

            <div className="text-center">
              <Link href="/auth/login" className="text-sm text-muted-foreground hover:text-primary">
                {t('auth.reset.backToLogin')}
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
