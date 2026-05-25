<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractsApi, resolveFlowType, mapFlowTypeForApi } from '@/api/contracts'
import { approvalsApi } from '@/api/approvals'
import { aiReviewApi } from '@/api/ai-review'
import { counterpartiesApi, type CounterpartyItem } from '@/api/counterparties'
import { templatesApi, type ContractTemplate } from '@/api/templates'
import { useAuthStore } from '@/stores/auth'
import { debounce } from '@/utils/debounce'
import type { Contract, FlowMatchResult } from '@/types/models'

const DRAFT_KEY = 'contract-draft'

type CreateMode = 'blank' | 'template' | 'history' | 'ai-parse'

const router = useRouter()
const auth = useAuthStore()
const mode = ref<CreateMode>('blank')
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

const saveDraft = debounce(() => {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...form, mode: mode.value }))
  } catch {
    /* 存储满等情况 */
  }
}, 400)

watch(form, saveDraft, { deep: true })
watch(mode, saveDraft)

onMounted(async () => {
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

async function onParseFile(file: File) {
  parseLoading.value = true
  pendingFile.value = file
  try {
    const text = await file.text()
    form.content = text.slice(0, 8000)
    const titleMatch = text.match(/合同名称[：:]\s*(.+)/)
    const cpMatch = text.match(/相对方[：:]\s*(.+)/)
    const amtMatch = text.match(/金额[：:]\s*([\d,]+)/)
    if (titleMatch) form.title = titleMatch[1].trim().slice(0, 100)
    if (cpMatch) form.counterparty_name = cpMatch[1].trim().slice(0, 80)
    if (amtMatch) form.amount = Number(amtMatch[1].replace(/,/g, '')) || form.amount
    ElMessage.success('已解析文件内容（演示模式，请核对字段）')
  } catch {
    ElMessage.warning('解析失败，请手动补全字段')
  } finally {
    parseLoading.value = false
  }
  return false
}

function onPendingUpload(file: File) {
  pendingFile.value = file
  ElMessage.info(`已选择附件：${file.name}，提交后将自动上传`)
  return false
}

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
  if (mode.value === 'ai-parse') return '上传合同文本，AI 自动解析字段（演示）'
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

    <el-form v-if="mode === 'ai-parse'" label-width="100px" style="max-width: 640px; margin-bottom: 16px">
      <el-form-item label="上传合同">
        <el-upload :auto-upload="true" :show-file-list="false" :before-upload="onParseFile">
          <el-button type="primary" :loading="parseLoading">上传 TXT 解析</el-button>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-form label-width="100px" style="max-width: 640px">
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
        <el-input v-model="form.content" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="附件（可选）">
        <el-upload :auto-upload="true" :show-file-list="false" :before-upload="onPendingUpload">
          <el-button>选择附件</el-button>
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
</style>
