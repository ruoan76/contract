import type { AppRole, ApiUser } from '@/types/models'
import { API_CONFIG } from './config'
import { setToken } from './client'

const cache: Partial<Record<AppRole, { token: string; user: ApiUser }>> = {}

export async function login(username: string, password = API_CONFIG.password) {
  const qs = new URLSearchParams({ username, password })
  const base = (API_CONFIG.baseUrl || '').replace(/\/$/, '')
  const res = await fetch(`${base}/api/v1/system/login?${qs}`, { method: 'POST' })
  const json = await res.json()
  if (!res.ok || json.code !== 200) {
    throw new Error(String(json.detail || json.message || '登录失败'))
  }
  setToken(json.data.token)
  sessionStorage.setItem('api_current_user', JSON.stringify(json.data.user))
  return json.data as { token: string; user: ApiUser }
}

export async function loginAsRole(role: AppRole) {
  const username = API_CONFIG.roleUsers[role]
  if (!username) throw new Error(`未知角色: ${role}`)
  const cached = cache[role]
  if (cached) {
    setToken(cached.token)
    sessionStorage.setItem('api_current_user', JSON.stringify(cached.user))
    return cached.user
  }
  const data = await login(username)
  cache[role] = { token: data.token, user: data.user }
  return data.user
}

export function clearAuthCache() {
  Object.keys(cache).forEach((k) => delete cache[k as AppRole])
}

export function getStoredUser(): ApiUser | null {
  const raw = sessionStorage.getItem('api_current_user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as ApiUser
  } catch {
    return null
  }
}

export const authApi = { login, loginAsRole, clearAuthCache, getStoredUser }
