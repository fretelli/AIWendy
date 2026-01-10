"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { projectsAPI, type Project } from "@/lib/api/projects"
import { useI18n } from "@/lib/i18n/provider"
import { useAuth } from "@/lib/auth-context"
import { useActiveProjectId } from "@/lib/active-project"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Icons } from "@/components/icons"

export default function ProjectsPage() {
  const { locale } = useI18n()
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const { projectId, setProjectId } = useActiveProjectId()

  const [mounted, setMounted] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  const active = useMemo(
    () => projects.find((p) => p.id === projectId) ?? null,
    [projects, projectId]
  )

  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (!isLoading && !user) router.push("/auth/login")
  }, [user, isLoading, router])

  const loadProjects = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await projectsAPI.listProjects(false)
      setProjects(list)
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "加载项目失败" : "Failed to load projects"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!mounted || !user) return
    loadProjects()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, user])

  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Icons.spinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) return null

  const handleCreate = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    try {
      const created = await projectsAPI.createProject({
        name: trimmed,
        description: description.trim() || null,
      })
      setName("")
      setDescription("")
      await loadProjects()
      setProjectId(created.id)
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "创建项目失败" : "Failed to create project"))
    } finally {
      setLoading(false)
    }
  }

  const setDefault = async (p: Project) => {
    setLoading(true)
    setError(null)
    try {
      await projectsAPI.updateProject(p.id, { is_default: true })
      await loadProjects()
      setProjectId(p.id)
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "设置默认项目失败" : "Failed to set default"))
    } finally {
      setLoading(false)
    }
  }

  const archive = async (p: Project, isArchived: boolean) => {
    setLoading(true)
    setError(null)
    try {
      await projectsAPI.updateProject(p.id, { is_archived: isArchived })
      await loadProjects()
      if (isArchived && projectId === p.id) setProjectId(null)
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "更新项目失败" : "Failed to update project"))
    } finally {
      setLoading(false)
    }
  }

  const remove = async (p: Project) => {
    if (!confirm(locale === "zh" ? `确定删除项目「${p.name}」吗？` : `Delete project "${p.name}"?`)) return
    setLoading(true)
    setError(null)
    try {
      await projectsAPI.deleteProject(p.id, false)
      await loadProjects()
      if (projectId === p.id) setProjectId(null)
    } catch (e: any) {
      setError(e?.message || (locale === "zh" ? "删除项目失败" : "Failed to delete project"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{locale === "zh" ? "项目" : "Projects"}</h1>
        <p className="text-sm text-muted-foreground">
          {locale === "zh"
            ? "用项目对聊天、知识库、日志等数据进行分组。"
            : "Group chats, knowledge base, journals, etc. by project."}
        </p>
        {active && (
          <div className="mt-2 text-sm">
            <span className="text-muted-foreground">{locale === "zh" ? "当前：" : "Current: "}</span>
            <span className="font-medium">{active.name}</span>
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "zh" ? "新建项目" : "Create Project"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">{locale === "zh" ? "名称" : "Name"}</div>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={locale === "zh" ? "例如：期货账户A" : "e.g. Futures Account A"} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{locale === "zh" ? "描述" : "Description"}</div>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder={locale === "zh" ? "可选" : "Optional"} rows={2} />
            </div>
          </div>
          <Button onClick={handleCreate} disabled={loading || !name.trim()}>
            {loading ? (locale === "zh" ? "处理中…" : "Working…") : (locale === "zh" ? "创建" : "Create")}
          </Button>
          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "zh" ? "项目列表" : "Projects"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {projects.length === 0 && (
            <div className="text-sm text-muted-foreground">
              {locale === "zh" ? "暂无项目" : "No projects yet"}
            </div>
          )}

          {projects.map((p) => (
            <div
              key={p.id}
              className="flex flex-col gap-2 rounded-md border p-3 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div className="font-medium truncate">{p.name}</div>
                  {p.is_default && <Badge variant="secondary">{locale === "zh" ? "默认" : "Default"}</Badge>}
                  {projectId === p.id && <Badge>{locale === "zh" ? "当前" : "Current"}</Badge>}
                  {p.is_archived && <Badge variant="outline">{locale === "zh" ? "已归档" : "Archived"}</Badge>}
                </div>
                {p.description && (
                  <div className="text-sm text-muted-foreground truncate">{p.description}</div>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setProjectId(p.id)}
                  disabled={projectId === p.id || p.is_archived}
                >
                  {locale === "zh" ? "设为当前" : "Set Active"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setDefault(p)}
                  disabled={loading || p.is_default || p.is_archived}
                >
                  {locale === "zh" ? "设为默认" : "Make Default"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => archive(p, !p.is_archived)}
                  disabled={loading}
                >
                  {p.is_archived ? (locale === "zh" ? "取消归档" : "Unarchive") : (locale === "zh" ? "归档" : "Archive")}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => remove(p)} disabled={loading}>
                  {locale === "zh" ? "删除" : "Delete"}
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

