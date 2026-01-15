"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { ChatInterface, type Message } from "@/components/chat/ChatInterface"
import { useI18n } from "@/lib/i18n/provider"
import { useAuth } from "@/lib/auth-context"
import { Icons } from "@/components/icons"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { coachesAPI, type ChatSession } from "@/lib/api/coaches"
import { useActiveProjectId } from "@/lib/active-project"
import { cn } from "@/lib/utils"

export default function ChatPage() {
  // All hooks must be called at the top level, before any conditional returns
  const { t } = useI18n()
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { projectId } = useActiveProjectId()

  const [mounted, setMounted] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingSessions, setLoadingSessions] = useState(false)

  // Get query params - these must be before any conditional returns
  const coachId = searchParams.get("coach") || "wendy"
  const sessionId = searchParams.get("session")

  // Define callbacks using useCallback to ensure stable references
  const loadSessions = useCallback(async () => {
    setLoadingSessions(true)
    try {
      const list = await coachesAPI.getUserSessions(undefined, projectId, undefined, 50)
      setSessions(list)
    } catch (e) {
      setSessions([])
    } finally {
      setLoadingSessions(false)
    }
  }, [projectId])

  const loadMessages = useCallback(async (sid: string) => {
    try {
      const data = await coachesAPI.getSessionMessages(sid)
      const loaded: Message[] = (data?.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at || Date.now()),
      }))
      setMessages(loaded)
    } catch (e) {
      setMessages([])
    }
  }, [])

  const createNewSession = useCallback(async () => {
    const title = `${t("chat.title")} - ${new Date().toLocaleString()}`
    const created = await coachesAPI.createSession({
      coach_id: coachId,
      project_id: projectId,
      title,
    })
    await loadSessions()
    router.push(`/chat?session=${created.id}&coach=${coachId}`)
  }, [coachId, projectId, t, loadSessions, router])

  // All useEffect hooks MUST be before any conditional returns
  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/auth/login")
    }
  }, [user, isLoading, router])

  useEffect(() => {
    if (!mounted) return
    loadSessions()
  }, [mounted, projectId, loadSessions])

  useEffect(() => {
    if (!mounted) return
    if (!sessionId) {
      setMessages([])
      return
    }
    loadMessages(sessionId)
  }, [mounted, sessionId, loadMessages])

  // Now we can have conditional returns
  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Icons.spinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  // Main render
  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">{t('chat.title')}</h1>
            <p className="text-sm text-muted-foreground">
              {t('common.tagline')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={createNewSession}>
              <Icons.refresh className="h-4 w-4 mr-2" />
              {t('chat.newChat')}
            </Button>
          </div>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden flex">
        {/* Sessions sidebar */}
        <aside className="hidden md:flex w-72 border-r bg-background flex-col">
          <div className="px-4 py-3 border-b">
            <div className="text-sm font-medium">{t("chat.history" as any) || "History"}</div>
            <div className="text-xs text-muted-foreground">
              {loadingSessions ? (t("common.loading") || "Loading…") : `${sessions.length} sessions`}
            </div>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {sessions.map((s) => {
                const active = s.id === sessionId
                const label = s.title || `${s.coach_id} • ${new Date(s.created_at).toLocaleString()}`
                return (
                  <button
                    key={s.id}
                    className={cn(
                      "w-full text-left rounded-md px-3 py-2 text-sm hover:bg-accent",
                      active && "bg-accent"
                    )}
                    onClick={() => router.push(`/chat?session=${s.id}&coach=${s.coach_id}`)}
                  >
                    <div className="truncate">{label}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {s.message_count} msgs
                      {s.project_id ? " • project" : ""}
                    </div>
                  </button>
                )
              })}
              {sessions.length === 0 && !loadingSessions && (
                <div className="px-3 py-2 text-sm text-muted-foreground">
                  No sessions yet.
                </div>
              )}
            </div>
          </ScrollArea>
        </aside>

        <div className="flex-1 overflow-hidden">
          {!sessionId ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="text-sm text-muted-foreground">
                  {t("chat.selectSession" as any) || "Select a session or start a new chat."}
                </div>
                <Button onClick={createNewSession}>
                  <Icons.refresh className="h-4 w-4 mr-2" />
                  {t("chat.newChat")}
                </Button>
              </div>
            </div>
          ) : (
            <ChatInterface
              key={sessionId}
              coachId={coachId}
              sessionId={sessionId}
              initialMessages={messages}
              placeholder={t('chat.typeMessage')}
              className="h-full"
              onNewChat={createNewSession}
            />
          )}
        </div>
      </div>
    </div>
  )
}