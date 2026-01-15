"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { knowledgeAPI, type KnowledgeDocument, type KnowledgeSearchResult } from "@/lib/api/knowledge"
import { projectsAPI, type Project } from "@/lib/api/projects"
import { tasksAPI } from "@/lib/api/tasks"
import { useActiveProjectId } from "@/lib/active-project"
import { useI18n } from "@/lib/i18n/provider"
import { useAuth } from "@/lib/auth-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Icons } from "@/components/icons"
import { API_V1_PREFIX } from "@/lib/config"

export default function KnowledgePage() {
  const { t } = useI18n()
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const { projectId, ready } = useActiveProjectId()

  const [mounted, setMounted] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [results, setResults] = useState<KnowledgeSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [q, setQ] = useState("")

  const activeProject = useMemo(
    () => projects.find((p) => p.id === projectId) ?? null,
    [projects, projectId]
  )

  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (!isLoading && !user) router.push("/auth/login")
  }, [user, isLoading, router])

  useEffect(() => {
    if (!mounted || !user || !ready) return
    ;(async () => {
      try {
        const list = await projectsAPI.listProjects(false)
        setProjects(list)
      } catch {
        setProjects([])
      }
    })()
  }, [mounted, user, ready])

  const loadDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const docs = await knowledgeAPI.listDocuments(projectId)
      setDocuments(docs)
    } catch (e: any) {
      setError(e?.message || t("knowledge.errors.load"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!mounted || !user || !ready) return
    loadDocuments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, user, ready, projectId])

  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Icons.spinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) return null

  const handleCreate = async () => {
    const docTitle = title.trim()
    const docContent = content.trim()
    if (!docTitle || !docContent) return
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/tasks/knowledge/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : ""
        },
        body: JSON.stringify({
          project_id: projectId,
          title: docTitle,
          content: docContent,
          source_type: "text",
        })
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        const detail = typeof data?.detail === "string" ? data.detail : t("knowledge.errors.queueTask")
        throw new Error(detail)
      }
      const queued = await response.json()
      if (!queued?.task_id) {
        throw new Error(t("knowledge.errors.missingTaskId"))
      }

      setTitle("")
      setContent("")
      await loadDocuments()

      await tasksAPI.waitForCompletion(queued.task_id, {
        timeoutMs: 5 * 60 * 1000,
      })
      await loadDocuments()
    } catch (e: any) {
      setError(e?.message || t("knowledge.errors.createDocument"))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (doc: KnowledgeDocument) => {
    if (!confirm(t("knowledge.confirmDelete", { title: doc.title }))) return
    setLoading(true)
    setError(null)
    try {
      await knowledgeAPI.deleteDocument(doc.id, false)
      await loadDocuments()
    } catch (e: any) {
      setError(e?.message || t("knowledge.errors.deleteDocument"))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    const query = q.trim()
    if (!query) return
    setLoading(true)
    setError(null)
    try {
      const res = await knowledgeAPI.search(query, projectId, 5)
      setResults(res)
    } catch (e: any) {
      setError(e?.message || t("knowledge.errors.search"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("knowledge.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("knowledge.subtitle")}
        </p>
        {activeProject && (
          <div className="mt-2 text-sm">
            <span className="text-muted-foreground">{t("knowledge.currentProjectLabel")} </span>
            <span className="font-medium">{activeProject.name}</span>
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("knowledge.addDocumentTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("knowledge.fields.title")}</div>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t("knowledge.fields.content")}</div>
              <Textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} />
            </div>
          </div>
          <Button onClick={handleCreate} disabled={loading || !title.trim() || !content.trim()}>
            {loading ? t("knowledge.actions.working") : t("knowledge.actions.import")}
          </Button>
          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("knowledge.searchTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-2 md:flex-row">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("knowledge.placeholders.query")} />
            <Button onClick={handleSearch} disabled={loading || !q.trim()}>
              {t("knowledge.actions.search")}
            </Button>
          </div>

          {results.length > 0 && (
            <div className="space-y-2">
              {results.map((r) => (
                <div key={r.chunk_id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium truncate">{r.document_title}</div>
                    <Badge variant="secondary">{r.score.toFixed(3)}</Badge>
                  </div>
                  <div className="mt-2 text-sm whitespace-pre-wrap">{r.content}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("knowledge.documentsTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {documents.length === 0 && (
            <div className="text-sm text-muted-foreground">
              {t("knowledge.emptyDocuments")}
            </div>
          )}

          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
              <div className="min-w-0">
                <div className="font-medium truncate">{doc.title}</div>
                <div className="text-xs text-muted-foreground">
                  {t("knowledge.chunks", { count: doc.chunk_count })}
                </div>
              </div>
              <Button variant="destructive" size="sm" onClick={() => handleDelete(doc)} disabled={loading}>
                {t("knowledge.actions.delete")}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
