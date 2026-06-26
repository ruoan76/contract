<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'
import type { Contract } from '@/types/models'
import StatusTag from '@/components/StatusTag.vue'
import {
  canDeleteContract,
  DELETE_DRAFT_CONFIRM_MESSAGE,
  DELETE_DRAFT_CONFIRM_TITLE,
} from '@/utils/contractDelete'
import { formatDate } from '@/utils/formatDate'

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
const route = useRoute()
const auth = useAuthStore()
const loading = ref(true)
const items = ref<Contract[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const typeFilter = ref('')
const riskFilter = ref('')
const keyword = ref('')
const scope = ref('mine')
const bucketFilter = ref('')

const BUCKET_LABELS: Record<string, string> = {
  executing: '执行中',
  expiring_soon: '即将到期（30 天内）',
  expired: '已到期',
}

const activeBucketLabel = computed(() =>
  bucketFilter.value ? BUCKET_LABELS[bucketFilter.value] || bucketFilter.value : '',
)

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
      scope: scope.value,
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (bucketFilter.value) params.bucket = bucketFilter.value
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

function applyRouteQuery() {
  const q = route.query
  if (typeof q.status === 'string') statusFilter.value = q.status
  if (typeof q.scope === 'string') scope.value = q.scope
  bucketFilter.value = typeof q.bucket === 'string' ? q.bucket : ''
}

function clearBucketFilter() {
  bucketFilter.value = ''
  router.replace({ name: 'contracts', query: { ...route.query, bucket: undefined } })
}

onMounted(() => {
  applyRouteQuery()
  load()
})

watch(
  () => route.query,
  () => {
    applyRouteQuery()
    page.value = 1
    load()
  },
)

watch([typeFilter, riskFilter, statusFilter], () => {
  page.value = 1
  load()
})

function goCreate() {
  router.push({ name: 'create' })
}

function onSearch() {
  page.value = 1
  load()
}

function onKeywordEnter() {
  onSearch()
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
  router.push({
    name: 'review-center',
    query: { tab: 'history', contractId: String(row.id) },
  })
}

function rowCanDelete(row: Contract) {
  return canDeleteContract(row, auth.user?.id, auth.role)
}

function endDateCellClass(): string {
  if (bucketFilter.value === 'expiring_soon') return 'date-warning'
  if (bucketFilter.value === 'expired') return 'date-danger'
  return ''
}

async function deleteDraft(row: Contract, e: Event) {
  e.stopPropagation()
  if (!rowCanDelete(row)) return
  try {
    await ElMessageBox.confirm(DELETE_DRAFT_CONFIRM_MESSAGE, DELETE_DRAFT_CONFIRM_TITLE, {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }
  try {
    await contractsApi.delete(row.id)
    ElMessage.success('草稿已删除')
    await load()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '删除失败')
  }
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>合同列表</h2>
      <div class="filters">
        <el-radio-group v-model="scope" size="small" @change="onSearch">
          <el-radio-button value="mine">我的</el-radio-button>
          <el-radio-button value="department">本部门</el-radio-button>
          <el-radio-button value="all">全公司</el-radio-button>
        </el-radio-group>
        <el-input
          v-model="keyword"
          placeholder="搜索标题/相对方"
          clearable
          style="width: 220px"
          @keyup.enter="onKeywordEnter"
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
        <el-button type="primary" plain @click="goCreate">新建合同</el-button>
      </div>
    </div>
    <el-alert
      v-if="activeBucketLabel"
      :title="`当前筛选：${activeBucketLabel}`"
      type="info"
      show-icon
      closable
      class="bucket-alert"
      @close="clearBucketFilter"
    />
    <el-table v-loading="loading" :data="items" stripe @row-click="openDetail">
      <el-table-column label="合同编号" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <el-link type="primary" underline="never" @click.stop="openDetail(row)">
            {{ row.contract_no || '—' }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="counterparty_name" label="相对方" width="140" />
      <el-table-column prop="amount" label="金额" width="120">
        <template #default="{ row }">¥{{ row.amount?.toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="110">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="到期日" width="110">
        <template #default="{ row }">
          <span :class="endDateCellClass()">{{ formatDate(row.end_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><StatusTag :status="row.status" /></template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
          <el-button link @click="openApprovalHistory(row, $event)">审批历史</el-button>
          <el-button link @click="openReviewHistory(row, $event)">评审历史</el-button>
          <el-button
            v-if="rowCanDelete(row)"
            link
            type="danger"
            @click="deleteDraft(row, $event)"
          >
            删除
          </el-button>
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
.bucket-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.date-warning {
  color: #e6a23c;
  font-weight: 500;
}

.date-danger {
  color: #f56c6c;
  font-weight: 500;
}
</style>
