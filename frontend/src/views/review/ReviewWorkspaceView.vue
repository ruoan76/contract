<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reviewsApi } from '@/api/reviews'
import { useAuthStore } from '@/stores/auth'
import { useContractContext } from '@/composables/useContractContext'
import ContractContextBar from '@/components/ContractContextBar.vue'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'

interface WorkspaceData {
  contract?: { id: number; title?: string; flow_type?: string; amount?: number }
  ai_summary?: { risk_level?: string; risk_score?: number }
  opinions?: Array<{ role: string; action: string; comment?: string; reviewer_name?: string }>
  required_roles?: string[]
}

const ROLE_TABS = [
  { key: 'legal', label: '法务' },
  { key: 'finance', label: '财务' },
  { key: 'executive', label: '高管' },
]

const router = useRouter()
const auth = useAuthStore()
const { contractId } = useContractContext()
const contract = ref<Contract | null>(null)
const workspace = ref<WorkspaceData | null>(null)
const activeTab = ref('legal')
const comment = ref('审核通过')
const loading = ref(false)
const demoStep = ref(0)

const visibleTabs = computed(() => {
  const required = workspace.value?.required_roles || ['legal']
  return ROLE_TABS.filter((t) => required.includes(t.key))
})

const approvedRoles = computed(() => {
  const set = new Set<string>()
  workspace.value?.opinions?.forEach((o) => {
    if (o.action === 'approve') set.add(o.role)
  })
  return set
})

const demoHints = [
  'DEMO-02 步骤 1：法务 Tab 提交通过',
  'DEMO-02 步骤 2：切换财务角色完成财务 Tab',
  'DEMO-02 步骤 3：切换高管角色完成高管 Tab',
]

async function load() {
  if (!contractId.value) return
  loading.value = true
  try {
    contract.value = await contractsApi.get(contractId.value)
    workspace.value = (await reviewsApi.workspace(contractId.value)) as WorkspaceData
    if (visibleTabs.value.length && !visibleTabs.value.find((t) => t.key === activeTab.value)) {
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

async function submitOpinion() {
  if (!contractId.value) {
    ElMessage.warning('请指定合同')
    return
  }
  const role = activeTab.value
  if (approvedRoles.value.has(role)) {
    ElMessage.info('该角色已评审')
    return
  }
  try {
    await auth.switchRole(role as 'legal' | 'finance' | 'executive')
    await reviewsApi.submitOpinion(contractId.value, role, 'approve', comment.value)
    ElMessage.success(`${ROLE_TABS.find((t) => t.key === role)?.label} 评审已通过`)
    demoStep.value = Math.min(demoStep.value + 1, demoHints.length - 1)
    await load()
    if (role === 'legal' && (workspace.value?.required_roles || []).length === 1) {
      router.push({ name: 'seal' })
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  }
}

async function returnForRevision() {
  if (!contractId.value) return
  try {
    await auth.switchRole('legal')
    await reviewsApi.returnForRevision(contractId.value, activeTab.value, comment.value || '请修订')
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
    <h2>评审工作台</h2>
    <el-steps v-if="(workspace?.required_roles?.length || 0) > 1" :active="demoStep" finish-status="success" style="margin: 12px 0">
      <el-step v-for="(hint, idx) in demoHints" :key="idx" :title="hint" />
    </el-steps>
    <el-alert
      v-if="workspace?.contract?.flow_type === 'simple'"
      type="info"
      title="简易流程：仅法务 Tab 可操作（DEMO-01）"
      :closable="false"
      style="margin: 12px 0"
    />
    <el-tabs v-model="activeTab">
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
            :disabled="approvedRoles.has(tab.key)"
            @click="submitOpinion"
          >
            {{ approvedRoles.has(tab.key) ? '已完成' : '提交通过' }}
          </el-button>
          <el-button type="warning" plain @click="returnForRevision">退回修订</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
    <el-table
      v-if="workspace?.opinions?.length"
      :data="workspace.opinions"
      stripe
      style="margin-top: 20px"
    >
      <el-table-column prop="role" label="角色" width="100" />
      <el-table-column prop="reviewer_name" label="评审人" width="120" />
      <el-table-column prop="action" label="动作" width="100" />
      <el-table-column prop="comment" label="意见" min-width="200" />
    </el-table>
  </div>
</template>
