<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usersApi, type SystemUser } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<SystemUser[]>([])
const keyword = ref('')
const roleFilter = ref('')
const editVisible = ref(false)
const editForm = ref({ id: 0, role_id: 0, status: 1 })

async function load() {
  loading.value = true
  try {
    await auth.switchRole('admin')
    const res = await usersApi.list({
      page: 1,
      page_size: 50,
      keyword: keyword.value || undefined,
      role_id: roleFilter.value ? Number(roleFilter.value) : undefined,
    })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openEdit(row: SystemUser) {
  editForm.value = { id: row.id, role_id: row.role_id || 0, status: row.status ?? 1 }
  editVisible.value = true
}

async function saveEdit() {
  try {
    await usersApi.update(editForm.value.id, {
      role_id: editForm.value.role_id || undefined,
      status: editForm.value.status,
    })
    ElMessage.success('用户已更新')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>用户管理</h2>
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索用户名/姓名"
          style="width: 200px"
          clearable
          @keyup.enter="load"
        />
        <el-input
          v-model="roleFilter"
          placeholder="角色 ID"
          style="width: 100px"
          clearable
          @keyup.enter="load"
        />
        <el-button @click="load">搜索</el-button>
      </div>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="role_name" label="角色" width="120" />
      <el-table-column prop="department_name" label="部门" width="140" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无用户" />

    <el-dialog v-model="editVisible" title="编辑用户" width="400px">
      <el-form label-width="80px">
        <el-form-item label="角色 ID">
          <el-input-number v-model="editForm.role_id" :min="1" />
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
}
</style>
