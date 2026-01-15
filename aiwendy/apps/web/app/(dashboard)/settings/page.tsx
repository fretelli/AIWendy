"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Icons } from "@/components/icons"
import { toast } from "@/hooks/use-toast"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth-context"
import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"

interface APIKeysData {
  openai_api_key: string | null
  anthropic_api_key: string | null
  has_openai: boolean
  has_anthropic: boolean
}

export default function SettingsPage() {
  const router = useRouter()
  const { t } = useI18n()
  const { user, isLoading: authLoading } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [apiKeys, setApiKeys] = useState<APIKeysData>({
    openai_api_key: null,
    anthropic_api_key: null,
    has_openai: false,
    has_anthropic: false,
  })
  const [newKeys, setNewKeys] = useState({
    openai_api_key: "",
    anthropic_api_key: "",
  })
  const [showOpenAIKey, setShowOpenAIKey] = useState(false)
  const [showAnthropicKey, setShowAnthropicKey] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.push("/auth/login")
      return
    }
    fetchAPIKeys()
  }, [authLoading, router, user])

  const fetchAPIKeys = async () => {
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/users/me/api-keys`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      })

      if (!response.ok) {
        throw new Error("Failed to fetch API keys")
      }

      const data = await response.json()
      setApiKeys(data)
    } catch (error) {
      console.error("Failed to fetch API keys:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: t("settings.page.toasts.loadError"),
      })
    } finally {
      setLoading(false)
    }
  }

  const updateAPIKeys = async () => {
    setSaving(true)
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/users/me/api-keys`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          openai_api_key: newKeys.openai_api_key || null,
          anthropic_api_key: newKeys.anthropic_api_key || null,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Failed to update API keys")
      }

      toast({
        title: t("common.success"),
        description: t("settings.page.toasts.updateSuccess"),
      })

      // Clear input fields
      setNewKeys({
        openai_api_key: "",
        anthropic_api_key: "",
      })

      // Refresh API keys display
      fetchAPIKeys()
    } catch (error: any) {
      console.error("Failed to update API keys:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || t("settings.page.toasts.updateError"),
      })
    } finally {
      setSaving(false)
    }
  }

  const deleteAPIKey = async (provider: string) => {
    const providerLabel = provider === "openai" ? "OpenAI" : "Anthropic"
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/users/me/api-keys/${provider}`, {
        method: "DELETE",
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to delete ${provider} API key`)
      }

      toast({
        title: t("common.success"),
        description: t("settings.page.toasts.deleteSuccess", { provider: providerLabel }),
      })

      // Refresh API keys display
      fetchAPIKeys()
    } catch (error) {
      console.error(`Failed to delete ${provider} API key:`, error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: t("settings.page.toasts.deleteError", { provider: providerLabel }),
      })
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Icons.spinner className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t('settings.title')}</h1>
        <p className="text-muted-foreground mt-2">
          {t('settings.page.subtitle')}
        </p>
      </div>

      <Tabs defaultValue="api-keys" className="space-y-4">
        <TabsList>
          <TabsTrigger value="api-keys">{t('settings.page.tabs.apiKeys')}</TabsTrigger>
          <TabsTrigger value="exchanges" onClick={() => router.push('/settings/exchanges')}>
            Exchanges
          </TabsTrigger>
          <TabsTrigger value="profile">{t('settings.page.tabs.profile')}</TabsTrigger>
          <TabsTrigger value="preferences">{t('settings.page.tabs.preferences')}</TabsTrigger>
          <TabsTrigger value="llm" onClick={() => router.push('/settings/llm')}>
            {t('settings.page.tabs.llm')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.page.apiKeys.title')}</CardTitle>
              <CardDescription>
                {t('settings.page.apiKeys.description')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Alert>
                <Icons.alertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>{t('settings.page.apiKeys.byokTitle')} </strong>
                  {t('settings.page.apiKeys.byokDescription')}
                </AlertDescription>
              </Alert>

              {/* OpenAI API Key */}
              <div className="space-y-2">
                <Label htmlFor="openai-key">{t('settings.page.apiKeys.openai')}</Label>
                {apiKeys.has_openai ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={apiKeys.openai_api_key || ""}
                      disabled
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteAPIKey("openai")}
                    >
                      {t('settings.page.apiKeys.remove')}
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Input
                      id="openai-key"
                      type={showOpenAIKey ? "text" : "password"}
                      placeholder="sk-..."
                      value={newKeys.openai_api_key}
                      onChange={(e) => setNewKeys({ ...newKeys, openai_api_key: e.target.value })}
                      className="font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                    >
                      {showOpenAIKey ? t('settings.page.apiKeys.hide') : t('settings.page.apiKeys.show')}
                    </Button>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  {t('settings.page.apiKeys.getOpenai')}{" "}
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {t('settings.page.apiKeys.openaiDashboard')}
                  </a>
                </p>
              </div>

              {/* Anthropic API Key */}
              <div className="space-y-2">
                <Label htmlFor="anthropic-key">{t('settings.page.apiKeys.anthropic')}</Label>
                {apiKeys.has_anthropic ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={apiKeys.anthropic_api_key || ""}
                      disabled
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteAPIKey("anthropic")}
                    >
                      {t('settings.page.apiKeys.remove')}
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Input
                      id="anthropic-key"
                      type={showAnthropicKey ? "text" : "password"}
                      placeholder="sk-ant-..."
                      value={newKeys.anthropic_api_key}
                      onChange={(e) => setNewKeys({ ...newKeys, anthropic_api_key: e.target.value })}
                      className="font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                    >
                      {showAnthropicKey ? t('settings.page.apiKeys.hide') : t('settings.page.apiKeys.show')}
                    </Button>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  {t('settings.page.apiKeys.getAnthropic')}{" "}
                  <a
                    href="https://console.anthropic.com/account/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {t('settings.page.apiKeys.anthropicConsole')}
                  </a>
                </p>
              </div>

              {/* Save button */}
              {(newKeys.openai_api_key || newKeys.anthropic_api_key) && (
                <div className="flex justify-end">
                  <Button onClick={updateAPIKeys} disabled={saving}>
                    {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
                    {t('settings.page.apiKeys.save')}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('settings.page.apiKeys.statusTitle')}</CardTitle>
              <CardDescription>
                {t('settings.page.apiKeys.statusDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">OpenAI</span>
                  <span className={apiKeys.has_openai ? "text-green-600" : "text-muted-foreground"}>
                    {apiKeys.has_openai ? t('settings.page.apiKeys.configured') : t('settings.page.apiKeys.notConfigured')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium">Anthropic</span>
                  <span className={apiKeys.has_anthropic ? "text-green-600" : "text-muted-foreground"}>
                    {apiKeys.has_anthropic ? t('settings.page.apiKeys.configured') : t('settings.page.apiKeys.notConfigured')}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.page.profile.title')}</CardTitle>
              <CardDescription>
                {t('settings.page.profile.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={user?.email || ""} disabled />
                </div>
                <div className="space-y-2">
                  <Label>{t('settings.page.profile.subscription')}</Label>
                  <Input value="free" disabled />
                </div>
                <p className="text-sm text-muted-foreground">
                  {t('settings.page.profile.comingSoon')}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.page.preferences.title')}</CardTitle>
              <CardDescription>
                {t('settings.page.preferences.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {t('settings.page.preferences.comingSoon')}
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
