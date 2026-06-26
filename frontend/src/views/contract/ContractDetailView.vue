<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  contractsApi,
  type ContractUploadResult,
  type ContractVersion,
} from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import { aiReviewApi, type AiReviewSummary } from '@/api/ai-review'
import { useContractContext } from '@/composables/useContractContext'
import { useAuthStore } from '@/stores/auth'
import type { Contract } from '@/types/models'
import ContractContextBar from '@/components/ContractContextBar.vue'
import StatusTag from '@/components/StatusTag.vue'
import {
  canDeleteContract,
  DELETE_DRAFT_CONFIRM_MESSAGE,
  DELETE_DRAFT_CONFIRM_TITLE,
} from '@/utils/contractDelete'
import {
  LIFECYCLE_STAGES,
  lifecycleActiveIndex,
} from '@/utils/contractLifecycle'
import { formatDate, formatDateRange, formatDateTime } from '@/utils/formatDate'
import ContractContentViewer from '@/components/ContractContentViewer.vue'
import { contractTypeLabel, aiReviewStatusLabel, riskLevelLabel } from '@/utils/enumLabels'

const router = useRouter()
const auth = useAuthStore()
const { contractId } = useContractContext()
const loading = ref(true)
const saving = ref(false)
const contract = ref<Contract | null>(null)
const versions = ref<ContractVersion[]>([])
const uploading = ref(false)
const lastUpload = ref<ContractUploadResult | null>(null)
const aiSummary = ref<AiReviewSummary | null>(null)
const flowHistory = ref<{ flow_type?: string; status?: string; steps?: unknown[] } | null>(null)
const detailTab = ref('overview')
const showAdvancedContent = ref<string[]>([])
const attachmentPreviewUrl = ref<string | null>(null)
const attachmentPreviewLoading = ref(false)

const isDraft = computed(() => contract.value?.status === 'draft')
const canDelete = computed(() =>
  canDeleteContract(contract.value, auth.user?.id, auth.role),
)
const deleting = ref(false)
const lifecycleIndex = computed(() => lifecycleActiveIndex(contract.value?.status))
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

async function deleteDraft() {
  const id = contractId.value
  if (!id || !canDelete.value) return
  try {
    await ElMessageBox.confirm(DELETE_DRAFT_CONFIRM_MESSAGE, DELETE_DRAFT_CONFIRM_TITLE, {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }
  deleting.value = true
  try {
    await contractsApi.delete(id)
    ElMessage.success('草稿已删除')
    router.push({ name: 'contracts' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  } finally {
    deleting.value = false
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

const approvalActiveStep = computed(() => {
  const steps = flowHistory.value?.steps as Array<{ status?: string; action?: string }> | undefined
  if (!steps?.length) return 0
  const pendingIdx = steps.findIndex(
    (s) => s.status === 'pending' || (!s.action && s.status !== 'completed'),
  )
  if (pendingIdx >= 0) return pendingIdx
  const inProgress = steps.findIndex((s) => s.status === 'in_progress')
  if (inProgress >= 0) return inProgress
  return steps.length
})

function attachmentFileName(path?: string | null) {
  if (!path) return '—'
  return path.split('/').pop() || path
}

const aiRiskLabel = computed(() => riskLevelLabel(aiSummary.value?.risk_level))

const latestPdfAttachment = computed(() => {
  const row = attachmentVersions.value.find((v) => {
    const name = v.file_path?.split('/').pop()?.toLowerCase() || ''
    return name.endsWith('.pdf')
  })
  return row || null
})

const contentLooksOcr = computed(() => /--- 第 \d+ 页 ---/.test(contract.value?.content || ''))

const showContentDualPane = computed(
  () => contentLooksOcr.value && Boolean(latestPdfAttachment.value),
)

function revokeAttachmentPreview() {
  if (attachmentPreviewUrl.value) {
    URL.revokeObjectURL(attachmentPreviewUrl.value)
    attachmentPreviewUrl.value = null
  }
}

async function loadAttachmentPreview() {
  const id = contractId.value
  if (!id || !latestPdfAttachment.value || attachmentPreviewUrl.value) return
  attachmentPreviewLoading.value = true
  try {
    const { blob, contentType } = await contractsApi.downloadAttachment(id)
    if (!contentType.includes('pdf') && blob.type && !blob.type.includes('pdf')) {
      return
    }
    revokeAttachmentPreview()
    attachmentPreviewUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '原文加载失败')
  } finally {
    attachmentPreviewLoading.value = false
  }
}

watch(
  [detailTab, showContentDualPane, contractId],
  ([tab, dual]) => {
    if (tab === 'content' && dual) {
      void loadAttachmentPreview()
    }
  },
  { immediate: true },
)

watch(contractId, () => {
  revokeAttachmentPreview()
})

onBeforeUnmount(revokeAttachmentPreview)
</script>

<template>
  <div v-loading="loading" class="page-card">
    <ContractContextBar :contract="contract" />
    <template v-if="contract">
      <el-tabs v-model="detailTab">
        <el-tab-pane label="概览" name="overview">
          <el-card shadow="never" style="margin-bottom: 16px">
            <template #header>合同生命周期</template>
            <el-steps :active="lifecycleIndex" finish-status="success" align-center>
              <el-step v-for="stage in LIFECYCLE_STAGES" :key="stage.key" :title="stage.label" />
            </el-steps>
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
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="saveDraft">保存草稿</el-button>
                <el-button
                  v-if="canDelete"
                  type="danger"
                  plain
                  :loading="deleting"
                  @click="deleteDraft"
                >
                  删除草稿
                </el-button>
              </el-form-item>
            </el-form>
            <el-descriptions v-if="contract" :column="2" border size="small" style="max-width: 720px; margin-top: 16px">
              <el-descriptions-item label="创建时间">
                {{ formatDateTime(contract.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="履约期">
                {{ formatDateRange(contract.start_date, contract.end_date) }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-descriptions v-else :column="2" border>
            <el-descriptions-item label="合同编号">{{ contract.contract_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ contractTypeLabel(contract.contract_type) }}</el-descriptions-item>
            <el-descriptions-item label="相对方">{{ contract.counterparty_name }}</el-descriptions-item>
            <el-descriptions-item label="金额">¥{{ contract.amount?.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(contract.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="履约期">
              {{ formatDateRange(contract.start_date, contract.end_date) }}
            </el-descriptions-item>
            <el-descriptions-item v-if="contract.sign_date" label="签署日期">
              {{ formatDate(contract.sign_date) }}
            </el-descriptions-item>
            <el-descriptions-item v-if="contract.archive_date" label="归档日期">
              {{ formatDate(contract.archive_date) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <StatusTag :status="contract.status" />
            </el-descriptions-item>
            <el-descriptions-item label="审批状态">
              <StatusTag v-if="contract.approval_status" :status="contract.approval_status" />
              <span v-else>—</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="正文与附件" name="content">
          <el-card shadow="never" v-loading="attachmentPreviewLoading">
            <template #header>合同正文</template>
            <ContractContentViewer
              v-if="showContentDualPane && attachmentPreviewUrl"
              :model-value="contract.content || ''"
              :preview-url="attachmentPreviewUrl"
              :ocr-used="contentLooksOcr"
              readonly
              :default-reading-mode="true"
            />
            <ContractContentViewer
              v-else-if="contentLooksOcr"
              :model-value="contract.content || ''"
              :ocr-used="true"
              readonly
              :default-reading-mode="true"
            />
            <pre v-else class="content-block">{{ contract.content || '（无正文）' }}</pre>
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
            <p v-if="lastUpload" class="upload-hint">已上传：{{ attachmentFileName(lastUpload.file_path) }}</p>
          </el-card>
          <el-card shadow="never" style="margin-top: 12px">
            <template #header>附件列表</template>
            <el-table :data="attachmentVersions" stripe size="small" empty-text="暂无附件">
              <el-table-column prop="version" label="版本" width="70" />
              <el-table-column label="文件名" min-width="220">
                <template #default="{ row }">{{ attachmentFileName(row.file_path) }}</template>
              </el-table-column>
              <el-table-column label="上传时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-collapse v-model="showAdvancedContent" style="margin-top: 12px">
            <el-collapse-item title="版本历史" name="versions">
              <el-table :data="versions" stripe size="small" empty-text="暂无版本记录">
                <el-table-column prop="version" label="版本" width="70" />
                <el-table-column prop="change_description" label="说明" min-width="140" />
                <el-table-column label="时间" width="180">
                  <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
            <el-collapse-item title="高级信息（路径与哈希）" name="tech">
              <el-table :data="attachmentVersions" stripe size="small" empty-text="暂无">
                <el-table-column label="文件名" min-width="160">
                  <template #default="{ row }">{{ attachmentFileName(row.file_path) }}</template>
                </el-table-column>
                <el-table-column prop="file_path" label="路径" min-width="220" show-overflow-tooltip />
                <el-table-column prop="file_hash" label="哈希" min-width="160" show-overflow-tooltip />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>

        <el-tab-pane label="审批与评审" name="approval">
          <el-card v-if="flowHistory?.steps?.length" shadow="never">
            <template #header>审批进度</template>
            <el-steps :active="approvalActiveStep" finish-status="success" align-center>
              <el-step
                v-for="(step, idx) in flowHistory.steps"
                :key="idx"
                :title="stepTitle(step, idx)"
                :description="stepDesc(step)"
              />
            </el-steps>
          </el-card>
          <el-empty v-else description="暂无审批记录" />
        </el-tab-pane>

        <el-tab-pane label="AI 报告摘要" name="ai">
          <el-card v-if="aiSummary" shadow="never">
            <el-descriptions :column="3" size="small" border>
              <el-descriptions-item label="风险等级">{{ aiRiskLabel }}</el-descriptions-item>
              <el-descriptions-item label="风险分">{{ aiSummary.risk_score ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ aiReviewStatusLabel(aiSummary.review_status) }}</el-descriptions-item>
            </el-descriptions>
            <div style="margin-top: 12px">
              <el-button type="primary" plain @click="goAiReview">查看完整报告</el-button>
              <el-button plain @click="goClauseCompare">条款比对</el-button>
            </div>
          </el-card>
          <el-empty v-else description="暂无 AI 审查报告">
            <el-button type="primary" @click="goAiReview">触发审查</el-button>
          </el-empty>
        </el-tab-pane>
      </el-tabs>
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
.upload-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #059669;
}
</style>
