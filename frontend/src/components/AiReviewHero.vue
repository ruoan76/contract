<script setup lang="ts">
import { computed } from 'vue'
import type { AiReviewSummary } from '@/api/ai-review'
import type { PrimaryActionSpec, StatusBarSpec } from '@/utils/aiReviewGate'
import { orderedGates } from '@/utils/aiReviewGate'
import { aiReviewStatusLabel, gateIdLabel, gateStatusLabel, riskLevelLabel, riskLevelTagType } from '@/utils/enumLabels'
import { formatDateTime } from '@/utils/formatDate'

const props = defineProps<{
  result: AiReviewSummary | null
  statusBar: StatusBarSpec | null
  primaryAction: PrimaryActionSpec
  hideVerdict?: boolean
  showSkeleton?: boolean
  hasReport?: boolean
}>()

const emit = defineEmits<{
  primary: []
  runReview: []
  exportPdf: []
  clauseCompare: []
  submitLegalReview: []
  confirmReport: []
  gateClick: [gateKey: string]
}>()

const gateEntries = computed(() => orderedGates(props.result?.gates))

const riskLabel = computed(() => {
  if (props.hideVerdict) return '审查中'
  if (props.result?.review_status === 'failed') return '审查失败'
  return riskLevelLabel(props.result?.risk_level || 'unknown')
})

const riskType = computed(() => {
  if (props.hideVerdict) return 'info'
  if (props.result?.review_status === 'failed') return 'danger'
  return riskLevelTagType(props.result?.risk_level)
})

const verdictHint = computed(() => {
  if (props.hideVerdict || !props.result) return ''
  if (props.result.review_status === 'failed') {
    return '审查未完成，请重新触发审查或联系管理员。'
  }
  const criticalCount = (props.result.clause_reviews || []).filter(
    (c) => c.risk_level === 'critical',
  ).length
  if (criticalCount > 0) {
    return `发现 ${criticalCount} 项极高风险，请优先处理后再进入评审。`
  }
  if (props.result.review_status === 'ai_done') {
    return 'AI 审查已完成，请确认报告或提交法务评审。'
  }
  if (props.result.review_status === 'confirmed' || props.result.review_status === 'reviewed') {
    return '报告已确认，可进入评审工作台继续流程。'
  }
  return '未发现极高风险，建议进入法务评审流程。'
})

function onPrimaryClick() {
  if (props.primaryAction.disabled) return
  emit('primary')
}

function isGateClickable(status?: string) {
  return status === 'warn' || status === 'fail'
}
</script>

<template>
  <el-card shadow="never" class="ai-review-hero">
    <el-alert
      v-if="statusBar"
      :type="statusBar.type"
      :title="statusBar.title"
      :description="statusBar.description"
      show-icon
      :closable="false"
      class="hero-status"
    />

    <el-skeleton v-if="showSkeleton" animated :rows="4" class="hero-skeleton" />

    <template v-else>
      <div v-if="!hasReport && !showSkeleton" class="hero-empty">
        <p class="hero-empty-text">暂无审查报告，触发 AI 审查后将在此展示结论与下一步操作。</p>
      </div>

      <template v-else-if="result && !hideVerdict">
        <div class="verdict-row">
          <el-tag :type="riskType" size="large">{{ riskLabel }}</el-tag>
          <span class="verdict-score">风险分 <strong>{{ result.risk_score ?? '—' }}</strong></span>
          <span class="verdict-meta">
            {{ aiReviewStatusLabel(result.review_status) }}
            · {{ formatDateTime(result.review_time) }}
          </span>
        </div>
        <p v-if="verdictHint" class="verdict-hint">{{ verdictHint }}</p>
      </template>

      <div class="hero-actions">
        <el-tooltip
          :content="primaryAction.disabledReason"
          :disabled="!primaryAction.disabled || !primaryAction.disabledReason"
          placement="top"
        >
          <el-button
            type="primary"
            :disabled="primaryAction.disabled"
            :loading="primaryAction.loading"
            @click="onPrimaryClick"
          >
            {{ primaryAction.label }}
          </el-button>
        </el-tooltip>
        <el-dropdown trigger="click">
          <el-button>更多</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-if="hasReport"
                @click="emit('runReview')"
              >
                重新审查
              </el-dropdown-item>
              <el-dropdown-item @click="emit('clauseCompare')">条款比对</el-dropdown-item>
              <el-dropdown-item v-if="hasReport" @click="emit('exportPdf')">导出 PDF</el-dropdown-item>
              <el-dropdown-item
                v-if="result?.review_status === 'ai_done'"
                divided
                @click="emit('submitLegalReview')"
              >
                提交法务评审
              </el-dropdown-item>
              <el-dropdown-item
                v-if="result?.review_status === 'ai_done'"
                @click="emit('confirmReport')"
              >
                确认 AI 报告
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="gateEntries.length && !hideVerdict && hasReport" class="gate-traffic">
        <button
          v-for="[key, item] in gateEntries"
          :key="key"
          type="button"
          class="gate-chip"
          :class="[
            `gate-${item.status || 'pending'}`,
            { clickable: isGateClickable(item.status) },
          ]"
          :title="isGateClickable(item.status) ? '点击查看相关条款' : undefined"
          @click="isGateClickable(item.status) && emit('gateClick', key)"
        >
          <span class="gate-chip-label">{{ gateIdLabel(key) }}</span>
          <span class="gate-chip-status">
            {{ item.summary?.trim() || gateStatusLabel(item.status) }}
          </span>
        </button>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.ai-review-hero {
  margin-bottom: 16px;
}
.hero-status {
  margin-bottom: 12px;
}
.hero-skeleton {
  margin-bottom: 12px;
}
.hero-empty {
  text-align: center;
  padding: 12px 0 4px;
}
.hero-empty-text {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.verdict-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}
.verdict-score {
  font-size: 15px;
  color: var(--el-text-color-regular);
}
.verdict-score strong {
  color: var(--el-text-color-primary);
  font-weight: 600;
}
.verdict-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.verdict-hint {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}
.hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.gate-traffic {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.gate-chip {
  flex: 1;
  min-width: 120px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  text-align: left;
  font: inherit;
}
.gate-chip.clickable {
  cursor: pointer;
}
.gate-chip.clickable:hover {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.gate-chip-label {
  display: block;
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 2px;
}
.gate-chip-status {
  display: block;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
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
@media (max-width: 900px) {
  .gate-chip {
    min-width: calc(50% - 8px);
  }
}
</style>
