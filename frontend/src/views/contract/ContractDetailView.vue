<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  contractsApi,
  type ContractUploadResult,
  type ContractVersion,
} from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import { aiReviewApi, type AiReviewSummary } from '@/api/ai-review'
import { useContractContext } from '@/composables/useContractContext'
import type { Contract } from '@/types/models'
import ContractContextBar from '@/components/ContractContextBar.vue'

const router = useRouter()
const { contractId } = useContractContext()
const loading = ref(true)
const saving = ref(false)
const contract = ref<Contract | null>(null)
const versions = ref<ContractVersion[]>([])
const uploading = ref(false)
const lastUpload = ref<ContractUploadResult | null>(null)
const aiSummary = ref<AiReviewSummary | null>(null)
const flowHistory = ref<{ flow_type?: string; status?: string; steps?: unknown[] } | null>(null)

const isDraft = computed(() => contract.value?.status === 'draft')
const attachmentVersions = computed(() =>
  versions.value.filter((v) => v.file_path),
)

const editForm = ref({
  title: '',
  contract_type: 'purchase',
  counterparty_name: '',
  amount: 0,
  content: '',
})

async function load() {
  const id = contractId.value
  if (!id) return
  loading.value = true
  try {
    const detail = (await contractsApi.get(id)) as Contract & { current_flow_id?: number }
    contract.value = detail
    editForm.value = {
      title: detail.title,
      contract_type: detail.contract_type,
      counterparty_name: detail.counterparty_name,
      amount: detail.amount,
      content: detail.content || '',
    }
    try {
      versions.value = (await contractsApi.listVersions(id)) || []
    } catch {
      versions.value = []
    }
    try {
      aiSummary.value = await aiReviewApi.latest(id)
    } catch {
      aiSummary.value = null
    }
    if (detail.current_flow_id) {
      try {
        flowHistory.value = await approvalsApi.history(detail.current_flow_id)
      } catch {
        flowHistory.value = null
      }
    } else {
      flowHistory.value = null
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(contractId, load)

async function saveDraft() {
  const id = contractId.value
  if (!id || !isDraft.value) return
  saving.value = true
  try {
    contract.value = await contractsApi.update(id, { ...editForm.value })
    ElMessage.success('草稿已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

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

function goAiReview() {
  if (!contractId.value) return
  router.push({ name: 'ai-review', params: { id: String(contractId.value) } })
}

function goClauseCompare() {
  if (!contractId.value) return
  router.push({ name: 'clause-compare', params: { id: String(contractId.value) } })
}

function stepTitle(step: unknown, idx: number) {
  const s = step as { node_name?: string }
  return s.node_name || `步骤 ${idx + 1}`
}

function stepDesc(step: unknown) {
  const s = step as { approver_name?: string }
  return s.approver_name || ''
}
</script>

<template>
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <template v-if="contract">
      <el-card v-if="flowHistory?.steps?.length" shadow="never" style="margin-bottom: 16px">
        <template #header>审批进度（{{ flowHistory.flow_type || '—' }} / {{ flowHistory.status || '—' }}）</template>
        <el-steps :active="flowHistory.steps.length" finish-status="success" align-center>
          <el-step
            v-for="(step, idx) in flowHistory.steps"
            :key="idx"
            :title="stepTitle(step, idx)"
            :description="stepDesc(step)"
          />
        </el-steps>
      </el-card>

      <el-card v-if="aiSummary" shadow="never" class="ai-summary" style="margin-bottom: 16px">
        <template #header>
          <span>AI 风险摘要</span>
          <span style="float: right">
            <el-button link type="primary" @click="goClauseCompare">条款比对</el-button>
            <el-button link type="primary" @click="goAiReview">查看报告</el-button>
          </span>
        </template>
        <el-descriptions :column="3" size="small">
          <el-descriptions-item label="风险等级">{{ aiSummary.risk_level || '—' }}</el-descriptions-item>
          <el-descriptions-item label="风险分">{{ aiSummary.risk_score ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ aiSummary.review_status || '—' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <template v-if="isDraft">
        <el-form label-width="100px" style="max-width: 720px">
          <el-form-item label="合同标题">
            <el-input v-model="editForm.title" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="editForm.contract_type" style="width: 100%">
              <el-option label="采购" value="purchase" />
              <el-option label="销售" value="sales" />
              <el-option label="服务" value="service" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="相对方">
            <el-input v-model="editForm.counterparty_name" />
          </el-form-item>
          <el-form-item label="金额">
            <el-input-number v-model="editForm.amount" :min="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="正文">
            <el-input v-model="editForm.content" type="textarea" :rows="4" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveDraft">保存草稿</el-button>
          </el-form-item>
        </el-form>
      </template>
      <el-descriptions v-else :column="2" border>
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
        <template #header>附件历史</template>
        <el-table :data="attachmentVersions" stripe size="small" empty-text="暂无附件">
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column prop="file_path" label="文件路径" min-width="220" show-overflow-tooltip />
          <el-table-column prop="file_hash" label="哈希" min-width="160" show-overflow-tooltip />
          <el-table-column prop="created_at" label="上传时间" width="180" />
        </el-table>
      </el-card>
      <el-card shadow="never" style="margin-top: 12px">
        <template #header>版本历史</template>
        <el-table :data="versions" stripe size="small" empty-text="暂无版本记录">
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column prop="change_description" label="说明" min-width="140" />
          <el-table-column prop="file_path" label="文件路径" min-width="200" show-overflow-tooltip />
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
.ai-summary :deep(.el-card__header) {
  display: flex;
  align-items: center;
}
</style>
