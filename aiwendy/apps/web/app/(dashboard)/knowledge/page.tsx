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
  const { locale } = useI18n()
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
      setError(e?.message || (locale === "zh" ? "加载知识库失败" : "Failed to load knowledge base"))
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
    const t = title.trim()
    const c = content.trim()
    if (!t || !c) return
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
          title: t,
          content: c,
          source_type: "text",
        })
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        const detail = typeof data?.detail === "string" ? data.detail : (locale === "zh" ? "创建任务失败" : "Failed to queue task")
        throw new Error(detail)
      }
      const queued = await response.json()
      if (!queued?.task_id) {
        throw new Error(locale === "zh" ? "任务返回缺少 task_id" : "Missing task_id")
      }

      setTitle("")
      setContent("")
      await loadDocuments()

      await tasksAPI.waitForCompletion(queued.task_id, {
        timeoutMs: 5 * 60 * 1000,
      })
      await loadDocuments()
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "创建文档失败" : "Failed to create document"))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (doc: KnowledgeDocument) => {
    if (!confirm(locale === "zh" ? `确定删除「${doc.title}」吗？` : `Delete "${doc.title}"?`)) return
    setLoading(true)
    setError(null)
    try {
      await knowledgeAPI.deleteDocument(doc.id, false)
      await loadDocuments()
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "删除文档失败" : "Failed to delete document"))
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
      setError(e?.message || (locale === "zh" ? "检索失败" : "Search failed"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{locale === "zh" ? "知识库" : "Knowledge Base"}</h1>
        <p className="text-sm text-muted-foreground">
          {locale === "zh"
            ? "把你的规则、策略、复盘要点等放进知识库，聊天时可按项目检索并注入上下文。"
            : "Store your rules/strategies/notes. Chat can retrieve and inject context per project."}
        </p>
        {activeProject && (
          <div className="mt-2 text-sm">
            <span className="text-muted-foreground">{locale === "zh" ? "当前项目：" : "Project: "}</span>
            <span className="font-medium">{activeProject.name}</span>
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "zh" ? "添加文档" : "Add Document"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">{locale === "zh" ? "标题" : "Title"}</div>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{locale === "zh" ? "内容" : "Content"}</div>
              <Textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} />
            </div>
          </div>
          <Button onClick={handleCreate} disabled={loading || !title.trim() || !content.trim()}>
            {loading ? (locale === "zh" ? "处理中…" : "Working…") : (locale === "zh" ? "导入" : "Import")}
          </Button>
          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "zh" ? "检索" : "Search"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-2 md:flex-row">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={locale === "zh" ? "输入问题…" : "Ask something…"} />
            <Button onClick={handleSearch} disabled={loading || !q.trim()}>
              {locale === "zh" ? "搜索" : "Search"}
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
          <CardTitle>{locale === "zh" ? "文档" : "Documents"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {documents.length === 0 && (
            <div className="text-sm text-muted-foreground">
              {locale === "zh" ? "暂无文档" : "No documents"}
            </div>
          )}

          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
              <div className="min-w-0">
                <div className="font-medium truncate">{doc.title}</div>
                <div className="text-xs text-muted-foreground">
                  {doc.chunk_count} {locale === "zh" ? "片段" : "chunks"}
                </div>
              </div>
              <Button variant="destructive" size="sm" onClick={() => handleDelete(doc)} disabled={loading}>
                {locale === "zh" ? "删除" : "Delete"}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
