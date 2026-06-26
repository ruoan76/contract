<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractsApi } from '@/api/contracts'
import { reviewsApi } from '@/api/reviews'
import type { Contract } from '@/types/models'
import { reviewActionLabel, reviewRoleLabel } from '@/utils/enumLabels'
import { formatDateTime } from '@/utils/formatDate'

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
const loadingContracts = ref(true)
const loadingHistory = ref(false)
const contracts = ref<Contract[]>([])
const selectedId = ref<number | null>(null)
const opinions = ref<ReviewOpinion[]>([])

async function loadContracts() {
  loadingContracts.value = true
  try {
    const res = await contractsApi.list({ page: 1, page_size: 100 })
    contracts.value = res.items || []
    if (!selectedId.value && contracts.value.length) {
      const q = route.query.contractId
      const fromQuery = q ? Number(q) : 0
      const match = fromQuery && contracts.value.some((c) => c.id === fromQuery)
      selectedId.value = match ? fromQuery : contracts.value[0].id
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载合同列表失败')
  } finally {
    loadingContracts.value = false
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
    console.error(e)
    opinions.value = []
    ElMessage.error('加载评审历史失败')
  } finally {
    loadingHistory.value = false
  }
}

onMounted(async () => {
  await loadContracts()
  await loadHistory()
})

watch(selectedId, loadHistory)

function openWorkspace() {
  if (!selectedId.value) return
  router.push({ name: 'review-workspace', params: { id: selectedId.value } })
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
  <div class="review-history-page">
    <div class="page-card selector-card">
      <div class="page-toolbar">
        <h2>评审历史</h2>
        <div class="toolbar-actions">
          <el-select
            v-model="selectedId"
            filterable
            placeholder="选择合同"
            style="width: 320px"
            :loading="loadingContracts"
          >
            <el-option
              v-for="c in contracts"
              :key="c.id"
              :label="`#${c.id} ${c.title}`"
              :value="c.id"
            />
          </el-select>
          <el-button :disabled="!selectedId" @click="openDetail">合同详情</el-button>
          <el-button type="primary" :disabled="!selectedId" @click="openWorkspace">进入评审工作台</el-button>
        </div>
      </div>
    </div>

    <div v-loading="loadingHistory" class="page-card">
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
  </div>
</template>

<style scoped>
.review-history-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.summary {
  color: #6b7280;
  margin-bottom: 16px;
}
.opinion-card {
  padding: 4px 0;
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
