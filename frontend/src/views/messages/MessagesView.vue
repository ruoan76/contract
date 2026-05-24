<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { notificationsApi, type NotificationItem } from '@/api/notifications'

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
    <el-table v-loading="loading" :data="items" stripe @row-click="openResource">
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="message" label="内容" min-width="240" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_read ? 'info' : 'warning'" size="small">
            {{ row.is_read ? '已读' : '未读' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="markRead(row)">标记已读</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无消息" />
  </div>
</template>
