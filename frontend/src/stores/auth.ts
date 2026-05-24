import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppRole, ApiUser, Contract } from '@/types/models'
import { loginAsRole, clearAuthCache, getStoredUser } from '@/api/auth'
import { ROLE_LABELS } from '@/api/config'

export const useAuthStore = defineStore('auth', () => {
  const role = ref<AppRole>((sessionStorage.getItem('app_role') as AppRole) || 'drafter')
  const user = ref<ApiUser | null>(getStoredUser())
  const loading = ref(false)

  /** DEMO 流程中最近操作的合同 */
  const lastContract = ref<Contract | null>(null)
  const lastFlowId = ref<number | null>(null)

  const roleLabel = computed(() => ROLE_LABELS[role.value] || role.value)
  const displayName = computed(() => user.value?.real_name || user.value?.username || '用户')

  async function switchRole(next: AppRole) {
    loading.value = true
    try {
      clearAuthCache()
      const u = await loginAsRole(next)
      role.value = next
      user.value = u
      sessionStorage.setItem('app_role', next)
    } finally {
      loading.value = false
    }
  }

  async function initAuth() {
    if (!user.value) {
      await switchRole(role.value)
    }
  }

  function setLastContract(c: Contract | null, flowId?: number | null) {
    lastContract.value = c
    if (c) sessionStorage.setItem('last_contract_id', String(c.id))
    if (flowId != null) {
      lastFlowId.value = flowId
      sessionStorage.setItem('last_flow_id', String(flowId))
    }
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
    setLastContract,
    restoreLastContractId,
  }
})
