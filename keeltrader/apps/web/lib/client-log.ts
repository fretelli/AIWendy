const CLIENT_DEBUG = process.env.NEXT_PUBLIC_CLIENT_DEBUG === '1'

function shouldLogToConsole(): boolean {
  return process.env.NODE_ENV !== 'production' || CLIENT_DEBUG
}

export function logClientError(scope: string, error: unknown): void {
  if (shouldLogToConsole()) {
    console.error(`[${scope}]`, error)
  }
}

export function logClientWarn(scope: string, message: string): void {
  if (shouldLogToConsole()) {
    console.warn(`[${scope}] ${message}`)
  }
}

export function clientErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return fallback
}
