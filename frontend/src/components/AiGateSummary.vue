<script setup lang="ts">
import type { AiGateItem } from '@/api/ai-review'

defineProps<{
  gates?: Record<string, AiGateItem>
}>()

const labels: Record<string, string> = {
  gate_validity: '效力',
  gate_subject: '主体',
  gate_clause: '条款',
  gate_consistency: '一致性',
  gate_output: '输出',
}
</script>

<template>
  <el-card v-if="gates" shadow="never" class="gate-card">
    <template #header>效力与门禁（审查优先顺序）</template>
    <div class="gate-grid">
      <div
        v-for="(item, key) in gates"
        :key="key"
        class="gate-cell"
        :class="`gate-${item.status || 'pending'}`"
      >
        <div class="gate-label">{{ labels[key] || key }}</div>
        <div class="gate-status">{{ item.summary || item.status || '—' }}</div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.gate-card {
  margin-bottom: 16px;
}
.gate-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
@media (max-width: 900px) {
  .gate-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.gate-cell {
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  font-size: 12px;
}
.gate-label {
  color: #6b7280;
  margin-bottom: 4px;
}
.gate-status {
  font-weight: 600;
}
.gate-pass {
  background: #ecfdf5;
  border-color: #a7f3d0;
}
.gate-warn {
  background: #fffbeb;
  border-color: #fde68a;
}
.gate-fail {
  background: #fef2f2;
  border-color: #fecaca;
}
.gate-pending {
  background: #f9fafb;
}
</style>
