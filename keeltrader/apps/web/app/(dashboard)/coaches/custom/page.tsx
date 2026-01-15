"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { coachesAPI, type CustomCoach } from "@/lib/api/coaches"
import { useI18n } from "@/lib/i18n/provider"
import { getActiveProjectId } from "@/lib/active-project"

const styleOptions = [
  { value: "empathetic", labelKey: "coaches.coachStyles.empathetic" },
  { value: "disciplined", labelKey: "coaches.coachStyles.disciplined" },
  { value: "analytical", labelKey: "coaches.coachStyles.analytical" },
  { value: "motivational", labelKey: "coaches.coachStyles.motivational" },
  { value: "socratic", labelKey: "coaches.coachStyles.socratic" },
] as const

export default function CustomCoachesPage() {
  const router = useRouter()
  const { locale, t } = useI18n()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [coaches, setCoaches] = useState<CustomCoach[]>([])

  const styleLabel = (style: string): string => {
    const opt = styleOptions.find((o) => o.value === (style as any))
    return opt ? t(opt.labelKey as any) : style
  }

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [style, setStyle] = useState<(typeof styleOptions)[number]["value"]>("empathetic")
  const [systemPrompt, setSystemPrompt] = useState("")

  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<CustomCoach | null>(null)
  const [editSaving, setEditSaving] = useState(false)
  const [editName, setEditName] = useState("")
  const [editDescription, setEditDescription] = useState("")
  const [editStyle, setEditStyle] = useState<(typeof styleOptions)[number]["value"]>("empathetic")
  const [editSystemPrompt, setEditSystemPrompt] = useState("")

  const defaultPrompt = useMemo(() => {
    if (locale === "zh") {
      return [
        "你是一位交易心理绩效教练。",
        "目标：帮助交易者提升纪律、情绪控制、风险管理与复盘质量。",
        "风格：专业、直接但不伤人；善于提问，引导用户形成可执行的行动计划。",
        "约束：不要提供投资建议或具体买卖点；聚焦心理与行为层面的改进。",
        "",
        "每次回答尽量包含：",
        "1) 你观察到的心理模式/偏差",
        "2) 1-3 个可执行的训练/行动步骤",
        "3) 1 个追问，帮助澄清或推进",
      ].join("\n")
    }
    return [
      "You are a trading psychology performance coach.",
      "Goal: help the trader improve discipline, emotional regulation, risk management, and review quality.",
      "Style: professional, direct but respectful; ask good questions and turn insights into an executable plan.",
      "Constraint: do not give investment advice or specific trade entries/exits; focus on psychology and behavior.",
      "",
      "In each answer, try to include:",
      "1) the psychological pattern/bias you notice",
      "2) 1-3 concrete training/action steps",
      "3) 1 follow-up question to clarify or move forward",
    ].join("\n")
  }, [locale])

  const load = async () => {
    setLoading(true)
    try {
      const list = await coachesAPI.getCustomCoaches()
      setCoaches(list.filter((c) => c.is_active))
    } catch (e: any) {
      setCoaches([])
      toast.error(t("coaches.custom.toasts.loadFailed"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!systemPrompt.trim()) setSystemPrompt(defaultPrompt)
  }, [defaultPrompt, systemPrompt])

  const handleCreate = async () => {
    if (!name.trim() || !systemPrompt.trim()) return
    setSaving(true)
    try {
      const created = await coachesAPI.createCustomCoach({
        name: name.trim(),
        description: description.trim() || undefined,
        style,
        system_prompt: systemPrompt.trim(),
        language: locale === "zh" ? "zh" : "en",
        is_public: false,
      })
      toast.success(t("coaches.custom.toasts.createSuccess"))
      setName("")
      setDescription("")
      setStyle("empathetic")
      setSystemPrompt(defaultPrompt)
      setCoaches((prev) => [created, ...prev])
    } catch (e: any) {
      toast.error(t("coaches.custom.toasts.createFailed"))
    } finally {
      setSaving(false)
    }
  }

  const startChat = async (coachId: string) => {
    try {
      const projectId = getActiveProjectId()
      const created = await coachesAPI.createSession({
        coach_id: coachId,
        project_id: projectId || undefined,
        title: t("coaches.custom.chatSessionTitle", { datetime: new Date().toLocaleString() }),
      })
      router.push(`/chat?session=${created.id}&coach=${coachId}`)
    } catch {
      toast.error(t("coaches.custom.toasts.startChatFailed"))
    }
  }

  const remove = async (coachId: string) => {
    try {
      await coachesAPI.deleteCustomCoach(coachId)
      setCoaches((prev) => prev.filter((c) => c.id !== coachId))
      toast.success(t("coaches.custom.toasts.deleted"))
    } catch {
      toast.error(t("coaches.custom.toasts.deleteFailed"))
    }
  }

  const openEdit = (coach: CustomCoach) => {
    setEditing(coach)
    setEditName(coach.name || "")
    setEditDescription(coach.description || "")
    setEditStyle((coach.style as any) || "empathetic")
    setEditSystemPrompt(coach.system_prompt || defaultPrompt)
    setEditOpen(true)
  }

  const handleEditSave = async () => {
    if (!editing) return
    if (!editName.trim() || !editSystemPrompt.trim()) return
    setEditSaving(true)
    try {
      const updated = await coachesAPI.updateCustomCoach(editing.id, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
        style: editStyle,
        system_prompt: editSystemPrompt.trim(),
      })
      setCoaches((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      toast.success(t("coaches.custom.toasts.saved"))
      setEditOpen(false)
      setEditing(null)
    } catch {
      toast.error(t("coaches.custom.toasts.saveFailed"))
    } finally {
      setEditSaving(false)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("coaches.custom.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("coaches.custom.subtitle")}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("coaches.custom.createTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("coaches.custom.fields.name")}</div>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("coaches.custom.placeholders.name")} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("coaches.custom.fields.style")}</div>
              <Select value={style} onValueChange={(v) => setStyle(v as any)}>
                <SelectTrigger>
                  <SelectValue placeholder={t("coaches.custom.placeholders.style")} />
                </SelectTrigger>
                <SelectContent>
                  {styleOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {t(opt.labelKey as any) || opt.value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t("coaches.custom.fields.descriptionOptional")}</div>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder={t("coaches.custom.placeholders.description")} />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t("coaches.custom.fields.systemPrompt")}</div>
            <Textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={10}
              placeholder={t("coaches.custom.placeholders.systemPrompt")}
            />
          </div>

          <Button onClick={handleCreate} disabled={saving || !name.trim() || !systemPrompt.trim()}>
            {saving ? t("coaches.custom.actions.creating") : t("coaches.custom.actions.create")}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("coaches.custom.listTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading && (
            <div className="text-sm text-muted-foreground">
              {t("coaches.custom.loading")}
            </div>
          )}

          {!loading && coaches.length === 0 && (
            <div className="text-sm text-muted-foreground">
              {t("coaches.custom.empty")}
            </div>
          )}

          {coaches.map((c) => (
            <div
              key={c.id}
              className="flex flex-col gap-2 rounded-md border p-3 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div className="font-medium truncate">{c.name}</div>
                  <Badge variant="outline" className="capitalize">{styleLabel(c.style)}</Badge>
                </div>
                {c.description && <div className="text-sm text-muted-foreground truncate">{c.description}</div>}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => startChat(c.id)}>
                  {t("coaches.custom.actions.chat")}
                </Button>
                <Button size="sm" variant="outline" onClick={() => openEdit(c)}>
                  {t("coaches.custom.actions.edit")}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => remove(c.id)}>
                  {t("coaches.custom.actions.delete")}
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Dialog open={editOpen} onOpenChange={(open) => {
        setEditOpen(open)
        if (!open) setEditing(null)
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t("coaches.custom.editTitle")}</DialogTitle>
            <DialogDescription>
              {t("coaches.custom.editHelp")}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("coaches.custom.fields.name")}</div>
              <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("coaches.custom.fields.style")}</div>
              <Select value={editStyle} onValueChange={(v) => setEditStyle(v as any)}>
                <SelectTrigger>
                  <SelectValue placeholder={t("coaches.custom.placeholders.style")} />
                </SelectTrigger>
                <SelectContent>
                  {styleOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {t(opt.labelKey as any) || opt.value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t("coaches.custom.fields.descriptionOptional")}</div>
            <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium">{t("coaches.custom.fields.systemPrompt")}</div>
              <Button type="button" variant="outline" size="sm" onClick={() => setEditSystemPrompt(defaultPrompt)}>
                {t("coaches.custom.actions.resetDefault")}
              </Button>
            </div>
            <Textarea
              value={editSystemPrompt}
              onChange={(e) => setEditSystemPrompt(e.target.value)}
              rows={12}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setEditOpen(false)}
              disabled={editSaving}
            >
              {t("coaches.custom.actions.cancel")}
            </Button>
            <Button
              type="button"
              onClick={handleEditSave}
              disabled={editSaving || !editName.trim() || !editSystemPrompt.trim()}
            >
              {editSaving ? t("coaches.custom.actions.saving") : t("coaches.custom.actions.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
