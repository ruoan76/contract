<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { notificationsApi, type NotificationItem } from '@/api/notifications'
import { formatDateTime } from '@/utils/formatDate'

const router = useRouter()
const loading = ref(true)
const items = ref<NotificationItem[]>([])
const unreadOnly = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await notificationsApi.list({ page: 1, page_size: 50, unread_only: unreadOnly.value })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function markRead(row: NotificationItem) {
  if (row.is_read) return
  try {
    await notificationsApi.markRead(row.id)
    row.is_read = 1
    ElMessage.success('已标记已读')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

function openResource(row: NotificationItem) {
  if (row.resource_type === 'contract' && row.resource_id) {
    router.push({ name: 'contract-detail', params: { id: row.resource_id } })
  }
}

function channelLabel(row: NotificationItem) {
  if (!row.channel) return '站内'
  if (row.channel === 'feishu') return '飞书'
  return row.channel
}

function isSlaOverdue(row: NotificationItem) {
  if (row.is_read || !row.created_at) return false
  const created = new Date(row.created_at).getTime()
  return Date.now() - created > 24 * 60 * 60 * 1000
}

function rowClassName({ row }: { row: NotificationItem }) {
  return isSlaOverdue(row) ? 'sla-overdue' : ''
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>消息中心</h2>
      <div>
        <el-checkbox v-model="unreadOnly" @change="load">仅未读</el-checkbox>
        <el-button style="margin-left: 8px" @click="load">刷新</el-button>
      </div>
    </div>
    <el-table
      v-loading="loading"
      :data="items"
      stripe
      :row-class-name="rowClassName"
      @row-click="openResource"
    >
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column prop="message" label="内容" min-width="200" show-overflow-tooltip />
      <el-table-column label="渠道" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.channel === 'feishu'" type="primary" size="small">飞书</el-tag>
          <el-tag v-else-if="row.channel" size="small">{{ channelLabel(row) }}</el-tag>
          <span v-else class="muted">站内</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_read ? 'info' : 'warning'" size="small">
            {{ row.is_read ? '已读' : '未读' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="markRead(row)">标记已读</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无消息" />
  </div>
</template>

<style scoped>
.muted {
  color: #9ca3af;
  font-size: 13px;
}
:deep(.sla-overdue) {
  background-color: #fef2f2 !important;
}
</style>
