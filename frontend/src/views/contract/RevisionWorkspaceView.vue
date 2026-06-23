<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractsApi } from '@/api/contracts'
import { aiReviewApi } from '@/api/ai-review'

import ContractContextBar from '@/components/ContractContextBar.vue'
import type { Contract } from '@/types/models'

const route = useRoute()
const router = useRouter()
const contractId = ref<number>(0)
const contract = ref<Contract | null>(null)
const content = ref('')
const changeDesc = ref('修改条款')
const trackChangeHints = ref<string[]>([])
const submitting = ref(false)

const canSubmitRevision = computed(() => {
  const s = contract.value?.status
  return s === 'draft' || s === 'returned'
})

const statusHint = computed(() => {
  const s = contract.value?.status
  if (!s || canSubmitRevision.value) return ''
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回',
    in_review: '评审中',
  }
  const label = map[s] || s
  return `当前合同状态为「${label}」，须由评审人退回修订后方可编辑。请前往评审中心或合同详情查看进度。`
})

function resolveId(): number {
  return Number(route.params.id) || 0
}

async function load() {
  contractId.value = resolveId()
  if (!contractId.value) return
  try {
    const c = await contractsApi.get(contractId.value)
    contract.value = c
    content.value = c.content || ''
    try {
      const latest = await aiReviewApi.latest(contractId.value)
      const reviewId = latest.review_id
      if (reviewId) {
        const issueResp = await aiReviewApi.listIssues(reviewId)
        const items = issueResp.items || []
        const commentIssues = items.filter((i) => i.revision_method === 'comment')
        if (commentIssues.length) {
          changeDesc.value = commentIssues
            .map((i) => `${i.clause || ''}: ${i.suggestion || i.description || ''}`)
            .join('\n')
        }
        trackChangeHints.value = items
          .filter((i) => i.revision_method === 'track_changes')
          .map((i) => `${i.clause}: ${i.suggestion || i.description || '请使用修订模式修改'}`)
      }
    } catch {
      /* 无 AI 报告时忽略 */
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(load)
watch(() => route.params.id, load)

async function submitRevision() {
  if (!contractId.value) {
    ElMessage.warning('无合同上下文')
    return
  }
  if (!canSubmitRevision.value) {
    ElMessage.warning(statusHint.value || '当前状态不可提交修订')
    return
  }
  submitting.value = true
  try {
    const rev = await contractsApi.submitRevision(contractId.value, {
      content: content.value,
      change_description: changeDesc.value,
    })
    if (import.meta.env.VITE_E2E !== '1') {
      await aiReviewApi.review(contractId.value)
    }
    ElMessage.success(`修订已提交，版本 v${rev.version || 2}`)
    router.push({ name: 'ai-review', params: { id: contractId.value } })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '修订失败')
  } finally {
    submitting.value = false
  }
}

function goReviewCenter() {
  router.push({ name: 'review-center' })
}
</script>

<template>
  <div class="page-card">
    <ContractContextBar :contract="contract" />
    <el-alert
      v-if="statusHint"
      type="info"
      :title="statusHint"
      :closable="false"
      style="margin-top: 12px"
    >
      <template #default>
        <el-button size="small" type="primary" plain @click="goReviewCenter">前往评审中心</el-button>
      </template>
    </el-alert>
    <el-alert
      v-for="(hint, idx) in trackChangeHints"
      :key="idx"
      type="warning"
      :title="hint"
      :closable="false"
      style="margin-top: 12px"
    />
    <el-form label-width="100px" style="max-width: 720px; margin-top: 16px">
      <el-form-item label="修订说明">
        <el-input v-model="changeDesc" :disabled="!canSubmitRevision" />
      </el-form-item>
      <el-form-item label="合同正文">
        <el-input v-model="content" type="textarea" :rows="8" :disabled="!canSubmitRevision" />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!canSubmitRevision"
          @click="submitRevision"
        >
          提交修订
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
