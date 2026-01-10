"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MessageInput } from "@/components/chat/MessageInput"
import { ModelSelector, type ModelConfig } from "@/components/chat/ModelSelector"
import { Icons } from "@/components/icons"
import { cn } from "@/lib/utils"
import { roundtableAPI } from "@/lib/api/roundtable"
import { API_V1_PREFIX } from "@/lib/config"
import { getAuthHeaders } from "@/lib/api/auth"
import type {
  RoundtableSession,
  RoundtableMessage,
  CoachBrief,
  RoundtableEvent,
  StreamingCoachResponse,
  MessageType,
} from "@/lib/types/roundtable"
import { CoachResponseCard, RoundIndicator } from "./CoachResponseCard"
import type { PendingAttachment, ChatAttachment, ApiMessageAttachment } from "@/types/chat"
import { canExtractText, isImageForVision } from "@/types/chat"

interface RoundtableChatProps {
  session: RoundtableSession
  initialMessages?: RoundtableMessage[]
  modelConfig: ModelConfig
  kbTiming: "off" | "message" | "round" | "coach" | "moderator"
  kbTopK: number
  kbMaxCandidates: number
  className?: string
  onSessionEnd?: () => void
}

export function RoundtableChat({
  session,
  initialMessages = [],
  modelConfig,
  kbTiming,
  kbTopK,
  kbMaxCandidates,
  className,
  onSessionEnd,
}: RoundtableChatProps) {
  const [messages, setMessages] = useState<RoundtableMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [currentRound, setCurrentRound] = useState(0)
  const [maxRounds, setMaxRounds] = useState<number>(session.discussion_mode === "free" ? 2 : 1)
  const [debateStyle, setDebateStyle] = useState<"converge" | "clash">("converge")
  const [streamingResponses, setStreamingResponses] = useState<
    Record<string, StreamingCoachResponse>
  >({})
  const [currentCoachId, setCurrentCoachId] = useState<string | null>(null)

  const [overrideEnabled, setOverrideEnabled] = useState(false)
  const [overrideModelConfig, setOverrideModelConfig] = useState<ModelConfig>(modelConfig)
  const [overrideKbTiming, setOverrideKbTiming] = useState(kbTiming)
  const [overrideKbTopK, setOverrideKbTopK] = useState(kbTopK)
  const [overrideKbMaxCandidates, setOverrideKbMaxCandidates] = useState(kbMaxCandidates)

  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingResponses, scrollToBottom])

  useEffect(() => {
    setMaxRounds(session.discussion_mode === "free" ? 2 : 1)
  }, [session.id, session.discussion_mode])

  useEffect(() => {
    setDebateStyle("converge")
  }, [session.id, session.discussion_mode])

  useEffect(() => {
    setOverrideModelConfig(modelConfig)
    setOverrideKbTiming(kbTiming)
    setOverrideKbTopK(kbTopK)
    setOverrideKbMaxCandidates(kbMaxCandidates)
    setOverrideEnabled(false)
  }, [session.id, modelConfig, kbTiming, kbTopK, kbMaxCandidates])

  // Build coaches map for quick lookup
  const coachesMap = new Map<string, CoachBrief>()
  session.coaches?.forEach((c) => coachesMap.set(c.id, c))
  // Also add moderator to the map if in moderated mode
  if (session.moderator) {
    coachesMap.set(session.moderator.id, session.moderator)
  }

  async function uploadFile(file: File): Promise<{
    id: string
    fileName: string
    fileSize: number
    mimeType: string
    type: string
    url: string
    thumbnailBase64?: string
  }> {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_V1_PREFIX}/files/upload`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || "Failed to upload file")
    }

    return response.json()
  }

  async function extractText(file: File): Promise<{ text: string } | null> {
    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${API_V1_PREFIX}/files/extract`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      })

      if (!response.ok) return null
      const data = await response.json()
      return data.success ? { text: data.text } : null
    } catch {
      return null
    }
  }

  async function transcribeAudio(file: File): Promise<{ text: string } | null> {
    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${API_V1_PREFIX}/files/transcribe`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      })

      if (!response.ok) return null
      const data = await response.json()
      return { text: data.text }
    } catch {
      return null
    }
  }

  function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  async function processAttachments(
    attachments: PendingAttachment[]
  ): Promise<{ uploaded: ChatAttachment[]; apiAttachments: ApiMessageAttachment[] }> {
    const uploaded: ChatAttachment[] = []
    const apiAttachments: ApiMessageAttachment[] = []

    for (const att of attachments) {
      try {
        const result = await uploadFile(att.file)

        const chatAttachment: ChatAttachment = {
          id: result.id,
          type: att.type,
          fileName: result.fileName,
          fileSize: result.fileSize,
          mimeType: result.mimeType,
          url: result.url,
          thumbnailUrl: result.type === "image" ? att.previewUrl : undefined,
        }

        const apiAttachment: ApiMessageAttachment = {
          id: result.id,
          type: att.type,
          fileName: result.fileName,
          fileSize: result.fileSize,
          mimeType: result.mimeType,
          url: result.url,
        }

        if (isImageForVision(att.type)) {
          apiAttachment.base64Data = await fileToBase64(att.file)
        }

        if (canExtractText(att.type)) {
          const extracted = await extractText(att.file)
          if (extracted) {
            chatAttachment.extractedText = extracted.text
            apiAttachment.extractedText = extracted.text
          }
        }

        if (att.type === "audio") {
          const transcribed = await transcribeAudio(att.file)
          if (transcribed) {
            chatAttachment.transcription = transcribed.text
            apiAttachment.transcription = transcribed.text
          }
        }

        uploaded.push(chatAttachment)
        apiAttachments.push(apiAttachment)
      } catch (error) {
        console.error(`Failed to process attachment ${att.file.name}:`, error)
      }
    }

    return { uploaded, apiAttachments }
  }

  const handleSend = async (value: string, attachments?: PendingAttachment[]) => {
    if (!value.trim() || isLoading) return

    if (!session?.id) {
      console.error("RoundtableChat: session.id is undefined")
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          session_id: "",
          coach_id: null,
          role: "assistant",
          content: "错误：会话 ID 无效，请刷新页面重试。",
          message_type: "response",
          created_at: new Date().toISOString(),
        },
      ])
      return
    }

    const userContent = value.trim()
    setInput("")
    setIsLoading(true)
    setStreamingResponses({})

    let uploadedAttachments: ChatAttachment[] = []
    let apiAttachments: ApiMessageAttachment[] = []

    if (attachments?.length) {
      const processed = await processAttachments(attachments)
      uploadedAttachments = processed.uploaded
      apiAttachments = processed.apiAttachments
    }

    const userMessage: RoundtableMessage = {
      id: `temp-${Date.now()}`,
      session_id: session.id,
      coach_id: null,
      role: "user",
      content: userContent,
      attachments: uploadedAttachments.length ? uploadedAttachments : undefined,
      message_type: "response",
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      const effectiveModel = overrideEnabled ? overrideModelConfig : modelConfig
      const effectiveKbTiming = overrideEnabled ? overrideKbTiming : kbTiming
      const effectiveKbTopK = overrideEnabled ? overrideKbTopK : kbTopK
      const effectiveKbMaxCandidates = overrideEnabled ? overrideKbMaxCandidates : kbMaxCandidates

      const chatRequest = {
        session_id: session.id,
        content: userContent,
        attachments: apiAttachments.length ? apiAttachments : undefined,
        max_rounds: maxRounds,
        debate_style: session.discussion_mode === "free" ? debateStyle : undefined,
        config_id: effectiveModel.configId,
        provider: effectiveModel.provider || undefined,
        model: effectiveModel.model || undefined,
        temperature: effectiveModel.temperature,
        max_tokens: effectiveModel.maxTokens,
        kb_timing: effectiveKbTiming,
        kb_top_k: effectiveKbTopK,
        kb_max_candidates: effectiveKbMaxCandidates,
      }
      console.log("RoundtableChat: sending request", chatRequest)
      const stream = roundtableAPI.chat(chatRequest)

      for await (const event of stream) {
        handleStreamEvent(event)
      }
    } catch (error) {
      console.error("Chat error:", error)
      const message = error instanceof Error ? error.message : null
      const errorMessage: RoundtableMessage = {
        id: `error-${Date.now()}`,
        session_id: session.id,
        coach_id: null,
        role: "assistant",
        content: message || "发生错误，请稍后重试。",
        message_type: "response",
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setCurrentCoachId(null)
      setStreamingResponses({})
      setOverrideEnabled(false)
    }
  }

  const handleStreamEvent = (event: RoundtableEvent) => {
    switch (event.type) {
      case "round_start":
        setCurrentRound(event.round)
        break

      case "coach_start":
        setCurrentCoachId(event.coach_id)
        setStreamingResponses((prev) => ({
          ...prev,
          [event.coach_id]: {
            coach_id: event.coach_id,
            coach_name: event.coach_name,
            coach_avatar: event.coach_avatar,
            content: "",
            isStreaming: true,
            message_type: "response",
          },
        }))
        break

      case "moderator_start":
        setCurrentCoachId(event.coach_id)
        setStreamingResponses((prev) => ({
          ...prev,
          [event.coach_id]: {
            coach_id: event.coach_id,
            coach_name: event.coach_name,
            coach_avatar: event.coach_avatar,
            content: "",
            isStreaming: true,
            message_type: event.message_type,
          },
        }))
        break

      case "content":
        setStreamingResponses((prev) => ({
          ...prev,
          [event.coach_id]: {
            ...prev[event.coach_id],
            content: (prev[event.coach_id]?.content || "") + event.content,
          },
        }))
        break

      case "coach_end":
        // Move streaming response to messages
        setStreamingResponses((prev) => {
          const response = prev[event.coach_id]
          if (response) {
            const coach = coachesMap.get(event.coach_id)
            const newMessage: RoundtableMessage = {
              id: `coach-${event.coach_id}-${Date.now()}`,
              session_id: session.id,
              coach_id: event.coach_id,
              coach: coach,
              role: "assistant",
              content: response.content,
              message_type: response.message_type || "response",
              turn_number: currentRound,
              created_at: new Date().toISOString(),
            }
            setMessages((prevMessages) => [...prevMessages, newMessage])
          }

          const { [event.coach_id]: _, ...rest } = prev
          return rest
        })
        setCurrentCoachId(null)
        break

      case "moderator_end":
        // Move moderator streaming response to messages
        setStreamingResponses((prev) => {
          const response = prev[event.coach_id]
          if (response) {
            // For moderator, try to get from session.moderator or coachesMap
            const coach = session.moderator || coachesMap.get(event.coach_id)
            const newMessage: RoundtableMessage = {
              id: `moderator-${event.message_type}-${Date.now()}`,
              session_id: session.id,
              coach_id: event.coach_id,
              coach: coach,
              role: "assistant",
              content: response.content,
              message_type: event.message_type,
              turn_number: currentRound,
              created_at: new Date().toISOString(),
            }
            setMessages((prevMessages) => [...prevMessages, newMessage])
          }

          const { [event.coach_id]: _, ...rest } = prev
          return rest
        })
        setCurrentCoachId(null)
        break

      case "round_end":
        // Round completed
        break

      case "done":
        // All done
        break

      case "error":
        console.error("Stream error:", event.message)
        break
    }
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header with coaches */}
      <div className="border-b px-4 py-3 bg-muted/30">
        <div className="flex items-center gap-3">
          <div className="flex -space-x-2">
            {/* Show moderator first if in moderated mode */}
            {session.discussion_mode === "moderated" && session.moderator && (
              <Avatar
                className={cn(
                  "h-8 w-8 border-2 border-amber-500 transition-all z-10",
                  currentCoachId === session.moderator.id && "ring-2 ring-amber-500 scale-110"
                )}
              >
                <AvatarImage src={session.moderator.avatar_url} alt={session.moderator.name} />
                <AvatarFallback className="text-xs bg-amber-100 text-amber-700">
                  {session.moderator.name.charAt(0)}
                </AvatarFallback>
              </Avatar>
            )}
            {session.coaches?.map((coach) => (
              <Avatar
                key={coach.id}
                className={cn(
                  "h-8 w-8 border-2 border-background transition-all",
                  currentCoachId === coach.id && "ring-2 ring-primary scale-110"
                )}
              >
                <AvatarImage src={coach.avatar_url} alt={coach.name} />
                <AvatarFallback className="text-xs">
                  {coach.name.charAt(0)}
                </AvatarFallback>
              </Avatar>
            ))}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{session.title || "圆桌讨论"}</span>
              {session.discussion_mode === "moderated" && (
                <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
                  主持人模式
                </Badge>
              )}
              {session.discussion_mode === "free" && (
                <Badge variant="outline" className="text-xs bg-primary/5 text-primary border-primary/20">
                  {maxRounds} 轮互辩（{debateStyle === "converge" ? "收敛" : "对立"}）
                </Badge>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {session.discussion_mode === "moderated" && session.moderator
                ? `主持：${session.moderator.name} | 嘉宾：${session.coaches?.map((c) => c.name).join("、")}`
                : session.coaches?.map((c) => c.name).join("、")}
            </div>
          </div>
          {session.discussion_mode === "free" && session.is_active && (
            <div className="hidden lg:flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">互辩轮数</span>
                <Select value={String(maxRounds)} onValueChange={(v) => setMaxRounds(Number(v))}>
                  <SelectTrigger className="h-8 w-[88px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1</SelectItem>
                    <SelectItem value="2">2</SelectItem>
                    <SelectItem value="3">3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">风格</span>
                <Select value={debateStyle} onValueChange={(v) => setDebateStyle(v as any)}>
                  <SelectTrigger className="h-8 w-[112px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="converge">收敛纠错</SelectItem>
                    <SelectItem value="clash">对立辩论</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          {session.is_active && onSessionEnd && (
            <Button variant="ghost" size="sm" onClick={onSessionEnd}>
              结束讨论
            </Button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <ScrollArea className="flex-1 px-4">
        <div className="py-4 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                开始您的圆桌讨论，多位教练将轮流为您提供见解
              </p>
            </div>
          )}

          {messages.map((msg, idx) => {
            // Show round indicator before first message of each round
            const showRoundIndicator =
              msg.turn_number !== undefined &&
              (idx === 0 || messages[idx - 1]?.turn_number !== msg.turn_number)

            return (
              <div key={msg.id}>
                {showRoundIndicator && msg.turn_number && (
                  <RoundIndicator round={msg.turn_number} />
                )}
                <CoachResponseCard
                  message={msg}
                  coach={msg.coach_id ? coachesMap.get(msg.coach_id) : null}
                />
              </div>
            )
          })}

          {/* Streaming responses */}
          {Object.values(streamingResponses).map((response) => (
            <CoachResponseCard
              key={response.coach_id}
              message={{
                id: `streaming-${response.coach_id}`,
                session_id: session.id,
                coach_id: response.coach_id,
                role: "assistant",
                content: response.content,
                message_type: response.message_type || "response",
                created_at: new Date().toISOString(),
              }}
              coach={coachesMap.get(response.coach_id)}
              isStreaming={response.isStreaming}
            />
          ))}

          {/* Loading indicator when waiting for first coach */}
          {isLoading && Object.keys(streamingResponses).length === 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Icons.spinner className="h-4 w-4 animate-spin" />
              教练们正在思考...
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input area */}
      <div className="border-t p-4 bg-background">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {overrideEnabled ? "Message overrides enabled (apply once)" : "Using session settings"}
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={isLoading || !session.is_active}
            onClick={() => setOverrideEnabled((v) => !v)}
          >
            {overrideEnabled ? "Use session" : "Override"}
          </Button>
        </div>

        {overrideEnabled && (
          <div className="mb-3 rounded-lg border bg-muted/30 p-3 space-y-3">
            <div className="flex flex-wrap items-center gap-2 justify-between">
              <div className="text-xs text-muted-foreground">Model</div>
              <ModelSelector config={overrideModelConfig} onConfigChange={setOverrideModelConfig} />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">KB</span>
                <Select value={overrideKbTiming} onValueChange={(v) => setOverrideKbTiming(v as any)}>
                  <SelectTrigger className="h-8 w-[150px]">
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
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">top_k</span>
                <Select value={String(overrideKbTopK)} onValueChange={(v) => setOverrideKbTopK(Number(v))}>
                  <SelectTrigger className="h-8 w-[88px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[0, 3, 5, 8, 10, 15, 20].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">candidates</span>
                <Select
                  value={String(overrideKbMaxCandidates)}
                  onValueChange={(v) => setOverrideKbMaxCandidates(Number(v))}
                >
                  <SelectTrigger className="h-8 w-[110px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[100, 200, 400, 800, 1200, 2000].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}
        {!session.is_active && <p className="text-xs text-muted-foreground mt-2">该讨论已结束</p>}

        {session.is_active && (
          <MessageInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            isLoading={isLoading}
            placeholder="输入您的问题，教练们会轮流给出建议..."
            className="mt-2"
          />
        )}
      </div>
    </div>
  )
}
