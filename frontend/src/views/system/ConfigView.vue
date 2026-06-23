<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  configApi,
  type ApproverConfig,
  type FlowNodeConfig,
  type ThresholdsConfig,
} from '@/api/config'
import { usersApi, type SystemUser } from '@/api/users'
import { approverRoleLabel, APPROVER_ROLE_OPTIONS, flowTypeLabel } from '@/utils/enumLabels'

const form = reactive<ThresholdsConfig>({
  simple_max: 100000,
  standard_max: 1000000,
  board_threshold: 1000000,
})
const approvers = ref<ApproverConfig[]>([])
const flowNodesByType = ref<Record<string, FlowNodeConfig[]>>({})
const userOptions = ref<SystemUser[]>([])
const activeTab = ref('approvers')

const approverForm = reactive({
  flow_type: 'standard',
  step: 1,
  role: 'approver',
  user_id: undefined as number | undefined,
  user_name: '',
})

const editingId = ref<number | null>(null)
const editForm = reactive({
  flow_type: 'standard',
  step: 1,
  role: 'approver',
  user_id: undefined as number | undefined,
  user_name: '',
})

const loading = ref(false)
const saving = ref(false)

const sortedApprovers = computed(() =>
  [...approvers.value].sort((a, b) => {
    const order: Record<string, number> = { simple: 0, standard: 1, large_amount: 2 }
    const fa = order[a.flow_type] ?? 9
    const fb = order[b.flow_type] ?? 9
    if (fa !== fb) return fa - fb
    return a.step - b.step
  }),
)

async function loadApprovers() {
  approvers.value = (await configApi.getApprovers()) || []
}

async function loadFlowNodes() {
  const data = await configApi.getFlowNodes()
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    flowNodesByType.value = data as Record<string, FlowNodeConfig[]>
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [thresholds, users] = await Promise.all([
      configApi.getThresholds(),
      usersApi.listOptions({ page_size: 100 }),
      loadApprovers(),
      loadFlowNodes(),
    ])
    Object.assign(form, thresholds)
    userOptions.value = users?.items ?? []
    if (userOptions.value.length && !approverForm.user_id) {
      const first = userOptions.value[0]
      approverForm.user_id = first.id
      approverForm.user_name = first.real_name || first.username
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function onUserPick(userId: number | undefined, target: 'add' | 'edit') {
  const u = userOptions.value.find((x) => x.id === userId)
  const name = u ? u.real_name || u.username : ''
  if (target === 'add') {
    approverForm.user_id = userId
    approverForm.user_name = name
  } else {
    editForm.user_id = userId
    editForm.user_name = name
  }
}

async function save() {
  saving.value = true
  try {
    const data = await configApi.updateThresholds({ ...form })
    Object.assign(form, data)
    ElMessage.success('阈值已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function addApprover() {
  if (!approverForm.user_id) {
    ElMessage.warning('请选择审批人')
    return
  }
  try {
    await configApi.createApprover({ ...approverForm })
    await loadApprovers()
    await loadFlowNodes()
    ElMessage.success('审批人已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

function startEdit(row: ApproverConfig) {
  editingId.value = row.id
  editForm.flow_type = row.flow_type
  editForm.step = row.step
  editForm.role = row.role
  editForm.user_id = row.user_id
  editForm.user_name = row.user_name || ''
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit() {
  if (editingId.value == null) return
  try {
    await configApi.updateApprover(editingId.value, { ...editForm })
    await loadApprovers()
    await loadFlowNodes()
    editingId.value = null
    ElMessage.success('已更新')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}

async function removeApprover(row: ApproverConfig) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${flowTypeLabel(row.flow_type)} 第 ${row.step} 步配置？`,
      '删除确认',
    )
    await configApi.deleteApprover(row.id)
    await loadApprovers()
    await loadFlowNodes()
    ElMessage.success('已删除')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

const flowNodeRows = computed(() => {
  const rows: { flow_type: string; node_id: string; node_name: string; approver_role?: string; user_id?: number }[] = []
  for (const [ft, nodes] of Object.entries(flowNodesByType.value)) {
    for (const n of nodes) {
      rows.push({ flow_type: ft, ...n })
    }
  }
  return rows
})
</script>

<template>
  <div v-loading="loading" class="page-card">
    <div class="page-toolbar">
      <el-button type="primary" :loading="saving" @click="save">保存阈值</el-button>
    </div>
    <el-form label-width="160px" style="max-width: 520px">
      <el-form-item label="简易流程上限（元）">
        <el-input-number v-model="form.simple_max" :min="0" :step="10000" style="width: 100%" />
      </el-form-item>
      <el-form-item label="标准流程上限（元）">
        <el-input-number v-model="form.standard_max" :min="0" :step="100000" style="width: 100%" />
      </el-form-item>
      <el-form-item label="董事会阈值（元）">
        <el-input-number v-model="form.board_threshold" :min="0" :step="100000" style="width: 100%" />
      </el-form-item>
    </el-form>

    <el-tabs v-model="activeTab" style="margin-top: 24px; max-width: 960px">
      <el-tab-pane label="审批人配置" name="approvers">
        <el-table :data="sortedApprovers" stripe size="small">
          <el-table-column label="流程类型" width="120">
            <template #default="{ row }">{{ flowTypeLabel(row.flow_type) }}</template>
          </el-table-column>
          <el-table-column prop="step" label="步骤" width="70" />
          <el-table-column label="角色" width="110">
            <template #default="{ row }">{{ approverRoleLabel(row.role) }}</template>
          </el-table-column>
          <el-table-column prop="user_name" label="审批人" min-width="120" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="startEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="removeApprover(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog
          :model-value="editingId != null"
          title="编辑审批人"
          width="480px"
          @close="cancelEdit"
        >
          <el-form label-width="80px">
            <el-form-item label="流程">
              <el-select v-model="editForm.flow_type" style="width: 100%">
                <el-option label="简易" value="simple" />
                <el-option label="标准" value="standard" />
                <el-option label="大额" value="large_amount" />
              </el-select>
            </el-form-item>
            <el-form-item label="步骤">
              <el-input-number v-model="editForm.step" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="角色">
              <el-select v-model="editForm.role" style="width: 100%">
                <el-option
                  v-for="opt in APPROVER_ROLE_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="审批人">
              <el-select
                :model-value="editForm.user_id"
                filterable
                style="width: 100%"
                @update:model-value="(v: number) => onUserPick(v, 'edit')"
              >
                <el-option
                  v-for="u in userOptions"
                  :key="u.id"
                  :label="u.real_name || u.username"
                  :value="u.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="cancelEdit">取消</el-button>
            <el-button type="primary" @click="saveEdit">保存</el-button>
          </template>
        </el-dialog>

        <el-form inline style="margin-top: 12px">
          <el-form-item label="流程">
            <el-select v-model="approverForm.flow_type" style="width: 120px">
              <el-option label="简易" value="simple" />
              <el-option label="标准" value="standard" />
              <el-option label="大额" value="large_amount" />
            </el-select>
          </el-form-item>
          <el-form-item label="步骤">
            <el-input-number v-model="approverForm.step" :min="1" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="approverForm.role" style="width: 120px">
              <el-option
                v-for="opt in APPROVER_ROLE_OPTIONS"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="审批人">
            <el-select
              :model-value="approverForm.user_id"
              filterable
              style="width: 140px"
              @update:model-value="(v: number) => onUserPick(v, 'add')"
            >
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="u.real_name || u.username"
                :value="u.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" plain @click="addApprover">保存步骤</el-button>
          </el-form-item>
        </el-form>
        <p class="config-hint">
          同一流程类型与步骤序号重复保存将覆盖原配置；保存后会同步到下方「运行时节点」。
        </p>
      </el-tab-pane>

      <el-tab-pane label="运行时节点" name="runtime">
        <p class="config-hint">
          提交审批时实际使用的节点顺序（由审批人配置自动生成，存于 flow_config.json）。
        </p>
        <el-table :data="flowNodeRows" stripe size="small">
          <el-table-column label="流程类型" width="120">
            <template #default="{ row }">{{ flowTypeLabel(row.flow_type) }}</template>
          </el-table-column>
          <el-table-column prop="node_id" label="节点 ID" width="160" />
          <el-table-column prop="node_name" label="节点名称" min-width="120" />
          <el-table-column prop="approver_role" label="角色标签" width="120" />
          <el-table-column label="指定用户 ID" width="110">
            <template #default="{ row }">{{ row.user_id ?? '—' }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.config-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
