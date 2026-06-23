<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { templatesApi, type ContractTemplate } from '@/api/templates'
import { useAuthStore } from '@/stores/auth'
import { templateCategoryLabel, templateStatusLabel } from '@/utils/enumLabels'
import { formatDateTime } from '@/utils/formatDate'
import { extractTemplateVariables } from '@/utils/templateFill'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<ContractTemplate[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')

const dialogVisible = ref(false)
const editVisible = ref(false)
const previewVisible = ref(false)
const previewRow = ref<ContractTemplate | null>(null)
const editId = ref(0)

const form = reactive({ name: '', category: 'purchase', content: '' })
const editForm = reactive({ name: '', category: 'purchase', content: '' })

const isAdmin = computed(() => auth.role === 'admin')
const isApprover = computed(() => auth.role === 'approver' || auth.role === 'admin')

const categoryOptions = [
  { value: 'purchase', label: '采购' },
  { value: 'sales', label: '销售' },
  { value: 'service', label: '服务' },
  { value: 'labor', label: '劳务' },
  { value: 'nda', label: '保密' },
]

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'pending_publish', label: '待发布' },
  { value: 'published', label: '已发布' },
  { value: 'deprecated', label: '已废止' },
]

const formVariablePreview = computed(() => extractTemplateVariables(form.content))
const editVariablePreview = computed(() => extractTemplateVariables(editForm.content))

async function load() {
  loading.value = true
  try {
    const res = await templatesApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
      category: categoryFilter.value || undefined,
    })
    items.value = res.items || []
    total.value = res.total ?? items.value.length
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  form.name = ''
  form.category = 'purchase'
  form.content = '甲方：{采购方名称}\n乙方：{相对方}\n合同金额：{金额} 元。'
  dialogVisible.value = true
}

function openEdit(row: ContractTemplate) {
  editId.value = row.id
  editForm.name = row.name
  editForm.category = row.category
  editForm.content = row.content || ''
  editVisible.value = true
}

function openPreview(row: ContractTemplate) {
  previewRow.value = row
  previewVisible.value = true
}

async function createTemplate() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }
  try {
    await templatesApi.create({ ...form })
    ElMessage.success('模板已创建')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

async function saveEdit() {
  try {
    await templatesApi.update(editId.value, { ...editForm })
    ElMessage.success('模板已保存')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function submitPublish(row: ContractTemplate) {
  try {
    await templatesApi.submitPublish(row.id)
    ElMessage.success('已提交发布审批')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  }
}

async function approvePublish(row: ContractTemplate) {
  try {
    await templatesApi.approvePublish(row.id)
    ElMessage.success('已批准发布')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '批准失败')
  }
}

async function rejectPublish(row: ContractTemplate) {
  try {
    await templatesApi.rejectPublish(row.id)
    ElMessage.success('已驳回')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '驳回失败')
  }
}

async function deprecate(row: ContractTemplate) {
  try {
    const { value } = await ElMessageBox.prompt('请输入废止原因（可选）', '废止模板', {
      confirmButtonText: '废止',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：条款已过期，由新版本替代',
    })
    await templatesApi.deprecate(row.id, value || undefined)
    ElMessage.success('模板已废止')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '废止失败')
    }
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function variableCount(row: ContractTemplate): number {
  return row.variable_count ?? row.variables?.length ?? extractTemplateVariables(row.content).length
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>模板管理</h2>
      <div class="toolbar-right">
        <el-input
          v-model="keyword"
          placeholder="搜索编码/名称"
          clearable
          style="width: 160px"
          @keyup.enter="() => { page = 1; load() }"
        />
        <el-select v-model="categoryFilter" placeholder="全部分类" clearable style="width: 120px">
          <el-option v-for="o in categoryOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 120px">
          <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-button @click="() => { page = 1; load() }">搜索</el-button>
        <el-button v-if="isAdmin" type="primary" @click="openCreate">新建模板</el-button>
      </div>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="code" label="编码" width="110">
        <template #default="{ row }">{{ row.code || '—' }}</template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="分类" width="88">
        <template #default="{ row }">{{ templateCategoryLabel(row.category) }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="64" align="center" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ templateStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="变量数" width="72" align="center">
        <template #default="{ row }">{{ variableCount(row) }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="168">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openPreview(row)">预览</el-button>
          <el-button v-if="row.status === 'draft' && isAdmin" link type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button v-if="row.status === 'draft' && isAdmin" link type="primary" @click="submitPublish(row)">
            提交发布
          </el-button>
          <el-button v-if="row.status === 'pending_publish' && isApprover" link type="success" @click="approvePublish(row)">
            批准
          </el-button>
          <el-button v-if="row.status === 'pending_publish' && isApprover" link type="warning" @click="rejectPublish(row)">
            驳回
          </el-button>
          <el-button v-if="row.status === 'published' && isAdmin" link type="danger" @click="deprecate(row)">
            废止
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无模板，请新建" />
    <div v-if="total > pageSize" class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPageChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" title="新建模板" width="640px">
      <el-form label-width="88px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="o in categoryOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="使用 {变量名} 标记可变字段" />
        </el-form-item>
        <el-form-item v-if="formVariablePreview.length" label="识别变量">
          <span class="var-tags">
            <el-tag v-for="v in formVariablePreview" :key="v" size="small" style="margin: 2px">{{ v }}</el-tag>
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTemplate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑模板" width="640px">
      <el-form label-width="88px">
        <el-form-item label="名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category" style="width: 100%">
            <el-option v-for="o in categoryOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="editForm.content" type="textarea" :rows="8" />
        </el-form-item>
        <el-form-item v-if="editVariablePreview.length" label="识别变量">
          <span class="var-tags">
            <el-tag v-for="v in editVariablePreview" :key="v" size="small" style="margin: 2px">{{ v }}</el-tag>
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="previewRow ? `预览：${previewRow.name}` : '预览'" width="720px">
      <template v-if="previewRow">
        <p class="preview-meta">
          <span>{{ previewRow.code }}</span>
          <span>{{ templateCategoryLabel(previewRow.category) }}</span>
          <span>v{{ previewRow.version ?? 1 }}</span>
          <el-tag size="small">{{ templateStatusLabel(previewRow.status) }}</el-tag>
        </p>
        <pre class="preview-content">{{ previewRow.content || '（无正文）' }}</pre>
      </template>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.preview-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 12px;
}
.preview-content {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  max-height: 420px;
  overflow: auto;
  background: #f9fafb;
  padding: 12px;
  border-radius: 8px;
  margin: 0;
}
</style>
