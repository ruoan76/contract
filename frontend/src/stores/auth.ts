import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppRole, ApiUser, Contract } from '@/types/models'
import { loginAsRole, clearAuthCache, getStoredUser } from '@/api/auth'
import { profileApi } from '@/api/profile'
import { getToken, clearSession, setToken, client } from '@/api/client'
import { ROLE_LABELS } from '@/api/config'
import { parseAppRole } from '@/utils/roleCode'

export const useAuthStore = defineStore('auth', () => {
  const role = ref<AppRole>((sessionStorage.getItem('app_role') as AppRole) || 'drafter')
  const user = ref<ApiUser | null>(getStoredUser())
  const loading = ref(false)
  const sessionVerified = ref(false)

  const lastContract = ref<Contract | null>(null)
  const lastFlowId = ref<number | null>(null)

  const roleLabel = computed(() => ROLE_LABELS[role.value] || role.value)
  const displayName = computed(() => user.value?.real_name || user.value?.username || '用户')

  function applyRoleFromCode(roleCode?: string | null) {
    const parsed = parseAppRole(roleCode)
    if (parsed) {
      role.value = parsed
      sessionStorage.setItem('app_role', parsed)
    }
  }

  function persistUser(u: ApiUser) {
    user.value = u
    sessionStorage.setItem('api_current_user', JSON.stringify(u))
  }

  /** 从 /profile 同步用户信息与 RBAC 角色（服务端为单一真相） */
  async function syncProfile() {
    const data = await profileApi.get()
    const apiUser: ApiUser = {
      id: data.id,
      username: data.username,
      real_name: data.real_name,
      role: data.role_code,
      department: data.department_name,
    }
    persistUser(apiUser)
    applyRoleFromCode(data.role_code)
    return data
  }

  async function completeLogin(token: string, loginUser: ApiUser & { role_code?: string }) {
    setToken(token)
    persistUser({
      id: loginUser.id,
      username: loginUser.username,
      real_name: loginUser.real_name,
      role: loginUser.role_code || loginUser.role,
    })
    applyRoleFromCode(loginUser.role_code || loginUser.role)
    try {
      await syncProfile()
    } catch {
      /* 后端未就绪时保留登录响应中的角色 */
    }
    sessionVerified.value = true
  }

  async function logout() {
    clearSession()
    clearAuthCache()
    sessionStorage.removeItem('app_role')
    user.value = null
    sessionVerified.value = false
  }

  async function switchRole(next: AppRole) {
    loading.value = true
    try {
      clearAuthCache()
      sessionVerified.value = false
      const u = await loginAsRole(next)
      role.value = next
      sessionStorage.setItem('app_role', next)
      persistUser(u)
      try {
        await syncProfile()
      } catch {
        /* 演示环境 profile 失败时保留演示角色 */
        role.value = next
        sessionStorage.setItem('app_role', next)
      }
    } finally {
      loading.value = false
    }
  }

  async function initAuth() {
    if (!getToken() || !user.value) {
      await switchRole(role.value)
      return
    }
    try {
      await syncProfile()
      sessionVerified.value = true
    } catch {
      await switchRole(role.value)
    }
  }

  async function ensureAuth() {
    if (sessionVerified.value) return
    if (getToken() && user.value) {
      try {
        await client.get('/api/v1/system/profile')
        await syncProfile()
        sessionVerified.value = true
        return
      } catch {
        clearSession()
        clearAuthCache()
        user.value = null
      }
    } else if (getToken() && !user.value) {
      clearSession()
    }
    await switchRole(role.value)
    sessionVerified.value = true
  }

  function setLastContract(c: Contract | null, flowId?: number | null) {
    lastContract.value = c
    if (c) sessionStorage.setItem('last_contract_id', String(c.id))
    else clearLastContractId()
    if (flowId != null) {
      lastFlowId.value = flowId
      sessionStorage.setItem('last_flow_id', String(flowId))
    }
  }

  function clearLastContractId() {
    lastContract.value = null
    sessionStorage.removeItem('last_contract_id')
  }

  function restoreLastContractId(): number | null {
    const id = sessionStorage.getItem('last_contract_id')
    return id ? Number(id) : null
  }

  return {
    role,
    user,
    loading,
    roleLabel,
    displayName,
    lastContract,
    lastFlowId,
    syncProfile,
    completeLogin,
    logout,
    switchRole,
    initAuth,
    ensureAuth,
    setLastContract,
    clearLastContractId,
    restoreLastContractId,
  }
})
