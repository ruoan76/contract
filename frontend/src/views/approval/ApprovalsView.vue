<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approvalsApi } from '@/api/approvals'
import { usersApi, type SystemUser } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import { isSkipAuth } from '@/utils/appEnv'
import type { ApprovalPendingItem } from '@/types/models'
import { formatDateTime } from '@/utils/formatDate'
import {
  approvalNodeLabel,
  contractTypeLabel,
  flowTypeLabel,
  riskLevelLabel,
  riskLevelTagType,
} from '@/utils/enumLabels'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const VIEWED_STORAGE_KEY = 'approval_viewed_contract_ids'

const loading = ref(true)
const items = ref<ApprovalPendingItem[]>([])
const selected = ref<ApprovalPendingItem[]>([])
const delegateVisible = ref(false)
const delegateTarget = ref<ApprovalPendingItem | null>(null)
const delegateUserId = ref<number | null>(null)
const userOptions = ref<SystemUser[]>([])

function rowTitle(row: ApprovalPendingItem): string {
  return row.contract_title || row.title || `合同 #${row.contract_id}`
}

function formatAmount(amount?: number): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  return `¥${amount.toLocaleString('zh-CN')}`
}

function currentNodeLabel(row: ApprovalPendingItem): string {
  return row.current_node_name || approvalNodeLabel(row.current_node)
}

function loadViewedIds(): Set<number> {
  try {
    const raw = sessionStorage.getItem(VIEWED_STORAGE_KEY)
    const arr = raw ? (JSON.parse(raw) as number[]) : []
    return new Set(arr.filter((n) => typeof n === 'number'))
  } catch {
    return new Set()
  }
}

function markContractViewed(contractId: number) {
  const set = loadViewedIds()
  set.add(contractId)
  sessionStorage.setItem(VIEWED_STORAGE_KEY, JSON.stringify([...set]))
}

function hasViewedContract(contractId: number): boolean {
  return loadViewedIds().has(contractId)
}

function openDetail(row: ApprovalPendingItem) {
  markContractViewed(row.contract_id)
  router.push({ name: 'contract-detail', params: { id: String(row.contract_id) } })
}

function openAiReview(row: ApprovalPendingItem) {
  markContractViewed(row.contract_id)
  router.push({ name: 'ai-review', params: { id: String(row.contract_id) } })
}

async function load() {
  loading.value = true
  try {
    const res = await approvalsApi.pending()
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

watch(
  () => route.path,
  (path) => {
    if (path === '/approvals') load()
  },
)

async function confirmRiskBeforeApprove(row: ApprovalPendingItem): Promise<boolean> {
  const level = row.ai_risk_level
  if (level === 'high' || level === 'critical') {
    try {
      await ElMessageBox.confirm(
        `合同「${rowTitle(row)}」AI 风险等级为「${riskLevelLabel(level)}」，请确认已审阅 AI 审查报告后再通过。`,
        '高风险二次确认',
        { type: 'warning', confirmButtonText: '继续通过', cancelButtonText: '取消' },
      )
    } catch {
      return false
    }
  } else if (level === 'medium') {
    try {
      await ElMessageBox.confirm(
        `合同「${rowTitle(row)}」AI 风险等级为「中」，请确认已打开 AI 审查报告并完成人工复核后再通过。`,
        '中风险复核确认',
        { type: 'warning', confirmButtonText: '已复核，继续通过', cancelButtonText: '取消' },
      )
    } catch {
      return false
    }
  }

  const needsMaterial =
    level === 'high' || level === 'critical' || level === 'medium'
  const hasAiReport = !!row.ai_review_status && row.ai_review_status !== 'pending'
  if (needsMaterial && hasAiReport && !hasViewedContract(row.contract_id)) {
    try {
      await ElMessageBox.confirm(
        '您尚未在本会话中打开过该合同的详情或 AI 报告。建议先审阅材料后再通过，是否仍要继续？',
        '审阅材料提示',
        { type: 'warning', confirmButtonText: '仍要通过', cancelButtonText: '先去查看' },
      )
    } catch {
      return false
    }
  }
  return true
}

async function approve(row: ApprovalPendingItem) {
  if (!(await confirmRiskBeforeApprove(row))) return
  try {
    const { value } = await ElMessageBox.prompt('请输入审批意见', '通过审批', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      inputPlaceholder: '同意',
      inputValidator: (v) => !!(v && v.trim()) || '请填写审批意见',
    })
    await approvalsApi.approve(row.flow_id, 'approve', value || '同意')
    ElMessage.success('审批通过')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '审批失败')
    }
  }
}

async function reject(row: ApprovalPendingItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回理由', '驳回审批', {
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '不符合采购规范',
      inputValidator: (v) => !!(v && v.trim()) || '请填写驳回理由',
    })
    await approvalsApi.approve(row.flow_id, 'reject', value || '驳回')
    ElMessage.success('已驳回')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '操作失败')
    }
  }
}

async function returnToDrafter(row: ApprovalPendingItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入退回原因', '退回起草人', {
      confirmButtonText: '退回',
      cancelButtonText: '取消',
      inputPlaceholder: '请补充附件或修改金额后重新提交',
      inputValidator: (v) => !!(v && v.trim()) || '请填写退回原因',
    })
    await approvalsApi.approve(row.flow_id, 'return', value || '退回修改')
    ElMessage.success('已退回起草人')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '退回失败')
    }
  }
}

async function openDelegate(row: ApprovalPendingItem) {
  delegateTarget.value = row
  delegateUserId.value = null
  try {
    const res = await usersApi.listOptions({ page_size: 50 })
    userOptions.value = res.items || []
  } catch {
    userOptions.value = []
  }
  delegateVisible.value = true
}

async function confirmDelegate() {
  if (!delegateTarget.value || !delegateUserId.value) {
    ElMessage.warning('请选择被委托人')
    return
  }
  try {
    await approvalsApi.approve(
      delegateTarget.value.flow_id,
      'delegate',
      '委托审批',
      delegateUserId.value,
    )
    ElMessage.success('已委托')
    delegateVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '委托失败')
  }
}

function isElevatedRisk(level?: string): boolean {
  return level === 'high' || level === 'critical' || level === 'medium'
}

async function batchApprove() {
  if (!selected.value.length) {
    ElMessage.warning('请先选择待办')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认批量通过 ${selected.value.length} 项待办？此操作将跳过逐单材料审阅确认。`,
      '批量通过确认',
      { type: 'warning', confirmButtonText: '确认批量通过', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const elevated = selected.value.filter((r) => isElevatedRisk(r.ai_risk_level))
  if (elevated.length) {
    const highCount = selected.value.filter(
      (r) => r.ai_risk_level === 'high' || r.ai_risk_level === 'critical',
    ).length
    const mediumCount = elevated.length - highCount
    const parts: string[] = []
    if (highCount) parts.push(`${highCount} 项高风险`)
    if (mediumCount) parts.push(`${mediumCount} 项中风险`)
    try {
      await ElMessageBox.confirm(
        `所选 ${selected.value.length} 项中有 ${parts.join('、')}，批量通过将跳过逐单材料审阅确认，确认继续？`,
        '风险批量确认',
        { type: 'warning' },
      )
    } catch {
      return
    }
  }
  for (const row of selected.value) {
    try {
      await approvalsApi.approve(row.flow_id, 'approve', '批量通过')
    } catch (e) {
      ElMessage.error(`流程 #${row.flow_id} 失败：${e instanceof Error ? e.message : ''}`)
      break
    }
  }
  ElMessage.success('批量审批完成')
  selected.value = []
  await load()
}

function handleMoreAction(command: string, row: ApprovalPendingItem) {
  if (command === 'reject') void reject(row)
  else if (command === 'return') void returnToDrafter(row)
  else if (command === 'delegate') void openDelegate(row)
  else if (command === 'ai') openAiReview(row)
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>待办审批</h2>
      <div style="display: flex; gap: 8px">
        <el-button plain :disabled="!selected.length" @click="batchApprove">
          批量通过 ({{ selected.length }})
        </el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>
    <el-table
      v-loading="loading"
      :data="items"
      stripe
      @selection-change="(rows: ApprovalPendingItem[]) => (selected = rows)"
    >
      <el-table-column type="selection" width="48" />
      <el-table-column prop="contract_no" label="合同编号" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.contract_no || '—' }}</template>
      </el-table-column>
      <el-table-column label="标题" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <el-link type="primary" underline="never" @click="openDetail(row)">
            {{ rowTitle(row) }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="88">
        <template #default="{ row }">{{ contractTypeLabel(row.contract_type) }}</template>
      </el-table-column>
      <el-table-column label="相对方" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.counterparty_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="金额" width="120" align="right">
        <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="流程类型" width="108">
        <template #default="{ row }">{{ flowTypeLabel(row.flow_type) }}</template>
      </el-table-column>
      <el-table-column label="当前节点" width="108">
        <template #default="{ row }">{{ currentNodeLabel(row) }}</template>
      </el-table-column>
      <el-table-column label="提交时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="AI 风险" width="88">
        <template #default="{ row }">
          <el-tag :type="riskLevelTagType(row.ai_risk_level)" size="small">
            {{ riskLevelLabel(row.ai_risk_level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openDetail(row)">审阅</el-button>
          <el-button type="primary" size="small" @click="approve(row)">通过</el-button>
          <el-dropdown trigger="click" @command="(cmd: string) => handleMoreAction(cmd, row)">
            <el-button size="small" plain>更多</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="ai">AI 报告</el-dropdown-item>
                <el-dropdown-item command="reject" divided>驳回</el-dropdown-item>
                <el-dropdown-item command="return">退回起草</el-dropdown-item>
                <el-dropdown-item command="delegate">委托</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !items.length" description="暂无待办审批">
      <p v-if="isSkipAuth" class="empty-hint">
        <template v-if="auth.role === 'drafter'">
          起草人账号看不到审批待办。请切换为「部门主管」账号，或提交合同后使用演示入口切换角色。
        </template>
        <template v-else-if="auth.role === 'admin'">
          管理员账号通常无审批待办；可切换为「部门主管」查看刚提交的合同。
        </template>
        <template v-else>
          当前账号下没有待处理的审批任务。
        </template>
      </p>
      <p v-else class="empty-hint">当前没有需要您处理的审批事项。</p>
    </el-empty>

    <el-dialog v-model="delegateVisible" title="审批委托" width="420px">
      <el-select v-model="delegateUserId" placeholder="选择被委托人" filterable style="width: 100%">
        <el-option
          v-for="u in userOptions"
          :key="u.id"
          :label="`${u.real_name || u.username} (${u.role_name || '-'})`"
          :value="u.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="delegateVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDelegate">确认委托</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.empty-hint {
  max-width: 420px;
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  text-align: center;
}
</style>
