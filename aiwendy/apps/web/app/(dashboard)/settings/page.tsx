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
  const { t, locale } = useI18n()
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
        title: "Error",
        description: "Failed to load API keys. Please try again.",
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
        title: "Success",
        description: "API keys updated successfully",
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
        title: "Error",
        description: error.message || "Failed to update API keys. Please try again.",
      })
    } finally {
      setSaving(false)
    }
  }

  const deleteAPIKey = async (provider: string) => {
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
        title: "Success",
        description: `${provider} API key deleted successfully`,
      })

      // Refresh API keys display
      fetchAPIKeys()
    } catch (error) {
      console.error(`Failed to delete ${provider} API key:`, error)
      toast({
        variant: "destructive",
        title: "Error",
        description: `Failed to delete ${provider} API key. Please try again.`,
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
          {locale === 'zh' ? '管理您的账户设置和偏好' : 'Manage your account settings and preferences'}
        </p>
      </div>

      <Tabs defaultValue="api-keys" className="space-y-4">
        <TabsList>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
          <TabsTrigger value="llm" onClick={() => router.push('/settings/llm')}>
            {locale === 'zh' ? 'LLM 配置' : 'LLM Configuration'}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Keys Configuration</CardTitle>
              <CardDescription>
                Configure your own API keys to use AI features. Your keys are encrypted and stored securely.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Alert>
                <Icons.alertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Bring Your Own Keys (BYOK):</strong> You can use your own OpenAI or Anthropic API keys for AI features.
                  Your keys are encrypted before storage and never shared.
                </AlertDescription>
              </Alert>

              {/* OpenAI API Key */}
              <div className="space-y-2">
                <Label htmlFor="openai-key">OpenAI API Key</Label>
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
                      Remove
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
                      {showOpenAIKey ? "Hide" : "Show"}
                    </Button>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  Get your API key from{" "}
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    OpenAI Dashboard
                  </a>
                </p>
              </div>

              {/* Anthropic API Key */}
              <div className="space-y-2">
                <Label htmlFor="anthropic-key">Anthropic API Key</Label>
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
                      Remove
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
                      {showAnthropicKey ? "Hide" : "Show"}
                    </Button>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  Get your API key from{" "}
                  <a
                    href="https://console.anthropic.com/account/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    Anthropic Console
                  </a>
                </p>
              </div>

              {/* Save button */}
              {(newKeys.openai_api_key || newKeys.anthropic_api_key) && (
                <div className="flex justify-end">
                  <Button onClick={updateAPIKeys} disabled={saving}>
                    {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
                    Save API Keys
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Key Status</CardTitle>
              <CardDescription>
                Current status of your configured API keys
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">OpenAI</span>
                  <span className={apiKeys.has_openai ? "text-green-600" : "text-muted-foreground"}>
                    {apiKeys.has_openai ? "Configured ✓" : "Not configured"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium">Anthropic</span>
                  <span className={apiKeys.has_anthropic ? "text-green-600" : "text-muted-foreground"}>
                    {apiKeys.has_anthropic ? "Configured ✓" : "Not configured"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Profile Settings</CardTitle>
              <CardDescription>
                Manage your profile information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={user?.email || ""} disabled />
                </div>
                <div className="space-y-2">
                  <Label>Subscription</Label>
                  <Input value="free" disabled />
                </div>
                <p className="text-sm text-muted-foreground">
                  Profile editing coming soon...
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Preferences</CardTitle>
              <CardDescription>
                Manage your application preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Preferences management coming soon...
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
