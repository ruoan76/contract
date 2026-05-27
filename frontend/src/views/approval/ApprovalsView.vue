<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approvalsApi } from '@/api/approvals'
import { usersApi, type SystemUser } from '@/api/users'
import type { ApprovalPendingItem } from '@/types/models'

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

function riskLabel(level?: string): string {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    unknown: '未知',
  }
  return map[level || 'unknown'] || level || '未知'
}

function riskTagType(level?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'info'
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

async function confirmHighRisk(row: ApprovalPendingItem): Promise<boolean> {
  if (row.ai_risk_level !== 'high') return true
  try {
    await ElMessageBox.confirm(
      `合同「${rowTitle(row)}」AI 风险等级为「高」，请确认已审阅 AI 审查报告后再通过。`,
      '高风险二次确认',
      { type: 'warning', confirmButtonText: '继续通过', cancelButtonText: '取消' },
    )
    return true
  } catch {
    return false
  }
}

async function approve(row: ApprovalPendingItem) {
  if (!(await confirmHighRisk(row))) return
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

async function openDelegate(row: ApprovalPendingItem) {
  delegateTarget.value = row
  delegateUserId.value = null
  try {
    const res = await usersApi.list({ page: 1, page_size: 50 })
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

async function batchApprove() {
  if (!selected.value.length) {
    ElMessage.warning('请先选择待办')
    return
  }
  const highRisk = selected.value.filter((r) => r.ai_risk_level === 'high')
  if (highRisk.length) {
    try {
      await ElMessageBox.confirm(
        `所选 ${selected.value.length} 项中有 ${highRisk.length} 项 AI 高风险，确认批量通过？`,
        '高风险批量确认',
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
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>待办审批</h2>
      <div style="display: flex; gap: 8px">
        <el-button type="primary" :disabled="!selected.length" @click="batchApprove">
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
      <el-table-column prop="flow_id" label="流程 ID" width="100" />
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">{{ rowTitle(row) }}</template>
      </el-table-column>
      <el-table-column prop="flow_type" label="流程类型" width="120" />
      <el-table-column label="当前步骤" width="100">
        <template #default="{ row }">{{ row.current_step ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="AI 风险" width="100">
        <template #default="{ row }">
          <el-tag :type="riskTagType(row.ai_risk_level)" size="small">
            {{ riskLabel(row.ai_risk_level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="approve(row)">通过</el-button>
          <el-button type="danger" size="small" plain @click="reject(row)">驳回</el-button>
          <el-button size="small" plain @click="openDelegate(row)">委托</el-button>
        </template>
      </el-table-column>
    </el-table>

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
