'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Icons } from '@/components/icons'
import { useAuth } from '@/lib/auth-context'
import { useI18n } from '@/components/language-provider'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const router = useRouter()
  const { register, login } = useAuth()
  const { t } = useI18n()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (password !== confirmPassword) {
      setError(t('auth.register.validation.passwordMismatch'))
      return
    }

    if (password.length < 8) {
      setError(t('auth.register.validation.passwordTooShort'))
      return
    }

    if (!agreeToTerms) {
      setError(t('auth.register.validation.mustAgree'))
      return
    }

    setIsLoading(true)

    try {
      await register(email, password, fullName)
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || t('auth.register.error'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSignup = async () => {
    setError(null)
    setIsLoading(true)

    try {
      // TODO: Implement Google OAuth
      console.log('Google signup not yet implemented')
    } catch (err: any) {
      setError(err.message || 'Failed to sign up with Google.')
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
            <CardTitle className="text-2xl text-center">{t('auth.register.title')}</CardTitle>
            <CardDescription className="text-center">
              {t('auth.register.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {error && (
              <Alert className="alert-error">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-6">
              <Button
                variant="outline"
                onClick={handleGoogleSignup}
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
                  <Label htmlFor="fullName">{t('auth.register.fullName')}</Label>
                  <Input
                    id="fullName"
                    placeholder="John Doe"
                    type="text"
                    autoCapitalize="words"
                    autoComplete="name"
                    autoCorrect="off"
                    disabled={isLoading}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
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
                    autoComplete="new-password"
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-1">
                  <Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    disabled={isLoading}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="terms"
                    checked={agreeToTerms}
                    onCheckedChange={(checked) => setAgreeToTerms(!!checked)}
                    disabled={isLoading}
                  />
                  <label
                    htmlFor="terms"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    {t('auth.register.termsPrefix')}{' '}
                    <Link
                      href="/terms"
                      className="underline underline-offset-4 hover:text-primary"
                    >
                      {t('auth.register.termsLink')}
                    </Link>
                  </label>
                </div>
                <Button disabled={isLoading || !agreeToTerms} type="submit" className="w-full">
                  {isLoading && (
                    <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {t('auth.register.submit')}
                </Button>
              </div>
            </form>
          </CardContent>
          <CardFooter>
            <div className="text-sm text-muted-foreground text-center w-full">
              {t('auth.register.hasAccount')}{' '}
              <Link
                href="/auth/login"
                className="underline underline-offset-4 hover:text-primary"
              >
                {t('auth.login.submit')}
              </Link>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
