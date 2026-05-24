<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  contractsApi,
  type ContractUploadResult,
  type ContractVersion,
} from '@/api/contracts'
import { useContractContext } from '@/composables/useContractContext'
import type { Contract } from '@/types/models'
import ContractContextBar from '@/components/ContractContextBar.vue'

const { contractId } = useContractContext()
const loading = ref(true)
const contract = ref<Contract | null>(null)
const versions = ref<ContractVersion[]>([])
const uploading = ref(false)
const lastUpload = ref<ContractUploadResult | null>(null)

async function load() {
  const id = contractId.value
  if (!id) return
  loading.value = true
  try {
    contract.value = await contractsApi.get(id)
    try {
      versions.value = (await contractsApi.listVersions(id)) || []
    } catch {
      versions.value = []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(contractId, load)

async function onUpload(file: File) {
  const id = contractId.value
  if (!id) return false
  uploading.value = true
  try {
    lastUpload.value = await contractsApi.upload(id, file)
    ElMessage.success('附件上传成功')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    uploading.value = false
  }
  return false
}
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
        <template #header>附件上传</template>
        <el-upload
          :auto-upload="true"
          :show-file-list="false"
          :disabled="uploading"
          :before-upload="onUpload"
        >
          <el-button type="primary" :loading="uploading">选择文件上传</el-button>
        </el-upload>
        <div v-if="lastUpload" class="upload-meta">
          <p><strong>路径：</strong>{{ lastUpload.file_path }}</p>
          <p><strong>哈希：</strong><code>{{ lastUpload.file_hash }}</code></p>
        </div>
      </el-card>
      <el-card shadow="never" style="margin-top: 12px">
        <template #header>版本历史</template>
        <el-table :data="versions" stripe size="small" empty-text="暂无版本记录">
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column prop="change_description" label="说明" min-width="140" />
          <el-table-column prop="file_path" label="文件路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="file_hash" label="文件哈希" min-width="160" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>
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
.upload-meta {
  margin-top: 12px;
  font-size: 13px;
  color: #374151;
}
.upload-meta code {
  font-size: 12px;
  word-break: break-all;
}
</style>
