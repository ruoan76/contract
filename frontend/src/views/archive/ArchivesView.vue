<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { archivesApi } from '@/api/archives'
import { downloadCsv } from '@/utils/exportCsv'

const router = useRouter()
const items = ref<Array<{ contract_id?: number; archive_location?: string; archived_at?: string }>>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await archivesApi.ledger()
    items.value = (res.items || []) as typeof items.value
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function openContract(row: { contract_id?: number }) {
  if (row.contract_id) {
    router.push({ name: 'contract-detail', params: { id: row.contract_id } })
  }
}

function exportCsv() {
  downloadCsv(
    'archives.csv',
    ['合同 ID', '归档位置', '归档时间'],
    items.value.map((r) => [
      String(r.contract_id ?? ''),
      r.archive_location ?? '',
      r.archived_at ?? '',
    ]),
  )
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <el-button @click="exportCsv">导出 CSV</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe @row-click="openContract">
      <el-table-column prop="contract_id" label="合同 ID" width="100" />
      <el-table-column prop="archive_location" label="归档位置" min-width="200" />
      <el-table-column prop="archived_at" label="归档时间" width="180" />
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无归档记录">
      <el-button type="primary" @click="router.push({ name: 'contracts' })">查看合同列表</el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 16px;
}
</style>
