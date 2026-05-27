import type { AppRole } from '@/types/models'

/** 各角色可见路由 name（正式环境 RBAC，见 permission-matrix） */
export const ROLE_VISIBLE_ROUTES: Record<AppRole, string[]> = {
  drafter: [
    'dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review',
    'archives', 'counterparties', 'revision-workspace', 'contract-detail',
  ],
  approver: [
    'dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review',
    'clause-compare-hub', 'clause-compare', 'approvals', 'archives', 'review-center', 'review-workspace',
    'review-history', 'counterparties', 'config', 'contract-detail', 'approval-history',
  ],
  legal: [
    'dashboard', 'contracts', 'ai-review', 'clause-compare-hub', 'clause-compare', 'seal', 'archives',
    'review-center', 'review-workspace', 'review-history', 'templates', 'contract-detail',
  ],
  finance: [
    'dashboard', 'contracts', 'ai-review', 'clause-compare-hub', 'clause-compare', 'archives',
    'review-center', 'review-workspace', 'review-history', 'contract-detail',
  ],
  executive: [
    'dashboard', 'contracts', 'ai-review', 'clause-compare-hub', 'clause-compare', 'archives',
    'review-center', 'review-workspace', 'review-history', 'contract-detail',
  ],
  archivist: ['dashboard', 'contracts', 'seal', 'archives', 'contract-detail'],
  admin: [
    'dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review',
    'clause-compare-hub', 'clause-compare', 'review-center', 'review-workspace', 'review-history',
    'approvals', 'seal', 'archives', 'counterparties', 'config', 'users', 'audit',
    'contract-detail', 'approval-history', 'revision-workspace',
  ],
}

export function canAccessRoute(role: AppRole, routeName?: string | null): boolean {
  if (!routeName) return true
  const allowed = ROLE_VISIBLE_ROUTES[role] || []
  return allowed.includes(routeName)
}
