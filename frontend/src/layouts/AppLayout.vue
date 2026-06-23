<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Odometer,
  Bell,
  EditPen,
  Document,
  Files,
  MagicStick,
  CopyDocument,
  View,
  Checked,
  Stamp,
  FolderOpened,
  OfficeBuilding,
  Setting,
  Cpu,
  User,
  List,
  ArrowDown,
} from '@element-plus/icons-vue'
import { NAV_ITEMS, ROUTE_TITLES } from '@/router/nav'
import { canAccessRoute } from '@/router/permissions'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/api/client'
import { isDemoNav, isSkipAuth } from '@/utils/appEnv'
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
  Checked,
  Stamp,
  FolderOpened,
  OfficeBuilding,
  Setting,
  Cpu,
  User,
  List,
}

const demoRoleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({
  value: value as AppRole,
  label,
}))

const navGroups = computed(() => {
  const groups = new Map<string, Array<(typeof NAV_ITEMS)[number] & { restricted?: boolean }>>()
  NAV_ITEMS.forEach((item) => {
    const allowed = canAccessRoute(auth.role, item.name)
    if (!isDemoNav && !allowed) return
    if (!groups.has(item.group)) groups.set(item.group, [])
    groups.get(item.group)!.push({ ...item, restricted: isDemoNav && !allowed })
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

onMounted(async () => {
  try {
    if (isSkipAuth || !getToken() || !auth.user) {
      await auth.ensureAuth()
    } else {
      await auth.initAuth()
    }
  } catch (e) {
    console.error('初始化认证失败', e)
  }
})

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push({ name: 'login' })
}

async function handleDemoRoleSwitch(next: AppRole) {
  if (next === auth.role) return
  try {
    await auth.switchRole(next)
    ElMessage.success(`已切换为：${ROLE_LABELS[next] || next}`)
    await router.push({ name: 'dashboard' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '切换角色失败')
  }
}

/** 侧栏选中：演示模式曾关闭 router 导致无法跳转，统一由此处理 */
function handleNavSelect(index: string) {
  const item = NAV_ITEMS.find((n) => n.path === index)
  if (!item) return
  if (!canAccessRoute(auth.role, item.name)) {
    ElMessage.warning(`当前角色（${auth.roleLabel}）无权访问「${item.title}」`)
    return
  }
  if (route.name === item.name) return
  void router.push({ name: item.name })
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
        background-color="#111827"
        text-color="#d1d5db"
        active-text-color="#60a5fa"
        class="sidebar-menu"
        @select="handleNavSelect"
      >
        <el-menu-item-group
          v-for="[group, items] in navGroups"
          :key="group"
          :title="group"
        >
          <el-menu-item
            v-for="item in items"
            :key="item.name"
            :index="item.path"
            :class="{ 'nav-restricted': item.restricted }"
          >
            <el-icon><component :is="iconMap[item.icon || 'Document']" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header" height="60px">
        <div class="header-left">
          <h1 class="header-title">{{ pageTitle }}</h1>
          <span v-if="breadcrumb" class="header-breadcrumb">{{ breadcrumb }}</span>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="(cmd: string) => (cmd === 'logout' ? handleLogout() : handleDemoRoleSwitch(cmd as AppRole))">
            <span class="user-menu-trigger-wrap">
            <button type="button" class="user-menu-trigger">
              <el-avatar size="small">{{ auth.displayName.slice(0, 1) }}</el-avatar>
              <span class="user-menu-text">
                <span class="user-menu-name">{{ auth.displayName }}</span>
                <span class="user-menu-role">{{ auth.roleLabel }}</span>
              </span>
              <el-icon class="user-menu-caret"><ArrowDown /></el-icon>
            </button>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <span class="profile-summary">
                    <span class="profile-summary-line">{{ auth.user?.username }}</span>
                    <span v-if="auth.user?.department" class="muted">{{ auth.user.department }}</span>
                  </span>
                </el-dropdown-item>
                <template v-if="isSkipAuth">
                  <el-dropdown-item divided disabled>演示切换角色</el-dropdown-item>
                  <el-dropdown-item
                    v-for="opt in demoRoleOptions"
                    :key="opt.value"
                    :command="opt.value"
                    :disabled="opt.value === auth.role"
                  >
                    {{ opt.label }}
                  </el-dropdown-item>
                </template>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
  overflow-y: auto;
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

.sidebar-menu :deep(.el-menu-item-group__title) {
  padding: 8px 20px 2px;
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.nav-restricted) {
  opacity: 0.45;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.user-menu-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.user-menu-trigger:hover {
  border-color: #d1d5db;
}

.user-menu-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
  max-width: 140px;
}

.user-menu-name {
  font-size: 13px;
  font-weight: 500;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.user-menu-role {
  font-size: 11px;
  color: #6b7280;
}

.user-menu-caret {
  color: #9ca3af;
  font-size: 12px;
}

.profile-summary {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
  cursor: default;
}

.profile-summary .muted {
  font-size: 12px;
  color: #6b7280;
}

.user-menu-trigger-wrap {
  display: inline-flex;
  vertical-align: middle;
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
