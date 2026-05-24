<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approvalsApi } from '@/api/approvals'
import { useAuthStore } from '@/stores/auth'
import type { ApprovalPendingItem } from '@/types/models'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<ApprovalPendingItem[]>([])

async function load() {
  loading.value = true
  try {
    await auth.switchRole('approver')
    const res = await approvalsApi.pending()
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function approve(row: ApprovalPendingItem) {
  try {
    await approvalsApi.approve(row.flow_id, 'approve', '同意')
    ElMessage.success('审批通过')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '审批失败')
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
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>待办审批</h2>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="flow_id" label="流程 ID" width="100" />
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column prop="contract_title" label="标题" min-width="200" />
      <el-table-column prop="flow_type" label="流程类型" width="120" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="approve(row)">通过</el-button>
          <el-button type="danger" size="small" plain @click="reject(row)">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
