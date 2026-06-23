<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus'
import { contractsApi, resolveFlowType, mapFlowTypeForApi, type ContractParseFields } from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import { aiReviewApi } from '@/api/ai-review'
import { counterpartiesApi, type CounterpartyItem } from '@/api/counterparties'
import { templatesApi, type ContractTemplate } from '@/api/templates'
import { useAuthStore } from '@/stores/auth'
import { debounce } from '@/utils/debounce'
import type { DocumentJSON } from '@/types/documentJson'
import type { Contract, FlowMatchResult } from '@/types/models'
import { flowTypeLabel } from '@/utils/enumLabels'
import { TEMPLATE_VAR_FORM_BIND } from '@/utils/templateFill'
import ContractContentViewer from '@/components/ContractContentViewer.vue'

const DRAFT_KEY = 'contract-draft'
const PARSEABLE_EXT = new Set(['pdf', 'docx', 'txt', 'doc'])

type CreateMode = 'blank' | 'template' | 'history' | 'ai-parse'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const mode = ref<CreateMode>('blank')
const wizardStep = ref(0)

const MODE_OPTIONS: { key: CreateMode; title: string; desc: string }[] = [
  { key: 'blank', title: '空白起草', desc: '手动填写全部字段' },
  { key: 'template', title: '模板起草', desc: '从已发布模板套用' },
  { key: 'history', title: '历史引用', desc: '引用历史合同字段' },
  { key: 'ai-parse', title: '智能起草', desc: '上传文件自动解析' },
]

function selectMode(m: CreateMode) {
  mode.value = m
  wizardStep.value = 1
}

function wizardBack() {
  if (wizardStep.value > 0) wizardStep.value -= 1
}

function wizardNext() {
  if (wizardStep.value !== 1) return
  if (mode.value === 'ai-parse' && !parseStatus.value) {
    ElMessage.warning('请先上传并解析合同文件')
    return
  }
  if (mode.value === 'template') {
    if (!selectedTemplateId.value) {
      ElMessage.warning('请选择模板')
      return
    }
    if (!form.content?.trim()) {
      ElMessage.warning('请先点击「填充模板」生成合同正文')
      return
    }
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写合同标题')
    return
  }
  if (!form.counterparty_name.trim()) {
    ElMessage.warning('请选择或填写相对方')
    return
  }
  wizardStep.value = 2
}
const submitting = ref(false)
const flowDialogVisible = ref(false)
const flowMatch = ref<FlowMatchResult | null>(null)
const counterparties = ref<CounterpartyItem[]>([])
const templates = ref<ContractTemplate[]>([])
const historyContracts = ref<Contract[]>([])

const form = reactive({
  title: '',
  contract_type: 'purchase',
  counterparty_name: '',
  amount: 10000,
  content: '',
})

const selectedTemplateId = ref<number | null>(null)
const selectedTemplateMeta = ref<{ version?: number; variables: string[] } | null>(null)
const templateVarValues = ref<Record<string, string>>({})
const selectedHistoryId = ref<number | null>(null)
const pendingFile = ref<File | null>(null)
const parseLoading = ref(false)
const parseStatus = ref<{
  char_count?: number
  ocr_used?: boolean
  confidence?: number
  party_parse_warning?: boolean
  counterparty_corrections?: string[]
  ocr_needs_review?: boolean
  layout_suspect?: boolean
  ocr_engine?: string | null
  full_text_raw?: string | null
  document_json?: DocumentJSON | null
} | null>(null)

const ocrConfirmChecked = ref(false)

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

/** 与后端 PAGE_MARKER_RE 一致：OCR 分页标记不应作为合同标题 */
const PAGE_MARKER_TITLE_RE = /^---\s*第\s*\d+\s*页\s*---$/

function titleFromFilename(filename: string): string {
  let base = filename.replace(/\.[^.]+$/, '').trim()
  base = base.replace(/[-—]\s*[\d.]+\s*万(?:元)?\s*$/i, '').trim()
  return base.slice(0, 120) || '未命名合同'
}

function isPageMarkerTitle(title: string): boolean {
  return PAGE_MARKER_TITLE_RE.test(title.trim())
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
  const trimmed = full.trimStart()
  if (trimmed.startsWith('%PDF-') || (trimmed.includes('endobj') && trimmed.includes('/Type'))) {
    ElMessage.error('解析结果异常（疑似 PDF 原始数据），请重新上传或联系管理员检查 OCR')
    parseStatus.value = null
    form.content = ''
    return {}
  }
  form.content = full.slice(0, 500_000)
  let parsedTitle = String(f.title || titleFromFilename(file.name)).slice(0, 120)
  let titleFromFilenameFallback = false
  if (isPageMarkerTitle(parsedTitle)) {
    parsedTitle = titleFromFilename(file.name)
    titleFromFilenameFallback = true
  }
  const snap = preParseSnapshot.value
  if (!snap || form.title === snap.title) {
    form.title = parsedTitle
    if (titleFromFilenameFallback) {
      ElMessage.warning('标题已从文件名推断，请核对')
    }
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
    ocr_needs_review: f.ocr_needs_review,
    layout_suspect: f.layout_suspect,
    ocr_engine: data.ocr_engine ?? null,
    full_text_raw: f.full_text_raw ?? null,
    document_json: (data.document_json ?? data.extracted_metadata?.document_json) as DocumentJSON | null,
  }
  parseStatus.value = status
  ocrConfirmChecked.value = false
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
    if (!form.content.trim()) {
      return false
    }
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

function isBlacklisted(name: string): boolean {
  const cp = counterparties.value.find((c) => c.name === name)
  if (!cp) return false
  return Number(cp.is_blacklist) === 1
}

/** 提交前刷新相对方列表，避免缓存导致黑名单漏检 */
async function ensureNotBlacklisted(name: string): Promise<boolean> {
  if (!name.trim()) return true
  if (isBlacklisted(name)) return false
  try {
    const res = await counterpartiesApi.list({ page_size: 100 })
    counterparties.value = res.items || []
  } catch {
    /* 刷新失败时沿用本地列表 */
  }
  return !isBlacklisted(name)
}

const needsOcrConfirm = computed(() => {
  if (mode.value !== 'ai-parse' || !parseStatus.value) return false
  if (parseStatus.value.party_parse_warning) return true
  const c = parseStatus.value.confidence
  return c != null && c < 0.6
})

watch(
  () => form.counterparty_name,
  (name) => {
    if (name && isBlacklisted(name)) {
      ElMessage.warning(`相对方「${name}」已在黑名单中，无法提交审批`)
    }
  },
)

onMounted(async () => {
  const q = route.query.mode
  if (q === 'blank' || q === 'template' || q === 'history' || q === 'ai-parse') {
    mode.value = q as CreateMode
    wizardStep.value = 1
  }
  restoreDraft()
  try {
    const [cpRes, tplRes, listRes] = await Promise.all([
      counterpartiesApi.list({ page_size: 100 }),
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

watch(selectedTemplateId, async (id) => {
  templateVarValues.value = {}
  selectedTemplateMeta.value = null
  if (!id) return
  try {
    const detail = await templatesApi.get(id)
    const vars = detail.variables?.length
      ? detail.variables
      : (detail.content || '').match(/\{([^{}]+)\}/g)?.map((m) => m.slice(1, -1).trim()) || []
    selectedTemplateMeta.value = { version: detail.version, variables: vars }
    const init: Record<string, string> = {}
    for (const v of vars) {
      init[v] = templateVarValues.value[v] || ''
    }
    templateVarValues.value = init
    form.contract_type = detail.category || form.contract_type
    if (!form.title.trim()) form.title = detail.name
  } catch {
    ElMessage.error('加载模板详情失败')
  }
})

function bindTemplateVarsToForm() {
  for (const [varName, field] of Object.entries(TEMPLATE_VAR_FORM_BIND)) {
    const val = templateVarValues.value[varName]
    if (val == null || val === '') continue
    if (field === 'amount') {
      const n = Number(String(val).replace(/,/g, ''))
      if (!Number.isNaN(n)) form.amount = n
    } else if (field === 'counterparty_name') {
      form.counterparty_name = val
    } else if (field === 'title') {
      form.title = val
    }
  }
}

async function applyTemplate() {
  if (!selectedTemplateId.value) {
    ElMessage.warning('请先选择模板')
    return
  }
  const vars = selectedTemplateMeta.value?.variables || []
  for (const v of vars) {
    if (!String(templateVarValues.value[v] ?? '').trim()) {
      ElMessage.warning(`请填写模板变量「${v}」`)
      return
    }
  }
  try {
    const res = await templatesApi.fill(selectedTemplateId.value, {
      ...templateVarValues.value,
      金额: templateVarValues.value['金额'] ?? form.amount,
      相对方: templateVarValues.value['相对方'] ?? form.counterparty_name,
    })
    form.content = res.content
    selectedTemplateMeta.value = {
      version: res.template_version ?? selectedTemplateMeta.value?.version,
      variables: res.variables || vars,
    }
    bindTemplateVarsToForm()
    const tpl = templates.value.find((t) => t.id === selectedTemplateId.value)
    if (tpl && !form.title.trim()) form.title = tpl.name
    if (tpl) form.contract_type = tpl.category || form.contract_type
    ElMessage.success('模板已填充，请核对正文与关键字段')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '填充失败')
  }
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
  if (mode.value === 'ai-parse' && !parseStatus.value) {
    ElMessage.warning('请先上传并完成文件解析')
    return
  }
  if (!form.title || !form.counterparty_name || !form.amount) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (!(await ensureNotBlacklisted(form.counterparty_name))) {
    await ElMessageBox.alert(
      `相对方「${form.counterparty_name}」已被列入黑名单，无法提交审批。请更换相对方或在相对方管理中解除黑名单。`,
      '黑名单拦截',
      { type: 'error', confirmButtonText: '知道了' },
    )
    ElMessage.error('该相对方在黑名单中，已阻止提交')
    return
  }
  if (needsOcrConfirm.value) {
    if (!ocrConfirmChecked.value) {
      ElMessage.warning('请先勾选「我已核对 OCR 解析字段」')
      return
    }
    try {
      await ElMessageBox.confirm(
        '解析结果可能存在 OCR 识别错误，请确认已人工核对标题、相对方与金额后再提交。',
        'OCR 字段确认',
        { confirmButtonText: '已核对，继续提交', cancelButtonText: '返回修改', type: 'warning' },
      )
    } catch {
      return
    }
  }
  submitting.value = true
  try {
    const flowType = resolveFlowType(form.contract_type, form.amount)
    flowMatch.value = await contractsApi.matchFlow(form.amount)
    const created = await contractsApi.create({
      title: form.title,
      contract_type: form.contract_type,
      counterparty_name: form.counterparty_name,
      amount: form.amount,
      content: form.content,
      ...(mode.value === 'template' && selectedTemplateId.value
        ? {
            template_id: selectedTemplateId.value,
            template_version: selectedTemplateMeta.value?.version,
            template_values: { ...templateVarValues.value },
          }
        : {}),
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

async function goApprovals() {
  flowDialogVisible.value = false
  try {
    await auth.switchRole('approver')
    await router.push({ name: 'approvals' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '切换审批角色失败')
  }
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
    return '请先上传 PDF/DOCX/TXT，系统将自动解析并填写下方字段（扫描件 OCR 约需数分钟）'
  }
  return '空白起草，填写全部字段'
})

function templateLabel(t: ContractTemplate) {
  const code = t.code ? `${t.code} · ` : ''
  const ver = t.version != null ? ` v${t.version}` : ''
  return `${code}${t.name}${ver}`
}
</script>

<template>
  <div class="page-card create-wizard">
    <el-steps :active="wizardStep" finish-status="success" align-center style="margin-bottom: 24px">
      <el-step title="选择方式" />
      <el-step title="基本信息" />
      <el-step title="正文与提交" />
    </el-steps>

    <div v-if="wizardStep === 0" class="mode-grid">
      <el-card
        v-for="opt in MODE_OPTIONS"
        :key="opt.key"
        shadow="hover"
        class="mode-card"
        @click="selectMode(opt.key)"
      >
        <h3>{{ opt.title }}</h3>
        <p>{{ opt.desc }}</p>
      </el-card>
    </div>

    <template v-if="wizardStep === 1">
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
      <template v-if="selectedTemplateMeta?.variables?.length">
        <el-form-item
          v-for="v in selectedTemplateMeta.variables"
          :key="v"
          :label="v"
          required
        >
          <el-input v-model="templateVarValues[v]" :placeholder="`填写 {${v}}`" />
        </el-form-item>
      </template>
      <el-form-item>
        <el-button type="primary" plain @click="applyTemplate">填充模板</el-button>
        <span v-if="form.content" class="fill-hint">已生成正文，可在下一步预览</span>
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

    <el-form
      v-if="mode === 'ai-parse'"
      label-width="120px"
      style="max-width: 640px; margin-bottom: 16px"
      data-testid="ai-parse-upload-form"
    >
      <el-form-item label="上传合同文件" required>
        <el-upload
          drag
          :auto-upload="true"
          :show-file-list="false"
          accept=".pdf,.docx,.txt,.doc"
          :disabled="parseLoading"
          :before-upload="onParseFile"
          data-testid="ai-parse-upload"
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
          title="相对方名称疑似 OCR 识别错误，请在下方字段中核对或修正。"
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
    </el-form>

    <p v-if="mode === 'ai-parse' && !parseStatus && !parseLoading" class="parse-wait-hint">
      上传合同文件后，系统将自动识别并填写下方字段
    </p>

    <el-form v-if="mode !== 'ai-parse' || parseStatus" label-width="120px" style="max-width: 640px">
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
          <el-option
            v-for="cp in counterparties"
            :key="cp.id"
            :label="cp.is_blacklist ? `${cp.name}（黑名单）` : cp.name"
            :value="cp.name"
          />
        </el-select>
        <el-alert
          v-if="isBlacklisted(form.counterparty_name)"
          type="error"
          :closable="false"
          show-icon
          title="该相对方在黑名单中，无法提交审批"
          style="margin-top: 8px"
        />
      </el-form-item>
      <el-form-item label="金额（元）" required>
        <el-input-number v-model="form.amount" :min="1" :step="1000" style="width: 100%" />
      </el-form-item>
      <div class="wizard-nav">
        <el-button @click="wizardBack">上一步</el-button>
        <el-button type="primary" @click="wizardNext">下一步</el-button>
      </div>
    </el-form>
    </template>

    <template v-if="wizardStep === 2">
      <p v-if="mode === 'ai-parse'" class="mode-hint">核对正文与 OCR 字段，确认无误后提交审批</p>
      <div v-if="mode === 'ai-parse' && parseStatus" class="content-viewer-wrap">
        <ContractContentViewer
          v-model="form.content"
          :source-file="pendingFile"
          :ocr-used="Boolean(parseStatus?.ocr_used)"
          :ocr-engine="parseStatus?.ocr_engine"
          :confidence="parseStatus?.confidence"
          :ocr-needs-review="Boolean(parseStatus?.ocr_needs_review)"
          :layout-suspect="Boolean(parseStatus?.layout_suspect)"
          :char-count="parseStatus?.char_count"
          :full-text-raw="parseStatus?.full_text_raw"
          :document-json="parseStatus?.document_json"
          :default-reading-mode="false"
          :min-rows="18"
        />
        <p v-if="contentHint" class="content-hint">{{ contentHint }}</p>
      </div>
      <el-form v-else label-width="120px" style="max-width: 640px">
        <el-form-item label="合同正文">
          <el-input v-model="form.content" type="textarea" :rows="6" />
          <p v-if="contentHint" class="content-hint">{{ contentHint }}</p>
        </el-form-item>
      </el-form>
      <el-form label-width="120px" style="max-width: 640px">
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
      <el-form-item v-if="needsOcrConfirm" label="OCR 确认">
        <el-checkbox v-model="ocrConfirmChecked" data-testid="ocr-confirm-checkbox">
          我已核对 OCR 解析的标题、相对方、金额与正文，确认无误后再提交
        </el-checkbox>
      </el-form-item>
      </el-form>
      <div class="wizard-footer">
        <el-button @click="wizardBack">上一步</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交审批</el-button>
      </div>
    </template>

    <el-dialog v-model="flowDialogVisible" title="流程匹配" width="520px">
      <p>
        流程类型：{{
          (flowMatch?.flow_label as string) ||
          flowTypeLabel(flowMatch?.flow_type || 'simple')
        }}
      </p>
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
        <el-button type="primary" @click="goApprovals">前往待办审批（部门主管）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.fill-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #6b7280;
}

.mode-hint {
  color: #6b7280;
  font-size: 13px;
  margin: 0 0 12px;
}
.mode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  max-width: 880px;
}
.mode-card {
  cursor: pointer;
  transition: transform 0.15s ease;
}
.mode-card:hover {
  transform: translateY(-2px);
}
.mode-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.mode-card p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.wizard-nav,
.wizard-footer {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
.wizard-footer {
  position: sticky;
  bottom: 0;
  background: #fff;
  padding-bottom: 8px;
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
.parse-wait-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #9ca3af;
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
.content-viewer-wrap {
  width: 100%;
  max-width: min(1400px, 100%);
  margin-bottom: 16px;
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
