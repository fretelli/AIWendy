"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Icons } from "@/components/icons"
import { toast } from "@/hooks/use-toast"
import { useAuth } from "@/lib/auth-context"
import { API_V1_PREFIX } from "@/lib/config"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

interface Checklist {
  id: string
  name: string
  description: string
  items: ChecklistItem[]
  is_required: boolean
  is_active: boolean
}

interface ChecklistItem {
  id: string
  type: string
  question: string
  required: boolean
}

export default function InterventionSettingsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [checklists, setChecklists] = useState<Checklist[]>([])
  const [sessionSettings, setSessionSettings] = useState({
    max_daily_loss_limit: 0,
    max_trades_per_day: 0,
  })
  const [newChecklist, setNewChecklist] = useState({
    name: "",
    description: "",
    items: [] as ChecklistItem[],
    is_required: false,
  })
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  useEffect(() => {
    if (user) {
      loadChecklists()
    }
  }, [user])

  const loadChecklists = async () => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(`${API_V1_PREFIX}/intervention/checklists`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      })

      if (!response.ok) throw new Error("Failed to load checklists")

      const data = await response.json()
      setChecklists(data)
    } catch (error) {
      console.error("Failed to load checklists:", error)
    } finally {
      setLoading(false)
    }
  }

  const startSession = async () => {
    setSaving(true)
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(`${API_V1_PREFIX}/intervention/session/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          max_daily_loss_limit: sessionSettings.max_daily_loss_limit * 100, // Convert to cents
          max_trades_per_day: sessionSettings.max_trades_per_day || null,
        }),
      })

      if (!response.ok) throw new Error("Failed to start session")

      toast({
        title: "Success",
        description: "Trading session started with risk limits",
      })
    } catch (error) {
      console.error("Failed to start session:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to start trading session",
      })
    } finally {
      setSaving(false)
    }
  }

  const createChecklist = async () => {
    if (!newChecklist.name || newChecklist.items.length === 0) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Please provide a name and at least one checklist item",
      })
      return
    }

    setSaving(true)
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const response = await fetch(`${API_V1_PREFIX}/intervention/checklists`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify(newChecklist),
      })

      if (!response.ok) throw new Error("Failed to create checklist")

      toast({
        title: "Success",
        description: "Checklist created successfully",
      })

      setShowCreateDialog(false)
      setNewChecklist({
        name: "",
        description: "",
        items: [],
        is_required: false,
      })
      loadChecklists()
    } catch (error) {
      console.error("Failed to create checklist:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to create checklist",
      })
    } finally {
      setSaving(false)
    }
  }

  const addChecklistItem = () => {
    setNewChecklist({
      ...newChecklist,
      items: [
        ...newChecklist.items,
        {
          id: `item-${Date.now()}`,
          type: "risk_check",
          question: "",
          required: false,
        },
      ],
    })
  }

  const updateChecklistItem = (index: number, field: string, value: any) => {
    const updatedItems = [...newChecklist.items]
    updatedItems[index] = { ...updatedItems[index], [field]: value }
    setNewChecklist({ ...newChecklist, items: updatedItems })
  }

  const removeChecklistItem = (index: number) => {
    setNewChecklist({
      ...newChecklist,
      items: newChecklist.items.filter((_, i) => i !== index),
    })
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
        <h1 className="text-3xl font-bold">Trading Intervention Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure risk limits and pre-trade checklists
        </p>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Risk Limits</CardTitle>
            <CardDescription>
              Set daily trading limits to prevent overtrading and excessive losses
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="max-loss">Maximum Daily Loss ($)</Label>
              <Input
                id="max-loss"
                type="number"
                placeholder="500"
                value={sessionSettings.max_daily_loss_limit || ""}
                onChange={(e) =>
                  setSessionSettings({
                    ...sessionSettings,
                    max_daily_loss_limit: parseFloat(e.target.value) || 0,
                  })
                }
              />
              <p className="text-sm text-muted-foreground">
                Trading will be blocked if you reach this loss limit
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-trades">Maximum Trades Per Day</Label>
              <Input
                id="max-trades"
                type="number"
                placeholder="10"
                value={sessionSettings.max_trades_per_day || ""}
                onChange={(e) =>
                  setSessionSettings({
                    ...sessionSettings,
                    max_trades_per_day: parseInt(e.target.value) || 0,
                  })
                }
              />
              <p className="text-sm text-muted-foreground">
                Prevents overtrading by limiting daily trade count
              </p>
            </div>

            <Button onClick={startSession} disabled={saving}>
              {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
              Start Trading Session
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Pre-Trade Checklists</CardTitle>
                <CardDescription>
                  Create checklists to complete before placing trades
                </CardDescription>
              </div>
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button>
                    <Icons.plus className="mr-2 h-4 w-4" />
                    Create Checklist
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Create Pre-Trade Checklist</DialogTitle>
                    <DialogDescription>
                      Add items to verify before placing trades
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="checklist-name">Checklist Name</Label>
                      <Input
                        id="checklist-name"
                        placeholder="My Trading Checklist"
                        value={newChecklist.name}
                        onChange={(e) =>
                          setNewChecklist({ ...newChecklist, name: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="checklist-description">Description</Label>
                      <Textarea
                        id="checklist-description"
                        placeholder="Optional description"
                        value={newChecklist.description}
                        onChange={(e) =>
                          setNewChecklist({ ...newChecklist, description: e.target.value })
                        }
                      />
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="is-required"
                        checked={newChecklist.is_required}
                        onCheckedChange={(checked) =>
                          setNewChecklist({ ...newChecklist, is_required: checked })
                        }
                      />
                      <Label htmlFor="is-required">
                        Required (must complete before trading)
                      </Label>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label>Checklist Items</Label>
                        <Button size="sm" variant="outline" onClick={addChecklistItem}>
                          <Icons.plus className="h-4 w-4" />
                        </Button>
                      </div>

                      {newChecklist.items.map((item, index) => (
                        <div key={item.id} className="border rounded-lg p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <Label>Item {index + 1}</Label>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => removeChecklistItem(index)}
                            >
                              <Icons.trash className="h-4 w-4" />
                            </Button>
                          </div>
                          <Input
                            placeholder="Question or check item"
                            value={item.question}
                            onChange={(e) =>
                              updateChecklistItem(index, "question", e.target.value)
                            }
                          />
                          <div className="flex items-center space-x-2">
                            <Switch
                              checked={item.required}
                              onCheckedChange={(checked) =>
                                updateChecklistItem(index, "required", checked)
                              }
                            />
                            <Label>Required</Label>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                        Cancel
                      </Button>
                      <Button onClick={createChecklist} disabled={saving}>
                        {saving && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
                        Create
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent>
            {checklists.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No checklists created yet. Create one to get started.
              </p>
            ) : (
              <div className="space-y-3">
                {checklists.map((checklist) => (
                  <div
                    key={checklist.id}
                    className="border rounded-lg p-4 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{checklist.name}</h3>
                      {checklist.is_required && (
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">
                          Required
                        </span>
                      )}
                    </div>
                    {checklist.description && (
                      <p className="text-sm text-muted-foreground">
                        {checklist.description}
                      </p>
                    )}
                    <p className="text-sm">
                      {checklist.items.length} item{checklist.items.length !== 1 ? "s" : ""}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
