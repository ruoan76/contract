import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppRole, ApiUser, Contract } from '@/types/models'
import { loginAsRole, clearAuthCache, getStoredUser } from '@/api/auth'
import { getToken, clearSession, client } from '@/api/client'
import { ROLE_LABELS } from '@/api/config'

export const useAuthStore = defineStore('auth', () => {
  const role = ref<AppRole>((sessionStorage.getItem('app_role') as AppRole) || 'drafter')
  const user = ref<ApiUser | null>(getStoredUser())
  const loading = ref(false)
  const sessionVerified = ref(false)

  /** DEMO 流程中最近操作的合同 */
  const lastContract = ref<Contract | null>(null)
  const lastFlowId = ref<number | null>(null)

  const roleLabel = computed(() => ROLE_LABELS[role.value] || role.value)
  const displayName = computed(() => user.value?.real_name || user.value?.username || '用户')

  async function switchRole(next: AppRole) {
    loading.value = true
    try {
      clearAuthCache()
      sessionVerified.value = false
      const u = await loginAsRole(next)
      role.value = next
      user.value = u
      sessionStorage.setItem('app_role', next)
    } finally {
      loading.value = false
    }
  }

  async function initAuth() {
    if (!getToken() || !user.value) {
      await switchRole(role.value)
    }
  }

  /** 确保有效 JWT（开发 skip-auth 或 token 过期时自动演示登录） */
  async function ensureAuth() {
    if (sessionVerified.value) return
    if (getToken() && user.value) {
      try {
        await client.get('/api/v1/system/profile')
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
    switchRole,
    initAuth,
    ensureAuth,
    setLastContract,
    clearLastContractId,
    restoreLastContractId,
  }
})
