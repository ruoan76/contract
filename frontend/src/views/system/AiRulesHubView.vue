<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  aiReviewConfigApi,
  type ChecklistItem,
  type FeedbackStat,
  type HardRule,
  type LegalSnippet,
  type RevisionRoute,
  type RiskLabel,
} from '@/api/ai-review-config'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const isAdmin = computed(() => auth.role === 'admin')
const canAccessRulesHub = computed(() => auth.role === 'admin' || auth.role === 'legal')
const accessDenied = ref(false)

const activeTab = ref('checklist')
const configVersion = ref<string | null>(null)
const hasUnpublishedEdits = ref(false)
const loading = ref(false)

function markDraftChanged() {
  hasUnpublishedEdits.value = true
}

function clearDraftFlag() {
  hasUnpublishedEdits.value = false
}

const checklist = ref<ChecklistItem[]>([])
const labels = ref<RiskLabel[]>([])
const routing = ref<RevisionRoute[]>([])
const hardRules = ref<HardRule[]>([])
const snippets = ref<LegalSnippet[]>([])
const feedback = ref<FeedbackStat[]>([])

const checklistFilter = ref({ gate_id: '', auto_only: false })

const editChecklist = ref<ChecklistItem | null>(null)
const showChecklistDialog = ref(false)
const detectJson = ref('')

const editLabel = ref<RiskLabel | null>(null)
const showLabelDialog = ref(false)

const editRoute = ref<Partial<RevisionRoute> | null>(null)
const showRouteDialog = ref(false)
const routeIsNew = ref(false)

const editHard = ref<Partial<HardRule> | null>(null)
const showHardDialog = ref(false)
const hardConfigJson = ref('')
const hardIsNew = ref(false)

const editSnippet = ref<Partial<LegalSnippet> | null>(null)
const showSnippetDialog = ref(false)
const snippetKeywordsText = ref('')
const snippetIsNew = ref(false)

const testText = ref('预付款比例 50% 超过约定')
const sandboxRuleId = ref('')
const testResult = ref('')

async function loadAll() {
  loading.value = true
  try {
    const [ver, cl, lb, rt, hr, sn, fb] = await Promise.all([
      aiReviewConfigApi.getVersion(),
      aiReviewConfigApi.listChecklist({
        gate_id: checklistFilter.value.gate_id || undefined,
        auto_detectable: checklistFilter.value.auto_only || undefined,
      }),
      aiReviewConfigApi.listRiskLabels(),
      aiReviewConfigApi.listRouting(),
      aiReviewConfigApi.listHardRules(),
      aiReviewConfigApi.listLegalSnippets(),
      aiReviewConfigApi.feedbackStats(30),
    ])
    configVersion.value = ver?.version ?? null
    checklist.value = cl?.items ?? []
    labels.value = lb?.items ?? []
    routing.value = rt?.items ?? []
    hardRules.value = hr?.items ?? []
    snippets.value = sn?.items ?? []
    feedback.value = fb?.items ?? []
    if (!sandboxRuleId.value && hardRules.value.length) {
      sandboxRuleId.value = hardRules.value[0].rule_id
    }
  } catch (e) {
    const isForbidden =
      (e instanceof ApiError && e.status === 403) ||
      String((e as Error).message || '').includes('需要以下角色') ||
      String((e as Error).message || '').includes('需要角色')
    if (isForbidden) {
      accessDenied.value = true
      ElMessage.warning('当前登录账号无规则中心权限，请右上角切换为「法务专员」或「系统管理员」')
    } else {
      ElMessage.error((e as Error).message || '加载失败')
    }
  } finally {
    loading.value = false
  }
}

/** 按 Tab 按需加载，避免切换时全量刷新 */
async function loadTab(tab?: string | number) {
  const name = String(tab || activeTab.value)
  loading.value = true
  try {
    if (name === 'checklist') {
      const [ver, cl] = await Promise.all([
        aiReviewConfigApi.getVersion(),
        aiReviewConfigApi.listChecklist({
          gate_id: checklistFilter.value.gate_id || undefined,
          auto_detectable: checklistFilter.value.auto_only || undefined,
        }),
      ])
      configVersion.value = ver?.version ?? null
      checklist.value = cl?.items ?? []
    } else if (name === 'labels') {
      labels.value = (await aiReviewConfigApi.listRiskLabels())?.items ?? []
    } else if (name === 'routing') {
      routing.value = (await aiReviewConfigApi.listRouting())?.items ?? []
    } else if (name === 'hard') {
      const hr = await aiReviewConfigApi.listHardRules()
      hardRules.value = hr?.items ?? []
      if (!sandboxRuleId.value && hardRules.value.length) {
        sandboxRuleId.value = hardRules.value[0].rule_id
      }
    } else if (name === 'snippets') {
      snippets.value = (await aiReviewConfigApi.listLegalSnippets())?.items ?? []
    } else if (name === 'feedback') {
      feedback.value = (await aiReviewConfigApi.feedbackStats(30))?.items ?? []
    } else {
      await loadAll()
    }
  } catch (e) {
    ElMessage.error((e as Error).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function initPage() {
  await auth.ensureAuth()
  if (!canAccessRulesHub.value) {
    accessDenied.value = true
    ElMessage.warning('仅法务专员与系统管理员可访问 AI 规则中心')
    return
  }
  accessDenied.value = false
  await loadTab(activeTab.value)
}

onMounted(initPage)

/** Element Plus 取消确认框会 reject 'cancel'，需吞掉以免 Uncaught (in promise) */
async function confirmOrCancel(message: string, title: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title)
    return true
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') throw e
    return false
  }
}

async function handlePublish() {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可发布配置')
    return
  }
  if (!(await confirmOrCancel('发布后新审查任务将使用当前草稿，确认发布？', '发布配置'))) return
  await aiReviewConfigApi.publish('规则中心发布')
  clearDraftFlag()
  ElMessage.success('已发布，新审查任务将使用当前配置')
  await loadAll()
}

async function handleImportSeeds() {
  if (!isAdmin.value) return
  if (!(await confirmOrCancel('将从 JSON 种子重新导入并覆盖路由表，继续？', '导入种子'))) return
  const res = await aiReviewConfigApi.importSeeds()
  clearDraftFlag()
  ElMessage.success(`已导入种子并刷新缓存：${res?.version}`)
  await loadAll()
}

function openChecklistEdit(row: ChecklistItem) {
  editChecklist.value = { ...row }
  detectJson.value = row.detect_config ? JSON.stringify(row.detect_config, null, 2) : ''
  showChecklistDialog.value = true
}

async function saveChecklistEdit() {
  if (!editChecklist.value) return
  let detect: Record<string, unknown> | null = null
  if (detectJson.value.trim()) {
    try {
      detect = JSON.parse(detectJson.value)
    } catch {
      ElMessage.error('detect_config 不是合法 JSON')
      return
    }
  }
  await aiReviewConfigApi.updateChecklist(editChecklist.value.id, {
    ...editChecklist.value,
    detect_config: detect,
  })
  markDraftChanged()
  ElMessage.success('已保存（草稿），发布后生效')
  showChecklistDialog.value = false
  await loadAll()
}

async function toggleChecklistEnabled(row: ChecklistItem) {
  await aiReviewConfigApi.updateChecklist(row.id, { enabled: !row.enabled })
  markDraftChanged()
  await loadAll()
}

function openLabelEdit(row: RiskLabel) {
  editLabel.value = { ...row }
  showLabelDialog.value = true
}

async function saveLabelEdit() {
  if (!editLabel.value?.id) return
  await aiReviewConfigApi.updateRiskLabel(editLabel.value.id, editLabel.value)
  markDraftChanged()
  ElMessage.success('标签已保存（草稿）')
  showLabelDialog.value = false
  await loadAll()
}

function openRouteEdit(row?: RevisionRoute) {
  routeIsNew.value = !row
  editRoute.value = row
    ? { ...row }
    : { issue_type: '', default_method: 'comment', auto_applicable: true, priority: 0, enabled: true }
  showRouteDialog.value = true
}

async function saveRouteEdit() {
  if (!editRoute.value) return
  if (routeIsNew.value) {
    await aiReviewConfigApi.createRouting(editRoute.value)
  } else if (editRoute.value.id) {
    await aiReviewConfigApi.updateRouting(editRoute.value.id, editRoute.value)
  }
  markDraftChanged()
  ElMessage.success('修订路由已保存（草稿）')
  showRouteDialog.value = false
  await loadAll()
}

async function deleteRoute(row: RevisionRoute) {
  if (!isAdmin.value) return
  if (!(await confirmOrCancel(`删除路由「${row.issue_type}」？`, '删除'))) return
  await aiReviewConfigApi.deleteRouting(row.id)
  markDraftChanged()
  await loadAll()
}

function openHardEdit(row?: HardRule) {
  if (!isAdmin.value && row === undefined) return
  hardIsNew.value = !row
  editHard.value = row
    ? { ...row }
    : {
        rule_id: '',
        name: '',
        rule_type: 'regex',
        enabled: true,
        config: {},
        risk_level: 'medium',
        dimension: 'compliance_check',
        revision_method: 'comment',
        clause: '',
      }
  hardConfigJson.value = row?.config ? JSON.stringify(row.config, null, 2) : '{}'
  showHardDialog.value = true
}

async function saveHardEdit() {
  if (!editHard.value || !isAdmin.value) return
  let cfg: Record<string, unknown> = {}
  if (hardConfigJson.value.trim()) {
    try {
      cfg = JSON.parse(hardConfigJson.value)
    } catch {
      ElMessage.error('config 不是合法 JSON')
      return
    }
  }
  const body = { ...editHard.value, config: cfg }
  if (hardIsNew.value) {
    await aiReviewConfigApi.createHardRule(body)
  } else if (editHard.value.id) {
    await aiReviewConfigApi.updateHardRule(editHard.value.id, body)
  }
  markDraftChanged()
  ElMessage.success('硬规则已保存（草稿）')
  showHardDialog.value = false
  await loadAll()
}

async function toggleHardEnabled(row: HardRule) {
  if (!isAdmin.value) return
  await aiReviewConfigApi.updateHardRule(row.id, { enabled: !row.enabled })
  markDraftChanged()
  await loadAll()
}

function openSnippetEdit(row?: LegalSnippet) {
  snippetIsNew.value = !row
  editSnippet.value = row
    ? { ...row }
    : { snippet_id: '', keywords: [], text: '', enabled: true }
  snippetKeywordsText.value = (row?.keywords || []).join(',')
  showSnippetDialog.value = true
}

async function saveSnippetEdit() {
  if (!editSnippet.value) return
  const keywords = snippetKeywordsText.value
    .split(/[,，、]/)
    .map((s) => s.trim())
    .filter(Boolean)
  const body = { ...editSnippet.value, keywords }
  if (snippetIsNew.value) {
    await aiReviewConfigApi.createLegalSnippet(body)
  } else if (editSnippet.value.id) {
    await aiReviewConfigApi.updateLegalSnippet(editSnippet.value.id, body)
  }
  markDraftChanged()
  ElMessage.success('法条已保存（草稿）')
  showSnippetDialog.value = false
  await loadAll()
}

async function deleteSnippet(row: LegalSnippet) {
  if (!isAdmin.value) return
  if (!(await confirmOrCancel(`删除法条 ${row.snippet_id}？`, '删除'))) return
  await aiReviewConfigApi.deleteLegalSnippet(row.id)
  markDraftChanged()
  await loadAll()
}

function downloadLegalTemplate() {
  const csv =
    'snippet_id,keywords,text,enabled\n' +
    'LB-NEW,"违约,赔偿","《民法典》第584条：示例条文",true\n'
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'legal_snippets_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function onLegalCsvImport(file: File) {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可导入法条 CSV')
    return false
  }
  loading.value = true
  try {
    const res = await aiReviewConfigApi.importLegalCsv(file)
    markDraftChanged()
    const errHint = res.errors?.length ? `，${res.errors.length} 条错误` : ''
    ElMessage.success(
      `导入完成：新增 ${res.created ?? 0}，更新 ${res.updated ?? 0}，跳过 ${res.skipped ?? 0}${errHint}。需发布配置后审查任务才使用新法条`,
    )
    await loadAll()
  } catch (e) {
    ElMessage.error((e as Error).message || '导入失败')
  } finally {
    loading.value = false
  }
  return false
}

async function runSandbox() {
  const hard = hardRules.value.find((r) => r.rule_id === sandboxRuleId.value)
  const res = await aiReviewConfigApi.testRule({
    text: testText.value,
    hard_rule: hard
      ? {
          rule_id: hard.rule_id,
          name: hard.name,
          rule_type: hard.rule_type,
          config: hard.config,
          risk_level: hard.risk_level,
          label_id: hard.label_id,
          gate_id: hard.gate_id,
          dimension: hard.dimension,
          title: hard.title,
          suggestion: hard.suggestion,
        }
      : undefined,
  })
  testResult.value = JSON.stringify(res, null, 2)
}

async function disableRule(ruleKey: string) {
  if (!isAdmin.value) return
  if (!(await confirmOrCancel(`停用规则 ${ruleKey}？`, '停用'))) return
  const res = (await aiReviewConfigApi.disableRule(ruleKey)) as {
    cache_refreshed?: boolean
    hint?: string
  }
  if (res?.cache_refreshed) {
    ElMessage.success('规则已停用，运行时缓存已即时刷新')
  } else {
    ElMessage.success(res?.hint || '规则已停用')
  }
  await loadAll()
}

const fpMap = computed(() => {
  const m = new Map<string, FeedbackStat>()
  for (const s of feedback.value) m.set(s.rule_key, s)
  return m
})

function fpBadge(ruleKey: string) {
  const s = fpMap.value.get(ruleKey)
  if (!s || s.fp_count + s.confirm_count < 3) return null
  return `${Math.round(s.fp_rate * 100)}% 误报`
}
</script>

<template>
  <div class="ai-rules-hub" v-loading="loading">
    <el-empty
      v-if="accessDenied"
      description="仅法务专员与系统管理员可访问。演示环境请在右上角切换角色后刷新本页。"
    />
    <template v-else>
    <div class="hub-header">
      <div>
        <h2>AI 规则中心</h2>
        <p class="muted">
          当前版本：{{ configVersion || 'JSON 回退' }} · 法务可编辑草稿，管理员发布 · 停用规则将即时刷新缓存
        </p>
      </div>
      <div class="hub-actions">
        <el-button v-if="isAdmin" @click="handleImportSeeds">导入种子</el-button>
        <el-button
          v-if="isAdmin"
          :type="hasUnpublishedEdits ? 'warning' : 'primary'"
          @click="handlePublish"
        >
          发布配置{{ hasUnpublishedEdits ? '（有待发布草稿）' : '' }}
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="configVersion == null"
      type="warning"
      :closable="false"
      show-icon
      title="未发布配置"
      description="审查任务可能走 JSON 种子回退。建议管理员执行「导入种子」并「发布配置」后，规则中心编辑才会在审查中生效。"
      class="hub-alert"
    />
    <el-alert
      v-else-if="hasUnpublishedEdits && isAdmin"
      type="warning"
      :closable="false"
      show-icon
      title="存在未发布草稿"
      description="清单/法条等已写入数据库，但新审查任务仍使用上一版已发布缓存，请点击「发布配置」。"
      class="hub-alert"
    />
    <el-alert
      v-else-if="hasUnpublishedEdits && !isAdmin"
      type="info"
      :closable="false"
      show-icon
      title="草稿已保存"
      description="您的修改已保存为草稿，请联系管理员发布配置后，新审查任务才会使用最新规则。"
      class="hub-alert"
    />

    <el-tabs v-model="activeTab" @tab-change="loadTab">
      <el-tab-pane label="审查清单" name="checklist">
        <div class="toolbar">
          <el-input v-model="checklistFilter.gate_id" placeholder="门禁筛选" clearable style="width: 180px" />
          <el-checkbox v-model="checklistFilter.auto_only">仅自动检测项</el-checkbox>
          <el-button @click="loadTab('checklist')">刷新</el-button>
        </div>
        <el-table :data="checklist" stripe max-height="520">
          <el-table-column prop="legacy_id" label="ID" width="60" />
          <el-table-column prop="item" label="审查项" min-width="160" show-overflow-tooltip />
          <el-table-column prop="gate_id" label="门禁" width="120" />
          <el-table-column label="自动检测" width="90">
            <template #default="{ row }">
              <el-tag :type="row.auto_detectable ? 'success' : 'info'" size="small">
                {{ row.auto_detectable ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.enabled" @change="toggleChecklistEnabled(row)" />
            </template>
          </el-table-column>
          <el-table-column label="误报" width="100">
            <template #default="{ row }">
              <el-tag v-if="fpBadge(`CK-${row.legacy_id}`)" type="warning" size="small">
                {{ fpBadge(`CK-${row.legacy_id}`) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openChecklistEdit(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="风险标签" name="labels">
        <el-table :data="labels" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="gate_id" label="门禁" width="140" />
          <el-table-column prop="color" label="颜色" width="100" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="openLabelEdit(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="修订路由" name="routing">
        <div class="toolbar">
          <el-button type="primary" @click="openRouteEdit()">新增路由</el-button>
        </div>
        <el-table :data="routing" stripe max-height="480">
          <el-table-column prop="issue_type" label="问题类型" min-width="180" />
          <el-table-column prop="default_method" label="默认方式" width="120" />
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRouteEdit(row)">编辑</el-button>
              <el-button v-if="isAdmin" link type="danger" @click="deleteRoute(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="硬规则" name="hard">
        <div class="toolbar">
          <el-button v-if="isAdmin" type="primary" @click="openHardEdit()">新增硬规则</el-button>
        </div>
        <el-table :data="hardRules" stripe max-height="360">
          <el-table-column prop="rule_id" label="规则ID" width="110" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="rule_type" label="类型" width="120" />
          <el-table-column label="启用" width="90">
            <template #default="{ row }">
              <el-switch
                v-if="isAdmin"
                :model-value="row.enabled"
                @change="toggleHardEnabled(row)"
              />
              <el-tag v-else :type="row.enabled ? 'success' : 'info'" size="small">
                {{ row.enabled ? '开' : '关' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="误报" width="100">
            <template #default="{ row }">
              <el-tag v-if="fpBadge(row.rule_id)" type="warning" size="small">{{ fpBadge(row.rule_id) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button v-if="isAdmin" link type="primary" @click="openHardEdit(row)">编辑</el-button>
              <el-button
                v-if="isAdmin && fpMap.get(row.rule_id)?.suggest_disable"
                link
                type="danger"
                @click="disableRule(row.rule_id)"
              >
                停用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="sandbox">
          <h4>规则沙箱</h4>
          <el-select v-model="sandboxRuleId" placeholder="选择硬规则" style="width: 240px; margin-bottom: 8px">
            <el-option
              v-for="r in hardRules"
              :key="r.rule_id"
              :label="`${r.rule_id} - ${r.name}`"
              :value="r.rule_id"
            />
          </el-select>
          <el-input v-model="testText" type="textarea" :rows="3" placeholder="粘贴合同片段" />
          <el-button style="margin-top: 8px" @click="runSandbox">测试所选硬规则</el-button>
          <pre v-if="testResult" class="sandbox-result">{{ testResult }}</pre>
        </div>
      </el-tab-pane>

      <el-tab-pane label="法条库" name="legal">
        <div class="toolbar">
          <el-button type="primary" @click="openSnippetEdit()">新增法条</el-button>
          <el-button @click="downloadLegalTemplate">下载模板</el-button>
          <el-upload
            v-if="isAdmin"
            :auto-upload="true"
            :show-file-list="false"
            accept=".csv"
            :before-upload="onLegalCsvImport"
          >
            <el-button>CSV 导入</el-button>
          </el-upload>
        </div>
        <el-table :data="snippets" stripe max-height="480">
          <el-table-column prop="snippet_id" label="ID" width="100" />
          <el-table-column label="关键词" min-width="160">
            <template #default="{ row }">{{ (row.keywords || []).join('、') }}</template>
          </el-table-column>
          <el-table-column prop="text" label="条文" min-width="240" show-overflow-tooltip />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openSnippetEdit(row)">编辑</el-button>
              <el-button v-if="isAdmin" link type="danger" @click="deleteSnippet(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="反馈统计" name="feedback">
        <p class="muted" style="margin-bottom: 8px">近 30 天内有反馈记录的规则</p>
        <el-table :data="feedback" stripe>
          <el-table-column prop="rule_key" label="规则键" width="120" />
          <el-table-column prop="fp_count" label="误报" width="80" />
          <el-table-column prop="confirm_count" label="确认" width="80" />
          <el-table-column label="误报率" width="100">
            <template #default="{ row }">{{ Math.round(row.fp_rate * 100) }}%</template>
          </el-table-column>
          <el-table-column label="建议" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.suggest_disable" type="danger" size="small">建议停用</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="操作" width="90">
            <template #default="{ row }">
              <el-button v-if="row.suggest_disable" link type="danger" @click="disableRule(row.rule_key)">
                停用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showChecklistDialog" title="编辑清单项" width="640px" destroy-on-close>
      <el-form v-if="editChecklist" label-width="100px">
        <el-form-item label="审查项">
          <el-input v-model="editChecklist.item" />
        </el-form-item>
        <el-form-item label="自动检测">
          <el-switch v-model="editChecklist.auto_detectable" />
        </el-form-item>
        <el-form-item label="detect_config">
          <el-input v-model="detectJson" type="textarea" :rows="8" placeholder='{"type":"regex","pattern":"..."}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChecklistDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!editChecklist" @click="saveChecklistEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showLabelDialog" title="编辑风险标签" width="480px" destroy-on-close>
      <el-form v-if="editLabel" label-width="80px">
        <el-form-item label="ID">
          <el-input v-model="editLabel.id" disabled />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="editLabel.name" />
        </el-form-item>
        <el-form-item label="门禁">
          <el-input v-model="editLabel.gate_id" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="editLabel.color" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLabelDialog = false">取消</el-button>
        <el-button type="primary" @click="saveLabelEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRouteDialog" :title="routeIsNew ? '新增修订路由' : '编辑修订路由'" width="560px" destroy-on-close>
      <el-form v-if="editRoute" label-width="100px">
        <el-form-item label="问题类型">
          <el-input v-model="editRoute.issue_type" />
        </el-form-item>
        <el-form-item label="默认方式">
          <el-input v-model="editRoute.default_method" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="editRoute.priority" :min="0" />
        </el-form-item>
        <el-form-item label="自动适用">
          <el-switch v-model="editRoute.auto_applicable" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRouteDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRouteEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showHardDialog" :title="hardIsNew ? '新增硬规则' : '编辑硬规则'" width="640px" destroy-on-close>
      <el-form v-if="editHard" label-width="100px">
        <el-form-item label="rule_id">
          <el-input v-model="editHard.rule_id" :disabled="!hardIsNew" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="editHard.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-input v-model="editHard.rule_type" placeholder="regex / missing_keywords / sign_area_unclear" />
        </el-form-item>
        <el-form-item label="config">
          <el-input v-model="hardConfigJson" type="textarea" :rows="8" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showHardDialog = false">取消</el-button>
        <el-button type="primary" @click="saveHardEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showSnippetDialog" :title="snippetIsNew ? '新增法条' : '编辑法条'" width="640px" destroy-on-close>
      <el-form v-if="editSnippet" label-width="100px">
        <el-form-item label="snippet_id">
          <el-input v-model="editSnippet.snippet_id" :disabled="!snippetIsNew" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="snippetKeywordsText" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="条文">
          <el-input v-model="editSnippet.text" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSnippetDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSnippetEdit">保存</el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.ai-rules-hub {
  padding: 16px 20px;
}
.hub-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.hub-alert {
  margin-bottom: 12px;
}
.hub-header h2 {
  margin: 0 0 4px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin: 0;
}
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.sandbox {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.sandbox-result {
  margin-top: 8px;
  padding: 8px;
  background: var(--el-fill-color-light);
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
}
</style>
