<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const type = computed(() => {
  const s = props.status
  if (s === 'sealed' || s === 'archived' || s === 'approved') return 'success'
  if (s === 'pending' || s === 'reviewing') return 'warning'
  if (s === 'rejected' || s === 'blacklisted') return 'danger'
  return 'info'
})

const label = computed(() => {
  const map: Record<string, string> = {
    draft: '草稿',
    pending: '待审批',
    approved: '已通过',
    sealed: '已用印',
    archived: '已归档',
    rejected: '已拒绝',
  }
  return map[props.status] || props.status
})
</script>

<template>
  <el-tag :type="type" size="small">{{ label }}</el-tag>
</template>
