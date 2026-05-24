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

type CreateMode = 'blank' | 'template' | 'history'

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
    const flow = await approvalsApi.submit(created.id, mapFlowTypeForApi(flowType))
    auth.setLastContract(created, flow.flow_id)
    localStorage.removeItem(DRAFT_KEY)
    flowDialogVisible.value = true
    ElMessage.success(`合同 #${created.id} 已提交审批`)
    try {
      await aiReviewApi.review(created.id)
    } catch {
      /* AI 可选 */
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
</style>
