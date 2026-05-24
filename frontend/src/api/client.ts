import { API_CONFIG } from './config'

export class ApiError extends Error {
  status: number
  data: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

let token = sessionStorage.getItem('api_token') || ''

export function setToken(value: string) {
  token = value || ''
  if (token) sessionStorage.setItem('api_token', token)
  else sessionStorage.removeItem('api_token')
}

export function getToken() {
  return token
}

async function parseResponse(res: Response) {
  const text = await res.text()
  let data: Record<string, unknown> | null = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { detail: text }
  }
  return data
}

export async function request<T>(
  method: string,
  path: string,
  options?: { body?: unknown; headers?: Record<string, string> },
): Promise<T> {
  const base = (API_CONFIG.baseUrl || '').replace(/\/$/, '')
  const url = base + path
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options?.headers || {}),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  if (options?.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, {
    method,
    headers,
    body: options?.body
      ? options.body instanceof FormData
        ? options.body
        : JSON.stringify(options.body)
      : undefined,
  })

  const data = await parseResponse(res)
  if (!res.ok) {
    const detail = data?.detail ?? data?.message ?? res.statusText
    const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
    throw new ApiError(msg, res.status, data)
  }
  if (data && data.code !== undefined && data.code !== 200) {
    throw new ApiError(String(data.message || 'API error'), Number(data.code), data)
  }
  return (data?.data !== undefined ? data.data : data) as T
}

export const client = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
  health: async () => {
    const base = (API_CONFIG.baseUrl || '').replace(/\/$/, '')
    const res = await fetch(`${base}/health`)
    return res.ok
  },
}
