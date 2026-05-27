import type { Contract } from '@/types/models'
import type { AppRole } from '@/types/models'

export interface LifecycleStage {
  key: string
  label: string
}

export const LIFECYCLE_STAGES: LifecycleStage[] = [
  { key: 'draft', label: '起草' },
  { key: 'pending', label: '审批/评审' },
  { key: 'approved', label: '已通过' },
  { key: 'sealed', label: '已用印' },
  { key: 'archived', label: '已归档' },
]

/** 根据合同主状态计算生命周期当前步（0-based） */
export function lifecycleActiveIndex(status?: string): number {
  const s = status || 'draft'
  if (s === 'draft' || s === 'returned') return 0
  if (s === 'pending') return 1
  if (s === 'approved' || s === 'seal_pending') return 2
  if (s === 'sealed' || s === 'signed' || s === 'executing') return 3
  if (s === 'archived' || s === 'terminated' || s === 'void') return 4
  return 1
}

export interface NextAction {
  label: string
  route: string
  params?: Record<string, string>
  query?: Record<string, string>
}

/** 根据状态与角色推荐下一步操作 */
export function suggestNextAction(
  contract: Contract | null,
  role: AppRole,
): NextAction | null {
  if (!contract?.id) return null
  const id = String(contract.id)
  const status = contract.status

  if (status === 'draft' || status === 'returned') {
    if (role === 'drafter' || role === 'admin') {
      return status === 'returned'
        ? { label: '去修订工作台', route: 'revision-workspace', params: { id } }
        : { label: '提交审批', route: 'create' }
    }
    return null
  }

  if (status === 'pending') {
    if (role === 'approver' || role === 'admin') {
      return { label: '去待办审批', route: 'approvals' }
    }
    if (['legal', 'finance', 'executive'].includes(role)) {
      return { label: '去评审工作台', route: 'review-workspace', params: { id } }
    }
    return { label: '查看 AI 审查报告', route: 'ai-review', params: { id } }
  }

  if (status === 'approved' || contract.approval_status === 'seal_pending') {
    if (role === 'archivist' || role === 'legal' || role === 'admin') {
      return { label: '去用印管理', route: 'seal' }
    }
  }

  if (status === 'sealed' || status === 'signed') {
    if (role === 'archivist' || role === 'admin') {
      return { label: '去归档台账', route: 'archives' }
    }
  }

  return { label: '查看审批历史', route: 'approval-history', params: { id } }
}
