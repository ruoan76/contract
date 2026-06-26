<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reviewsApi } from '@/api/reviews'
import { aiReviewApi, labelName } from '@/api/ai-review'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useContractContext } from '@/composables/useContractContext'
import ContractContextBar from '@/components/ContractContextBar.vue'
import AiSummaryPanel from '@/components/AiSummaryPanel.vue'
import type { AiSummaryPanelData } from '@/utils/aiRecommendation'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'
import {
  aiDimensionLabel,
  aiIssueHumanStatusLabel,
  reviewActionLabel,
  reviewRoleLabel,
  riskLevelLabel,
  riskLevelTagType,
} from '@/utils/enumLabels'
import type { DimensionSummaryInput } from '@/utils/aiRecommendation'

interface AiIssueRow {
  id?: number
  clause?: string
  risk_level?: string
  dimension?: string
  suggestion?: string
  description?: string
  legal_basis?: string
  revision_method?: string
  human_status?: string
  label_id?: string
  source?: string
}

interface WorkspaceData {
  contract?: { id: number; title?: string; flow_type?: string; amount?: number }
  ai_summary?: AiSummaryPanelData & { dimension_summaries?: DimensionSummaryInput[] }
  ai_issues?: AiIssueRow[]
  opinions?: Array<{ role: string; action: string; comment?: string; reviewer_name?: string }>
  required_roles?: string[]
  ai_gate?: { ready?: boolean; message?: string | null }
}

const ROLE_TABS = [
  { key: 'legal', label: '法务' },
  { key: 'finance', label: '财务' },
  { key: 'executive', label: '高管' },
]

const REVIEW_ROLES = new Set(['legal', 'finance', 'executive'])

const router = useRouter()
const auth = useAuthStore()
const { contractId } = useContractContext()
const contract = ref<Contract | null>(null)
const workspace = ref<WorkspaceData | null>(null)
const activeTab = ref('legal')
const comment = ref('审核通过')
const loading = ref(false)
const aiRetrying = ref(false)
const showHistory = ref<string[]>([])

const AI_READY = new Set(['ai_done', 'reviewed', 'confirmed'])

const aiGateReady = computed(() => {
  if (import.meta.env.VITE_E2E === '1') return true
  if (workspace.value?.ai_gate?.ready === false) return false
  if (workspace.value?.ai_gate?.ready === true) return true
  const st = workspace.value?.ai_summary?.review_status
  return !!st && AI_READY.has(st)
})

const aiGateMessage = computed(() => {
  if (workspace.value?.ai_gate?.message) return workspace.value.ai_gate.message
  const st = workspace.value?.ai_summary?.review_status
  if (!st) return '请先完成 AI 审查后再提交评审'
  if (st === 'reviewing') return 'AI 审查进行中，请稍后再提交评审'
  if (st === 'failed') return 'AI 审查失败，请重新触发审查后再提交评审'
  if (!AI_READY.has(st)) return '请先完成 AI 审查后再提交评审'
  return ''
})

const visibleTabs = computed(() => {
  const required = workspace.value?.required_roles || ['legal']
  const tabs = ROLE_TABS.filter((t) => required.includes(t.key))
  if (REVIEW_ROLES.has(auth.role)) {
    return tabs.filter((t) => t.key === auth.role)
  }
  return tabs
})

const currentReviewRole = computed(() => {
  if (REVIEW_ROLES.has(auth.role)) return auth.role
  return activeTab.value
})

const approvedRoles = computed(() => {
  const set = new Set<string>()
  workspace.value?.opinions?.forEach((o) => {
    if (o.action === 'approve') set.add(o.role)
  })
  return set
})

function goAiReport() {
  if (!contractId.value) return
  router.push({ name: 'ai-review', params: { id: String(contractId.value) } })
}

async function patchIssueStatus(issueId: number, status: 'confirmed' | 'false_positive') {
  try {
    await aiReviewApi.patchIssue(issueId, status)
    ElMessage.success(status === 'confirmed' ? '已确认' : '已标记误报')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function confirmAiReport() {
  const rid = workspace.value?.ai_summary?.review_id
  if (!rid) {
    ElMessage.warning('暂无 AI 报告')
    return
  }
  try {
    await aiReviewApi.confirm(rid)
    ElMessage.success('AI 报告已确认')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '确认失败')
  }
}

async function load() {
  if (!contractId.value) return
  loading.value = true
  try {
    contract.value = await contractsApi.get(contractId.value)
    workspace.value = (await reviewsApi.workspace(contractId.value)) as WorkspaceData
    if (visibleTabs.value.length) {
      activeTab.value = visibleTabs.value[0].key
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(contractId, load)

async function retryAiReview() {
  if (!contractId.value) return
  aiRetrying.value = true
  try {
    await aiReviewApi.review(contractId.value)
    ElMessage.success('已重新触发 AI 审查，正在生成报告…')
    for (let i = 0; i < 24; i++) {
      await new Promise((r) => setTimeout(r, 5000))
      await load()
      const st = workspace.value?.ai_summary?.review_status
      if (st === 'ai_done' || st === 'failed') break
    }
    if (aiGateReady.value) {
      ElMessage.success('AI 审查已完成，可提交评审')
    } else if (workspace.value?.ai_summary?.review_status === 'failed') {
      ElMessage.error(aiGateMessage.value || 'AI 审查仍失败')
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '触发 AI 审查失败')
  } finally {
    aiRetrying.value = false
  }
}

async function submitOpinion() {
  if (!contractId.value) {
    ElMessage.warning('请指定合同')
    return
  }
  if (!aiGateReady.value) {
    ElMessage.warning(aiGateMessage.value || '请先完成 AI 审查')
    return
  }
  const role = currentReviewRole.value
  if (!visibleTabs.value.some((t) => t.key === role)) {
    ElMessage.warning('当前账号无权提交该评审')
    return
  }
  if (approvedRoles.value.has(role)) {
    ElMessage.info('该角色已评审')
    return
  }
  try {
    await reviewsApi.submitOpinion(contractId.value, role, 'approve', comment.value)
    ElMessage.success(`${ROLE_TABS.find((t) => t.key === role)?.label} 评审已通过`)
    await load()
    if (role === 'legal' && (workspace.value?.required_roles || []).length === 1) {
      try {
        await ElMessageBox.confirm('法务评审已通过，是否前往用印管理？', '确认下一步', {
          confirmButtonText: '前往用印',
          cancelButtonText: '留在此页',
          type: 'info',
        })
        router.push({ name: 'seal' })
      } catch {
        /* 用户选择留在此页 */
      }
    }
  } catch (e) {
    const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : '提交失败'
    ElMessage.error(msg)
  }
}

async function returnForRevision() {
  if (!contractId.value) return
  const role = currentReviewRole.value
  try {
    await reviewsApi.returnForRevision(contractId.value, role, comment.value || '请修订')
    ElMessage.success('已退回修订')
    router.push({ name: 'revision-workspace', params: { id: String(contractId.value) } })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '退回失败')
  }
}
</script>

<template>
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <el-empty v-if="!contractId" description="请从评审中心选择合同">
      <el-button type="primary" @click="router.push({ name: 'review-center' })">前往评审中心</el-button>
    </el-empty>
    <template v-else>
      <el-alert
        v-if="!aiGateReady"
        type="warning"
        :title="aiGateMessage || 'AI 审查未就绪'"
        :closable="false"
        style="margin: 12px 0"
      >
        <template #default>
          <p style="margin: 0 0 8px">提交评审前须完成 AI 初筛。</p>
          <el-button size="small" type="primary" :loading="aiRetrying" @click="retryAiReview">
            重新触发 AI 审查
          </el-button>
          <el-button size="small" link type="primary" @click="goAiReport">查看 AI 报告</el-button>
        </template>
      </el-alert>
      <el-alert
        v-if="workspace?.contract?.flow_type === 'simple'"
        type="info"
        title="简易流程：仅法务评审"
        :closable="false"
        style="margin: 12px 0"
      />
      <AiSummaryPanel
        v-if="workspace?.ai_summary"
        :summary="workspace.ai_summary"
        show-confirm-button
        @view-report="goAiReport"
        @confirm-report="confirmAiReport"
      />
      <el-card v-if="workspace?.ai_issues?.length" shadow="never" style="margin-bottom: 16px">
        <template #header>待确认项</template>
        <el-table :data="workspace.ai_issues" size="small" stripe>
          <el-table-column prop="clause" label="条款" min-width="120" />
          <el-table-column label="标签" width="100">
            <template #default="{ row }">{{ labelName(row.label_id) }}</template>
          </el-table-column>
          <el-table-column label="维度" width="100">
            <template #default="{ row }">{{ aiDimensionLabel(row.dimension) }}</template>
          </el-table-column>
          <el-table-column label="风险" width="100">
            <template #default="{ row }">
              <el-tag :type="riskLevelTagType(row.risk_level)" size="small">
                {{ riskLevelLabel(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="建议" min-width="180">
            <template #default="{ row }">
              <div class="issue-suggestion">{{ row.suggestion || '—' }}</div>
              <div v-if="row.description" class="issue-desc">{{ row.description }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ aiIssueHumanStatusLabel(row.human_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.id && row.human_status === 'pending'"
                link
                type="primary"
                @click="patchIssueStatus(row.id, 'confirmed')"
              >
                确认
              </el-button>
              <el-button
                v-if="row.id && row.human_status === 'pending'"
                link
                type="warning"
                @click="patchIssueStatus(row.id, 'false_positive')"
              >
                误报
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-tabs v-if="visibleTabs.length" v-model="activeTab">
        <el-tab-pane
          v-for="tab in visibleTabs"
          :key="tab.key"
          :label="tab.label + (approvedRoles.has(tab.key) ? ' ✓' : '')"
          :name="tab.key"
        >
          <el-input v-model="comment" type="textarea" :rows="3" placeholder="评审意见" />
          <div style="margin-top: 12px; display: flex; gap: 8px">
            <el-button
              type="primary"
              :disabled="approvedRoles.has(tab.key) || !aiGateReady"
              @click="submitOpinion"
            >
              {{ approvedRoles.has(tab.key) ? '已完成' : '提交通过' }}
            </el-button>
            <el-button type="warning" plain @click="returnForRevision">退回修订</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
      <el-empty v-else description="当前账号无可操作的评审角色">
        <el-button @click="router.push({ name: 'review-center' })">返回评审中心</el-button>
      </el-empty>
      <el-collapse v-if="workspace?.opinions?.length" v-model="showHistory" style="margin-top: 20px">
        <el-collapse-item title="历史评审意见" name="history">
          <el-table :data="workspace.opinions" stripe size="small">
            <el-table-column label="角色" width="100">
              <template #default="{ row }">{{ reviewRoleLabel(row.role) }}</template>
            </el-table-column>
            <el-table-column prop="reviewer_name" label="评审人" width="120" />
            <el-table-column label="动作" width="100">
              <template #default="{ row }">{{ reviewActionLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="comment" label="意见" min-width="200" />
          </el-table>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<style scoped>
.issue-suggestion {
  font-size: 13px;
  line-height: 1.5;
}

.issue-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>
