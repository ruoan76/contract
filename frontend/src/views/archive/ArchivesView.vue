<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { archivesApi } from '@/api/archives'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const items = ref<Array<{ contract_id?: number; archive_location?: string; archived_at?: string }>>([])
const loading = ref(false)
const archiving = ref(false)

const contractId = ref(auth.restoreLastContractId() || auth.lastContract?.id || 0)

onMounted(async () => {
  loading.value = true
  try {
    const res = await archivesApi.ledger()
    items.value = (res.items || []) as typeof items.value
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function openContract(row: { contract_id?: number }) {
  if (row.contract_id) {
    router.push({ name: 'contract-detail', params: { id: row.contract_id } })
  }
}

function go(name: string) {
  if (!contractId.value && name !== 'create') {
    ElMessage.warning('请先在新建合同页创建并提交合同')
    return
  }
  if (name === 'ai-review') {
    router.push({ name: 'ai-review', params: { id: contractId.value } })
  } else if (name === 'review-workspace') {
    router.push({ name: 'review-workspace', params: { id: contractId.value } })
  } else {
    router.push({ name })
  }
}

async function archiveCurrent() {
  if (!contractId.value) {
    ElMessage.warning('无当前合同，请先完成 DEMO-02 前置步骤')
    return
  }
  archiving.value = true
  try {
    await archivesApi.archive(contractId.value, '/archive/demo-02')
    ElMessage.success('归档成功')
    const res = await archivesApi.ledger()
    items.value = (res.items || []) as typeof items.value
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '归档失败，请确认已完成审批与三角色评审')
  } finally {
    archiving.value = false
  }
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>归档台账</h2>
    </div>

    <el-alert
      title="DEMO-02 标准流程指引"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
    >
      <p>当前合同 ID：{{ contractId || '未选择' }}。按序完成：AI 审查 → 三角色评审 → 归档。</p>
      <div class="demo-actions">
        <el-button size="small" @click="go('create')">1. 新建合同</el-button>
        <el-button size="small" @click="go('ai-review')">2. AI 审查</el-button>
        <el-button size="small" @click="go('review-workspace')">3. 评审工作台</el-button>
        <el-button size="small" type="primary" :loading="archiving" @click="archiveCurrent">
          4. 归档当前合同
        </el-button>
      </div>
    </el-alert>

    <el-table v-loading="loading" :data="items" stripe @row-click="openContract">
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column prop="archive_location" label="归档位置" min-width="200" />
      <el-table-column prop="archived_at" label="归档时间" width="180" />
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无归档记录" />
  </div>
</template>

<style scoped>
.demo-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
</style>
