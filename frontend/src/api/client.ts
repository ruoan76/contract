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

/** 清除本地登录态（token 失效或 SECRET_KEY 变更后） */
export function clearSession() {
  token = ''
  sessionStorage.removeItem('api_token')
  sessionStorage.removeItem('api_current_user')
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
  options?: {
    body?: unknown
    headers?: Record<string, string>
    _retried?: boolean
    timeoutMs?: number
  },
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

  const signal =
    options?.timeoutMs != null && options.timeoutMs > 0
      ? AbortSignal.timeout(options.timeoutMs)
      : undefined

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: options?.body
        ? options.body instanceof FormData
          ? options.body
          : JSON.stringify(options.body)
        : undefined,
      signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'TimeoutError') {
      throw new ApiError('请求超时，请稍后重试', 408)
    }
    throw e
  }

  const data = await parseResponse(res)
  if (res.status === 401 && !options?._retried) {
    clearSession()
  }
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
  post: <T>(path: string, body?: unknown, opts?: { timeoutMs?: number }) =>
    request<T>('POST', path, { body, ...opts }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
  health: async () => {
    const base = (API_CONFIG.baseUrl || '').replace(/\/$/, '')
    const res = await fetch(`${base}/health`)
    return res.ok
  },
}
