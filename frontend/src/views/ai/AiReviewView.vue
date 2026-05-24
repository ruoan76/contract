<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiReviewApi, type AiReviewSummary } from '@/api/ai-review'
import { useAuthStore } from '@/stores/auth'
import ContractContextBar from '@/components/ContractContextBar.vue'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'

const route = useRoute()
const auth = useAuthStore()
const contractId = ref(0)
const contract = ref<Contract | null>(null)
const result = ref<AiReviewSummary | null>(null)
const loading = ref(false)

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

function resolveId() {
  return Number(route.params.id) || auth.restoreLastContractId() || auth.lastContract?.id || 0
}

async function load() {
  contractId.value = resolveId()
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

onMounted(load)
watch(() => route.params.id, load)

async function runReview() {
  if (!contractId.value) {
    ElMessage.warning('无合同 ID')
    return
  }
  loading.value = true
  try {
    await aiReviewApi.review(contractId.value)
    await load()
    ElMessage.success('AI 审查已完成')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '审查失败')
  } finally {
    loading.value = false
  }
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
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <div class="page-toolbar">
      <h2>AI 审查报告</h2>
      <el-button type="primary" @click="runReview">触发审查</el-button>
    </div>
    <el-empty v-if="!result" description="暂无审查报告，请先触发审查" />
    <template v-else>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="审查 ID">{{ result.review_id }}</el-descriptions-item>
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
      <el-table
        v-if="result.clause_reviews?.length"
        :data="result.clause_reviews"
        stripe
        style="margin-top: 16px"
      >
        <el-table-column prop="clause" label="条款" min-width="160" />
        <el-table-column prop="risk_level" label="风险" width="100" />
        <el-table-column prop="confidence" label="置信度" width="100" />
        <el-table-column prop="suggestion" label="建议" min-width="200" />
      </el-table>
    </template>
  </div>
</template>
