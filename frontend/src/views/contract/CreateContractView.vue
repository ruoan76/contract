<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { contractsApi, resolveFlowType, mapFlowTypeForApi, type ContractParseFields } from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import { aiReviewApi } from '@/api/ai-review'
import { counterpartiesApi, type CounterpartyItem } from '@/api/counterparties'
import { templatesApi, type ContractTemplate } from '@/api/templates'
import { useAuthStore } from '@/stores/auth'
import { debounce } from '@/utils/debounce'
import type { Contract, FlowMatchResult } from '@/types/models'

const DRAFT_KEY = 'contract-draft'
const PARSEABLE_EXT = new Set(['pdf', 'docx', 'txt', 'doc'])

type CreateMode = 'blank' | 'template' | 'history' | 'ai-parse'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const mode = ref<CreateMode>('ai-parse')
const submitting = ref(false)
const flowDialogVisible = ref(false)
const flowMatch = ref<FlowMatchResult | null>(null)
const counterparties = ref<CounterpartyItem[]>([])
const templates = ref<ContractTemplate[]>([])
const historyContracts = ref<Contract[]>([])

const form = reactive({
  title: '小额办公耗材采购',
  contract_type: 'purchase',
  counterparty_name: '得力集团',
  amount: 80000,
  content: '采购办公耗材，金额 8 万元，简易流程演示。',
})

const selectedTemplateId = ref<number | null>(null)
const selectedHistoryId = ref<number | null>(null)
const pendingFile = ref<File | null>(null)
const parseLoading = ref(false)
const parseStatus = ref<{
  char_count?: number
  ocr_used?: boolean
  confidence?: number
  party_parse_warning?: boolean
  counterparty_corrections?: string[]
} | null>(null)

/** 解析开始前表单快照，用于避免覆盖用户已修改字段 */
const preParseSnapshot = ref<{
  title: string
  counterparty_name: string
  amount: number
} | null>(null)

function restoreDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return
    const draft = JSON.parse(raw) as Partial<typeof form> & { mode?: CreateMode }
    Object.assign(form, draft)
    if (draft.mode) mode.value = draft.mode
    ElMessage.info('已恢复本地草稿')
  } catch {
    /* 忽略损坏草稿 */
  }
}

function saveDraftImmediate() {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...form, mode: mode.value }))
  } catch {
    /* 存储满等情况 */
  }
}

function fileExtension(name: string): string {
  return name.split('.').pop()?.toLowerCase() || ''
}

function isParseableFile(file: File): boolean {
  return PARSEABLE_EXT.has(fileExtension(file.name))
}

function titleFromFilename(filename: string): string {
  return filename.replace(/\.[^.]+$/, '').slice(0, 120)
}

function inferContractType(
  fields: ContractParseFields,
  fullText: string,
  filename: string,
): string {
  const hint = `${fullText.slice(0, 800)} ${filename}`
  if (/建设|信息化|开发|服务项目|技术服务/.test(hint)) return 'service'
  if (fields.contract_type) return fields.contract_type
  return 'purchase'
}

function fillFormFromParse(
  data: Awaited<ReturnType<typeof contractsApi.parse>>,
  file: File,
): {
  char_count?: number
  ocr_used?: boolean
  confidence?: number
  party_parse_warning?: boolean
  counterparty_corrections?: string[]
} {
  const f = data.fields || {}
  const full = f.full_text || f.text_preview || ''
  form.content = full.slice(0, 500_000)
  const parsedTitle = String(f.title || titleFromFilename(file.name)).slice(0, 120)
  const snap = preParseSnapshot.value
  if (!snap || form.title === snap.title) {
    form.title = parsedTitle
  }
  const parsedCounterparty = f.party_b
    ? String(f.party_b).slice(0, 80)
    : f.party_a
      ? String(f.party_a).slice(0, 80)
      : ''
  if (parsedCounterparty && (!snap || form.counterparty_name === snap.counterparty_name)) {
    form.counterparty_name = parsedCounterparty
  }
  if (f.amount != null && f.amount > 0 && (!snap || form.amount === snap.amount)) {
    form.amount = f.amount
  }
  form.contract_type = inferContractType(f, full, file.name)
  const status = {
    char_count: data.char_count ?? f.char_count,
    ocr_used: data.ocr_used ?? f.ocr_used,
    confidence: f.confidence,
    party_parse_warning: f.party_parse_warning,
    counterparty_corrections: f.counterparty_corrections,
  }
  parseStatus.value = status
  return status
}

async function applyParsedFile(file: File): Promise<boolean> {
  if (!isParseableFile(file)) {
    ElMessage.warning('仅支持 PDF、DOCX、TXT 格式自动解析')
    return false
  }
  parseLoading.value = true
  pendingFile.value = file
  parseStatus.value = null
  preParseSnapshot.value = {
    title: form.title,
    counterparty_name: form.counterparty_name,
    amount: form.amount,
  }
  const loading = ElLoading.service({
    lock: true,
    text: '正在解析合同，扫描件 OCR 可能需要数分钟…',
    background: 'rgba(0, 0, 0, 0.35)',
  })
  try {
    const data = await contractsApi.parse(file)
    const status = fillFormFromParse(data, file)
    saveDraftImmediate()
    const ocrHint = status.ocr_used ? '（已 OCR）' : ''
    if (status.party_parse_warning || (status.confidence != null && status.confidence < 0.6)) {
      ElMessage.warning(
        `解析完成${ocrHint}：约 ${status.char_count ?? 0} 字。相对方或字段疑似 OCR 错误，请人工核对后再提交。`,
      )
    } else {
      ElMessage.success(
        `解析完成${ocrHint}：约 ${status.char_count ?? 0} 字，请核对字段`,
      )
    }
    return true
  } catch (e) {
    ElMessage.warning(e instanceof Error ? e.message : '解析失败，请手动补全字段')
    return false
  } finally {
    loading.close()
    parseLoading.value = false
  }
}

const saveDraft = debounce(saveDraftImmediate, 400)

watch(form, saveDraft, { deep: true })
watch(mode, saveDraft)

onMounted(async () => {
  const q = route.query.mode
  if (q === 'blank' || q === 'template' || q === 'history' || q === 'ai-parse') {
    mode.value = q
  }
  restoreDraft()
  try {
    const [cpRes, tplRes, listRes] = await Promise.all([
      counterpartiesApi.list(),
      templatesApi.list({ status: 'published', page_size: 50 }).catch(() => ({ items: [] })),
      contractsApi.list({ page: 1, page_size: 20 }),
    ])
    counterparties.value = cpRes.items || []
    templates.value = (tplRes.items || []).filter((t) => t.status === 'published')
    historyContracts.value = listRes.items || []
  } catch {
    counterparties.value = []
  }
})

function applyTemplate() {
  const tpl = templates.value.find((t) => t.id === selectedTemplateId.value)
  if (!tpl) return
  form.title = tpl.name
  form.contract_type = tpl.category || form.contract_type
  form.content = tpl.content || form.content
  ElMessage.success(`已套用模板：${tpl.name}`)
}

function applyHistory() {
  const c = historyContracts.value.find((x) => x.id === selectedHistoryId.value)
  if (!c) return
  form.title = `${c.title}（引用）`
  form.contract_type = c.contract_type || form.contract_type
  form.counterparty_name = c.counterparty_name
  form.amount = c.amount
  form.content = c.content || form.content
  ElMessage.success(`已引用合同 #${c.id}`)
}

async function submit() {
  if (!form.title || !form.counterparty_name || !form.amount) {
    ElMessage.warning('请填写必填项')
    return
  }
  submitting.value = true
  try {
    await auth.switchRole('drafter')
    const flowType = resolveFlowType(form.contract_type, form.amount)
    flowMatch.value = await contractsApi.matchFlow(form.amount)
    const created = await contractsApi.create({
      title: form.title,
      contract_type: form.contract_type,
      counterparty_name: form.counterparty_name,
      amount: form.amount,
      content: form.content,
    })
    if (pendingFile.value) {
      try {
        await contractsApi.upload(created.id, pendingFile.value)
      } catch {
        ElMessage.warning('合同已创建，附件上传失败')
      }
      pendingFile.value = null
    }
    const flow = await approvalsApi.submit(created.id, mapFlowTypeForApi(flowType))
    auth.setLastContract(created, flow.flow_id)
    localStorage.removeItem(DRAFT_KEY)
    flowDialogVisible.value = true
    ElMessage.success(`合同 #${created.id} 已提交审批`)
    // E2E / 演示环境跳过后台 AI，避免同步审查长时间占库导致审批 500
    if (import.meta.env.VITE_E2E !== '1') {
      void (async () => {
        try {
          await aiReviewApi.review(created.id)
          ElMessage.success('AI 初筛已触发')
        } catch (e) {
          ElMessage.warning(
            e instanceof Error
              ? `AI 初筛未成功：${e.message}，请稍后在「AI 审查报告」手动触发`
              : 'AI 初筛未成功，请稍后在「AI 审查报告」手动触发',
          )
        }
      })()
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

function goApprovals() {
  flowDialogVisible.value = false
  router.push({ name: 'approvals' })
}

function goLegalReview() {
  flowDialogVisible.value = false
  const c = auth.lastContract
  if (c?.id) {
    router.push({ name: 'review-workspace', params: { id: String(c.id) } })
  }
}

/** Element Plus 需返回 Promise，否则异步解析未完成就结束 */
function onParseFile(file: File) {
  return applyParsedFile(file).then(() => false)
}

function onPendingUpload(file: File) {
  if (isParseableFile(file)) {
    return applyParsedFile(file).then(() => false)
  }
  pendingFile.value = file
  ElMessage.info(`已选择附件：${file.name}，提交后将自动上传`)
  return false
}

const attachmentLabel = computed(() =>
  mode.value === 'ai-parse' ? '上传合同文件' : '附件（可选）',
)

const contentHint = computed(() => {
  if (!parseStatus.value?.char_count) return ''
  return `共 ${parseStatus.value.char_count} 字，完整正文已写入，提交后一并保存`
})

const flowSteps = () => {
  const steps = flowMatch.value?.steps
  if (Array.isArray(steps) && steps.length) return steps
  return [
    { step: 1, role: 'approver', name: '部门主管' },
    { step: 2, role: 'legal', name: '法务评审' },
    { step: 3, role: 'seal', name: '用印' },
  ]
}

const modeHint = computed(() => {
  if (mode.value === 'template') return '从已发布模板套用正文与标题'
  if (mode.value === 'history') return '引用历史合同字段快速起草'
  if (mode.value === 'ai-parse') {
    return '上传 PDF/DOCX/TXT 后自动解析并填写下方字段（扫描件 OCR 约需数分钟）'
  }
  return '空白起草，填写全部字段'
})

function templateLabel(t: ContractTemplate) {
  const ver = t.version != null ? ` v${t.version}` : ''
  return `${t.name}${ver}`
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>新建合同</h2>
    </div>

    <el-tabs v-model="mode" style="margin-bottom: 16px">
      <el-tab-pane label="空白起草" name="blank" />
      <el-tab-pane label="模板起草" name="template" />
      <el-tab-pane label="历史引用" name="history" />
      <el-tab-pane label="智能起草" name="ai-parse" />
    </el-tabs>
    <p class="mode-hint">{{ modeHint }}</p>

    <el-form v-if="mode === 'template'" label-width="100px" style="max-width: 640px; margin-bottom: 16px">
      <el-form-item label="选择模板">
        <el-select v-model="selectedTemplateId" filterable placeholder="已发布模板" style="width: 100%">
          <el-option
            v-for="t in templates"
            :key="t.id"
            :label="templateLabel(t)"
            :value="t.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" plain @click="applyTemplate">套用模板</el-button>
      </el-form-item>
    </el-form>

    <el-form v-if="mode === 'history'" label-width="100px" style="max-width: 640px; margin-bottom: 16px">
      <el-form-item label="历史合同">
        <el-select v-model="selectedHistoryId" filterable placeholder="选择合同" style="width: 100%">
          <el-option
            v-for="c in historyContracts"
            :key="c.id"
            :label="`#${c.id} ${c.title}`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" plain @click="applyHistory">引用字段</el-button>
      </el-form-item>
    </el-form>

    <el-form label-width="120px" style="max-width: 640px">
      <el-form-item v-if="mode === 'ai-parse'" label="上传合同文件" required>
        <el-upload
          drag
          :auto-upload="true"
          :show-file-list="false"
          accept=".pdf,.docx,.txt,.doc"
          :disabled="parseLoading"
          :before-upload="onParseFile"
        >
          <div class="upload-dragger-inner">
            <p>拖拽或点击上传 PDF / DOCX / TXT</p>
            <p class="upload-dragger-sub">上传后自动解析标题、金额、相对方与正文（扫描件 OCR 约 2–4 分钟）</p>
          </div>
        </el-upload>
        <el-upload
          class="upload-fallback"
          :auto-upload="true"
          :show-file-list="false"
          accept=".pdf,.docx,.txt,.doc"
          :disabled="parseLoading"
          :before-upload="onParseFile"
        >
          <el-button type="primary" plain :loading="parseLoading" style="margin-top: 8px">
            选择文件解析
          </el-button>
        </el-upload>
        <p v-if="parseStatus" class="parse-status" :class="{ 'parse-status-warn': parseStatus.party_parse_warning }">
          已提取 {{ parseStatus.char_count ?? 0 }} 字
          <span v-if="parseStatus.ocr_used"> · 扫描件 OCR</span>
          <span v-if="parseStatus.confidence != null"> · 置信度 {{ Math.round(parseStatus.confidence * 100) }}%</span>
        </p>
        <el-alert
          v-if="parseStatus?.party_parse_warning"
          type="warning"
          :closable="false"
          show-icon
          title="相对方名称疑似 OCR 识别错误，请在下方的「相对方」字段中核对或修正。"
          style="margin-top: 8px"
        />
        <el-alert
          v-if="parseStatus?.counterparty_corrections?.length"
          type="info"
          :closable="false"
          style="margin-top: 8px"
        >
          <template #title>已尝试与相对方库匹配校正</template>
          <ul class="correction-list">
            <li v-for="(line, i) in parseStatus.counterparty_corrections" :key="i">{{ line }}</li>
          </ul>
        </el-alert>
        <span v-if="pendingFile" class="pending-file">{{ pendingFile.name }}</span>
      </el-form-item>
      <el-form-item label="合同标题" required>
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="合同类型" required>
        <el-select v-model="form.contract_type" style="width: 100%">
          <el-option label="采购" value="purchase" />
          <el-option label="销售" value="sales" />
          <el-option label="服务" value="service" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="相对方" required>
        <el-select
          v-model="form.counterparty_name"
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入相对方"
          style="width: 100%"
        >
          <el-option v-for="cp in counterparties" :key="cp.id" :label="cp.name" :value="cp.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="金额（元）" required>
        <el-input-number v-model="form.amount" :min="1" :step="1000" style="width: 100%" />
      </el-form-item>
      <el-form-item label="合同正文">
        <el-input v-model="form.content" type="textarea" :rows="6" />
        <p v-if="contentHint" class="content-hint">{{ contentHint }}</p>
      </el-form-item>
      <el-form-item v-if="mode !== 'ai-parse'" :label="attachmentLabel">
        <el-upload
          :auto-upload="true"
          :show-file-list="false"
          accept=".pdf,.docx,.txt,.doc"
          :disabled="parseLoading"
          :before-upload="onPendingUpload"
        >
          <el-button :loading="parseLoading">选择附件</el-button>
        </el-upload>
        <span v-if="pendingFile" class="pending-file">{{ pendingFile.name }}</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">提交审批</el-button>
      </el-form-item>
    </el-form>

    <el-dialog v-model="flowDialogVisible" title="流程匹配" width="520px">
      <p>流程类型：{{ flowMatch?.flow_type || 'simple' }}</p>
      <el-timeline style="margin-top: 12px">
        <el-timeline-item
          v-for="(s, idx) in flowSteps()"
          :key="idx"
          :timestamp="'步骤 ' + (s.step ?? idx + 1)"
        >
          {{ s.name || s.role }}
        </el-timeline-item>
      </el-timeline>
      <template #footer>
        <el-button @click="flowDialogVisible = false">关闭</el-button>
        <el-button @click="goLegalReview">提交法务评审</el-button>
        <el-button type="primary" @click="goApprovals">前往待办审批</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mode-hint {
  color: #6b7280;
  font-size: 13px;
  margin: 0 0 12px;
}
.pending-file {
  margin-left: 8px;
  font-size: 12px;
  color: #6b7280;
}
.parse-status {
  margin-top: 8px;
  font-size: 12px;
  color: #059669;
}
.parse-status-warn {
  color: #d97706;
}
.correction-list {
  margin: 4px 0 0;
  padding-left: 18px;
  font-size: 12px;
}
.content-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}
.upload-dragger-inner {
  padding: 12px 0;
  color: #374151;
}
.upload-dragger-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}
</style>
