<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import {
  Odometer,
  Bell,
  EditPen,
  Document,
  Files,
  MagicStick,
  CopyDocument,
  View,
  Edit,
  Clock,
  Checked,
  Stamp,
  FolderOpened,
  OfficeBuilding,
  Setting,
  User,
  List,
} from '@element-plus/icons-vue'
import { NAV_ITEMS, ROUTE_TITLES } from '@/router/nav'
import { canAccessRoute } from '@/router/permissions'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/api/client'
import { ROLE_LABELS } from '@/api/config'
import type { AppRole } from '@/types/models'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const iconMap: Record<string, object> = {
  Odometer,
  Bell,
  EditPen,
  Document,
  Files,
  MagicStick,
  CopyDocument,
  View,
  Edit,
  Clock,
  Checked,
  Stamp,
  FolderOpened,
  OfficeBuilding,
  Setting,
  User,
  List,
}

const navGroups = computed(() => {
  const groups = new Map<string, Array<(typeof NAV_ITEMS)[number] & { restricted?: boolean }>>()
  NAV_ITEMS.forEach((item) => {
    const allowed = canAccessRoute(auth.role, item.name)
    if (!groups.has(item.group)) groups.set(item.group, [])
    groups.get(item.group)!.push({ ...item, restricted: !allowed })
  })
  return [...groups.entries()].filter(([, items]) => items.length > 0)
})

const pageTitle = computed(() => {
  const name = route.name as string
  return ROUTE_TITLES[name]?.[0] || (route.meta.title as string) || '合同平台'
})

const breadcrumb = computed(() => {
  const name = route.name as string
  return ROUTE_TITLES[name]?.[1] || ''
})

const activeMenu = computed(() => {
  if (route.meta.drilldown) return ''
  return route.path
})

const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))

async function onRoleChange(role: AppRole) {
  await auth.switchRole(role)
  router.push({ name: 'dashboard' })
}

onMounted(async () => {
  try {
    if (import.meta.env.VITE_SKIP_AUTH !== '1' && (!getToken() || !auth.user)) {
      await auth.initAuth()
    }
  } catch (e) {
    console.error('初始化认证失败', e)
  }
})

function goCreate() {
  router.push({ name: 'create' })
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="sidebar">
      <div class="sidebar-brand">
        <div class="logo">合</div>
        <div>
          <div class="brand-title">合同审批平台</div>
          <div class="brand-sub">Contract Lifecycle</div>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#111827"
        text-color="#d1d5db"
        active-text-color="#60a5fa"
        class="sidebar-menu"
      >
        <template v-for="[group, items] in navGroups" :key="group">
          <div class="nav-group-title">{{ group }}</div>
          <el-menu-item
            v-for="item in items"
            :key="item.name"
            :index="item.path"
            :class="{ 'nav-restricted': item.restricted }"
          >
            <el-icon><component :is="iconMap[item.icon || 'Document']" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
      <div class="sidebar-footer">
        <el-avatar size="small">{{ auth.displayName.slice(0, 1) }}</el-avatar>
        <div>
          <div class="user-name">{{ auth.displayName }}</div>
          <div class="user-role">{{ auth.roleLabel }}</div>
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="app-header" height="60px">
        <div class="header-left">
          <h1 class="header-title">{{ pageTitle }}</h1>
          <span v-if="breadcrumb" class="header-breadcrumb">{{ breadcrumb }}</span>
        </div>
        <div class="header-right">
          <span class="role-switch-label">演示角色</span>
          <el-select
            :model-value="auth.role"
            placeholder="切换角色"
            style="width: 160px"
            @change="onRoleChange"
          >
            <el-option
              v-for="opt in roleOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-button type="primary" @click="goCreate">新建合同</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.sidebar {
  background: #111827;
  color: #fff;
  display: flex;
  flex-direction: column;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #374151;
}

.logo {
  width: 36px;
  height: 36px;
  background: var(--primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.brand-title {
  font-size: 15px;
  font-weight: 600;
}

.brand-sub {
  font-size: 11px;
  color: #9ca3af;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 38px;
  line-height: 38px;
  margin-bottom: 0;
  padding-left: 16px !important;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  margin-right: 8px;
  font-size: 16px;
}

.nav-group-title {
  padding: 8px 20px 2px;
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.nav-restricted) {
  opacity: 0.45;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #374151;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
}

.user-role {
  font-size: 11px;
  color: #9ca3af;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.role-switch-label {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 24px;
  gap: 16px;
  overflow: visible;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-breadcrumb {
  font-size: 12px;
  color: #6b7280;
}

.app-main {
  padding: 24px;
  background: #f9fafb;
}
</style>
