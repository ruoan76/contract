<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sealsApi } from '@/api/seals'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'

interface SealItem {
  id: number
  contract_id: number
  status?: string
  seal_type?: string
}

const auth = useAuthStore()
const router = useRouter()
const items = ref<SealItem[]>([])
const loading = ref(false)
const contractId = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await sealsApi.list()
    items.value = (res.items || []) as SealItem[]
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  contractId.value = auth.restoreLastContractId() || auth.lastContract?.id || null
  load()
})

async function applySeal() {
  const cid = contractId.value
  if (!cid) {
    ElMessage.warning('请先在合同详情或新建流程中选择合同')
    return
  }
  loading.value = true
  try {
    await auth.switchRole('drafter')
    await sealsApi.apply(cid)
    ElMessage.success('用印申请已提交')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '申请失败')
  } finally {
    loading.value = false
  }
}

async function approveSeal(row: SealItem) {
  loading.value = true
  try {
    await auth.switchRole('admin')
    await sealsApi.approve(row.id)
    ElMessage.success('用印已确认')
    await load()
    const c = await contractsApi.get(row.contract_id)
    if (c.status === 'sealed') {
      router.push({ name: 'contract-detail', params: { id: row.contract_id } })
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '确认失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>用印管理</h2>
      <el-button type="primary" :loading="loading" @click="applySeal">
        对合同 #{{ contractId ?? '—' }} 申请用印
      </el-button>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="申请 ID" width="100" />
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column prop="seal_type" label="印章类型" width="120" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'approved'"
            link
            type="primary"
            @click="approveSeal(row)"
          >
            确认用印
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无用印申请" />
  </div>
</template>
