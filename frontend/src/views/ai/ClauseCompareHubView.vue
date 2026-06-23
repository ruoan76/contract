<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'
import type { Contract } from '@/types/models'
import { formatContractOptionLabel } from '@/utils/contractLabel'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const contracts = ref<Contract[]>([])
const selectedId = ref<number | null>(null)

onMounted(async () => {
  const lastId = auth.restoreLastContractId() || auth.lastContract?.id
  if (lastId) selectedId.value = lastId

  loading.value = true
  try {
    const res = await contractsApi.list({ page: 1, page_size: 50 })
    contracts.value = res.items || []
    if (!selectedId.value && contracts.value.length) {
      selectedId.value = contracts.value[0].id
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载合同列表失败')
  } finally {
    loading.value = false
  }
})

function goCompare() {
  if (!selectedId.value) {
    ElMessage.warning('请先选择要比对的合同')
    return
  }
  router.push({
    name: 'clause-compare',
    params: { id: String(selectedId.value) },
  })
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>条款比对</h2>
    </div>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="请选择要比对的合同。系统将加载上一版本与当前版本正文供差异分析。"
      style="margin-bottom: 16px"
    />
    <el-form v-loading="loading" label-width="100px" style="max-width: 560px">
      <el-form-item label="选择合同">
        <el-select v-model="selectedId" filterable placeholder="选择合同" style="width: 100%">
          <el-option
            v-for="c in contracts"
            :key="c.id"
            :label="formatContractOptionLabel(c)"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-testid="clause-compare-go" @click="goCompare">
          进入比对
        </el-button>
        <el-button @click="router.push({ name: 'contracts' })">返回合同列表</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
