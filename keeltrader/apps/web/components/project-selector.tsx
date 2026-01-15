'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'

import { projectsAPI, type Project } from '@/lib/api/projects'
import { useActiveProjectId } from '@/lib/active-project'
import { useI18n } from '@/lib/i18n/provider'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

export function ProjectSelector({ collapsed }: { collapsed?: boolean }) {
  const { t } = useI18n()
  const { projectId, setProjectId, ready } = useActiveProjectId()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)

  const selected = useMemo(
    () => projects.find((p) => p.id === projectId) ?? null,
    [projects, projectId]
  )

  useEffect(() => {
    if (!ready) return

    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const list = await projectsAPI.listProjects(false)
        if (cancelled) return
        setProjects(list)

        if (!projectId) {
          const defaultProject = list.find((p) => p.is_default) ?? list[0]
          if (defaultProject) setProjectId(defaultProject.id)
          return
        }

        const exists = list.some((p) => p.id === projectId)
        if (!exists) {
          const fallback = list.find((p) => p.is_default) ?? list[0]
          setProjectId(fallback ? fallback.id : null)
        }
      } catch (e) {
        if (cancelled) return
        setProjects([])
        setProjectId(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [projectId, ready, setProjectId])

  if (collapsed) return null

  return (
    <div className="px-3 py-3 border-b">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="text-xs font-medium text-muted-foreground">
          {t('projects.selector.label')}
        </div>
        <Button asChild size="sm" variant="ghost" className="h-7 px-2">
          <Link href="/projects">{t('nav.projects' as any)}</Link>
        </Button>
      </div>

      <Select
        value={selected?.id ?? ''}
        onValueChange={(value) => setProjectId(value || null)}
        disabled={loading || projects.length === 0}
      >
        <SelectTrigger className={cn('h-9', loading && 'opacity-80')}>
          <SelectValue
            placeholder={loading ? t('projects.selector.loading') : t('projects.selector.placeholder')}
          />
        </SelectTrigger>
        <SelectContent>
          {projects.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

