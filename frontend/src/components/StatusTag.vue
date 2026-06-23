<script setup lang="ts">
import { computed } from 'vue'
import { CONTRACT_STATUS_LABELS } from '@/utils/enumLabels'

const props = defineProps<{ status: string }>()

const type = computed(() => {
  const s = props.status
  if (s === 'sealed' || s === 'archived' || s === 'approved' || s === 'signed' || s === 'executing') {
    return 'success'
  }
  if (s === 'pending' || s === 'reviewing' || s === 'in_review' || s === 'returned' || s === 'seal_pending') {
    return 'warning'
  }
  if (s === 'rejected' || s === 'blacklisted' || s === 'terminated' || s === 'void') {
    return 'danger'
  }
  return 'info'
})

const label = computed(() => CONTRACT_STATUS_LABELS[props.status] || props.status)
</script>

<template>
  <el-tag :type="type" size="small">{{ label }}</el-tag>
</template>
