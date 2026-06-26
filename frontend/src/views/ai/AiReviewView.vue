<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  aiReviewApi,
  groupClausesByDimension,
  labelName,
  LABEL_OPTIONS,
  type AiClauseReview,
  type AiReviewSummary,
  type ChecklistMatrix,
} from '@/api/ai-review'
import { ApiError } from '@/api/client'
import { useContractContext } from '@/composables/useContractContext'
import { useAuthStore } from '@/stores/auth'
import ContractContextBar from '@/components/ContractContextBar.vue'
import AiReviewHero from '@/components/AiReviewHero.vue'
import AiChecklistMatrix from '@/components/AiChecklistMatrix.vue'
import AiSummaryPanel from '@/components/AiSummaryPanel.vue'
import type { Contract } from '@/types/models'
import {
  aiDimensionLabel,
  riskLevelLabel,
} from '@/utils/enumLabels'
import {
  buildPrimaryAction,
  buildStatusBar,
  GATE_DRILL_FILTERS,
} from '@/utils/aiReviewGate'
import { toSummaryPanelData } from '@/utils/aiReviewSummary'

const router = useRouter()
const auth = useAuthStore()
const { contractId, fetchContract } = useContractContext()
const contract = ref<Contract | null>(null)
const contractMissing = ref(false)
const result = ref<AiReviewSummary | null>(null)
const checklistMatrix = ref<ChecklistMatrix | null>(null)
const initialLoading = ref(false)
const reviewingLoading = ref(false)
const polling = ref(false)
const filterRiskLevel = ref('')
const filterDimension = ref('')
const filterLabelId = ref('')
const filterGateId = ref('')
const matrixRiskFilter = ref('')
const activeTab = ref('summary')
let pollTimer: ReturnType<typeof setInterval> | null = null

const isReviewing = computed(
  () => result.value?.review_status === 'reviewing' || result.value?.review_status === 'pending',
)

const hideVerdict = computed(() => isReviewing.value || reviewingLoading.value)

const summaryPanelData = computed(() => toSummaryPanelData(result.value))

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
  if (filterGateId.value) {
    items = items.filter((c) => c.gate_id === filterGateId.value)
  }
  return items
})

const dimensionGroups = computed(() => groupClausesByDimension(filteredClauses.value))

const dimensionOptions = computed(() => {
  const dims = new Set((result.value?.clause_reviews || []).map((c) => c.dimension).filter(Boolean))
  return [...dims] as string[]
})

const totalClauseCount = computed(() => result.value?.clause_reviews?.length ?? 0)
const filteredClauseCount = computed(() => filteredClauses.value.length)
const hasActiveClauseFilters = computed(
  () =>
    Boolean(
      filterRiskLevel.value || filterDimension.value || filterLabelId.value || filterGateId.value,
    ),
)
const clauseFilterSummary = computed(() => {
  if (!hasActiveClauseFilters.value) return ''
  return `已筛选 ${filteredClauseCount.value} / ${totalClauseCount.value} 条条款`
})
const showFilteredClauseEmpty = computed(
  () =>
    hasActiveClauseFilters.value &&
    filteredClauseCount.value === 0 &&
    totalClauseCount.value > 0,
)

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

const truncationHint = computed(() => {
  const summary = result.value?.summary as
    | { clause_reviews_truncated?: boolean; issues_total?: number; clause_reviews_count?: number }
    | undefined
  if (!summary?.clause_reviews_truncated) return ''
  return `条款列表已截断展示 ${summary.clause_reviews_count ?? '?'} / ${summary.issues_total ?? '?'} 条，完整数据请导出或查看清单矩阵。`
})

const statusBar = computed(() =>
  buildStatusBar(result.value, {
    isReviewing: isReviewing.value,
    polling: polling.value,
    failedDimensions: failedDimensions.value,
    truncationHint: hideVerdict.value ? undefined : truncationHint.value || undefined,
  }),
)

const primaryAction = computed(() =>
  buildPrimaryAction(result.value, auth.role, {
    isReviewing: isReviewing.value,
    polling: polling.value,
    hasContract: Boolean(contractId.value),
  }),
)

const matrixTabLabel = computed(() => {
  const total = checklistMatrix.value?.total
  return total != null ? `清单矩阵（${total} 项）` : '清单矩阵'
})

const clausesTabLabel = computed(() => {
  if (!totalClauseCount.value && !result.value?.rule_violations?.length) return '条款明细'
  if (hasActiveClauseFilters.value) {
    return `条款明细（${filteredClauseCount.value}/${totalClauseCount.value}）`
  }
  if (totalClauseCount.value) return `条款明细（${totalClauseCount.value} 条）`
  return '条款明细'
})

function pickDefaultTab() {
  if (hasActiveClauseFilters.value) {
    activeTab.value = 'clauses'
    return
  }
  const clauses = result.value?.clause_reviews || []
  const hasHighRisk = clauses.some((c) => c.risk_level === 'critical' || c.risk_level === 'high')
  if (hasHighRisk || summaryPanelData.value?.top_clauses?.length) {
    activeTab.value = 'summary'
    return
  }
  if (!clauses.length && checklistMatrix.value?.total) {
    activeTab.value = 'matrix'
    return
  }
  activeTab.value = 'summary'
}

watch([filterRiskLevel, filterDimension, filterLabelId, filterGateId], () => {
  if (!hasActiveClauseFilters.value) return
  activeTab.value = 'clauses'
})

watch(
  () => result.value?.review_id,
  () => {
    if (result.value && !isReviewing.value) pickDefaultTab()
  },
)

async function fetchLatestReview() {
  if (!contractId.value) return
  const [latest, matrix] = await Promise.all([
    aiReviewApi.latest(contractId.value),
    aiReviewApi.checklistMatrix(contractId.value).catch(() => null),
  ])
  result.value = latest
  checklistMatrix.value = matrix
}

function ensurePollingIfReviewing() {
  if (isReviewing.value) {
    startPolling()
  } else {
    stopPolling()
  }
}

async function load() {
  contractMissing.value = false
  if (!contractId.value) {
    contract.value = null
    result.value = null
    checklistMatrix.value = null
    stopPolling()
    return
  }
  initialLoading.value = true
  try {
    const c = await fetchContract(contractId.value)
    if (!c) {
      contractMissing.value = true
      contract.value = null
      result.value = null
      stopPolling()
      ElMessage.warning('合同不存在，请从列表重新选择')
      return
    }
    contract.value = c
    try {
      await fetchLatestReview()
      ensurePollingIfReviewing()
      pickDefaultTab()
    } catch {
      result.value = null
      checklistMatrix.value = null
      stopPolling()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    initialLoading.value = false
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
      await fetchLatestReview()
      const status = result.value?.review_status
      if (status === 'failed') {
        stopPolling()
        reviewingLoading.value = false
        ElMessage.error('AI 审查失败，请稍后重试')
        return
      }
      if (!isReviewing.value) {
        stopPolling()
        reviewingLoading.value = false
        pickDefaultTab()
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
  reviewingLoading.value = true
  stopPolling()
  try {
    const started = await aiReviewApi.review(contractId.value)
    await fetchLatestReview()
    if (started?.status === 'reviewing' || isReviewing.value) {
      startPolling()
      ElMessage.info('审查进行中，正在生成报告…')
    } else {
      stopPolling()
      reviewingLoading.value = false
      pickDefaultTab()
      ElMessage.success('AI 审查已完成')
    }
  } catch (e) {
    reviewingLoading.value = false
    const msg =
      e instanceof ApiError
        ? e.message
        : e instanceof Error
          ? e.message
          : '审查失败'
    ElMessage.error(msg)
    try {
      await fetchLatestReview()
      ensurePollingIfReviewing()
    } catch {
      /* 忽略刷新失败 */
    }
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

function onPrimaryAction() {
  const action = primaryAction.value.action
  if (action === 'runReview') runReview()
  else if (action === 'confirmReport') confirmReport()
  else if (action === 'submitLegalReview') submitLegalReview()
  else if (action === 'goReviewWorkspace') submitLegalReview()
}

function onGateClick(gateKey: string) {
  const drill = GATE_DRILL_FILTERS[gateKey]
  filterRiskLevel.value = drill?.riskLevel || ''
  filterGateId.value = drill?.gateId || ''
  filterDimension.value = ''
  filterLabelId.value = ''
  activeTab.value = 'clauses'
}

function onMatrixRiskClick(level: string) {
  matrixRiskFilter.value = matrixRiskFilter.value === level ? '' : level
  activeTab.value = 'matrix'
}

function clearClauseFilters() {
  filterRiskLevel.value = ''
  filterDimension.value = ''
  filterLabelId.value = ''
  filterGateId.value = ''
}

async function sendClauseFeedback(
  type: 'false_positive' | 'false_negative',
  row: AiClauseReview,
) {
  if (!result.value?.review_id) return
  const parts = [row.clause || '未命名条款']
  if (row.label_id) parts.push(`标签 ${labelName(row.label_id)}`)
  if (row.dimension) parts.push(`维度 ${aiDimensionLabel(row.dimension)}`)
  try {
    await aiReviewApi.feedback(result.value.review_id, type, parts.join(' · '))
    ElMessage.success(type === 'false_positive' ? '已标记误报' : '已标记漏报')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '反馈失败')
  }
}
</script>

<template>
  <div v-loading="initialLoading" class="page-card ai-report">
    <ContractContextBar :contract="contract" />

    <el-empty v-if="!contractId" description="请从合同列表选择一份合同">
      <el-button type="primary" @click="router.push({ name: 'contracts' })">去合同列表</el-button>
    </el-empty>
    <el-empty v-else-if="contractMissing" description="合同不存在或已被删除">
      <el-button type="primary" @click="router.push({ name: 'contracts' })">去合同列表</el-button>
    </el-empty>

    <template v-else>
      <AiReviewHero
        :result="result"
        :status-bar="statusBar"
        :primary-action="primaryAction"
        :hide-verdict="hideVerdict"
        :show-skeleton="hideVerdict && Boolean(result)"
        :has-report="Boolean(result) && !hideVerdict"
        @primary="onPrimaryAction"
        @run-review="runReview"
        @export-pdf="exportPdf"
        @clause-compare="goClauseCompare"
        @submit-legal-review="submitLegalReview"
        @confirm-report="confirmReport"
        @gate-click="onGateClick"
      />

      <el-tabs v-if="result && !hideVerdict" v-model="activeTab" class="report-tabs">
        <el-tab-pane label="待办与结论" name="summary">
          <AiSummaryPanel
            v-if="summaryPanelData"
            embedded
            :summary="summaryPanelData"
            @confirm-report="confirmReport"
          />
          <el-empty v-else description="暂无摘要数据" />
        </el-tab-pane>

        <el-tab-pane :label="matrixTabLabel" name="matrix">
          <p class="section-hint">清单矩阵展示全量审查项统计，不受条款筛选影响。</p>
          <AiChecklistMatrix
            :matrix="checklistMatrix"
            :risk-filter="matrixRiskFilter"
            @risk-stat-click="onMatrixRiskClick"
          />
          <el-empty v-if="!checklistMatrix" description="暂无清单矩阵数据" />
        </el-tab-pane>

        <el-tab-pane :label="clausesTabLabel" name="clauses">
          <p class="section-hint">以下筛选仅作用于 AI 条款审查明细。</p>
          <div class="filters">
            <el-select v-model="filterRiskLevel" clearable placeholder="风险等级" style="width: 140px">
              <el-option label="极高风险" value="critical" />
              <el-option label="高风险" value="high" />
              <el-option label="中风险" value="medium" />
              <el-option label="低风险" value="low" />
            </el-select>
            <el-select v-model="filterDimension" clearable placeholder="审查维度" style="width: 180px">
              <el-option v-for="d in dimensionOptions" :key="d" :label="aiDimensionLabel(d)" :value="d" />
            </el-select>
            <el-select v-model="filterLabelId" clearable placeholder="风险标签" style="width: 160px">
              <el-option
                v-for="opt in LABEL_OPTIONS"
                :key="opt.id"
                :label="opt.name"
                :value="opt.id"
              />
            </el-select>
            <el-button v-if="hasActiveClauseFilters" link type="primary" @click="clearClauseFilters">
              清空筛选
            </el-button>
            <el-tag v-if="clauseFilterSummary" type="info" class="filter-summary">
              {{ clauseFilterSummary }}
            </el-tag>
          </div>

          <el-card v-if="result?.rule_violations?.length" shadow="never" class="rules-block">
            <template #header>采购规则引擎</template>
            <p class="subsection-hint">规则引擎结果不受条款筛选影响。</p>
            <el-table :data="result.rule_violations" stripe size="small">
              <el-table-column prop="rule_name" label="规则名称" min-width="140" />
              <el-table-column label="严重度" width="100">
                <template #default="{ row }">{{ riskLevelLabel(row.severity) }}</template>
              </el-table-column>
              <el-table-column prop="message" label="说明" min-width="200" />
            </el-table>
          </el-card>

          <el-empty
            v-if="showFilteredClauseEmpty"
            description="当前筛选条件下无匹配条款，请调整或清空筛选"
          />

          <div v-for="group in dimensionGroups" :key="group.key" class="dimension-block">
            <h3>{{ group.label }}</h3>
            <el-table :data="group.items" stripe size="small">
              <el-table-column prop="clause" label="条款" min-width="140" />
              <el-table-column label="标签" width="110">
                <template #default="{ row }">{{ labelName(row.label_id) }}</template>
              </el-table-column>
              <el-table-column label="风险" width="90">
                <template #default="{ row }">{{ riskLevelLabel(row.risk_level) }}</template>
              </el-table-column>
              <el-table-column prop="suggestion" label="建议" min-width="180" show-overflow-tooltip />
              <el-table-column label="反馈" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="sendClauseFeedback('false_positive', row)">
                    误报
                  </el-button>
                  <el-button link size="small" @click="sendClauseFeedback('false_negative', row)">
                    漏报
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.report-tabs {
  margin-top: 4px;
}
.section-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.subsection-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-summary {
  margin-left: 4px;
}
.rules-block {
  margin-top: 0;
  margin-bottom: 16px;
}
.dimension-block {
  margin-top: 20px;
}
.dimension-block h3 {
  font-size: 15px;
  margin: 0 0 8px;
}
@media print {
  .filters,
  .el-button {
    display: none !important;
  }
}
</style>
