<script setup lang="ts">
import { computed } from 'vue'
import type { ChecklistMatrix, ChecklistMatrixCategory } from '@/api/ai-review'
import { checklistConclusionLabel, riskLevelLabel } from '@/utils/enumLabels'

const props = defineProps<{
  matrix: ChecklistMatrix | null
  /** 按风险等级过滤清单项（来自统计卡钻取） */
  riskFilter?: string
}>()

const emit = defineEmits<{
  riskStatClick: [level: string]
}>()

const riskStats = computed(() => props.matrix?.risk_stats || {})

const filteredCategories = computed((): ChecklistMatrixCategory[] => {
  if (!props.matrix?.categories) return []
  if (!props.riskFilter) return props.matrix.categories
  return props.matrix.categories
    .map((cat) => ({
      ...cat,
      items: cat.items.filter((item) => item.risk_level === props.riskFilter),
    }))
    .filter((cat) => cat.items.length > 0)
})

const filteredTotal = computed(() =>
  filteredCategories.value.reduce((sum, cat) => sum + cat.items.length, 0),
)

function conclusionType(c: string) {
  if (c === 'pass') return 'success'
  if (c === 'fail') return 'danger'
  if (c === 'attention') return 'warning'
  return 'warning'
}

function onRiskStatClick(level: string, count: number) {
  if (count <= 0) return
  emit('riskStatClick', level)
}
</script>

<template>
  <div v-if="matrix" class="checklist-matrix">
    <el-alert
      v-if="riskFilter"
      type="info"
      :closable="false"
      show-icon
      :title="`当前仅展示「${riskLevelLabel(riskFilter)}」清单项，共 ${filteredTotal} 条`"
      style="margin-bottom: 12px"
    />
    <el-alert
      v-if="matrix.coverage_rate != null"
      type="info"
      :closable="false"
      show-icon
      :title="`清单覆盖率 ${((matrix.coverage_rate ?? 0) * 100).toFixed(1)}%（已评估 ${matrix.mlx_evaluated_count ?? 0} / ${matrix.total} 项）`"
      style="margin-bottom: 12px"
    />
    <div class="stat-cards">
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ matrix.total }}</div>
        <div class="stat-label">总审查项</div>
      </el-card>
      <el-card
        shadow="never"
        class="stat-card stat-critical"
        :class="{ active: riskFilter === 'critical', clickable: (riskStats.critical ?? 0) > 0 }"
        @click="onRiskStatClick('critical', riskStats.critical ?? 0)"
      >
        <div class="stat-value">{{ riskStats.critical ?? 0 }}</div>
        <div class="stat-label">极高风险</div>
      </el-card>
      <el-card
        shadow="never"
        class="stat-card stat-high"
        :class="{ active: riskFilter === 'high', clickable: (riskStats.high ?? 0) > 0 }"
        @click="onRiskStatClick('high', riskStats.high ?? 0)"
      >
        <div class="stat-value">{{ riskStats.high ?? 0 }}</div>
        <div class="stat-label">高风险</div>
      </el-card>
      <el-card
        shadow="never"
        class="stat-card stat-medium"
        :class="{ active: riskFilter === 'medium', clickable: (riskStats.medium ?? 0) > 0 }"
        @click="onRiskStatClick('medium', riskStats.medium ?? 0)"
      >
        <div class="stat-value">{{ riskStats.medium ?? 0 }}</div>
        <div class="stat-label">中风险</div>
      </el-card>
      <el-card
        shadow="never"
        class="stat-card stat-low"
        :class="{ active: riskFilter === 'low', clickable: (riskStats.low ?? 0) > 0 }"
        @click="onRiskStatClick('low', riskStats.low ?? 0)"
      >
        <div class="stat-value">{{ riskStats.low ?? 0 }}</div>
        <div class="stat-label">低风险</div>
      </el-card>
    </div>
    <el-empty v-if="riskFilter && !filteredCategories.length" description="该风险等级下暂无清单项" />
    <el-collapse v-else>
      <el-collapse-item
        v-for="cat in filteredCategories"
        :key="cat.name"
        :title="`${cat.name}（${cat.items.length} 项）`"
      >
        <el-table :data="cat.items" stripe size="small">
          <el-table-column prop="id" label="序号" width="70" />
          <el-table-column prop="item" label="审查项" min-width="160" />
          <el-table-column label="结论" width="100">
            <template #default="{ row }">
              <el-tag :type="conclusionType(row.conclusion)" size="small">
                {{ checklistConclusionLabel(row.conclusion) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="风险等级" width="90">
            <template #default="{ row }">{{ riskLevelLabel(row.risk_level) }}</template>
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
  margin-top: 0;
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
.stat-card.clickable {
  cursor: pointer;
}
.stat-card.clickable:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.stat-card.active {
  outline: 2px solid var(--el-color-primary-light-5);
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
