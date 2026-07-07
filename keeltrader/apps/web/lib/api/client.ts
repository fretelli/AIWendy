import { API_V1_PREFIX } from '@/lib/config'

type ApiErrorPayload =
  | {
      error?: {
        message?: unknown
      }
      detail?: unknown
    }
  | null
  | undefined

type JsonBody = object

export type ApiRequestInit = Omit<RequestInit, 'body'> & {
  body?: BodyInit | JsonBody | null
}

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function isJsonBody(body: ApiRequestInit['body']): body is JsonBody {
  if (!body || typeof body !== 'object') return false
  if (body instanceof FormData) return false
  if (body instanceof Blob) return false
  if (body instanceof ArrayBuffer) return false
  if (ArrayBuffer.isView(body)) return false
  if (body instanceof URLSearchParams) return false
  if (body instanceof ReadableStream) return false
  return true
}

function normalizeApiPath(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (normalized.startsWith('/api/proxy/')) return normalized
  if (normalized.startsWith('/v1/')) return `/api/proxy${normalized}`
  return `${API_V1_PREFIX}${normalized}`
}

function formatFastApiDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const parts: string[] = []
    for (const item of detail) {
      if (!item || typeof item !== 'object') continue
      const msg = (item as { msg?: unknown }).msg
      const loc = (item as { loc?: unknown }).loc
      if (typeof msg !== 'string') continue

      if (Array.isArray(loc)) {
        const locText = loc.map(String).join('.')
        parts.push(locText ? `${locText}: ${msg}` : msg)
      } else {
        parts.push(msg)
      }
    }
    if (parts.length) return parts.join('; ')
  }

  return null
}

export function getApiErrorMessage(payload: ApiErrorPayload): string | null {
  if (!payload || typeof payload !== 'object') return null

  const errorMessage = payload.error?.message
  if (typeof errorMessage === 'string' && errorMessage.trim()) return errorMessage

  return formatFastApiDetail(payload.detail)
}

export async function readApiError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload
    const message = getApiErrorMessage(payload) ?? response.statusText ?? 'Request failed'
    return new ApiError(message, response.status, payload)
  }

  const text = await response.text().catch(() => '')
  return new ApiError(text || response.statusText || 'Request failed', response.status)
}

export async function apiFetch(path: string, init: ApiRequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const body = init.body
  const hasBody = body !== undefined && body !== null
  const requestBody = isJsonBody(body) ? JSON.stringify(body) : (body as BodyInit | null | undefined)

  if (hasBody && isJsonBody(body) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(normalizeApiPath(path), {
    ...init,
    body: requestBody,
    headers,
    credentials: 'include',
  })
}

export async function apiJson<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init)
  const contentType = response.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await response.json().catch(() => null) : null

  if (!response.ok) {
    const message = getApiErrorMessage(payload as ApiErrorPayload) ?? response.statusText ?? 'Request failed'
    throw new ApiError(message, response.status, payload)
  }

  return payload as T
}

export async function apiStream(path: string, init: ApiRequestInit = {}): Promise<Response> {
  const response = await apiFetch(path, init)
  if (!response.ok) {
    throw await readApiError(response)
  }
  return response
}

export async function apiForm<T>(path: string, form: FormData, init: Omit<ApiRequestInit, 'body'> = {}): Promise<T> {
  return apiJson<T>(path, {
    ...init,
    method: init.method ?? 'POST',
    body: form,
  })
}
