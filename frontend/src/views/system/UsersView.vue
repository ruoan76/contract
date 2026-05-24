<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usersApi, type SystemUser } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<SystemUser[]>([])
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    await auth.switchRole('admin')
    const res = await usersApi.list({ page: 1, page_size: 50, keyword: keyword.value || undefined })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>用户管理</h2>
      <el-input
        v-model="keyword"
        placeholder="搜索用户名/姓名"
        style="width: 200px"
        clearable
        @keyup.enter="load"
      />
      <el-button @click="load">搜索</el-button>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="role_name" label="角色" width="120" />
      <el-table-column prop="department_name" label="部门" width="140" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="phone" label="电话" width="140" />
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无用户" />
  </div>
</template>
