<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'
import StatusTag from '@/components/StatusTag.vue'

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '待审批', value: 'pending' },
  { label: '评审中', value: 'in_review' },
  { label: '已用印', value: 'sealed' },
  { label: '已归档', value: 'archived' },
]

const TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: '采购', value: 'purchase' },
  { label: '销售', value: 'sales' },
  { label: '服务', value: 'service' },
  { label: '其他', value: 'other' },
]

const RISK_OPTIONS = [
  { label: '全部风险', value: '' },
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
]

const router = useRouter()
const loading = ref(true)
const items = ref<Contract[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const typeFilter = ref('')
const riskFilter = ref('')
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.type = typeFilter.value
    if (riskFilter.value) params.risk_level = riskFilter.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const res = await contractsApi.list(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
  } catch (e) {
    console.error(e)
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

function openDetail(row: Contract) {
  router.push({ name: 'contract-detail', params: { id: row.id } })
}

function openApprovalHistory(row: Contract, e: Event) {
  e.stopPropagation()
  router.push({ name: 'approval-history', params: { id: row.id } })
}

function openReviewHistory(row: Contract, e: Event) {
  e.stopPropagation()
  router.push({ name: 'review-history', query: { contractId: String(row.id) } })
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>合同列表</h2>
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索标题/相对方"
          clearable
          style="width: 220px"
          @keyup.enter="onSearch"
        />
        <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 120px">
          <el-option v-for="opt in TYPE_OPTIONS" :key="opt.value || 'all'" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-select v-model="riskFilter" placeholder="风险" clearable style="width: 120px">
          <el-option v-for="opt in RISK_OPTIONS" :key="opt.value || 'all'" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
          <el-option
            v-for="opt in STATUS_OPTIONS"
            :key="opt.value || 'all'"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-button type="primary" @click="onSearch">查询</el-button>
      </div>
    </div>
    <el-table v-loading="loading" :data="items" stripe @row-click="openDetail">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="counterparty_name" label="相对方" width="140" />
      <el-table-column prop="amount" label="金额" width="120">
        <template #default="{ row }">¥{{ row.amount?.toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><StatusTag :status="row.status" /></template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
          <el-button link @click="openApprovalHistory(row, $event)">审批历史</el-button>
          <el-button link @click="openReviewHistory(row, $event)">评审历史</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
