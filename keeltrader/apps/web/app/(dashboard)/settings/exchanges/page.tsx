"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Icons } from "@/components/icons"
import { toast } from "@/hooks/use-toast"
import { useAuth } from "@/lib/auth-context"
import { useI18n } from "@/lib/i18n/provider"
import { userExchangeApi, ExchangeConnection, ExchangeType } from "@/lib/api/user-exchanges"
import { Switch } from "@/components/ui/switch"

export default function ExchangeSettingsPage() {
  const router = useRouter()
  const { t } = useI18n()
  const { user, isLoading: authLoading } = useAuth()
  const [loading, setLoading] = useState(true)
  const [connections, setConnections] = useState<ExchangeConnection[]>([])
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [editingConnection, setEditingConnection] = useState<ExchangeConnection | null>(null)
  const [testingConnection, setTestingConnection] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    exchange_type: "binance" as ExchangeType,
    name: "",
    api_key: "",
    api_secret: "",
    passphrase: "",
    is_testnet: false,
  })
  const [showApiKey, setShowApiKey] = useState(false)
  const [showApiSecret, setShowApiSecret] = useState(false)
  const [showPassphrase, setShowPassphrase] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.push("/auth/login")
      return
    }
    fetchConnections()
  }, [authLoading, router, user])

  const fetchConnections = async () => {
    try {
      const data = await userExchangeApi.getConnections()
      setConnections(data)
    } catch (error) {
      console.error("Failed to fetch connections:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: "Failed to load exchange connections",
      })
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      exchange_type: "binance",
      name: "",
      api_key: "",
      api_secret: "",
      passphrase: "",
      is_testnet: false,
    })
    setShowApiKey(false)
    setShowApiSecret(false)
    setShowPassphrase(false)
  }

  const handleAdd = async () => {
    if (!formData.api_key || !formData.api_secret) {
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: "API Key and Secret are required",
      })
      return
    }

    setSaving(true)
    try {
      const newConnection = await userExchangeApi.createConnection({
        exchange_type: formData.exchange_type,
        name: formData.name || `My ${formData.exchange_type} Account`,
        api_key: formData.api_key,
        api_secret: formData.api_secret,
        passphrase: formData.passphrase || undefined,
        is_testnet: formData.is_testnet,
      })

      setConnections([...connections, newConnection])
      setShowAddDialog(false)
      resetForm()

      toast({
        title: t("common.success"),
        description: "Exchange connection added successfully",
      })
    } catch (error: any) {
      console.error("Failed to add connection:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || "Failed to add exchange connection",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async () => {
    if (!editingConnection) return

    setSaving(true)
    try {
      const updated = await userExchangeApi.updateConnection(editingConnection.id, {
        name: formData.name || undefined,
        api_key: formData.api_key || undefined,
        api_secret: formData.api_secret || undefined,
        passphrase: formData.passphrase || undefined,
      })

      setConnections(connections.map(c => c.id === updated.id ? updated : c))
      setShowEditDialog(false)
      setEditingConnection(null)
      resetForm()

      toast({
        title: t("common.success"),
        description: "Exchange connection updated successfully",
      })
    } catch (error: any) {
      console.error("Failed to update connection:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || "Failed to update exchange connection",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (connectionId: string) => {
    if (!confirm("Are you sure you want to delete this connection?")) {
      return
    }

    try {
      await userExchangeApi.deleteConnection(connectionId)
      setConnections(connections.filter(c => c.id !== connectionId))

      toast({
        title: t("common.success"),
        description: "Exchange connection deleted successfully",
      })
    } catch (error: any) {
      console.error("Failed to delete connection:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || "Failed to delete exchange connection",
      })
    }
  }

  const handleTest = async (connectionId: string) => {
    setTestingConnection(connectionId)
    try {
      const result = await userExchangeApi.testConnection(connectionId)

      if (result.success) {
        toast({
          title: "✅ Connection Successful",
          description: result.data ?
            `Connected to ${result.data.exchange}. Found ${result.data.currencies_count} currencies.` :
            result.message,
        })

        // Refresh connections to update last_sync_at
        fetchConnections()
      } else {
        toast({
          variant: "destructive",
          title: "❌ Connection Failed",
          description: result.message,
        })
      }
    } catch (error: any) {
      console.error("Failed to test connection:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || "Failed to test connection",
      })
    } finally {
      setTestingConnection(null)
    }
  }

  const handleToggleActive = async (connection: ExchangeConnection) => {
    try {
      const updated = await userExchangeApi.updateConnection(connection.id, {
        is_active: !connection.is_active,
      })

      setConnections(connections.map(c => c.id === updated.id ? updated : c))

      toast({
        title: t("common.success"),
        description: updated.is_active ? "Connection activated" : "Connection deactivated",
      })
    } catch (error: any) {
      console.error("Failed to toggle connection:", error)
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error.message || "Failed to update connection",
      })
    }
  }

  const openEditDialog = (connection: ExchangeConnection) => {
    setEditingConnection(connection)
    setFormData({
      exchange_type: connection.exchange_type as ExchangeType,
      name: connection.name,
      api_key: "",
      api_secret: "",
      passphrase: "",
      is_testnet: connection.is_testnet,
    })
    setShowEditDialog(true)
  }

  const getExchangeIcon = (exchangeType: string) => {
    const icons: Record<string, string> = {
      binance: "🟡",
      okx: "⚫",
      bybit: "🟠",
      coinbase: "🔵",
      kraken: "🟣",
    }
    return icons[exchangeType] || "🔷"
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never"
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Icons.spinner className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Exchange Connections</h1>
          <p className="text-muted-foreground mt-2">
            Manage your cryptocurrency exchange API connections
          </p>
        </div>
        <Button onClick={() => {
          resetForm()
          setShowAddDialog(true)
        }}>
          <Icons.plus className="mr-2 h-4 w-4" />
          Add Exchange
        </Button>
      </div>

      {/* Security Alert */}
      <Alert className="mb-6">
        <Icons.alertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>Security:</strong> Only use READ-ONLY API keys. Never share keys with trading permissions.
          All credentials are encrypted in our database.
        </AlertDescription>
      </Alert>

      {/* Connections List */}
      {connections.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Icons.wallet className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No exchange connections</h3>
              <p className="text-muted-foreground mt-2">
                Add your first exchange connection to get started
              </p>
              <Button className="mt-4" onClick={() => {
                resetForm()
                setShowAddDialog(true)
              }}>
                <Icons.plus className="mr-2 h-4 w-4" />
                Add Exchange
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {connections.map((connection) => (
            <Card key={connection.id} className={!connection.is_active ? "opacity-60" : ""}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{getExchangeIcon(connection.exchange_type)}</span>
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {connection.name}
                        {connection.is_testnet && (
                          <Badge variant="outline" className="text-xs">Testnet</Badge>
                        )}
                      </CardTitle>
                      <CardDescription className="capitalize mt-1">
                        {connection.exchange_type}
                      </CardDescription>
                    </div>
                  </div>
                  <Switch
                    checked={connection.is_active}
                    onCheckedChange={() => handleToggleActive(connection)}
                  />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* API Key */}
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">API Key</Label>
                  <p className="font-mono text-sm">{connection.api_key_masked}</p>
                </div>

                {/* Last Sync */}
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Last Sync</Label>
                  <p className="text-sm">{formatDate(connection.last_sync_at)}</p>
                </div>

                {/* Error */}
                {connection.last_error && (
                  <Alert variant="destructive">
                    <Icons.alertCircle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      {connection.last_error}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTest(connection.id)}
                    disabled={testingConnection === connection.id}
                  >
                    {testingConnection === connection.id ? (
                      <Icons.spinner className="mr-2 h-3 w-3 animate-spin" />
                    ) : (
                      <Icons.check className="mr-2 h-3 w-3" />
                    )}
                    Test
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => openEditDialog(connection)}
                  >
                    <Icons.edit className="mr-2 h-3 w-3" />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDelete(connection.id)}
                  >
                    <Icons.trash className="mr-2 h-3 w-3" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Exchange Connection</DialogTitle>
            <DialogDescription>
              Connect to your cryptocurrency exchange account
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Exchange Type */}
            <div className="space-y-2">
              <Label>Exchange</Label>
              <Select
                value={formData.exchange_type}
                onValueChange={(value: ExchangeType) => setFormData({ ...formData, exchange_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="binance">🟡 Binance</SelectItem>
                  <SelectItem value="okx">⚫ OKX</SelectItem>
                  <SelectItem value="bybit">🟠 Bybit</SelectItem>
                  <SelectItem value="coinbase">🔵 Coinbase</SelectItem>
                  <SelectItem value="kraken">🟣 Kraken</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Name */}
            <div className="space-y-2">
              <Label>Name (Optional)</Label>
              <Input
                placeholder={`My ${formData.exchange_type} Account`}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            {/* API Key */}
            <div className="space-y-2">
              <Label>API Key *</Label>
              <div className="flex gap-2">
                <Input
                  type={showApiKey ? "text" : "password"}
                  placeholder="Enter your API key"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  className="font-mono"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* API Secret */}
            <div className="space-y-2">
              <Label>API Secret *</Label>
              <div className="flex gap-2">
                <Input
                  type={showApiSecret ? "text" : "password"}
                  placeholder="Enter your API secret"
                  value={formData.api_secret}
                  onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                  className="font-mono"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowApiSecret(!showApiSecret)}
                >
                  {showApiSecret ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Passphrase (for OKX) */}
            {formData.exchange_type === "okx" && (
              <div className="space-y-2">
                <Label>Passphrase</Label>
                <div className="flex gap-2">
                  <Input
                    type={showPassphrase ? "text" : "password"}
                    placeholder="Enter your passphrase"
                    value={formData.passphrase}
                    onChange={(e) => setFormData({ ...formData, passphrase: e.target.value })}
                    className="font-mono"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPassphrase(!showPassphrase)}
                  >
                    {showPassphrase ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            )}

            {/* Testnet */}
            <div className="flex items-center space-x-2">
              <Switch
                id="testnet"
                checked={formData.is_testnet}
                onCheckedChange={(checked) => setFormData({ ...formData, is_testnet: checked })}
              />
              <Label htmlFor="testnet">Use Testnet</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAdd} disabled={saving}>
              {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
              Add Connection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Exchange Connection</DialogTitle>
            <DialogDescription>
              Update your exchange connection details
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Name */}
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                placeholder={editingConnection?.name}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            {/* API Key (Optional Update) */}
            <div className="space-y-2">
              <Label>New API Key (Optional)</Label>
              <div className="flex gap-2">
                <Input
                  type={showApiKey ? "text" : "password"}
                  placeholder="Leave empty to keep current"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  className="font-mono"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* API Secret (Optional Update) */}
            <div className="space-y-2">
              <Label>New API Secret (Optional)</Label>
              <div className="flex gap-2">
                <Input
                  type={showApiSecret ? "text" : "password"}
                  placeholder="Leave empty to keep current"
                  value={formData.api_secret}
                  onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                  className="font-mono"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowApiSecret(!showApiSecret)}
                >
                  {showApiSecret ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Passphrase (for OKX) */}
            {editingConnection?.exchange_type === "okx" && (
              <div className="space-y-2">
                <Label>New Passphrase (Optional)</Label>
                <div className="flex gap-2">
                  <Input
                    type={showPassphrase ? "text" : "password"}
                    placeholder="Leave empty to keep current"
                    value={formData.passphrase}
                    onChange={(e) => setFormData({ ...formData, passphrase: e.target.value })}
                    className="font-mono"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPassphrase(!showPassphrase)}
                  >
                    {showPassphrase ? <Icons.eyeOff className="h-4 w-4" /> : <Icons.eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
              Update Connection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
