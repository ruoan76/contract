<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiReviewApi,
  groupClausesByDimension,
  labelName,
  LABEL_OPTIONS,
  type AiReviewSummary,
} from '@/api/ai-review'
import { ApiError } from '@/api/client'
import { useContractContext } from '@/composables/useContractContext'
import ContractContextBar from '@/components/ContractContextBar.vue'
import AiGateSummary from '@/components/AiGateSummary.vue'
import AiChecklistMatrix from '@/components/AiChecklistMatrix.vue'
import type { Contract } from '@/types/models'
import type { ChecklistMatrix } from '@/api/ai-review'

const router = useRouter()
const { contractId, fetchContract } = useContractContext()
const contract = ref<Contract | null>(null)
const contractMissing = ref(false)
const result = ref<AiReviewSummary | null>(null)
const checklistMatrix = ref<ChecklistMatrix | null>(null)
const loading = ref(false)
const polling = ref(false)
const filterRiskLevel = ref('')
const filterDimension = ref('')
const filterLabelId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
const detailCollapse = ref<string[]>([])

const riskLabel = computed(() => {
  const level = result.value?.risk_level || 'unknown'
  const map: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '极高风险',
  }
  return map[level] || level
})

const riskType = computed(() => {
  const level = result.value?.risk_level
  if (level === 'critical') return 'danger'
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  return 'success'
})

const filteredClauses = computed(() => {
  let items = result.value?.clause_reviews || []
  if (filterRiskLevel.value) {
    items = items.filter((c) => c.risk_level === filterRiskLevel.value)
  }
  if (filterDimension.value) {
    items = items.filter((c) => c.dimension === filterDimension.value)
  }
  if (filterLabelId.value) {
    items = items.filter((c) => c.label_id === filterLabelId.value)
  }
  return items
})

const dimensionGroups = computed(() => groupClausesByDimension(filteredClauses.value))

const dimensionOptions = computed(() => {
  const dims = new Set((result.value?.clause_reviews || []).map((c) => c.dimension).filter(Boolean))
  return [...dims] as string[]
})

const isReviewing = computed(
  () => result.value?.review_status === 'reviewing' || result.value?.review_status === 'pending',
)

const ENGINE_DIMENSION_LABELS: Record<string, string> = {
  compliance: '合规性',
  risk: '风险条款',
  financial: '财务条款',
  capability: '履约能力',
  anomaly: '异常检测',
}

function dimensionLabel(key: string) {
  return ENGINE_DIMENSION_LABELS[key] || key
}

const failedDimensions = computed(() => {
  const detail = result.value?.completeness_detail as
    | { failed_dimensions?: string[] }
    | undefined
  if (detail?.failed_dimensions?.length) {
    return detail.failed_dimensions
  }
  const dims = (result.value?.summary as { dimensions?: { dimension?: string; status?: string }[] })
    ?.dimensions
  if (!dims?.length) return []
  return dims
    .filter((d) => d.status === 'failed' && d.dimension)
    .map((d) => d.dimension as string)
})

const pinnedCriticalIssues = computed(() => {
  const items = result.value?.clause_reviews || []
  return items.filter((c) => c.risk_level === 'critical')
})

const truncationHint = computed(() => {
  const summary = result.value?.summary as
    | { clause_reviews_truncated?: boolean; issues_total?: number; clause_reviews_count?: number }
    | undefined
  if (!summary?.clause_reviews_truncated) return ''
  return `条款列表已截断展示 ${summary.clause_reviews_count ?? '?'} / ${summary.issues_total ?? '?'} 条，完整数据请导出或查看清单矩阵。`
})

const completenessAlert = computed(() => {
  const c =
    result.value?.review_completeness ||
    (result.value?.summary as { review_completeness?: string } | undefined)?.review_completeness
  if (!c || c === 'full') return null
  const failedNames = failedDimensions.value
    .map((d) => dimensionLabel(d))
    .join('、')
  const failedPart = failedNames ? `未成功维度：${failedNames}。` : ''
  if (c === 'failed') {
    return {
      type: 'error' as const,
      title: 'AI 审查失败',
      desc: `请稍后重试或联系管理员，暂勿仅依据风险分决策。${failedPart}`,
    }
  }
  return {
    type: 'warning' as const,
    title: '审查未完整完成',
    desc: `部分维度未成功分析，结论仅供参考，请法务重点复核。${failedPart}`,
  }
})

async function load() {
  contractMissing.value = false
  if (!contractId.value) {
    contract.value = null
      result.value = null
      checklistMatrix.value = null
      return
  }
  loading.value = true
  try {
    const c = await fetchContract(contractId.value)
    if (!c) {
      contractMissing.value = true
      contract.value = null
      result.value = null
      ElMessage.warning('合同不存在，请从列表重新选择')
      return
    }
    contract.value = c
    try {
      const [latest, matrix] = await Promise.all([
        aiReviewApi.latest(contractId.value),
        aiReviewApi.checklistMatrix(contractId.value).catch(() => null),
      ])
      result.value = latest
      checklistMatrix.value = matrix
    } catch {
      result.value = null
      checklistMatrix.value = null
    }
  } catch (e) {
    console.error(e)
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  polling.value = false
}

function startPolling() {
  stopPolling()
  polling.value = true
  pollTimer = setInterval(async () => {
    if (!contractId.value) return
    try {
      const [latest, matrix] = await Promise.all([
        aiReviewApi.latest(contractId.value),
        aiReviewApi.checklistMatrix(contractId.value).catch(() => null),
      ])
      result.value = latest
      checklistMatrix.value = matrix
      if (!isReviewing.value) {
        stopPolling()
        ElMessage.success('AI 审查已完成')
      }
    } catch {
      /* 轮询中忽略 */
    }
  }, 2000)
}

onMounted(load)
watch(contractId, load)
onUnmounted(stopPolling)

async function runReview() {
  if (!contractId.value) {
    ElMessage.warning('无合同 ID')
    return
  }
  loading.value = true
  try {
    await aiReviewApi.review(contractId.value)
    await load()
    if (isReviewing.value) {
      startPolling()
      ElMessage.info('审查进行中，正在轮询结果…')
    } else {
      ElMessage.success('AI 审查已完成')
    }
  } catch (e) {
    const msg =
      e instanceof ApiError
        ? e.message
        : e instanceof Error
          ? e.message
          : '审查失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function exportPdf() {
  if (!result.value?.review_id) {
    window.print()
    return
  }
  aiReviewApi
    .downloadReport(result.value.review_id, 'pdf')
    .then(({ blob, filename, contentType }) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      if (contentType.includes('html')) {
        ElMessage.warning('PDF 引擎不可用，已下载 HTML 报告，可用浏览器打印为 PDF')
      } else {
        ElMessage.success('报告已下载')
      }
    })
    .catch((e) => {
      ElMessage.error(e instanceof Error ? e.message : '报告下载失败')
    })
}

function submitLegalReview() {
  if (!contractId.value) {
    ElMessage.warning('无合同 ID')
    return
  }
  router.push({ name: 'review-workspace', params: { id: String(contractId.value) } })
}

async function confirmReport() {
  if (!result.value?.review_id) return
  try {
    await aiReviewApi.confirm(result.value.review_id)
    await load()
    ElMessage.success('AI 报告已确认')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '确认失败')
  }
}

function goClauseCompare() {
  if (!contractId.value) return
  router.push({ name: 'clause-compare', params: { id: String(contractId.value) } })
}

async function sendFeedback(type: 'false_positive' | 'false_negative') {
  if (!result.value?.review_id) return
  try {
    await aiReviewApi.feedback(result.value.review_id, type, 'Vue 前端反馈')
    ElMessage.success(type === 'false_positive' ? '已标记误报' : '已标记漏报')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '反馈失败')
  }
}
</script>

<template>
  <div v-loading="loading" class="page-card ai-report">
    <ContractContextBar :contract="contract" />
    <el-alert
      v-if="completenessAlert"
      :type="completenessAlert.type"
      :title="completenessAlert.title"
      :description="completenessAlert.desc"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />
    <el-alert
      v-if="truncationHint"
      type="info"
      :title="truncationHint"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />
    <AiGateSummary v-if="result?.gates" :gates="result.gates" />
    <div class="page-toolbar">
      <div class="toolbar-actions">
        <el-tag v-if="polling" type="info">审查中…</el-tag>
        <el-button type="primary" @click="runReview">触发审查</el-button>
        <el-button v-if="contractId" @click="goClauseCompare">条款比对</el-button>
        <el-button v-if="result" type="success" @click="submitLegalReview">提交法务评审</el-button>
        <el-button
          v-if="result?.review_id && result.review_status === 'ai_done'"
          type="warning"
          @click="confirmReport"
        >
          确认 AI 报告
        </el-button>
        <el-button v-if="result" @click="exportPdf">导出 PDF</el-button>
      </div>
    </div>
    <el-empty v-if="!contractId" description="请从合同列表选择一份合同">
      <el-button type="primary" @click="router.push({ name: 'contracts' })">去合同列表</el-button>
    </el-empty>
    <el-empty v-else-if="contractMissing" description="合同不存在，可能已被删除或数据库已重置">
      <el-button type="primary" @click="router.push({ name: 'contracts' })">去合同列表</el-button>
    </el-empty>
    <el-empty v-else-if="!result" description="暂无审查报告，请先触发审查" />
    <template v-else>
      <el-card shadow="never" class="conclusion-card">
        <div class="conclusion-row">
          <el-tag :type="riskType" size="large">{{ riskLabel }}</el-tag>
          <span class="conclusion-score">风险分 {{ result.risk_score ?? '—' }}</span>
        </div>
        <p v-if="result.recommendation" class="conclusion-rec">{{ result.recommendation }}</p>
        <p v-else-if="pinnedCriticalIssues.length" class="conclusion-rec">
          发现 {{ pinnedCriticalIssues.length }} 项需优先处理的问题，请查看下方列表。
        </p>
        <p v-else class="conclusion-rec">未发现 critical 级风险，建议进入法务评审流程。</p>
      </el-card>

      <el-card
        v-if="pinnedCriticalIssues.length"
        shadow="never"
        class="critical-block"
      >
        <template #header>需优先处理</template>
        <el-table :data="pinnedCriticalIssues" stripe size="small">
          <el-table-column prop="clause" label="条款" min-width="140" />
          <el-table-column label="标签" width="110">
            <template #default="{ row }">{{ labelName(row.label_id) }}</template>
          </el-table-column>
          <el-table-column prop="suggestion" label="建议" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-card>

      <div class="filters">
        <el-select v-model="filterRiskLevel" clearable placeholder="风险等级" style="width: 140px">
          <el-option label="极高风险" value="critical" />
          <el-option label="高风险" value="high" />
          <el-option label="中风险" value="medium" />
          <el-option label="低风险" value="low" />
        </el-select>
        <el-select v-model="filterDimension" clearable placeholder="审查维度" style="width: 180px">
          <el-option v-for="d in dimensionOptions" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="filterLabelId" clearable placeholder="风险标签" style="width: 160px">
          <el-option
            v-for="opt in LABEL_OPTIONS"
            :key="opt.id"
            :label="opt.name"
            :value="opt.id"
          />
        </el-select>
      </div>
      <el-descriptions :column="2" border style="margin-top: 12px">
        <el-descriptions-item label="状态">{{ result.review_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审查时间">{{ result.review_time ?? '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-collapse v-model="detailCollapse" style="margin-top: 16px">
        <el-collapse-item title="审查门禁与清单详情" name="matrix">
          <el-card shadow="never" class="checklist-section">
            <AiChecklistMatrix :matrix="checklistMatrix" />
            <el-empty v-if="!checklistMatrix" description="暂无清单矩阵数据" />
          </el-card>
        </el-collapse-item>
        <el-collapse-item title="规则引擎与维度明细" name="details">
          <el-card v-if="result.rule_violations?.length" shadow="never" class="rules-block">
            <template #header>采购规则引擎</template>
            <el-table :data="result.rule_violations" stripe size="small">
              <el-table-column prop="rule_name" label="规则名称" min-width="140" />
              <el-table-column prop="severity" label="严重度" width="100" />
              <el-table-column prop="message" label="说明" min-width="200" />
            </el-table>
          </el-card>
          <div v-for="group in dimensionGroups" :key="group.key" class="dimension-block">
            <h3>{{ group.label }}</h3>
            <el-table :data="group.items" stripe size="small">
              <el-table-column prop="clause" label="条款" min-width="140" />
              <el-table-column label="标签" width="110">
                <template #default="{ row }">{{ labelName(row.label_id) }}</template>
              </el-table-column>
              <el-table-column prop="risk_level" label="风险" width="90" />
              <el-table-column prop="suggestion" label="建议" min-width="180" show-overflow-tooltip />
            </el-table>
          </div>
        </el-collapse-item>
      </el-collapse>

      <div style="margin-top: 16px">
        <el-button size="small" @click="sendFeedback('false_positive')">标记误报</el-button>
        <el-button size="small" @click="sendFeedback('false_negative')">标记漏报</el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.conclusion-card {
  margin-bottom: 16px;
}
.conclusion-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.conclusion-score {
  font-size: 15px;
  color: #374151;
}
.conclusion-rec {
  margin: 12px 0 0;
  font-size: 14px;
  color: #4b5563;
  line-height: 1.5;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.checklist-section {
  margin-top: 16px;
}
.critical-block {
  margin-top: 16px;
  border-color: var(--el-color-danger-light-5);
}
.rules-block {
  margin-top: 16px;
}
.score-floor-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-color-warning);
  font-weight: normal;
}
.dimension-block {
  margin-top: 20px;
}
.dimension-block h3 {
  font-size: 15px;
  margin: 0 0 8px;
}
@media print {
  .toolbar-actions,
  .filters,
  .el-button {
    display: none !important;
  }
}
.reasoning-cell {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.evidence-quote {
  font-size: 12px;
  color: var(--el-text-color-regular);
  font-style: italic;
  border-left: 3px solid var(--el-color-primary-light-5);
  padding-left: 8px;
}
</style>
