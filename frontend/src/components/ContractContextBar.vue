<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import StatusTag from '@/components/StatusTag.vue'
import { useAuthStore } from '@/stores/auth'
import { suggestNextAction } from '@/utils/contractLifecycle'
import type { Contract } from '@/types/models'

const props = defineProps<{
  contract: Contract | null
}>()

const router = useRouter()
const auth = useAuthStore()

const nextAction = computed(() => suggestNextAction(props.contract, auth.role))

const secondaryRoutes = [
  { name: 'approval-history', label: '审批历史' },
  { name: 'review-history', label: '评审历史', query: true },
  { name: 'ai-review', label: 'AI 报告' },
  { name: 'review-workspace', label: '评审工作台' },
  { name: 'revision-workspace', label: '修订' },
]

function go(name: string, query?: Record<string, string>) {
  if (!props.contract) return
  router.push({ name, params: { id: props.contract.id }, query })
}

function goReviewHistory() {
  if (!props.contract) return
  router.push({
    name: 'review-center',
    query: { tab: 'history', contractId: String(props.contract.id) },
  })
}

function goNext() {
  const action = nextAction.value
  if (!action || !props.contract) return
  router.push({
    name: action.route,
    params: action.params,
    query: action.query,
  })
}

function goSecondary(item: (typeof secondaryRoutes)[number]) {
  if (item.query) {
    goReviewHistory()
    return
  }
  go(item.name)
}
</script>

<template>
  <div v-if="contract" class="context-bar">
    <div class="context-left">
      <el-button link @click="router.push({ name: 'contracts' })">← 返回列表</el-button>
      <span class="context-title">{{ contract.title }}</span>
      <StatusTag :status="contract.status" />
    </div>
    <div class="context-actions">
      <el-button v-if="nextAction" type="primary" size="small" @click="goNext">
        {{ nextAction.label }}
      </el-button>
      <el-dropdown trigger="click">
        <el-button size="small">更多</el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in secondaryRoutes"
              :key="item.name"
              @click="goSecondary(item)"
            >
              {{ item.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style scoped>
.context-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}
.context-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.context-title {
  font-size: 16px;
  font-weight: 600;
}
.context-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
