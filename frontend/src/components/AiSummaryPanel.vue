<script setup lang="ts">
import { computed, ref } from 'vue'
import { buildDimensionBlocks, type DimensionBlock } from '@/utils/aiRecommendation'
import type { AiSummaryPanelData } from '@/utils/aiRecommendation'
import {
  aiReviewStatusLabel,
  dimensionStatusTagType,
  riskLevelLabel,
  riskLevelTagType,
} from '@/utils/enumLabels'
const props = defineProps<{
  summary: AiSummaryPanelData
  showConfirmButton?: boolean
}>()

const emit = defineEmits<{
  viewReport: []
  confirmReport: []
}>()

const expandedKeys = ref<Set<string>>(new Set())

const riskTagType = computed(() => riskLevelTagType(props.summary.risk_level))

const dimensionBlocks = computed(() =>
  buildDimensionBlocks({
    dimensionSummaries: props.summary.dimension_summaries,
    recommendation: props.summary.recommendation,
  }),
)

const topClauses = computed(() => props.summary.top_clauses || [])

function toggleExpand(key: string) {
  const next = new Set(expandedKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedKeys.value = next
}

function isExpanded(key: string) {
  return expandedKeys.value.has(key)
}

function needsExpand(block: DimensionBlock) {
  return block.content.length > 180
}

function statusLabel(status?: string) {
  if (status === 'failed') return '分析失败'
  if (status === 'degraded') return '部分降级'
  if (status === 'ok') return '正常'
  return status || ''
}
</script>

<template>
  <el-card shadow="never" class="ai-summary-panel">
    <template #header>
      <div class="panel-header">
        <span>AI 初筛摘要</span>
        <el-button link type="primary" @click="emit('viewReport')">查看完整报告</el-button>
      </div>
    </template>

    <div class="conclusion-row">
      <el-tag :type="riskTagType" size="large">{{ riskLevelLabel(summary.risk_level) }}</el-tag>
      <span class="conclusion-meta">
        <span class="meta-item">风险分 <strong>{{ summary.risk_score ?? '—' }}</strong></span>
        <span class="meta-item">状态 {{ aiReviewStatusLabel(summary.review_status) }}</span>
      </span>
    </div>

    <div v-if="topClauses.length" class="priority-block">
      <div class="block-title">优先关注</div>
      <el-table :data="topClauses" size="small" stripe class="priority-table">
        <el-table-column prop="clause" label="条款" min-width="120" />
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="riskLevelTagType(row.risk_level)" size="small">
              {{ riskLevelLabel(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="suggestion" label="建议" min-width="200" show-overflow-tooltip />
      </el-table>
    </div>

    <div v-if="dimensionBlocks.length" class="dimension-grid">
      <el-row :gutter="12">
        <el-col
          v-for="block in dimensionBlocks"
          :key="block.key"
          :xs="24"
          :md="12"
          class="dimension-col"
        >
          <div class="dimension-card">
            <div class="dimension-card-head">
              <span class="dimension-title">{{ block.label }}</span>
              <span v-if="block.score != null" class="dimension-score">{{ block.score }} 分</span>
              <el-tag
                v-if="block.status && block.status !== 'ok'"
                :type="dimensionStatusTagType(block.status)"
                size="small"
              >
                {{ statusLabel(block.status) }}
              </el-tag>
            </div>
            <p
              class="dimension-body"
              :class="{ collapsed: needsExpand(block) && !isExpanded(block.key) }"
            >
              {{ block.content }}
            </p>
            <el-button
              v-if="needsExpand(block)"
              link
              type="primary"
              size="small"
              class="expand-btn"
              @click="toggleExpand(block.key)"
            >
              {{ isExpanded(block.key) ? '收起' : '展开全文' }}
            </el-button>
          </div>
        </el-col>
      </el-row>
    </div>

    <div v-if="summary.review_id && showConfirmButton" class="panel-actions">
      <el-button
        v-if="summary.review_status === 'ai_done'"
        size="small"
        type="warning"
        @click="emit('confirmReport')"
      >
        确认 AI 报告
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.ai-summary-panel {
  margin-bottom: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.conclusion-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.conclusion-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.meta-item strong {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.priority-block {
  margin-bottom: 16px;
}

.dimension-grid {
  margin-top: 4px;
}

.dimension-col {
  margin-bottom: 12px;
}

.dimension-card {
  height: 100%;
  padding: 12px 14px;
  background: var(--el-fill-color-lighter);
  border-left: 3px solid var(--el-color-primary-light-5);
  border-radius: 4px;
}

.dimension-card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.dimension-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.dimension-score {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dimension-body {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
  word-break: break-word;
}

.dimension-body.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.expand-btn {
  margin-top: 4px;
  padding: 0;
}

.panel-actions {
  margin-top: 12px;
}
</style>
