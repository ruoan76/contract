<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { auditApi, type AuditLogItem } from '@/api/audit'
import { useAuthStore } from '@/stores/auth'
import { downloadCsv } from '@/utils/exportCsv'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<AuditLogItem[]>([])
const actionFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

async function load() {
  loading.value = true
  try {
    await auth.switchRole('admin')
    const res = await auditApi.list({
      page: 1,
      page_size: 100,
      action: actionFilter.value || undefined,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1],
    })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function exportCsv() {
  downloadCsv(
    'audit-logs.csv',
    ['用户', '动作', '资源类型', '资源', '状态', '时间'],
    items.value.map((r) => [
      r.username ?? '',
      r.action ?? '',
      r.resource_type ?? '',
      r.resource_name ?? String(r.resource_id ?? ''),
      r.status ?? '',
      String(r.created_at ?? ''),
    ]),
  )
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>审计日志</h2>
      <div class="filters">
        <el-input
          v-model="actionFilter"
          placeholder="动作筛选"
          clearable
          style="width: 160px"
          @keyup.enter="load"
        />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 260px"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
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
  flex-wrap: wrap;
  align-items: center;
}
</style>
