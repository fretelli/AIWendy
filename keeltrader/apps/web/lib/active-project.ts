'use client'

import { useCallback, useEffect, useState } from 'react'

const ACTIVE_PROJECT_ID_KEY = 'keeltrader_active_project_id'

export function getActiveProjectId(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(ACTIVE_PROJECT_ID_KEY)
}

export function setActiveProjectId(projectId: string | null): void {
  if (typeof window === 'undefined') return
  if (projectId) {
    window.localStorage.setItem(ACTIVE_PROJECT_ID_KEY, projectId)
  } else {
    window.localStorage.removeItem(ACTIVE_PROJECT_ID_KEY)
  }
}

export function useActiveProjectId() {
  const [projectId, setProjectIdState] = useState<string | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setProjectIdState(getActiveProjectId())
    setReady(true)
  }, [])

  const setProjectId = useCallback((next: string | null) => {
    setActiveProjectId(next)
    setProjectIdState(next)
  }, [])

  return { projectId, setProjectId, ready }
}

