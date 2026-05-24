<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { auditApi, type AuditLogItem } from '@/api/audit'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<AuditLogItem[]>([])

onMounted(async () => {
  try {
    await auth.switchRole('admin')
    const res = await auditApi.list({ page: 1, page_size: 50 })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-card">
    <h2>审计日志</h2>
    <el-table v-loading="loading" :data="items" stripe style="margin-top: 16px">
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="action" label="动作" width="140" />
      <el-table-column prop="resource_type" label="资源类型" width="120" />
      <el-table-column prop="resource_name" label="资源" min-width="160" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无审计记录" />
  </div>
</template>
