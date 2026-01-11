"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { useActiveProjectId } from "@/lib/active-project"
import { Icons } from "@/components/icons"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { roundtableAPI } from "@/lib/api/roundtable"
import { coachesAPI, type Coach } from "@/lib/api/coaches"
import { useI18n } from "@/lib/i18n/provider"
import type {
  CoachPreset,
  RoundtableSession,
  RoundtableMessage,
} from "@/lib/types/roundtable"
import { PresetSelector } from "@/components/roundtable/PresetSelector"
import { CoachMultiSelector } from "@/components/roundtable/CoachMultiSelector"
import { RoundtableChat } from "@/components/roundtable/RoundtableChat"
import { ModelSelector, type ModelConfig } from "@/components/chat/ModelSelector"

type SelectionMode = "preset" | "custom"
type DiscussionMode = "free" | "moderated"

export default function RoundtablePage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { projectId } = useActiveProjectId()
  const { locale } = useI18n()
  const isZh = locale === "zh"

  const [mounted, setMounted] = useState(false)
  const [loading, setLoading] = useState(true)

  // Data state
  const [presets, setPresets] = useState<CoachPreset[]>([])
  const [coaches, setCoaches] = useState<Coach[]>([])
  const [sessions, setSessions] = useState<RoundtableSession[]>([])

  // Selection state
  const [mode, setMode] = useState<SelectionMode>("preset")
  const [selectedPreset, setSelectedPreset] = useState<CoachPreset | null>(null)
  const [selectedCoachIds, setSelectedCoachIds] = useState<string[]>([])

  // Discussion mode state (new for moderator feature)
  const [discussionMode, setDiscussionMode] = useState<DiscussionMode>("free")
  const [moderatorId, setModeratorId] = useState<string>("host")

  // Active session
  const sessionId = searchParams.get("session")
  const [activeSession, setActiveSession] = useState<RoundtableSession | null>(null)
  const [activeMessages, setActiveMessages] = useState<RoundtableMessage[]>([])

  // Model configuration
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    provider: "",
    configId: undefined,
    model: "",
    stream: true,
    temperature: 0.7,
    maxTokens: 4096,
  })

  // Knowledge base settings
  const [kbTiming, setKbTiming] = useState<"off" | "message" | "round" | "coach" | "moderator">("off")
  const [kbTopK, setKbTopK] = useState<number>(5)
  const [kbMaxCandidates, setKbMaxCandidates] = useState<number>(400)

  // Load initial data
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [presetsData, coachesData, sessionsData] = await Promise.all([
        roundtableAPI.getPresets(),
        coachesAPI.getCoaches(),
        roundtableAPI.getSessions(projectId, undefined, 20),
      ])
      setPresets(presetsData)
      setCoaches(coachesData)
      setSessions(sessionsData)
    } catch (error) {
      console.error("Failed to load data:", error)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  // Load session if ID is provided
  const loadSession = useCallback(async (sid: string) => {
    try {
      const data = await roundtableAPI.getSession(sid)
      setActiveSession(data.session)
      setActiveMessages(data.messages)

      setKbTiming(data.session.kb_timing || "off")
      setKbTopK(data.session.kb_top_k || 5)
      setKbMaxCandidates(data.session.kb_max_candidates || 400)

      setModelConfig((prev) => ({
        ...prev,
        configId: data.session.llm_config_id || undefined,
        provider: data.session.llm_provider || prev.provider,
        model: data.session.llm_model || prev.model,
        temperature: data.session.llm_temperature ?? prev.temperature,
        maxTokens: data.session.llm_max_tokens ?? prev.maxTokens,
      }))
    } catch (error) {
      console.error("Failed to load session:", error)
      router.push("/roundtable")
    }
  }, [router])

  useEffect(() => {
    if (!activeSession?.id) return

    const timeout = window.setTimeout(() => {
      roundtableAPI
        .updateSessionSettings(activeSession.id, {
          config_id: modelConfig.configId ?? null,
          provider: modelConfig.provider ? modelConfig.provider : null,
          model: modelConfig.model ? modelConfig.model : null,
          temperature: modelConfig.temperature ?? null,
          max_tokens: modelConfig.maxTokens ?? null,
          kb_timing: kbTiming,
          kb_top_k: kbTopK,
          kb_max_candidates: kbMaxCandidates,
        })
        .then((updated) => setActiveSession(updated))
        .catch((error) => {
          console.error("Failed to update roundtable settings:", error)
        })
    }, 600)

    return () => window.clearTimeout(timeout)
  }, [activeSession?.id, modelConfig, kbTiming, kbTopK, kbMaxCandidates])

  // Effects
  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/auth/login")
    }
  }, [user, authLoading, router])

  useEffect(() => {
    if (mounted && user) {
      loadData()
    }
  }, [mounted, user, loadData])

  useEffect(() => {
    if (mounted && sessionId) {
      loadSession(sessionId)
    } else {
      setActiveSession(null)
      setActiveMessages([])
    }
  }, [mounted, sessionId, loadSession])

  // Handlers
  const handlePresetSelect = (preset: CoachPreset) => {
    setSelectedPreset(preset)
    setSelectedCoachIds(preset.coach_ids)
  }

  const handleStartSession = async () => {
    if (selectedCoachIds.length < 2) return

    try {
      const hasModelSettings =
        Boolean(modelConfig.configId) || Boolean(modelConfig.provider) || Boolean(modelConfig.model)

      const session = await roundtableAPI.createSession({
        preset_id: mode === "preset" ? selectedPreset?.id : undefined,
        coach_ids: mode === "custom" ? selectedCoachIds : undefined,
        project_id: projectId,
        discussion_mode: discussionMode,
        moderator_id: discussionMode === "moderated" ? moderatorId : undefined,
        config_id: modelConfig.configId,
        provider: modelConfig.provider ? modelConfig.provider : undefined,
        model: modelConfig.model ? modelConfig.model : undefined,
        temperature: hasModelSettings ? modelConfig.temperature : undefined,
        max_tokens: hasModelSettings ? modelConfig.maxTokens : undefined,
        kb_timing: kbTiming,
        kb_top_k: kbTopK,
        kb_max_candidates: kbMaxCandidates,
      })

      await loadData() // Refresh sessions list
      router.push(`/roundtable?session=${session.id}`)
    } catch (error) {
      console.error("Failed to create session:", error)
    }
  }

  const handleSessionEnd = async () => {
    if (!activeSession) return

    try {
      await roundtableAPI.endSession(activeSession.id)
      await loadData()
      router.push("/roundtable")
    } catch (error) {
      console.error("Failed to end session:", error)
    }
  }

  const handleNewSession = () => {
    setSelectedPreset(null)
    setSelectedCoachIds([])
    router.push("/roundtable")
  }

  // Loading states
  if (!mounted || authLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Icons.spinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  // Render active session
  if (activeSession) {
    return (
      <div className="flex flex-col h-full bg-background">
        {/* Model Selector Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Session settings</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">KB</span>
              <Select value={kbTiming} onValueChange={(v) => setKbTiming(v as any)}>
                <SelectTrigger className="h-8 w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="off">Off</SelectItem>
                  <SelectItem value="message">Per message</SelectItem>
                  <SelectItem value="round">Per round</SelectItem>
                  <SelectItem value="coach">Per coach</SelectItem>
                  <SelectItem value="moderator">Moderator only</SelectItem>
                </SelectContent>
              </Select>
              <Input
                className="h-8 w-[72px]"
                type="number"
                min={0}
                max={20}
                value={kbTopK}
                onChange={(e) => setKbTopK(Number(e.target.value || 0))}
                title="KB top_k"
              />
              <Input
                className="h-8 w-[96px]"
                type="number"
                min={50}
                max={2000}
                value={kbMaxCandidates}
                onChange={(e) => setKbMaxCandidates(Number(e.target.value || 400))}
                title="KB max_candidates"
              />
            </div>
          </div>
          <ModelSelector config={modelConfig} onConfigChange={setModelConfig} />
        </div>

        <RoundtableChat
          session={activeSession}
          initialMessages={activeMessages}
          onSessionEnd={handleSessionEnd}
          modelConfig={modelConfig}
          kbTiming={kbTiming}
          kbTopK={kbTopK}
          kbMaxCandidates={kbMaxCandidates}
          className="flex-1"
        />
      </div>
    )
  }

  // Render session selection
  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">{isZh ? "圆桌讨论" : "Roundtable"}</h1>
            <p className="text-sm text-muted-foreground">
              {isZh
                ? "多位 AI 教练共同为您分析问题，提供多角度建议"
                : "Multiple AI coaches analyze your question and provide perspectives."}
            </p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Sessions sidebar */}
        <aside className="hidden md:flex w-72 border-r bg-background flex-col">
          <div className="px-4 py-3 border-b">
            <div className="text-sm font-medium">{isZh ? "历史记录" : "History"}</div>
            <div className="text-xs text-muted-foreground">
              {loading
                ? (isZh ? "加载中..." : "Loading...")
                : isZh
                  ? `${sessions.length} 个讨论`
                  : `${sessions.length} sessions`}
            </div>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {sessions.map((s) => {
                const coachNames = s.coaches?.map((c) => c.name).join(isZh ? "、" : ", ")
                const dateLabel = new Date(s.created_at).toLocaleDateString(isZh ? "zh-CN" : "en-US")
                const label = s.title || `${coachNames} • ${dateLabel}`
                return (
                  <button
                    key={s.id}
                    className={cn(
                      "w-full text-left rounded-md px-3 py-2 text-sm hover:bg-accent",
                      sessionId === s.id && "bg-accent"
                    )}
                    onClick={() => router.push(`/roundtable?session=${s.id}`)}
                  >
                    <div className="truncate">{label}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {isZh ? `${s.message_count} 条消息` : `${s.message_count} messages`} •{" "}
                      {s.is_active ? (isZh ? "进行中" : "Active") : (isZh ? "已结束" : "Ended")}
                    </div>
                  </button>
                )
              })}
              {sessions.length === 0 && !loading && (
                <div className="px-3 py-2 text-sm text-muted-foreground">
                  {isZh ? "暂无讨论记录" : "No discussions yet"}
                </div>
              )}
            </div>
          </ScrollArea>
        </aside>

        {/* Selection area */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Icons.spinner className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              <Tabs
                value={mode}
                onValueChange={(v) => setMode(v as SelectionMode)}
              >
                <TabsList className="grid w-full grid-cols-2 max-w-md">
                  <TabsTrigger value="preset">{isZh ? "预设组合" : "Presets"}</TabsTrigger>
                  <TabsTrigger value="custom">{isZh ? "自定义选择" : "Custom"}</TabsTrigger>
                </TabsList>

                <TabsContent value="preset" className="mt-6">
                  <PresetSelector
                    presets={presets}
                    selectedPresetId={selectedPreset?.id}
                    onSelect={handlePresetSelect}
                  />
                </TabsContent>

                <TabsContent value="custom" className="mt-6">
                  <CoachMultiSelector
                    coaches={coaches}
                    selectedIds={selectedCoachIds}
                    onSelectionChange={setSelectedCoachIds}
                  />
                </TabsContent>
              </Tabs>

              {/* Discussion Mode Selection */}
              {selectedCoachIds.length >= 2 && (
                <div className="mt-6 p-4 bg-muted/50 rounded-lg space-y-6">
                  <div>
                    <div className="text-sm font-medium mb-3">{isZh ? "讨论模式" : "Discussion mode"}</div>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        className={cn(
                          "p-4 rounded-lg border-2 text-left transition-all",
                          discussionMode === "free"
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-muted-foreground/50"
                        )}
                        onClick={() => setDiscussionMode("free")}
                      >
                        <div className="font-medium mb-1">{isZh ? "自由讨论" : "Free discussion"}</div>
                        <div className="text-xs text-muted-foreground">
                          {isZh ? "教练们按顺序轮流发言，各抒己见" : "Coaches take turns sharing their views."}
                        </div>
                      </button>
                      <button
                        className={cn(
                          "p-4 rounded-lg border-2 text-left transition-all",
                          discussionMode === "moderated"
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-muted-foreground/50"
                        )}
                        onClick={() => setDiscussionMode("moderated")}
                      >
                        <div className="font-medium mb-1">{isZh ? "主持人模式" : "Moderator mode"}</div>
                        <div className="text-xs text-muted-foreground">
                          {isZh
                            ? "由主持人控制节奏、总结要点、引导深入"
                            : "A moderator manages pace, summarizes, and guides deeper."}
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Moderator Selection (only in moderated mode) */}
                  {discussionMode === "moderated" && (
                    <div>
                      <div className="text-sm font-medium mb-3">{isZh ? "选择主持人" : "Choose moderator"}</div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          className={cn(
                            "px-3 py-2 rounded-lg border text-sm transition-all",
                            moderatorId === "host"
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:border-muted-foreground/50"
                          )}
                          onClick={() => setModeratorId("host")}
                        >
                          {isZh ? "专属主持人" : "Dedicated moderator"}
                        </button>
                        {coaches
                          .filter((c) => selectedCoachIds.includes(c.id))
                          .map((coach) => (
                            <button
                              key={coach.id}
                              className={cn(
                                "px-3 py-2 rounded-lg border text-sm transition-all",
                                moderatorId === coach.id
                                  ? "border-primary bg-primary/10 text-primary"
                                  : "border-border hover:border-muted-foreground/50"
                              )}
                              onClick={() => setModeratorId(coach.id)}
                            >
                              {coach.name}
                            </button>
                          ))}
                      </div>
                      <div className="text-xs text-muted-foreground mt-2">
                        {moderatorId === "host"
                          ? (isZh
                            ? "专属主持人将保持中立，不参与具体建议"
                            : "The dedicated moderator stays neutral and won’t provide specific advice.")
                          : (isZh
                            ? "该教练将同时担任主持人和讨论者双重角色"
                            : "This coach will act as both moderator and participant.")}
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t">
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <div>
                        <div className="text-sm font-medium">{isZh ? "会话设置（可选）" : "Session settings (optional)"}</div>
                        <div className="text-xs text-muted-foreground">
                          {isZh
                            ? "创建时可选，进入会话后也可以随时修改"
                            : "Optional at creation; can be changed anytime in the session."}
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs text-muted-foreground">KB</span>
                        <Select value={kbTiming} onValueChange={(v) => setKbTiming(v as any)}>
                          <SelectTrigger className="h-8 w-[140px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="off">{isZh ? "关闭" : "Off"}</SelectItem>
                            <SelectItem value="message">{isZh ? "按消息" : "Per message"}</SelectItem>
                            <SelectItem value="round">{isZh ? "按轮次" : "Per round"}</SelectItem>
                            <SelectItem value="coach">{isZh ? "按教练" : "Per coach"}</SelectItem>
                            <SelectItem value="moderator">{isZh ? "仅主持人" : "Moderator only"}</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          className="h-8 w-[72px]"
                          type="number"
                          min={0}
                          max={20}
                          value={kbTopK}
                          onChange={(e) => setKbTopK(Number(e.target.value || 0))}
                          title="KB top_k"
                        />
                        <Input
                          className="h-8 w-[96px]"
                          type="number"
                          min={50}
                          max={2000}
                          value={kbMaxCandidates}
                          onChange={(e) => setKbMaxCandidates(Number(e.target.value || 400))}
                          title="KB max_candidates"
                        />
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span className="text-xs text-muted-foreground">Model</span>
                        <ModelSelector config={modelConfig} onConfigChange={setModelConfig} />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Start button */}
              <div className="flex justify-center pt-4">
                <Button
                  size="lg"
                  onClick={handleStartSession}
                  disabled={selectedCoachIds.length < 2}
                >
                  {isZh ? "开始圆桌讨论" : "Start roundtable"}
                  {selectedCoachIds.length > 0 && (
                    <span className="ml-2">
                      {isZh ? `(${selectedCoachIds.length} 位教练)` : `(${selectedCoachIds.length} coaches)`}
                    </span>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
