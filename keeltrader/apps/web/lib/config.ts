export const API_PROXY_PREFIX = "/api/proxy"
export const API_V1_PREFIX = `${API_PROXY_PREFIX}/v1`

export function getApiUrl(): string {
  return API_V1_PREFIX
}

