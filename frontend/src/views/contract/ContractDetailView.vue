<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'
import type { Contract } from '@/types/models'
import ContractContextBar from '@/components/ContractContextBar.vue'

const route = useRoute()
const auth = useAuthStore()
const loading = ref(true)
const contract = ref<Contract | null>(null)

async function load() {
  const id = Number(route.params.id)
  if (!id) return
  loading.value = true
  try {
    contract.value = await contractsApi.get(id)
    auth.setLastContract(contract.value)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <template v-if="contract">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="合同 ID">{{ contract.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ contract.contract_type }}</el-descriptions-item>
        <el-descriptions-item label="相对方">{{ contract.counterparty_name }}</el-descriptions-item>
        <el-descriptions-item label="金额">¥{{ contract.amount?.toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="审批状态">{{ contract.approval_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="主状态">{{ contract.status }}</el-descriptions-item>
      </el-descriptions>
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>合同正文</template>
        <pre class="content-block">{{ contract.content || '（无正文）' }}</pre>
      </el-card>
      <el-card shadow="never" style="margin-top: 12px">
        <template #header>附件</template>
        <el-empty description="附件上传功能 V1.1 规划" :image-size="60" />
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.content-block {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}
</style>
