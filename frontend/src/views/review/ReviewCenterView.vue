<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { reviewsApi } from '@/api/reviews'

interface PendingItem {
  contract_id: number
  title?: string
  flow_type?: string
  pending_role?: string
}

const router = useRouter()
const loading = ref(true)
const items = ref<PendingItem[]>([])
const roleFilter = ref('')

async function load() {
  loading.value = true
  try {
    const res = await reviewsApi.pending(roleFilter.value || undefined)
    items.value = (res.items || []) as PendingItem[]
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(roleFilter, load)

function openWorkspace(row: PendingItem) {
  router.push({ name: 'review-workspace', params: { id: row.contract_id } })
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>评审中心</h2>
      <el-select v-model="roleFilter" placeholder="全部角色" clearable style="width: 140px" @change="load">
        <el-option label="法务" value="legal" />
        <el-option label="财务" value="finance" />
        <el-option label="高管" value="executive" />
      </el-select>
    </div>
    <el-table v-loading="loading" :data="items" stripe @row-click="openWorkspace">
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="flow_type" label="流程" width="120" />
      <el-table-column prop="pending_role" label="待办角色" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openWorkspace(row)">进入工作台</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无待评审合同" />
  </div>
</template>
