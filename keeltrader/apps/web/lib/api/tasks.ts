import { getApiUrl } from '@/lib/config'

export interface TaskStatus {
  task_id: string
  state: string
  ready: boolean
  successful?: boolean | null
  failed?: boolean | null
  result?: any
  error?: string
  info?: any
  traceback?: string
}

export type TaskStreamEvent = TaskStatus & Record<string, any>

class TasksAPI {
  private apiUrl: string

  constructor() {
    this.apiUrl = getApiUrl()
  }

  private getHeaders() {
    const token = localStorage.getItem('keeltrader_access_token')
    return {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
    }
  }

  async getStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${this.apiUrl}/tasks/status/${taskId}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to fetch task status'
      throw new Error(detail)
    }
    return response.json()
  }

  async waitForCompletion(
    taskId: string,
    options?: {
      timeoutMs?: number
      onEvent?: (evt: TaskStreamEvent) => void
    }
  ): Promise<any> {
    const timeoutMs = options?.timeoutMs ?? 8 * 60 * 1000
    const startedAt = Date.now()

    const response = await fetch(`${this.apiUrl}/tasks/stream/${taskId}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : 'Failed to stream task'
      throw new Error(detail)
    }

    if (!response.body) {
      throw new Error('Streaming not supported in this browser')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let lastEvent: TaskStreamEvent | null = null

    const parseEvent = (raw: string): TaskStreamEvent | null => {
      const lines = raw.split('\n')
      let data = ''
      for (const line of lines) {
        if (line.startsWith('data:')) {
          data += line.slice(5).trimStart()
        }
      }
      if (!data) return null
      try {
        return JSON.parse(data)
      } catch {
        return null
      }
    }

    while (true) {
      if (Date.now() - startedAt > timeoutMs) {
        try { await reader.cancel() } catch {}
        throw new Error('Task timed out (check worker/beat)')
      }

      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      while (true) {
        const sep = buffer.indexOf('\n\n')
        if (sep === -1) break
        const raw = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)

        // Ignore keepalive pings/comments.
        if (!raw.trim() || raw.startsWith(':') || raw.startsWith('event: ping')) continue

        const evt = parseEvent(raw)
        if (!evt) continue

        lastEvent = evt
        options?.onEvent?.(evt)

        if (evt.ready === true) {
          if (evt.successful || evt.state === 'SUCCESS') return evt.result
          throw new Error(evt.error || 'Task failed')
        }
      }
    }

    if (lastEvent?.ready) {
      if (lastEvent.successful) return lastEvent.result
      throw new Error(lastEvent.error || 'Task failed')
    }

    throw new Error('Task stream ended unexpectedly')
  }
}

export const tasksAPI = new TasksAPI()
