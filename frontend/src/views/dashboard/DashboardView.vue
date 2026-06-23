<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { contractsApi } from '@/api/contracts'
import { canAccessRoute } from '@/router/permissions'
import { useAuthStore } from '@/stores/auth'
import type { DashboardBucketItem, DashboardData } from '@/types/models'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const data = ref<DashboardData>({
  stats: {
    total: 0,
    pending_approval: 0,
    executing_count: 0,
    expiring_soon_count: 0,
    expired_count: 0,
  },
  executing: [],
  expiring_soon: [],
  expired: [],
})

const stats = computed(() => data.value.stats ?? {})

const heroCount = computed(() => {
  if (canAccessRoute(auth.role, 'approvals')) return stats.value.pending_approval ?? 0
  if (['legal', 'finance', 'executive'].includes(auth.role)) return stats.value.pending_approval ?? 0
  return stats.value.pending_approval ?? 0
})

const heroLabel = computed(() => {
  if (canAccessRoute(auth.role, 'approvals')) return '项待办审批'
  if (['legal', 'finance', 'executive'].includes(auth.role)) return '项合同待处理'
  if (canAccessRoute(auth.role, 'create')) return '份草稿待提交'
  return '项待关注'
})

const heroAction = computed(() => {
  if (canAccessRoute(auth.role, 'approvals') && (stats.value.pending_approval ?? 0) > 0) {
    return { label: '处理待办审批', route: 'approvals' }
  }
  if (['legal', 'finance', 'executive'].includes(auth.role)) {
    return { label: '前往评审中心', route: 'review-center' }
  }
  if (canAccessRoute(auth.role, 'create')) {
    return { label: '新建合同', route: 'create' }
  }
  return { label: '查看合同列表', route: 'contracts' }
})

onMounted(async () => {
  try {
    data.value = await contractsApi.dashboard()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function go(name: string, query?: Record<string, string>) {
  router.push({ name, query })
}

function goPendingStat() {
  go('contracts', { status: 'pending', scope: 'all' })
}

function goHero() {
  go(heroAction.value.route)
}

function goExecutingStat() {
  go('contracts', { bucket: 'executing', scope: 'all' })
}

function goExpiringStat() {
  go('contracts', { bucket: 'expiring_soon', scope: 'all' })
}

function goDetail(row: DashboardBucketItem) {
  router.push({ name: 'contract-detail', params: { id: String(row.id) } })
}

function formatAmount(amount?: number) {
  if (amount == null) return '—'
  return `¥ ${amount.toLocaleString()}`
}
</script>

<template>
  <div v-loading="loading" class="page-card dashboard">
    <el-card shadow="never" class="hero-card">
      <div class="hero-inner">
        <div>
          <p class="hero-greeting">您好，{{ auth.displayName }}</p>
          <p class="hero-stat">
            您有 <strong>{{ heroCount }}</strong> {{ heroLabel }}
          </p>
        </div>
        <el-button type="primary" size="large" @click="goHero">{{ heroAction.label }}</el-button>
      </div>
    </el-card>

    <el-row :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card" @click="go('contracts')">
          <div class="stat-label">合同总数</div>
          <div class="stat-value">{{ stats.total ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card warn" @click="goPendingStat">
          <div class="stat-label">待审批</div>
          <div class="stat-value">{{ stats.pending_approval ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card primary" @click="goExecutingStat">
          <div class="stat-label">执行中</div>
          <div class="stat-value">{{ stats.executing_count ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card danger" @click="goExpiringStat">
          <div class="stat-label">即将到期 (≤30天)</div>
          <div class="stat-value">{{ stats.expiring_soon_count ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="kanban">
      <el-col :xs="24" :md="8">
        <div class="kanban-col">
          <div class="kanban-title">执行中 <span class="count">{{ data.executing?.length ?? 0 }}</span></div>
          <el-card
            v-for="item in data.executing ?? []"
            :key="item.id"
            shadow="hover"
            class="kanban-card"
            @click="goDetail(item)"
          >
            <div class="kc-title">{{ item.contract_no }} {{ item.title }}</div>
            <div class="kc-meta">
              <span>相对方：{{ item.counterparty_name }}</span>
              <span v-if="item.end_date">交付：{{ item.end_date }}</span>
            </div>
            <div class="kc-amount">{{ formatAmount(item.amount) }}</div>
          </el-card>
          <el-empty v-if="!(data.executing?.length)" description="暂无执行中合同" :image-size="64">
            <el-button @click="go('contracts')">查看合同列表</el-button>
          </el-empty>
        </div>
      </el-col>
      <el-col :xs="24" :md="8">
        <div class="kanban-col">
          <div class="kanban-title warn">即将到期 <span class="count">{{ data.expiring_soon?.length ?? 0 }}</span></div>
          <el-card
            v-for="item in data.expiring_soon ?? []"
            :key="item.id"
            shadow="hover"
            class="kanban-card border-warn"
            @click="goDetail(item)"
          >
            <div class="kc-title">{{ item.contract_no }} {{ item.title }}</div>
            <div class="kc-meta">
              <span>相对方：{{ item.counterparty_name }}</span>
              <span v-if="item.end_date">到期：{{ item.end_date }}</span>
            </div>
            <div class="kc-amount">{{ formatAmount(item.amount) }}</div>
          </el-card>
          <el-empty v-if="!(data.expiring_soon?.length)" description="暂无即将到期合同" :image-size="64" />
        </div>
      </el-col>
      <el-col :xs="24" :md="8">
        <div class="kanban-col">
          <div class="kanban-title danger">已到期 <span class="count">{{ data.expired?.length ?? 0 }}</span></div>
          <el-card
            v-for="item in data.expired ?? []"
            :key="item.id"
            shadow="hover"
            class="kanban-card border-danger"
            @click="goDetail(item)"
          >
            <div class="kc-title">{{ item.contract_no }} {{ item.title }}</div>
            <div class="kc-meta">
              <span>相对方：{{ item.counterparty_name }}</span>
              <span v-if="item.end_date">到期：{{ item.end_date }}</span>
            </div>
            <div class="kc-amount">{{ formatAmount(item.amount) }}</div>
          </el-card>
          <el-empty v-if="!(data.expired?.length)" description="暂无已到期合同" :image-size="64" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard {
  padding-bottom: 24px;
}
.hero-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #eff6ff 0%, #f9fafb 100%);
  border: 1px solid #dbeafe;
}
.hero-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.hero-greeting {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}
.hero-stat {
  margin: 4px 0 0;
  font-size: 20px;
  color: #111827;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  cursor: pointer;
  transition: transform 0.15s ease;
  margin-bottom: 12px;
}
.stat-card:hover {
  transform: translateY(-2px);
}
.stat-card.warn .stat-value {
  color: #d97706;
}
.stat-card.primary .stat-value {
  color: #1d4ed8;
}
.stat-card.danger .stat-value {
  color: #dc2626;
}
.stat-label {
  color: #6b7280;
  font-size: 13px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
  color: #111827;
}
.kanban-col {
  min-height: 200px;
}
.kanban-title {
  font-weight: 600;
  margin-bottom: 12px;
  font-size: 14px;
}
.kanban-title.warn {
  color: #d97706;
}
.kanban-title.danger {
  color: #dc2626;
}
.kanban-title .count {
  font-weight: 400;
  color: #9ca3af;
  margin-left: 4px;
}
.kanban-card {
  cursor: pointer;
  margin-bottom: 10px;
}
.kanban-card.border-warn {
  border-left: 3px solid #f59e0b;
}
.kanban-card.border-danger {
  border-left: 3px solid #ef4444;
}
.kc-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.kc-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #6b7280;
}
.kc-amount {
  margin-top: 8px;
  font-weight: 600;
  color: #1d4ed8;
}
</style>
