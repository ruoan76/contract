import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { contractsApi } from '@/api/contracts'
import { ApiError } from '@/api/client'
import type { Contract } from '@/types/models'

/** 统一解析当前合同 ID（路由 param > session > store） */
export function useContractContext() {
  const route = useRoute()
  const auth = useAuthStore()

  const contractId = computed(() => {
    const param = route.params.id
    if (param) return Number(param)
    return auth.restoreLastContractId() || auth.lastContract?.id || 0
  })

  /** 加载合同；404 时清除过期的 session 合同 ID */
  async function fetchContract(id: number): Promise<Contract | null> {
    try {
      const c = await contractsApi.get(id)
      auth.setLastContract(c)
      return c
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 400)) {
        auth.clearLastContractId()
        return null
      }
      throw e
    }
  }

  return { contractId, auth, fetchContract }
}
