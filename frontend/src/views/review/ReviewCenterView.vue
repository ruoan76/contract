<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { reviewsApi } from '@/api/reviews'
import { contractsApi } from '@/api/contracts'
import type { Contract } from '@/types/models'
import { formatContractOptionLabel } from '@/utils/contractLabel'
import { flowTypeLabel, reviewActionLabel, reviewRoleLabel } from '@/utils/enumLabels'
import { formatDateTime } from '@/utils/formatDate'

interface PendingItem {
  contract_id: number
  contract_no?: string
  title?: string
  flow_type?: string
  pending_roles?: string[]
}

interface ReviewOpinion {
  id?: number
  role?: string
  action?: string
  comment?: string
  reviewer_name?: string
  created_at?: string
}

const router = useRouter()
const route = useRoute()
const centerTab = ref('pending')
const loading = ref(true)
const pendingItems = ref<PendingItem[]>([])
const roleFilter = ref('')

const loadingHistory = ref(false)
const contracts = ref<Contract[]>([])
const selectedId = ref<number | null>(null)
const opinions = ref<ReviewOpinion[]>([])

const pendingCount = computed(() => pendingItems.value.length)

async function loadPending() {
  loading.value = true
  try {
    const res = await reviewsApi.pending(roleFilter.value || undefined)
    pendingItems.value = (res.items || []) as PendingItem[]
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadContracts() {
  try {
    const res = await contractsApi.list({ page: 1, page_size: 100 })
    contracts.value = res.items || []
    const q = route.query.contractId
    const fromQuery = q ? Number(q) : 0
    if (fromQuery && contracts.value.some((c) => c.id === fromQuery)) {
      selectedId.value = fromQuery
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadHistory() {
  if (!selectedId.value) {
    opinions.value = []
    return
  }
  loadingHistory.value = true
  try {
    const res = await reviewsApi.history(selectedId.value)
    opinions.value = (res.opinions || []) as ReviewOpinion[]
  } catch (e) {
    opinions.value = []
  } finally {
    loadingHistory.value = false
  }
}

onMounted(async () => {
  if (route.query.tab === 'history') centerTab.value = 'history'
  await loadPending()
  await loadContracts()
  await loadHistory()
})

watch(roleFilter, loadPending)
watch(selectedId, loadHistory)
watch(centerTab, (tab) => {
  if (tab === 'history') loadHistory()
})

function formatPendingRoles(roles?: string[]) {
  if (!roles?.length) return '—'
  return roles.map((r) => reviewRoleLabel(r)).join('、')
}

function openWorkspace(row: PendingItem) {
  router.push({ name: 'review-workspace', params: { id: row.contract_id } })
}

function openDetail() {
  if (!selectedId.value) return
  router.push({ name: 'contract-detail', params: { id: selectedId.value } })
}

function formatRole(role?: string) {
  return reviewRoleLabel(role)
}

function formatAction(action?: string) {
  return reviewActionLabel(action)
}
</script>

<template>
  <div class="page-card">
    <el-tabs v-model="centerTab">
      <el-tab-pane :label="`待评审 (${pendingCount})`" name="pending">
        <div class="tab-toolbar">
          <el-select v-model="roleFilter" placeholder="全部角色" clearable style="width: 140px">
            <el-option label="法务" value="legal" />
            <el-option label="财务" value="finance" />
            <el-option label="高管" value="executive" />
          </el-select>
        </div>
        <el-table v-loading="loading" :data="pendingItems" stripe>
          <el-table-column label="合同编号" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.contract_no || '—' }}</template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column label="流程" width="120">
            <template #default="{ row }">{{ flowTypeLabel(row.flow_type) }}</template>
          </el-table-column>
          <el-table-column label="待办角色" width="140">
            <template #default="{ row }">
              {{ formatPendingRoles(row.pending_roles) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="openWorkspace(row)">进入工作台</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && !pendingItems.length" description="暂无待评审合同" />
      </el-tab-pane>

      <el-tab-pane label="评审历史" name="history">
        <div class="tab-toolbar">
          <el-select
            v-model="selectedId"
            filterable
            placeholder="选择合同"
            style="width: 320px"
          >
            <el-option
              v-for="c in contracts"
              :key="c.id"
              :label="formatContractOptionLabel(c)"
              :value="c.id"
            />
          </el-select>
          <el-button :disabled="!selectedId" @click="openDetail">合同详情</el-button>
          <el-button type="primary" :disabled="!selectedId" @click="openWorkspace({ contract_id: selectedId! })">
            进入评审工作台
          </el-button>
        </div>
        <div v-loading="loadingHistory">
          <el-empty v-if="!selectedId" description="请选择合同查看评审记录" />
          <el-empty v-else-if="!opinions.length" description="该合同暂无评审意见" />
          <template v-else>
            <p class="summary">合同 #{{ selectedId }} · 共 {{ opinions.length }} 条评审记录</p>
            <el-timeline>
              <el-timeline-item
                v-for="(item, idx) in opinions"
                :key="item.id ?? idx"
                :timestamp="formatDateTime(item.created_at)"
                placement="top"
              >
                <div class="opinion-card">
                  <div class="opinion-head">
                    <strong>{{ formatRole(item.role) }}</strong>
                    <el-tag size="small" :type="item.action === 'approve' ? 'success' : 'warning'">
                      {{ formatAction(item.action) }}
                    </el-tag>
                  </div>
                  <p v-if="item.reviewer_name" class="reviewer">评审人：{{ item.reviewer_name }}</p>
                  <p v-if="item.comment" class="comment">{{ item.comment }}</p>
                </div>
              </el-timeline-item>
            </el-timeline>
          </template>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.tab-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.summary {
  color: #6b7280;
  margin-bottom: 16px;
}
.opinion-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.reviewer {
  color: #6b7280;
  font-size: 13px;
  margin: 4px 0 0;
}
.comment {
  margin: 6px 0 0;
  color: #374151;
}
</style>
