<script setup lang="ts">
import { computed } from 'vue'
import type { ChecklistMatrix } from '@/api/ai-review'

const props = defineProps<{
  matrix: ChecklistMatrix | null
}>()

const riskStats = computed(() => props.matrix?.risk_stats || {})

function conclusionLabel(c: string) {
  if (c === 'pass') return '通过'
  if (c === 'fail') return '未通过'
  if (c === 'attention') return '需关注'
  return '待确认'
}

function conclusionType(c: string) {
  if (c === 'pass') return 'success'
  if (c === 'fail') return 'danger'
  if (c === 'attention') return 'warning'
  return 'warning'
}

function riskLabel(level?: string) {
  const map: Record<string, string> = {
    critical: '极高',
    high: '高',
    medium: '中',
    low: '低',
  }
  return map[level || ''] || level || '—'
}
</script>

<template>
  <div v-if="matrix" class="checklist-matrix">
    <el-alert
      v-if="matrix.coverage_rate != null"
      type="info"
      :closable="false"
      show-icon
      :title="`MLX 清单覆盖率 ${((matrix.coverage_rate ?? 0) * 100).toFixed(1)}%（已评估 ${matrix.mlx_evaluated_count ?? 0} / ${matrix.total} 项）`"
      style="margin-bottom: 12px"
    />
    <div class="stat-cards">
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ matrix.total }}</div>
        <div class="stat-label">总审查项</div>
      </el-card>
      <el-card shadow="never" class="stat-card stat-critical">
        <div class="stat-value">{{ riskStats.critical ?? 0 }}</div>
        <div class="stat-label">极高风险</div>
      </el-card>
      <el-card shadow="never" class="stat-card stat-high">
        <div class="stat-value">{{ riskStats.high ?? 0 }}</div>
        <div class="stat-label">高风险</div>
      </el-card>
      <el-card shadow="never" class="stat-card stat-medium">
        <div class="stat-value">{{ riskStats.medium ?? 0 }}</div>
        <div class="stat-label">中风险</div>
      </el-card>
      <el-card shadow="never" class="stat-card stat-low">
        <div class="stat-value">{{ riskStats.low ?? 0 }}</div>
        <div class="stat-label">低风险</div>
      </el-card>
    </div>
    <el-collapse>
      <el-collapse-item
        v-for="cat in matrix.categories"
        :key="cat.name"
        :title="`${cat.name}（${cat.items.length} 项）`"
      >
        <el-table :data="cat.items" stripe size="small">
          <el-table-column prop="id" label="序号" width="70" />
          <el-table-column prop="item" label="审查项" min-width="160" />
          <el-table-column label="结论" width="100">
            <template #default="{ row }">
              <el-tag :type="conclusionType(row.conclusion)" size="small">
                {{ conclusionLabel(row.conclusion) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="风险等级" width="90">
            <template #default="{ row }">{{ riskLabel(row.risk_level) }}</template>
          </el-table-column>
          <el-table-column prop="ai_suggestion" label="AI 分析建议" min-width="200" show-overflow-tooltip />
          <el-table-column prop="evidence" label="原文证据" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.checklist-matrix {
  margin-top: 16px;
}
.stat-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1;
  min-width: 100px;
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
}
.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.stat-critical .stat-value {
  color: var(--el-color-danger);
}
.stat-high .stat-value {
  color: var(--el-color-danger);
}
.stat-medium .stat-value {
  color: var(--el-color-warning);
}
.stat-low .stat-value {
  color: var(--el-color-success);
}
</style>
