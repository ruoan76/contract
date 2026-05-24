<script setup lang="ts">
import { useRouter } from 'vue-router'
import StatusTag from '@/components/StatusTag.vue'
import type { Contract } from '@/types/models'

const props = defineProps<{
  contract: Contract | null
}>()

const router = useRouter()

function go(name: string) {
  if (!props.contract) return
  router.push({ name, params: { id: props.contract.id } })
}

function goReviewHistory() {
  if (!props.contract) return
  router.push({ name: 'review-history', query: { contractId: String(props.contract.id) } })
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
      <el-button size="small" @click="go('approval-history')">审批历史</el-button>
      <el-button size="small" @click="goReviewHistory">评审历史</el-button>
      <el-button size="small" @click="go('ai-review')">AI 报告</el-button>
      <el-button size="small" @click="go('review-workspace')">评审工作台</el-button>
      <el-button size="small" @click="go('revision-workspace')">修订</el-button>
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
