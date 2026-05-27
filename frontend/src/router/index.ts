import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { canAccessRoute } from './permissions'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/api/client'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/dashboard/DashboardView.vue'),
          meta: { title: '状态看板' },
        },
        {
          path: 'messages',
          name: 'messages',
          component: () => import('@/views/messages/MessagesView.vue'),
          meta: { title: '消息中心' },
        },
        {
          path: 'create',
          name: 'create',
          component: () => import('@/views/contract/CreateContractView.vue'),
          meta: { title: '新建合同' },
        },
        {
          path: 'contracts',
          name: 'contracts',
          component: () => import('@/views/contract/ContractListView.vue'),
          meta: { title: '合同列表' },
        },
        {
          path: 'contracts/:id',
          name: 'contract-detail',
          component: () => import('@/views/contract/ContractDetailView.vue'),
          meta: { title: '合同详情', drilldown: true },
        },
        {
          path: 'contracts/:id/approval-history',
          name: 'approval-history',
          component: () => import('@/views/contract/ApprovalHistoryView.vue'),
          meta: { title: '审批历史', drilldown: true },
        },
        {
          path: 'contracts/:id/revision',
          name: 'revision-workspace',
          component: () => import('@/views/contract/RevisionWorkspaceView.vue'),
          meta: { title: '修订工作台', drilldown: true },
        },
        {
          path: 'templates',
          name: 'templates',
          component: () => import('@/views/template/TemplatesView.vue'),
          meta: { title: '模板管理' },
        },
        {
          path: 'ai-review/:id?',
          name: 'ai-review',
          component: () => import('@/views/ai/AiReviewView.vue'),
          meta: { title: '审查报告' },
        },
        {
          path: 'contracts/:id/clause-compare',
          name: 'clause-compare',
          component: () => import('@/views/ai/ClauseCompareView.vue'),
          meta: { title: '条款比对', drilldown: true },
        },
        {
          path: 'clause-compare',
          name: 'clause-compare-hub',
          component: () => import('@/views/ai/ClauseCompareHubView.vue'),
          meta: { title: '条款比对' },
        },
        {
          path: 'review-center',
          name: 'review-center',
          component: () => import('@/views/review/ReviewCenterView.vue'),
          meta: { title: '评审中心' },
        },
        {
          path: 'review-workspace/:id?',
          name: 'review-workspace',
          component: () => import('@/views/review/ReviewWorkspaceView.vue'),
          meta: { title: '评审工作台' },
        },
        {
          path: 'review-history',
          name: 'review-history',
          component: () => import('@/views/review/ReviewHistoryView.vue'),
          meta: { title: '评审历史' },
        },
        {
          path: 'approvals',
          name: 'approvals',
          component: () => import('@/views/approval/ApprovalsView.vue'),
          meta: { title: '待办审批' },
        },
        {
          path: 'seal',
          name: 'seal',
          component: () => import('@/views/seal/SealView.vue'),
          meta: { title: '用印管理' },
        },
        {
          path: 'archives',
          name: 'archives',
          component: () => import('@/views/archive/ArchivesView.vue'),
          meta: { title: '归档台账' },
        },
        {
          path: 'counterparties',
          name: 'counterparties',
          component: () => import('@/views/counterparty/CounterpartiesView.vue'),
          meta: { title: '相对方管理' },
        },
        {
          path: 'config',
          name: 'config',
          component: () => import('@/views/system/ConfigView.vue'),
          meta: { title: '审批配置' },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/system/UsersView.vue'),
          meta: { title: '用户管理' },
        },
        {
          path: 'audit',
          name: 'audit',
          component: () => import('@/views/system/AuditView.vue'),
          meta: { title: '审计日志' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  if (import.meta.env.VITE_SKIP_AUTH === '1' && !to.meta.public) {
    try {
      await auth.ensureAuth()
    } catch (e) {
      console.error('演示登录失败', e)
    }
    next()
    return
  }
  if (to.meta.public) {
    next()
    return
  }
  if (!auth.user && !getToken()) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }
  if (!auth.user) {
    try {
      await auth.initAuth()
    } catch {
      /* 后端未启动时仍允许进入，页面内提示 */
    }
  }
  const name = to.name as string | undefined
  if (name && !canAccessRoute(auth.role, name)) {
    next({ name: 'dashboard' })
    return
  }
  next()
})

export default router
