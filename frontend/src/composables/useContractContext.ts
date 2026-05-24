import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/** 统一解析当前合同 ID（路由 param > session > store） */
export function useContractContext() {
  const route = useRoute()
  const auth = useAuthStore()

  const contractId = computed(() => {
    const param = route.params.id
    if (param) return Number(param)
    return auth.restoreLastContractId() || auth.lastContract?.id || 0
  })

  return { contractId, auth }
}
