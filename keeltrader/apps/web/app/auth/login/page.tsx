'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useAuth } from '@/lib/auth-context'
import { getPendingInvite, savePendingInviteFromParams } from '@/lib/research-api'
import { LanguageSwitcher, useI18n } from '@/lib/i18n/provider'

function getErrorMessage(error: unknown): string | null {
  if (error instanceof Error) {
    return error.message
  }

  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = (error as { message?: unknown }).message
    return typeof message === 'string' && message.trim() ? message : null
  }

  return null
}

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [inviteNotice, setInviteNotice] = useState<{ source: string; type: string } | null>(null)

  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, user, isLoading: authLoading } = useAuth()
  const { t } = useI18n()

  useEffect(() => {
    const params = new URLSearchParams(searchParams?.toString() || '')
    const pendingInvite = savePendingInviteFromParams(params, 'auth_login', 'auth_login')
    if (pendingInvite) {
      const latestInvite = getPendingInvite()
      queueMicrotask(() => {
        setInviteNotice({
          source: String(latestInvite?.invite_code || latestInvite?.inviter_user_id || '-'),
          type: String(latestInvite?.source_type || 'auth_login'),
        })
      })
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      await login(email, password)
      const next = searchParams?.get('next')
      const destination =
        next && next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/auth')
          ? next
          : '/agentos'
      router.replace(destination)
    } catch (err: unknown) {
      setError(getErrorMessage(err) || t('landing.auth.login.error'))
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
          <LanguageSwitcher />
        </div>

        <div className="mx-auto grid w-full max-w-md gap-6">
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
                    <AlertDescription>{t('landing.auth.login.checking')}</AlertDescription>
                  </Alert>
                ) : null}
                {user ? (
                  <Alert>
                    <AlertDescription>
                      {t('landing.auth.login.alreadySignedIn')}
                    </AlertDescription>
                  </Alert>
                ) : null}
                {inviteNotice && (
                  <Alert>
                    <AlertDescription>
                      {t('landing.auth.login.inviteCaptured', inviteNotice)}
                    </AlertDescription>
                  </Alert>
                )}
                {error && (
                  <Alert className="alert-error">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

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
                {t('landing.auth.login.protectedNotice')}
              </div>
              <div className="rounded-md border p-4">
                {t('landing.auth.login.researchNotice')}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
