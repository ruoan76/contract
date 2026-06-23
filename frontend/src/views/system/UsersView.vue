<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usersApi, type SystemRole, type SystemUser } from '@/api/users'
import { formatDateTime } from '@/utils/formatDate'

const loading = ref(true)
const items = ref<SystemUser[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const roleFilterId = ref<number | undefined>()
const statusFilter = ref<number | undefined>()
const roles = ref<SystemRole[]>([])

const editVisible = ref(false)
const createVisible = ref(false)
const resetPwdVisible = ref(false)
const resetPwdUserId = ref(0)
const resetPwdValue = ref('')

const editForm = ref({ id: 0, role_id: undefined as number | undefined, status: 1 })
const createForm = ref({
  username: '',
  password: '',
  real_name: '',
  email: '',
  phone: '',
  role_id: undefined as number | undefined,
})

async function loadRoles() {
  try {
    roles.value = (await usersApi.listRoles()) || []
  } catch {
    roles.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const res = await usersApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      role_id: roleFilterId.value,
      status: statusFilter.value,
    })
    items.value = res.items || []
    total.value = res.total ?? items.value.length
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadRoles()
  await load()
})

function openEdit(row: SystemUser) {
  editForm.value = { id: row.id, role_id: row.role_id, status: row.status ?? 1 }
  editVisible.value = true
}

function openCreate() {
  createForm.value = {
    username: '',
    password: '',
    real_name: '',
    email: '',
    phone: '',
    role_id: roles.value[0]?.id,
  }
  createVisible.value = true
}

function openResetPassword(row: SystemUser) {
  resetPwdUserId.value = row.id
  resetPwdValue.value = ''
  resetPwdVisible.value = true
}

async function saveEdit() {
  try {
    await usersApi.update(editForm.value.id, {
      role_id: editForm.value.role_id,
      status: editForm.value.status,
    })
    ElMessage.success('用户已更新')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}

async function saveCreate() {
  if (!createForm.value.username.trim() || !createForm.value.real_name.trim()) {
    ElMessage.warning('请填写用户名与姓名')
    return
  }
  if ((createForm.value.password || '').length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  try {
    await usersApi.create({
      username: createForm.value.username.trim(),
      password: createForm.value.password,
      real_name: createForm.value.real_name.trim(),
      email: createForm.value.email || undefined,
      phone: createForm.value.phone || undefined,
      role_id: createForm.value.role_id,
    })
    ElMessage.success('用户已创建')
    createVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

async function confirmResetPassword() {
  if ((resetPwdValue.value || '').length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  try {
    await usersApi.resetPassword(resetPwdUserId.value, resetPwdValue.value)
    ElMessage.success('密码已重置')
    resetPwdVisible.value = false
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '重置失败')
  }
}

async function toggleStatus(row: SystemUser) {
  const next = row.status === 1 ? 0 : 1
  const action = next === 0 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}用户「${row.real_name || row.username}」？`, `${action}用户`, {
      type: 'warning',
    })
    await usersApi.update(row.id, { status: next })
    ElMessage.success(`已${action}`)
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '操作失败')
    }
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <el-button type="primary" @click="openCreate">新增用户</el-button>
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索用户名/姓名"
          style="width: 200px"
          clearable
          @keyup.enter="load"
        />
        <el-select v-model="roleFilterId" placeholder="全部角色" clearable style="width: 160px">
          <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 120px">
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-button @click="() => { page = 1; load() }">搜索</el-button>
      </div>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="role_name" label="角色" width="120" />
      <el-table-column prop="department_name" label="部门" width="140" />
      <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column label="状态" width="88">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="168">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openResetPassword(row)">重置密码</el-button>
          <el-button link :type="row.status === 1 ? 'danger' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 1 ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无用户" />
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

    <el-dialog v-model="editVisible" title="编辑用户" width="420px">
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-select v-model="editForm.role_id" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" title="新增用户" width="480px">
      <el-form label-width="88px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="createForm.real_name" />
        </el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role_id" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="createForm.phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetPwdVisible" title="重置密码" width="400px">
      <el-form label-width="88px">
        <el-form-item label="新密码" required>
          <el-input v-model="resetPwdValue" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmResetPassword">确认重置</el-button>
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
  gap: 8px;
}
.filters {
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
</style>
