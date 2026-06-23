<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  counterpartiesApi,
  type CounterpartyItem,
  type CounterpartyPayload,
} from '@/api/counterparties'
import { useAuthStore } from '@/stores/auth'
import { downloadCsv } from '@/utils/exportCsv'

const auth = useAuthStore()
const isAdmin = computed(() => auth.role === 'admin')

const items = ref<CounterpartyItem[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const blacklistFilter = ref<string>('')
const statusFilter = ref<string>('1')

const createVisible = ref(false)
const editVisible = ref(false)
const detailVisible = ref(false)
const detail = ref<CounterpartyItem | null>(null)

const emptyForm = (): CounterpartyPayload => ({
  name: '',
  credit_code: '',
  legal_person: '',
  contact_name: '',
  contact_phone: '',
  address: '',
  industry: '',
  credit_rating: '',
})

const createForm = reactive(emptyForm())
const editForm = reactive({ id: 0, ...emptyForm() })

const CREDIT_RATINGS = ['A', 'B', 'C', 'D']

async function load() {
  loading.value = true
  try {
    const params: {
      page: number
      page_size: number
      keyword?: string
      is_blacklist?: number
      status?: number
    } = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (blacklistFilter.value !== '') params.is_blacklist = Number(blacklistFilter.value)
    if (statusFilter.value === '-1') params.status = -1
    else if (statusFilter.value !== '') params.status = Number(statusFilter.value)

    const res = await counterpartiesApi.list(params)
    items.value = res.items || []
    total.value = res.total ?? 0
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function onSearch() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function onSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  load()
}

function openCreate() {
  Object.assign(createForm, emptyForm())
  createVisible.value = true
}

function openEdit(row: CounterpartyItem) {
  editForm.id = row.id
  editForm.name = row.name
  editForm.credit_code = row.credit_code ?? ''
  editForm.legal_person = row.legal_person ?? ''
  editForm.contact_name = row.contact_name ?? ''
  editForm.contact_phone = row.contact_phone ?? ''
  editForm.address = row.address ?? ''
  editForm.industry = row.industry ?? ''
  editForm.credit_rating = row.credit_rating ?? ''
  editVisible.value = true
}

async function openDetail(row: CounterpartyItem) {
  loading.value = true
  try {
    detail.value = await counterpartiesApi.get(row.id)
    detailVisible.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载详情失败')
  } finally {
    loading.value = false
  }
}

function validateForm(form: CounterpartyPayload): boolean {
  if (!form.name.trim()) {
    ElMessage.warning('请填写相对方名称')
    return false
  }
  return true
}

function payloadFromForm(form: CounterpartyPayload): CounterpartyPayload {
  const body: CounterpartyPayload = { name: form.name.trim() }
  const opt = (v?: string) => (v?.trim() ? v.trim() : undefined)
  body.credit_code = opt(form.credit_code)
  body.legal_person = opt(form.legal_person)
  body.contact_name = opt(form.contact_name)
  body.contact_phone = opt(form.contact_phone)
  body.address = opt(form.address)
  body.industry = opt(form.industry)
  body.credit_rating = opt(form.credit_rating)
  return body
}

async function submitCreate() {
  if (!validateForm(createForm)) return
  loading.value = true
  try {
    await counterpartiesApi.create(payloadFromForm(createForm))
    ElMessage.success('相对方已创建')
    createVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    loading.value = false
  }
}

async function submitEdit() {
  if (!validateForm(editForm)) return
  loading.value = true
  try {
    await counterpartiesApi.update(editForm.id, payloadFromForm(editForm))
    ElMessage.success('已保存')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    loading.value = false
  }
}

async function confirmBlacklist(row: CounterpartyItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入列入黑名单的原因', '确认拉黑', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: '违规合作',
      inputPattern: /\S+/,
      inputErrorMessage: '原因不能为空',
    })
    loading.value = true
    await counterpartiesApi.blacklist(row.id, value.trim())
    ElMessage.success('已加入黑名单')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '操作失败')
    }
  } finally {
    loading.value = false
  }
}

async function confirmUnblacklist(row: CounterpartyItem) {
  try {
    await ElMessageBox.confirm(`确定将「${row.name}」移出黑名单？`, '解除黑名单', {
      type: 'warning',
    })
    loading.value = true
    await counterpartiesApi.unblacklist(row.id)
    ElMessage.success('已移出黑名单')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '操作失败')
    }
  } finally {
    loading.value = false
  }
}

async function confirmDisable(row: CounterpartyItem) {
  try {
    await ElMessageBox.confirm(
      `确定禁用「${row.name}」？禁用后默认列表不再展示，已关联合同不受影响。`,
      '禁用相对方',
      { type: 'warning' },
    )
    loading.value = true
    await counterpartiesApi.disable(row.id)
    ElMessage.success('已禁用')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '操作失败')
    }
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  downloadCsv(
    'counterparties.csv',
    ['ID', '名称', '信用代码', '联系人', '电话', '信用评级', '黑名单', '状态'],
    items.value.map((r) => [
      String(r.id),
      r.name,
      r.credit_code ?? '',
      r.contact_name ?? '',
      r.contact_phone ?? '',
      r.credit_rating ?? '',
      r.is_blacklist ? '是' : '否',
      r.status === 0 ? '禁用' : '启用',
    ]),
  )
}

async function onImport(file: File) {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可导入')
    return false
  }
  loading.value = true
  try {
    const res = await counterpartiesApi.importCsv(file)
    const errHint = res.errors?.length ? `，${res.errors.length} 条错误` : ''
    ElMessage.success(`导入完成：新增 ${res.created ?? 0}，跳过 ${res.skipped ?? 0}${errHint}`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    loading.value = false
  }
  return false
}

function downloadTemplate() {
  const csv =
    'name,credit_code,contact_name,contact_phone,legal_person,address,industry,credit_rating\n' +
    '示例公司,91110000MA00000000,张三,13800000000,李四,北京市朝阳区,信息技术,B\n'
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'counterparties_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function isBlacklisted(row: CounterpartyItem) {
  return !!row.is_blacklist
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索名称/信用代码"
          style="width: 220px"
          clearable
          @keyup.enter="onSearch"
        />
        <el-select v-model="blacklistFilter" placeholder="黑名单" clearable style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="是" value="1" />
          <el-option label="否" value="0" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态" style="width: 120px">
          <el-option label="仅启用" value="1" />
          <el-option label="仅禁用" value="0" />
          <el-option label="全部状态" value="-1" />
        </el-select>
        <el-button type="primary" @click="onSearch">搜索</el-button>
        <el-button type="primary" plain @click="openCreate">新增相对方</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button @click="downloadTemplate">下载模板</el-button>
        <el-upload
          v-if="isAdmin"
          :auto-upload="true"
          :show-file-list="false"
          :before-upload="onImport"
        >
          <el-button>CSV 导入</el-button>
        </el-upload>
        <el-button @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="ID" width="72" />
      <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
      <el-table-column prop="credit_code" label="信用代码" min-width="160" show-overflow-tooltip />
      <el-table-column prop="contact_name" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="电话" width="120" />
      <el-table-column prop="credit_rating" label="评级" width="72" />
      <el-table-column label="黑名单" width="88">
        <template #default="{ row }">
          <el-tag :type="isBlacklisted(row) ? 'danger' : 'success'" size="small">
            {{ isBlacklisted(row) ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="72">
        <template #default="{ row }">
          <el-tag :type="row.status === 0 ? 'info' : 'success'" size="small">
            {{ row.status === 0 ? '禁用' : '启用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="isAdmin && !isBlacklisted(row) && row.status !== 0"
            link
            type="danger"
            @click="confirmBlacklist(row)"
          >
            拉黑
          </el-button>
          <el-button
            v-if="isAdmin && isBlacklisted(row)"
            link
            type="warning"
            @click="confirmUnblacklist(row)"
          >
            解除拉黑
          </el-button>
          <el-button
            v-if="isAdmin && row.status !== 0"
            link
            type="danger"
            @click="confirmDisable(row)"
          >
            禁用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !items.length" description="暂无相对方" />

    <div v-if="total > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>

    <el-dialog v-model="createVisible" title="新增相对方" width="560px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="单位全称" />
        </el-form-item>
        <el-form-item label="信用代码">
          <el-input v-model="createForm.credit_code" placeholder="统一社会信用代码（可选）" />
        </el-form-item>
        <el-form-item label="法定代表人">
          <el-input v-model="createForm.legal_person" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="createForm.contact_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="createForm.contact_phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="createForm.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="createForm.industry" />
        </el-form-item>
        <el-form-item label="信用评级">
          <el-select v-model="createForm.credit_rating" clearable placeholder="请选择" style="width: 100%">
            <el-option v-for="r in CREDIT_RATINGS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑相对方" width="560px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="信用代码">
          <el-input v-model="editForm.credit_code" />
        </el-form-item>
        <el-form-item label="法定代表人">
          <el-input v-model="editForm.legal_person" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="editForm.contact_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="editForm.contact_phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="editForm.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="editForm.industry" />
        </el-form-item>
        <el-form-item label="信用评级">
          <el-select v-model="editForm.credit_rating" clearable style="width: 100%">
            <el-option v-for="r in CREDIT_RATINGS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="相对方详情" size="420px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="信用代码">{{ detail.credit_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="法定代表人">{{ detail.legal_person || '—' }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ detail.contact_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ detail.contact_phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ detail.address || '—' }}</el-descriptions-item>
          <el-descriptions-item label="行业">{{ detail.industry || '—' }}</el-descriptions-item>
          <el-descriptions-item label="信用评级">{{ detail.credit_rating || '—' }}</el-descriptions-item>
          <el-descriptions-item label="黑名单">
            <el-tag :type="isBlacklisted(detail) ? 'danger' : 'success'" size="small">
              {{ isBlacklisted(detail) ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.blacklist_reason" label="拉黑原因">
            {{ detail.blacklist_reason }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ detail.status === 0 ? '禁用' : '启用' }}
          </el-descriptions-item>
          <el-descriptions-item label="关联合同数">
            {{ detail.contract_count ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.created_at" label="创建时间">
            {{ detail.created_at }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
