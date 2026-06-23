<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sealsApi } from '@/api/seals'
import { contractsApi } from '@/api/contracts'
import { sealStatusLabel, sealTypeLabel } from '@/utils/enumLabels'
import type { Contract } from '@/types/models'
import { formatContractOptionLabel } from '@/utils/contractLabel'

interface SealItem {
  id: number
  contract_id: number
  status?: string
  seal_type?: string
  seal_image_path?: string
}

const router = useRouter()
const items = ref<SealItem[]>([])
const loading = ref(false)
const contracts = ref<Contract[]>([])
const selectedContractId = ref<number | null>(null)

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

async function loadContracts() {
  try {
    const res = await contractsApi.list({ page: 1, page_size: 100, status: 'approved' })
    contracts.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  await Promise.all([load(), loadContracts()])
})

const selectedContract = computed(() =>
  contracts.value.find((c) => c.id === selectedContractId.value),
)

async function applySeal() {
  const cid = selectedContractId.value
  if (!cid) {
    ElMessage.warning('请先选择要申请用印的合同')
    return
  }
  loading.value = true
  try {
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

async function uploadScan(row: SealItem, file: File) {
  loading.value = true
  try {
    const res = await sealsApi.uploadScan(row.id, file)
    ElMessage.success('扫描件已上传')
    row.seal_image_path = res.seal_image_path
    row.status = 'completed'
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    loading.value = false
  }
  return false
}

function openContract(row: SealItem) {
  router.push({ name: 'contract-detail', params: { id: row.contract_id } })
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <div class="apply-row">
        <el-select
          v-model="selectedContractId"
          filterable
          clearable
          placeholder="选择已通过审批的合同"
          style="width: 320px"
        >
          <el-option
            v-for="c in contracts"
            :key="c.id"
            :label="formatContractOptionLabel(c)"
            :value="c.id"
          />
        </el-select>
        <el-button type="primary" :loading="loading" :disabled="!selectedContractId" @click="applySeal">
          申请用印
        </el-button>
      </div>
    </div>
    <p v-if="selectedContract" class="hint">已选：{{ selectedContract.title }}</p>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="申请 ID" width="100" />
      <el-table-column prop="contract_id" label="合同 ID" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="openContract(row)">#{{ row.contract_id }}</el-button>
        </template>
      </el-table-column>
      <el-table-column label="印章类型" width="120">
        <template #default="{ row }">{{ sealTypeLabel(row.seal_type) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">{{ sealStatusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="seal_image_path" label="扫描件" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'approved' && row.status !== 'completed'"
            link
            type="primary"
            @click="approveSeal(row)"
          >
            确认用印
          </el-button>
          <el-upload
            :auto-upload="true"
            :show-file-list="false"
            :before-upload="(f: File) => uploadScan(row, f)"
          >
            <el-button link type="success">上传扫描件</el-button>
          </el-upload>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无用印申请">
      <el-button type="primary" :disabled="!selectedContractId" @click="applySeal">申请用印</el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
.apply-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.hint {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 12px;
}
</style>
