<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  aiReviewApi,
  groupClausesByDimension,
  labelName,
  LABEL_OPTIONS,
  type AiReviewSummary,
} from '@/api/ai-review'
import { useContractContext } from '@/composables/useContractContext'
import ContractContextBar from '@/components/ContractContextBar.vue'
import AiGateSummary from '@/components/AiGateSummary.vue'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'

const router = useRouter()
const { contractId } = useContractContext()
const contract = ref<Contract | null>(null)
const result = ref<AiReviewSummary | null>(null)
const loading = ref(false)
const polling = ref(false)
const filterRiskLevel = ref('')
const filterDimension = ref('')
const filterLabelId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

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
  if (level === 'high' || level === 'critical') return 'danger'
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

async function load() {
  if (!contractId.value) return
  loading.value = true
  try {
    contract.value = await contractsApi.get(contractId.value)
    try {
      result.value = await aiReviewApi.latest(contractId.value)
    } catch {
      result.value = null
    }
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
      result.value = await aiReviewApi.latest(contractId.value)
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
    ElMessage.error(e instanceof Error ? e.message : '审查失败')
  } finally {
    loading.value = false
  }
}

function exportPdf() {
  if (result.value?.review_id) {
    aiReviewApi
      .downloadReport(result.value.review_id, 'pdf')
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `ai-review-${result.value?.review_id}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      })
      .catch(() => window.print())
    return
  }
  window.print()
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

function sourceLabel(source?: string) {
  if (source === 'rule') return '规则'
  if (source === 'llm') return 'LLM'
  return source || '—'
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
    <AiGateSummary v-if="result?.gates" :gates="result.gates" />
    <div class="page-toolbar">
      <h2>AI 审查报告</h2>
      <div class="toolbar-actions">
        <el-tag v-if="polling" type="info">审查中…</el-tag>
        <el-button type="primary" @click="runReview">触发审查</el-button>
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
    <el-empty v-if="!result" description="暂无审查报告，请先触发审查" />
    <template v-else>
      <div class="filters">
        <el-select v-model="filterRiskLevel" clearable placeholder="风险等级" style="width: 140px">
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
      <el-descriptions :column="2" border>
        <el-descriptions-item label="审查 ID">{{ result.review_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ result.review_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="riskType">{{ riskLabel }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险分">{{ result.risk_score ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="审查时间">{{ result.review_time ?? '-' }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 16px">
        <el-button size="small" @click="sendFeedback('false_positive')">标记误报</el-button>
        <el-button size="small" @click="sendFeedback('false_negative')">标记漏报</el-button>
      </div>
      <el-card v-if="result.rule_violations?.length" shadow="never" class="rules-block">
        <template #header>采购规则引擎</template>
        <el-table :data="result.rule_violations" stripe size="small">
          <el-table-column prop="rule_id" label="规则 ID" width="100" />
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
          <el-table-column label="来源" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.source === 'rule' ? 'warning' : 'info'">
                {{ sourceLabel(row.source) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="legal_basis" label="法律依据" min-width="160" show-overflow-tooltip />
          <el-table-column prop="confidence" label="置信度" width="80" />
          <el-table-column prop="suggestion" label="建议" min-width="180" show-overflow-tooltip />
        </el-table>
      </div>
    </template>
  </div>
</template>

<style scoped>
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
.rules-block {
  margin-top: 16px;
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
</style>
