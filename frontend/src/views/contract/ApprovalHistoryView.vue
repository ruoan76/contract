<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contractsApi } from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import ContractContextBar from '@/components/ContractContextBar.vue'
import StatusTag from '@/components/StatusTag.vue'
import { flowTypeLabel } from '@/utils/enumLabels'
import type { Contract } from '@/types/models'

interface ApprovalStep {
  step?: number
  node_name?: string
  approver_name?: string
  action?: string
  comment?: string
  status?: string
  completed_at?: string
}

const route = useRoute()
const contractId = computed(() => Number(route.params.id))
const loading = ref(true)
const contract = ref<Contract | null>(null)
const history = ref<{
  flow_id?: number
  status?: string
  flow_type?: string
  total_steps?: number
  steps?: ApprovalStep[]
} | null>(null)

const ACTION_LABEL: Record<string, string> = {
  approve: '通过',
  reject: '驳回',
  pending: '待处理',
}

async function load() {
  if (!contractId.value) return
  loading.value = true
  try {
    const detail = (await contractsApi.get(contractId.value)) as Contract & {
      current_flow_id?: number
    }
    contract.value = detail
    const flowId = detail.current_flow_id
    if (!flowId) {
      history.value = null
      return
    }
    history.value = (await approvalsApi.history(flowId)) as typeof history.value
  } catch (e) {
    console.error(e)
    history.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(contractId, load)

function stepType(step: ApprovalStep) {
  if (step.action === 'approve') return 'success'
  if (step.action === 'reject') return 'danger'
  if (step.status === 'pending') return 'info'
  return 'primary'
}

function formatAction(step: ApprovalStep) {
  return ACTION_LABEL[step.action || step.status || ''] || step.action || step.status || '节点'
}
</script>

<template>
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <h2>审批历史 · 合同 #{{ contractId }}</h2>
    <el-empty v-if="!history" description="暂无审批流程，请先提交审批" />
    <template v-else>
      <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
        <el-descriptions-item label="流程 ID">{{ history.flow_id }}</el-descriptions-item>
        <el-descriptions-item label="流程类型">{{ flowTypeLabel(history.flow_type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <StatusTag v-if="history.status" :status="history.status" />
          <span v-else>—</span>
        </el-descriptions-item>
      </el-descriptions>
      <p class="summary">共 {{ history.total_steps || history.steps?.length || 0 }} 个节点</p>
      <el-timeline>
        <el-timeline-item
          v-for="(step, idx) in history.steps || []"
          :key="idx"
          :type="stepType(step)"
          :timestamp="step.completed_at || `步骤 ${step.step ?? idx + 1}`"
          placement="top"
        >
          <div class="step-card">
            <div class="step-head">
              <strong>{{ step.node_name || `节点 ${step.step}` }}</strong>
              <el-tag size="small" :type="stepType(step)">{{ formatAction(step) }}</el-tag>
            </div>
            <p v-if="step.approver_name" class="meta">审批人：{{ step.approver_name }}</p>
            <p v-if="step.comment" class="comment">{{ step.comment }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </template>
  </div>
</template>

<style scoped>
.summary {
  color: #6b7280;
  margin-bottom: 12px;
}
.step-card {
  padding: 2px 0;
}
.step-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.meta {
  color: #6b7280;
  font-size: 13px;
  margin: 4px 0 0;
}
.comment {
  margin: 6px 0 0;
  color: #374151;
}
</style>
