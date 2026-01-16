'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useAuth } from '@/lib/auth-context'
import { useI18n } from '@/components/language-provider'

const GUEST_EMAIL = 'guest@local.keeltrader'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [guestAvailable, setGuestAvailable] = useState(false)

  const router = useRouter()
  const { login, user, isLoading: authLoading } = useAuth()
  const { t } = useI18n()

  useEffect(() => {
    if (authLoading) return
    if (user && user.email !== GUEST_EMAIL) router.push('/dashboard')
  }, [authLoading, router, user])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const response = await fetch('/api/proxy/v1/users/me')
        if (!response.ok) return
        const payload = (await response.json().catch(() => null)) as { email?: unknown } | null
        if (!cancelled) setGuestAvailable(payload?.email === GUEST_EMAIL)
      } catch {
        // ignore guest detection errors
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || t('auth.login.error'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleContinueAsGuest = () => {
    localStorage.removeItem('keeltrader_access_token')
    localStorage.removeItem('keeltrader_refresh_token')
    router.push('/dashboard')
  }

  const handleGoogleLogin = async () => {
    setError(null)
    setIsLoading(true)

    try {
      // TODO: Implement Google OAuth
      console.log('Google login not yet implemented')
    } catch (err: any) {
      setError(err.message || 'Failed to login with Google.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container flex h-screen w-screen flex-col items-center justify-center">
      <Link
        href="/"
        className="absolute left-4 top-4 md:left-8 md:top-8"
      >
        <Icons.chevronLeft className="mr-2 h-4 w-4 inline" />
        {t('auth.back')}
      </Link>

      <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t('auth.login.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.login.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {guestAvailable && (
              <Alert>
                <AlertDescription>
                  Guest mode is enabled — login is optional.
                </AlertDescription>
              </Alert>
            )}
            {error && (
              <Alert className="alert-error">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-6">
              <Button
                variant="outline"
                onClick={handleGoogleLogin}
                disabled={isLoading}
              >
                <Icons.google className="mr-2 h-4 w-4" />
                Google
              </Button>
              <Button variant="outline" disabled={isLoading}>
                <Icons.gitHub className="mr-2 h-4 w-4" />
                GitHub
              </Button>
            </div>

            {guestAvailable && (
              <Button
                variant="secondary"
                onClick={handleContinueAsGuest}
                disabled={isLoading}
              >
                Continue as Guest
              </Button>
            )}

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  {t('auth.orContinueWith')}
                </span>
              </div>
            </div>

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
                <div className="grid gap-1">
                  <Label htmlFor="password">{t('auth.password')}</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                <Button disabled={isLoading} type="submit" className="w-full">
                  {isLoading && (
                    <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {t('auth.login.submit')}
                </Button>
              </div>
            </form>
          </CardContent>
          <CardFooter>
            <div className="text-sm text-muted-foreground text-center w-full">
              <Link
                href="/auth/forgot-password"
                className="underline underline-offset-4 hover:text-primary"
              >
                {t('auth.login.forgot')}
              </Link>
              {' · '}
              <Link
                href="/auth/register"
                className="underline underline-offset-4 hover:text-primary"
              >
                {t('auth.login.noAccount')}
              </Link>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
