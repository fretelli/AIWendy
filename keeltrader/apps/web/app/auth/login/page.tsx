'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useAuth } from '@/lib/auth-context'
import { getPendingInvite, savePendingInviteFromParams } from '@/lib/research-api'
import { useI18n } from '@/lib/i18n/provider'
import { ResearchHub } from '@/components/research/ResearchHub'

const GUEST_EMAIL = 'guest@local.keeltrader'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [guestAvailable, setGuestAvailable] = useState(false)
  const [inviteNotice, setInviteNotice] = useState<string | null>(null)

  const searchParams = useSearchParams()
  const { login, logout, user, isLoading: authLoading } = useAuth()
  const { t } = useI18n()

  useEffect(() => {
    const params = new URLSearchParams(searchParams?.toString() || '')
    const pendingInvite = savePendingInviteFromParams(params, 'auth_login', 'auth_login')
    if (pendingInvite) {
      const latestInvite = getPendingInvite()
      setInviteNotice(`已捕获邀请来源：${latestInvite?.invite_code || latestInvite?.inviter_user_id || '-'} · ${latestInvite?.source_type || 'auth_login'}`)
    }
  }, [searchParams])

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
    } catch (err: any) {
      setError(err.message || t('landing.auth.login.error'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleContinueAsGuest = () => {
    logout()
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
    <div className="min-h-screen w-full bg-background">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-6 md:px-8">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
            <Icons.chevronLeft className="mr-2 inline h-4 w-4" />
            {t('landing.auth.back')}
          </Link>
          <Button asChild variant="outline" size="sm">
            <Link href="/research">直接进入研报中心</Link>
          </Button>
        </div>

        <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="space-y-6">
            <Card>
              <CardHeader className="space-y-1">
                <CardTitle className="text-2xl text-center">{t('landing.auth.login.title')}</CardTitle>
                <CardDescription className="text-center">
                  {t('landing.auth.login.subtitle')}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                {authLoading ? (
                  <Alert>
                    <AlertDescription>正在检查账号状态...</AlertDescription>
                  </Alert>
                ) : null}
                {user && user.email !== GUEST_EMAIL ? (
                  <Alert>
                    <AlertDescription>
                      已登录，下面直接使用研报中心；也可以退出切换账号。
                    </AlertDescription>
                  </Alert>
                ) : null}
                {guestAvailable && (
                  <Alert>
                    <AlertDescription>
                      Guest mode is enabled — login is optional.
                    </AlertDescription>
                  </Alert>
                )}
                {inviteNotice && (
                  <Alert>
                    <AlertDescription>{inviteNotice}</AlertDescription>
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
                      {t('landing.auth.orContinueWith')}
                    </span>
                  </div>
                </div>

                <form onSubmit={handleSubmit}>
                  <div className="grid gap-2">
                    <div className="grid gap-1">
                      <Label htmlFor="email">{t('landing.auth.email')}</Label>
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
                      <Label htmlFor="password">{t('landing.auth.password')}</Label>
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
                      {t('landing.auth.login.submit')}
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
                    {t('landing.auth.login.forgot')}
                  </Link>
                  {' · '}
                  <Link
                    href="/auth/register"
                    className="underline underline-offset-4 hover:text-primary"
                  >
                    {t('landing.auth.login.noAccount')}
                  </Link>
                </div>
              </CardFooter>
            </Card>

            <div className="grid gap-3 text-sm text-muted-foreground">
              <div className="rounded-md border p-4">
                登录后同页就能使用研报首页、期刊、研报详情、机构图鉴、积分商城、权益、偏好和反馈。
              </div>
              <div className="rounded-md border p-4">
                积分商城许愿会写入 research 后台反馈列表，管理员能在同一处看到并处理。
              </div>
            </div>
          </div>

          <section id="research-center" className="min-w-0">
            <ResearchHub />
          </section>
        </div>
      </div>
    </div>
  )
}
